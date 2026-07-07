#!/usr/bin/env python3
"""
collect_panel_data.py

Collects quarterly panel data for the 14 confirmed Tier A repos.
Panel window: 2023 Q1 – 2025 Q4 (12 quarters).

Outputs (all in same directory as this script):
  08_panel_data.csv          — long format: one row per repo × quarter
  08_contributor_history.csv — repo × quarter × author_login × commit_count
  08_collection_log.txt      — timestamped progress and error log

Metrics per (repo, quarter):
  commits (human), commits_bot,
  pr_count_total, pr_count_refactor (label OR title match),
  pr_count_refactor_label, pr_count_refactor_title, pr_refactor_ratio,
  pr_review_latency_median, pr_review_latency_p75,
  issues_opened, issues_closed, issue_backlog_delta,
  contributor_count, contributor_turnover_frac, label_coverage_warn

Notes:
  - Code churn (additions/deletions) is NOT collected here: the
    stats/code_frequency endpoint returns HTTP 422 for repos of this size.
    Churn comes from local clones via collect_git_metrics.py.
  - contributor_turnover_frac = fraction of the previous quarter's human
    authors absent this quarter (bounded [0,1]). The paper's core-team
    turnover measure (Mockus 80% cumulative-commit threshold) is computed
    downstream from 08_contributor_history.csv.
  - Bot accounts (dependabot, renovate, github-actions, *[bot], ...) are
    excluded from author/contributor metrics and counted in commits_bot.

Usage:
  $env:GITHUB_TOKEN = "ghp_..."   # Windows PowerShell
  python collect_panel_data.py

Resume: already-collected repos are skipped automatically (all 12 quarters present).
"""

import csv
import json
import math
import os
import re
import ssl
import sys
import time
from collections import defaultdict
from datetime import datetime, timezone
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

# Windows consoles/redirects default to cp1252, which can't encode the
# arrows/checkmarks in log lines — force UTF-8 with replacement.
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

# ---------------------------------------------------------------------------
# SSL context — verified via certifi when available (Windows Python 3.13's
# system CA bundle is unreliable); only falls back to unverified if neither
# certifi nor the system bundle can be loaded.
# ---------------------------------------------------------------------------
# This machine sits behind a TLS-intercepting proxy/AV whose root cert
# fails Python 3.13's default VERIFY_X509_STRICT (Basic Constraints not
# marked critical). Chain verification still works with the system store
# once the strict flag is dropped — far better than CERT_NONE.
_SSL_CTX = ssl.create_default_context()
_SSL_CTX.verify_flags &= ~ssl.VERIFY_X509_STRICT

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

# (owner/repo, event_type)
# event_type: full_rewrite | migration | pivot | fuzzy | transition | control
TIER_A_REPOS = [
    ("PostHog/posthog",              "full_rewrite"),   # AI arch rebuilt twice
    ("Infisical/infisical",          "migration"),      # MongoDB → PostgreSQL
    ("dagger/dagger",                "full_rewrite"),   # Project Theseus Go rewrite
    ("triggerdotdev/trigger.dev",    "full_rewrite"),   # v3 rewrite
    ("appwrite/appwrite",            "full_rewrite"),   # v2.0 execution engine (right-censored?)
    ("airbytehq/airbyte",            "migration"),      # Python CDK v2
    ("zed-industries/zed",           "transition"),     # Full OSS transition Jan 2024 (left-censored pre-2024)
    ("LedgerHQ/ledger-live",         "migration"),      # monorepo → turborepo
    ("weaviate/weaviate",            "migration"),      # storage layer + gRPC client v4
    ("astral-sh/ruff",               "full_rewrite"),   # Rust rewrites of Python tools
    ("inngest/inngest",              "full_rewrite"),   # v1 → v2 SDK
    ("milvus-io/milvus",             "full_rewrite"),   # Python → Go+Rust v2.0
    ("tursodatabase/libsql",         "pivot"),          # ChiselStrike → Turso pivot
    ("qdrant/qdrant",                "fuzzy"),          # iterative storage engine evolution
]

QUARTERS = [
    ("2023-Q1", "2023-01-01T00:00:00Z", "2023-04-01T00:00:00Z"),
    ("2023-Q2", "2023-04-01T00:00:00Z", "2023-07-01T00:00:00Z"),
    ("2023-Q3", "2023-07-01T00:00:00Z", "2023-10-01T00:00:00Z"),
    ("2023-Q4", "2023-10-01T00:00:00Z", "2024-01-01T00:00:00Z"),
    ("2024-Q1", "2024-01-01T00:00:00Z", "2024-04-01T00:00:00Z"),
    ("2024-Q2", "2024-04-01T00:00:00Z", "2024-07-01T00:00:00Z"),
    ("2024-Q3", "2024-07-01T00:00:00Z", "2024-10-01T00:00:00Z"),
    ("2024-Q4", "2024-10-01T00:00:00Z", "2025-01-01T00:00:00Z"),
    ("2025-Q1", "2025-01-01T00:00:00Z", "2025-04-01T00:00:00Z"),
    ("2025-Q2", "2025-04-01T00:00:00Z", "2025-07-01T00:00:00Z"),
    ("2025-Q3", "2025-07-01T00:00:00Z", "2025-10-01T00:00:00Z"),
    ("2025-Q4", "2025-10-01T00:00:00Z", "2026-01-01T00:00:00Z"),
    # Extension 2026-07-07: two post-AI-adoption quarters (most adoption
    # dates land 2024-Q4..2025-Q4, so these carry the treatment effects).
    ("2026-Q1", "2026-01-01T00:00:00Z", "2026-04-01T00:00:00Z"),
    ("2026-Q2", "2026-04-01T00:00:00Z", "2026-07-01T00:00:00Z"),
]

PANEL_START  = "2023-01-01T00:00:00Z"
PANEL_END    = "2026-07-01T00:00:00Z"
PANEL_START_TS = 1672531200   # 2023-01-01 UTC unix
# BUGFIX 2026-07-05: this was 1735689600, which is 2025-01-01, not 2026-01-01.
# It silently discarded every PR merged and issue opened/closed in 2025.
# Cross-check: datetime.fromtimestamp(PANEL_END_TS, tz=UTC) is asserted below.
PANEL_END_TS   = 1782864000   # 2026-07-01 UTC unix

# This constant has burned us once — fail loudly if it ever drifts again.
assert datetime.fromtimestamp(PANEL_END_TS, tz=timezone.utc).strftime(
    "%Y-%m-%dT%H:%M:%SZ") == PANEL_END, "PANEL_END_TS does not match PANEL_END"
assert QUARTERS[-1][2] == PANEL_END, "last quarter must end at PANEL_END"

# Label substrings that identify a PR as refactor-type (case-insensitive)
REFACTOR_LABEL_PATTERNS = [
    "refactor", "cleanup", "clean-up", "migration", "migrate",
    "rewrite", "tech-debt", "technical-debt", "debt", "chore",
    "maintenance", "improvement", "architectural", "breaking-change",
    "breaking", "overhaul", "restructure", "rearchitect",
]

# Title patterns for refactor-type PRs. Most repos here label < 50% of PRs,
# so labels alone badly undercount (see label_coverage_warn). Deliberately
# narrower than the label list: no bare "chore"/"improvement", which in
# titles are dominated by dependency bumps and routine tweaks.
REFACTOR_TITLE_RE = re.compile(
    r"(^|\b)(refactor\w*|rewrite|rewrote|rewrit\w*|migrat\w*"
    r"|clean[- ]?up|overhaul\w*|restructur\w*|re-?architect\w*"
    r"|tech(nical)?[- ]debt|deprecat\w*)($|\b)",
    re.IGNORECASE,
)

# Bot detection: excluded from author/contributor metrics, counted separately.
KNOWN_BOT_LOGINS = {
    "dependabot", "dependabot-preview", "renovate", "renovate-bot",
    "github-actions", "github actions", "greenkeeper", "snyk-bot",
    "codecov", "codecov-commenter", "imgbot", "allcontributors",
    "pre-commit-ci", "semantic-release-bot", "mergify", "kodiakhq",
    "devin-ai-integration", "sweep-ai", "vercel", "netlify", "sfdc-lightning",
}

def _is_bot(login: str) -> bool:
    l = login.lower()
    if l.startswith("_name:"):
        l = l[len("_name:"):]
    l = l.strip()
    return (
        l.endswith("[bot]")
        or l in KNOWN_BOT_LOGINS
        or "dependabot" in l
        or "renovate" in l
        or "github-actions" in l
        or "github actions" in l
    )

OUT_DIR         = os.path.dirname(os.path.abspath(__file__))
PANEL_CSV       = os.path.join(OUT_DIR, "08_panel_data.csv")
CONTRIB_CSV     = os.path.join(OUT_DIR, "08_contributor_history.csv")
LOG_FILE        = os.path.join(OUT_DIR, "08_collection_log.txt")

def _load_dotenv():
    """Walk up from the script's directory to find a .env file and load it."""
    directory = os.path.dirname(os.path.abspath(__file__))
    for _ in range(5):  # search up to 5 levels up
        candidate = os.path.join(directory, ".env")
        if os.path.isfile(candidate):
            with open(candidate, encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith("#") or "=" not in line:
                        continue
                    key, _, value = line.partition("=")
                    key = key.strip()
                    value = value.strip().strip('"').strip("'")
                    if key and key not in os.environ:
                        os.environ[key] = value
            return
        parent = os.path.dirname(directory)
        if parent == directory:
            break
        directory = parent

_load_dotenv()

GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN", "")
BASE_URL     = "https://api.github.com"

PANEL_FIELDS = [
    "repo", "event_type", "quarter",
    "commits", "commits_bot",
    "pr_count_total", "pr_count_refactor",
    "pr_count_refactor_label", "pr_count_refactor_title",
    "pr_refactor_ratio",
    "pr_review_latency_median", "pr_review_latency_p75",
    "issues_opened", "issues_closed", "issue_backlog_delta",
    "contributor_count", "contributor_turnover_frac",
    "label_coverage_warn",
]

CONTRIB_FIELDS = ["repo", "quarter", "author_login", "commit_count"]

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

def log(msg: str):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] {msg}"
    print(line, flush=True)
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(line + "\n")

# ---------------------------------------------------------------------------
# GitHub API helpers
# ---------------------------------------------------------------------------

def _headers() -> dict:
    h = {
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "vibecoding-panel-collector/1.0",
    }
    if GITHUB_TOKEN:
        h["Authorization"] = f"Bearer {GITHUB_TOKEN}"
    return h


def _sleep_for_rate_limit(resp_headers: dict):
    remaining = resp_headers.get("X-RateLimit-Remaining", "100")
    reset_ts   = resp_headers.get("X-RateLimit-Reset")
    if int(remaining) < 50 and reset_ts:
        wait = max(0, int(reset_ts) - int(time.time())) + 5
        log(f"  [rate-limit] {remaining} req remaining — sleeping {wait}s until reset")
        time.sleep(wait)


def _get(url: str, call_sleep: float = 0.3, retries: int = 3):
    """
    Make a GET request and return (response_body_bytes, headers_dict).
    Handles 429/403 (rate limit), 202 (stats computing), and transient errors.
    Returns (None, None) after exhausting retries.
    """
    req = Request(url, headers=_headers())
    for attempt in range(retries):
        try:
            with urlopen(req, timeout=30, context=_SSL_CTX) as resp:
                headers = dict(resp.headers)
                body = resp.read()
                time.sleep(call_sleep)
                return body, headers
        except HTTPError as e:
            if e.code in (403, 429):
                _sleep_for_rate_limit(dict(e.headers))
                continue
            if e.code == 202:
                # Stats endpoint is computing — wait and retry
                wait = 10 * (attempt + 1)
                log(f"  [202 computing] retrying in {wait}s ...")
                time.sleep(wait)
                continue
            if e.code == 409:
                # Empty repo
                return b"[]", {}
            if e.code == 401:
                # Bad credentials must be fatal: continuing writes rows of
                # silent zeros into the panel (this happened 2026-07-05).
                log(f"  [401] GitHub token rejected — aborting run")
                raise SystemExit("FATAL: GITHUB_TOKEN is invalid or expired.")
            if e.code == 404:
                log(f"  [404] not found: {url}")
                return None, None
            log(f"  [HTTP {e.code}] {url}")
            return None, None
        except URLError as e:
            wait = 10 * (attempt + 1)
            log(f"  [network error] {e} — retrying in {wait}s")
            time.sleep(wait)
    log(f"  [gave up after {retries} attempts] {url}")
    return None, None


def _paginate(base_url: str, call_sleep: float = 0.3, stop_before_ts: float = None):
    """
    Yield all items from a paginated GitHub API endpoint.
    If stop_before_ts is given, stops when an item's 'updated_at' < stop_before_ts
    (used for PRs/issues to avoid fetching pre-panel history).
    """
    url = base_url + ("&" if "?" in base_url else "?") + "per_page=100&page=1"
    page = 1
    while url:
        body, headers = _get(url, call_sleep=call_sleep)
        if body is None:
            return
        items = json.loads(body) if body else []
        if not isinstance(items, list):
            # Sometimes API returns an object on error
            return
        if not items:
            return

        early_stop = False
        for item in items:
            updated = item.get("updated_at") or item.get("pushed_at")
            if stop_before_ts and updated:
                item_ts = _parse_iso(updated)
                if item_ts and item_ts < stop_before_ts:
                    early_stop = True
                    break
            yield item

        if early_stop:
            return

        # Parse next page from Link header
        link = headers.get("Link", "")
        next_url = None
        for part in link.split(","):
            part = part.strip()
            if 'rel="next"' in part:
                m = re.search(r"<([^>]+)>", part)
                if m:
                    next_url = m.group(1)
        url = next_url
        if url:
            page += 1

# ---------------------------------------------------------------------------
# Timestamp helpers
# ---------------------------------------------------------------------------

def _parse_iso(s: str):
    if not s:
        return None
    try:
        # Handle both "2023-01-15T12:00:00Z" and "2023-01-15T12:00:00+00:00"
        s = s.replace("Z", "+00:00")
        return datetime.fromisoformat(s).timestamp()
    except Exception:
        return None


def _ts_to_quarter(ts: float) -> str:
    dt = datetime.fromtimestamp(ts, tz=timezone.utc)
    q = (dt.month - 1) // 3 + 1
    return f"{dt.year}-Q{q}"


def _quarter_set() -> set:
    return {q for q, _, _ in QUARTERS}

# ---------------------------------------------------------------------------
# Statistics
# ---------------------------------------------------------------------------

def _median(values: list):
    if not values:
        return None
    s = sorted(values)
    n = len(s)
    mid = n // 2
    return s[mid] if n % 2 == 1 else (s[mid - 1] + s[mid]) / 2.0


def _percentile(values: list, p: float):
    if not values:
        return None
    s = sorted(values)
    idx = (len(s) - 1) * p / 100.0
    lo = int(idx)
    hi = min(lo + 1, len(s) - 1)
    return s[lo] + (idx - lo) * (s[hi] - s[lo])


def _round2(v):
    return round(v, 4) if v is not None else None

# ---------------------------------------------------------------------------
# Data collectors
# ---------------------------------------------------------------------------

def collect_commits_and_authors(repo: str,
                                skip_quarters: set = None) -> tuple[dict, dict, dict]:
    """
    Returns:
      commits_by_q:     {quarter: int | None}  — human (non-bot) commits
      bot_commits_by_q: {quarter: int | None}
      authors_by_q:     {quarter: dict | None} — human authors only
    None sentinels mean the quarter was already saved (skip_quarters).
    """
    skip_quarters = skip_quarters or set()
    commits_by_q = {}
    bot_commits_by_q = {}
    authors_by_q = {}

    for qname, since, until in QUARTERS:
        if qname in skip_quarters:
            commits_by_q[qname] = None   # sentinel: load from existing CSV
            bot_commits_by_q[qname] = None
            authors_by_q[qname] = None
            log(f"   {qname}: skipped (already collected)")
            continue

        url = (f"{BASE_URL}/repos/{repo}/commits"
               f"?since={since}&until={until}&per_page=100")
        count = 0
        bot_count = 0
        authors: dict[str, int] = defaultdict(int)

        for commit in _paginate(url, call_sleep=0.2):
            author_obj = commit.get("author") or {}
            login = author_obj.get("login") if author_obj else None
            if not login:
                commit_author = (commit.get("commit") or {}).get("author") or {}
                name = commit_author.get("name") or "unknown"
                login = f"_name:{name}"
            if _is_bot(login):
                bot_count += 1
                continue
            count += 1
            authors[login] += 1

        commits_by_q[qname] = count
        bot_commits_by_q[qname] = bot_count
        authors_by_q[qname] = dict(authors)
        log(f"   {qname}: {count:>5} human commits (+{bot_count} bot), "
            f"{len(authors):>3} authors")

    return commits_by_q, bot_commits_by_q, authors_by_q


def collect_prs(repo: str, needed_start_ts: float = None) -> dict:
    """
    Returns {quarter: {total, refactor_count, latencies: []}}
    Paginates closed PRs sorted by updated desc; stops before needed_start_ts
    (default: panel start). On resume runs only the not-yet-written quarters
    need PR data, so pagination can stop much earlier — a PR merged in a
    needed quarter always has updated_at >= its merge time.
    """
    # stop fetching once items are older than a month before the first
    # quarter we still need
    stop_ts = (needed_start_ts or PANEL_START_TS) - 30 * 86400

    url = (f"{BASE_URL}/repos/{repo}/pulls"
           f"?state=closed&sort=updated&direction=desc&per_page=100")

    q_data: dict[str, dict] = {
        q: {"total": 0, "refactor_label": 0, "refactor_title": 0,
            "refactor_any": 0, "latencies": [], "labeled_count": 0}
        for q, _, _ in QUARTERS
    }
    all_quarters = _quarter_set()

    for pr in _paginate(url, call_sleep=0.3, stop_before_ts=stop_ts):
        merged_at = pr.get("merged_at")
        if not merged_at:
            continue  # closed but not merged — skip

        merged_ts = _parse_iso(merged_at)
        if not merged_ts:
            continue
        if merged_ts < PANEL_START_TS or merged_ts >= PANEL_END_TS:
            continue

        q = _ts_to_quarter(merged_ts)
        if q not in all_quarters:
            continue

        q_data[q]["total"] += 1

        # Label matching
        labels = pr.get("labels") or []
        if labels:
            q_data[q]["labeled_count"] += 1
        label_names = [lbl.get("name", "").lower() for lbl in labels]
        by_label = any(
            pattern in name
            for name in label_names
            for pattern in REFACTOR_LABEL_PATTERNS
        )
        # Title matching (labels alone undercount where label coverage is low)
        by_title = bool(REFACTOR_TITLE_RE.search(pr.get("title") or ""))

        if by_label:
            q_data[q]["refactor_label"] += 1
        if by_title:
            q_data[q]["refactor_title"] += 1
        if by_label or by_title:
            q_data[q]["refactor_any"] += 1

        # Review latency
        created_ts = _parse_iso(pr.get("created_at"))
        if created_ts and merged_ts > created_ts:
            latency_days = (merged_ts - created_ts) / 86400.0
            q_data[q]["latencies"].append(latency_days)

    return q_data


def collect_issues(repo: str, needed_start_iso: str = None) -> dict:
    """
    Returns {quarter: {opened: int, closed: int}}
    Paginates issues (state=all) since needed_start_iso (default panel
    start); skips PR-type items. The `since` param filters on updated_at,
    so an old issue closed inside a needed quarter is still returned.
    """
    since = needed_start_iso or PANEL_START
    url = (f"{BASE_URL}/repos/{repo}/issues"
           f"?state=all&sort=created&direction=asc&since={since}&per_page=100")

    q_data: dict[str, dict] = {
        q: {"opened": 0, "closed": 0}
        for q, _, _ in QUARTERS
    }
    all_quarters = _quarter_set()

    for issue in _paginate(url, call_sleep=0.3):
        if issue.get("pull_request"):
            continue  # this is actually a PR, not an issue

        # Opened
        created_ts = _parse_iso(issue.get("created_at"))
        if created_ts and PANEL_START_TS <= created_ts < PANEL_END_TS:
            q = _ts_to_quarter(created_ts)
            if q in all_quarters:
                q_data[q]["opened"] += 1

        # Closed
        closed_ts = _parse_iso(issue.get("closed_at"))
        if closed_ts and PANEL_START_TS <= closed_ts < PANEL_END_TS:
            q = _ts_to_quarter(closed_ts)
            if q in all_quarters:
                q_data[q]["closed"] += 1

        # Stop early: if created_at is past panel end, we're done
        if created_ts and created_ts >= PANEL_END_TS:
            break

    return q_data

# ---------------------------------------------------------------------------
# Resume support
# ---------------------------------------------------------------------------

def load_checkpoint(panel_csv: str, contrib_csv: str) -> tuple[set, dict]:
    """
    Returns:
      done_pairs   — set of (repo, quarter) already written to panel CSV
      authors_cache — {(repo, quarter): set[author_login]} from contributor CSV
                      used to reconstruct prev_authors when resuming mid-repo
    """
    done_pairs: set = set()
    authors_cache: dict = defaultdict(set)

    if os.path.exists(panel_csv):
        with open(panel_csv, encoding="utf-8") as f:
            for row in csv.DictReader(f):
                done_pairs.add((row["repo"], row["quarter"]))

    if os.path.exists(contrib_csv):
        with open(contrib_csv, encoding="utf-8") as f:
            for row in csv.DictReader(f):
                authors_cache[(row["repo"], row["quarter"])].add(row["author_login"])

    return done_pairs, dict(authors_cache)

# ---------------------------------------------------------------------------
# Main collection loop
# ---------------------------------------------------------------------------

def collect_repo(repo: str, event_type: str, call_sleep: float,
                 panel_writer, contrib_writer, panel_file, contrib_file,
                 done_pairs: set, authors_cache: dict):
    log(f"\n{'='*60}")
    log(f"Collecting: {repo} [{event_type}]")
    log(f"{'='*60}")

    skip_quarters = {q for (r, q) in done_pairs if r == repo}
    n_skip = len(skip_quarters)
    if n_skip:
        log(f"  Resuming — {n_skip}/{len(QUARTERS)} quarters already saved, "
            f"skipping them")

    # PR/issue pagination only needs to reach back to the earliest quarter
    # we still have to write.
    needed = [(q, since) for q, since, _ in QUARTERS if q not in skip_quarters]
    needed_start_iso = needed[0][1] if needed else PANEL_START
    needed_start_ts  = _parse_iso(needed_start_iso) or PANEL_START_TS

    # 1. Commits + authors — skips already-done quarters
    log("  → commits + authors ...")
    commits_by_q, bot_commits_by_q, authors_by_q = \
        collect_commits_and_authors(repo, skip_quarters)

    # 2. PRs (paginated back to the first needed quarter)
    log(f"  → closed PRs (back to {needed_start_iso[:10]}) ...")
    pr_data = collect_prs(repo, needed_start_ts)

    # 3. Issues (paginated back to the first needed quarter)
    log("  → issues ...")
    issue_data = collect_issues(repo, needed_start_iso)

    # 4. Compute metrics and write one row per quarter immediately
    rows_written = 0
    prev_authors: set = set()   # last non-empty human-author set seen

    for i, (qname, _, _) in enumerate(QUARTERS):
        # Skip quarters already in the CSV, but keep turnover continuity
        if (repo, qname) in done_pairs:
            cached = {a for a in authors_cache.get((repo, qname), set())
                      if not _is_bot(a)}
            if cached:
                prev_authors = cached
            continue

        raw_authors = authors_by_q.get(qname)
        curr_authors = set(raw_authors.keys()) if raw_authors else set()

        # Turnover = fraction of previous quarter's authors absent this
        # quarter (bounded [0,1]). None for the first observed quarter.
        if not prev_authors:
            turnover_frac = None
        else:
            departed = len(prev_authors - curr_authors)
            turnover_frac = round(departed / len(prev_authors), 4)

        if curr_authors:
            prev_authors = curr_authors

        # PR metrics
        pq = pr_data.get(qname, {})
        total_prs      = pq.get("total", 0)
        refactor_any   = pq.get("refactor_any", 0)
        refactor_label = pq.get("refactor_label", 0)
        refactor_title = pq.get("refactor_title", 0)
        latencies      = pq.get("latencies", [])
        labeled_count  = pq.get("labeled_count", 0)

        refactor_ratio = round(refactor_any / total_prs, 4) if total_prs > 0 else None
        lat_median     = _round2(_median(latencies))
        lat_p75        = _round2(_percentile(latencies, 75))

        label_coverage_warn = (
            1 if total_prs >= 10 and (labeled_count / total_prs) < 0.05 else 0
        )

        # Issues
        iq = issue_data.get(qname, {})
        issues_opened = iq.get("opened", 0)
        issues_closed = iq.get("closed", 0)
        backlog_delta = issues_opened - issues_closed

        commits     = commits_by_q.get(qname) or 0
        commits_bot = bot_commits_by_q.get(qname) or 0
        n_authors   = len(curr_authors)

        row = {
            "repo":                      repo,
            "event_type":                event_type,
            "quarter":                   qname,
            "commits":                   commits,
            "commits_bot":               commits_bot,
            "pr_count_total":            total_prs,
            "pr_count_refactor":         refactor_any,
            "pr_count_refactor_label":   refactor_label,
            "pr_count_refactor_title":   refactor_title,
            "pr_refactor_ratio":         refactor_ratio if refactor_ratio is not None else "",
            "pr_review_latency_median":  lat_median if lat_median is not None else "",
            "pr_review_latency_p75":     lat_p75 if lat_p75 is not None else "",
            "issues_opened":             issues_opened,
            "issues_closed":             issues_closed,
            "issue_backlog_delta":       backlog_delta,
            "contributor_count":         n_authors,
            "contributor_turnover_frac": turnover_frac if turnover_frac is not None else "",
            "label_coverage_warn":       label_coverage_warn,
        }

        # Write panel row immediately and flush
        panel_writer.writerow(row)
        panel_file.flush()

        # Write contributor history rows and flush
        for author, count in (raw_authors or {}).items():
            contrib_writer.writerow({
                "repo":         repo,
                "quarter":      qname,
                "author_login": author,
                "commit_count": count,
            })
        contrib_file.flush()

        rows_written += 1

    log(f"  ✓ {repo} done — {rows_written} new quarter rows written "
        f"({n_skip} already had)")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main():
    if not GITHUB_TOKEN:
        print("WARNING: GITHUB_TOKEN not set — unauthenticated API (10 req/min).\n"
              "Set $env:GITHUB_TOKEN = 'ghp_...' for much faster collection.\n",
              flush=True)
        call_sleep = 6.1
    else:
        print(f"Authenticated (token: ...{GITHUB_TOKEN[-4:]})\n", flush=True)
        call_sleep = 0.3

    # Load checkpoint: per-(repo, quarter) granularity
    done_pairs, authors_cache = load_checkpoint(PANEL_CSV, CONTRIB_CSV)
    all_q = {q for q, _, _ in QUARTERS}
    done_repos = {repo for (repo, _) in done_pairs
                  if {q for (r, q) in done_pairs if r == repo} >= all_q}

    if done_pairs:
        log(f"Checkpoint loaded: {len(done_pairs)} (repo, quarter) pairs already saved "
            f"({len(done_repos)} repos fully complete)")

    # Open output files in append mode
    panel_exists   = os.path.exists(PANEL_CSV)
    contrib_exists = os.path.exists(CONTRIB_CSV)

    with open(PANEL_CSV, "a", newline="", encoding="utf-8") as pf, \
         open(CONTRIB_CSV, "a", newline="", encoding="utf-8") as cf:

        panel_writer   = csv.DictWriter(pf, fieldnames=PANEL_FIELDS)
        contrib_writer = csv.DictWriter(cf, fieldnames=CONTRIB_FIELDS)

        if not panel_exists:
            panel_writer.writeheader()
        if not contrib_exists:
            contrib_writer.writeheader()

        for repo, event_type in TIER_A_REPOS:
            if repo in done_repos:
                log(f"Skipping {repo} (all 12 quarters already collected)")
                continue
            collect_repo(repo, event_type, call_sleep,
                         panel_writer, contrib_writer, pf, cf,
                         done_pairs, authors_cache)

    log("\nAll done.")
    log(f"Panel data:          {PANEL_CSV}")
    log(f"Contributor history: {CONTRIB_CSV}")
    log(f"Log:                 {LOG_FILE}")

    # Print quick summary
    print("\n" + "=" * 60)
    print(f"{'Repo':<35} {'Qtrs':>5}")
    print("-" * 60)
    counts: dict[str, int] = defaultdict(int)
    with open(PANEL_CSV, encoding="utf-8") as f:
        for row in csv.DictReader(f):
            counts[row["repo"]] += 1
    for repo, _ in TIER_A_REPOS:
        print(f"{repo:<35} {counts.get(repo, 0):>5}")
    print("=" * 60)


if __name__ == "__main__":
    main()
