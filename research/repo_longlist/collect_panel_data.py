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
  commits, pr_count_total, pr_count_refactor, pr_refactor_ratio,
  pr_review_latency_median, pr_review_latency_p75,
  additions, deletions, churn_ratio,
  issues_opened, issues_closed, issue_backlog_delta,
  contributor_count, contributor_turnover_frac, label_coverage_warn

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

# ---------------------------------------------------------------------------
# SSL context (Windows Python 3.13 CA bundle workaround)
# ---------------------------------------------------------------------------
_SSL_CTX = ssl.create_default_context()
_SSL_CTX.check_hostname = False
_SSL_CTX.verify_mode = ssl.CERT_NONE

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
]

PANEL_START  = "2023-01-01T00:00:00Z"
PANEL_END    = "2026-01-01T00:00:00Z"
PANEL_START_TS = 1672531200   # 2023-01-01 UTC unix
PANEL_END_TS   = 1735689600   # 2026-01-01 UTC unix

# Label substrings that identify a PR as refactor-type (case-insensitive)
REFACTOR_LABEL_PATTERNS = [
    "refactor", "cleanup", "clean-up", "migration", "migrate",
    "rewrite", "tech-debt", "technical-debt", "debt", "chore",
    "maintenance", "improvement", "architectural", "breaking-change",
    "breaking", "overhaul", "restructure", "rearchitect",
]

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
    "commits",
    "pr_count_total", "pr_count_refactor", "pr_refactor_ratio",
    "pr_review_latency_median", "pr_review_latency_p75",
    "additions", "deletions", "churn_ratio",
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

def collect_code_frequency(repo: str) -> dict:
    """
    Returns {quarter_name: (additions, deletions)} for all quarters.
    Uses /repos/{repo}/stats/code_frequency (weekly data, cached by GitHub).
    deletions in the API response are negative — we store absolute values.
    Retries up to 3 times on 202 (computing).
    """
    url = f"{BASE_URL}/repos/{repo}/stats/code_frequency"
    result = {q: (0, 0) for q, _, _ in QUARTERS}

    for attempt in range(4):
        body, headers = _get(url, call_sleep=0.5)
        if body is None:
            return result
        if body == b"" or body == b"null":
            # 202 was handled inside _get; if we get empty body, wait
            log(f"  [code_freq] empty response attempt {attempt+1}, waiting 15s ...")
            time.sleep(15)
            continue
        data = json.loads(body)
        if not isinstance(data, list) or not data:
            log(f"  [code_freq] unexpected response: {str(data)[:80]}")
            return result

        add_by_q = defaultdict(int)
        del_by_q = defaultdict(int)
        for entry in data:
            ts, adds, dels = entry[0], entry[1], entry[2]
            if ts < PANEL_START_TS or ts >= PANEL_END_TS:
                continue
            q = _ts_to_quarter(float(ts))
            if q in result:
                add_by_q[q] += max(0, adds)
                del_by_q[q] += abs(dels)  # API returns negative deletions

        for q in result:
            result[q] = (add_by_q[q], del_by_q[q])
        return result

    log(f"  [code_freq] gave up for {repo}")
    return result


def collect_commits_and_authors(repo: str,
                                skip_quarters: set = None) -> tuple[dict, dict]:
    """
    Returns:
      commits_by_q: {quarter: int | None}  — None means already saved, skip API call
      authors_by_q: {quarter: dict | None} — None means load from authors_cache on use
    Paginates commits per quarter to extract author.login.
    Skips API calls for quarters in skip_quarters (already written to CSV).
    """
    skip_quarters = skip_quarters or set()
    commits_by_q = {}
    authors_by_q = {}

    for qname, since, until in QUARTERS:
        if qname in skip_quarters:
            commits_by_q[qname] = None   # sentinel: load from existing CSV
            authors_by_q[qname] = None
            log(f"   {qname}: skipped (already collected)")
            continue

        url = (f"{BASE_URL}/repos/{repo}/commits"
               f"?since={since}&until={until}&per_page=100")
        count = 0
        authors: dict[str, int] = defaultdict(int)

        for commit in _paginate(url, call_sleep=0.2):
            count += 1
            author_obj = commit.get("author") or {}
            login = author_obj.get("login") if author_obj else None
            if not login:
                commit_author = (commit.get("commit") or {}).get("author") or {}
                name = commit_author.get("name") or "unknown"
                login = f"_name:{name}"
            authors[login] += 1

        commits_by_q[qname] = count
        authors_by_q[qname] = dict(authors)
        log(f"   {qname}: {count:>5} commits, {len(authors):>3} authors")

    return commits_by_q, authors_by_q


def collect_prs(repo: str) -> dict:
    """
    Returns {quarter: {total, refactor_count, latencies: []}}
    Paginates closed PRs sorted by updated desc; stops before panel start.
    """
    # stop fetching once items are older than a month before panel start
    stop_ts = PANEL_START_TS - 30 * 86400

    url = (f"{BASE_URL}/repos/{repo}/pulls"
           f"?state=closed&sort=updated&direction=desc&per_page=100")

    q_data: dict[str, dict] = {
        q: {"total": 0, "refactor": 0, "latencies": [], "labeled_count": 0}
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
        is_refactor = any(
            pattern in name
            for name in label_names
            for pattern in REFACTOR_LABEL_PATTERNS
        )
        if is_refactor:
            q_data[q]["refactor"] += 1

        # Review latency
        created_ts = _parse_iso(pr.get("created_at"))
        if created_ts and merged_ts > created_ts:
            latency_days = (merged_ts - created_ts) / 86400.0
            q_data[q]["latencies"].append(latency_days)

    return q_data


def collect_issues(repo: str) -> dict:
    """
    Returns {quarter: {opened: int, closed: int}}
    Paginates issues (state=all) since panel start; skips PR-type items.
    """
    stop_ts = PANEL_END_TS + 30 * 86400  # stop past panel end

    url = (f"{BASE_URL}/repos/{repo}/issues"
           f"?state=all&sort=created&direction=asc&since={PANEL_START}&per_page=100")

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
        log(f"  Resuming — {n_skip}/12 quarters already saved, skipping them")

    # 1. Code frequency (1 API call, all-time weekly)
    log("  → code frequency ...")
    freq = collect_code_frequency(repo)

    # 2. Commits + authors — skips already-done quarters
    log("  → commits + authors ...")
    commits_by_q, authors_by_q = collect_commits_and_authors(repo, skip_quarters)

    # 3. PRs (single paginated pass — always re-fetched for incomplete repos)
    log("  → closed PRs ...")
    pr_data = collect_prs(repo)

    # 4. Issues (single paginated pass)
    log("  → issues ...")
    issue_data = collect_issues(repo)

    # 5. Compute metrics and write one row per quarter immediately
    quarter_names = [q for q, _, _ in QUARTERS]
    rows_written = 0

    for i, (qname, _, _) in enumerate(QUARTERS):
        # Skip quarters already in the CSV
        if (repo, qname) in done_pairs:
            # Still need prev_authors for turnover continuity; read from cache
            prev_authors_this = authors_cache.get((repo, qname), set())
            # Update running prev_authors for next iteration
            if i == 0:
                _prev = prev_authors_this
            else:
                _prev = prev_authors_this if prev_authors_this else _prev  # noqa: F821
            continue

        # Resolve author set: None sentinel means this quarter was skipped in
        # collect_commits_and_authors, which shouldn't happen for non-done quarters.
        raw_authors = authors_by_q.get(qname)
        curr_authors = set(raw_authors.keys()) if raw_authors else set()

        # Contributor turnover: compare to previous quarter's author set
        if i == 0:
            _prev = set()
        prev_authors = _prev

        if not prev_authors:
            turnover_frac = None
        else:
            new_count = len(curr_authors - prev_authors)
            turnover_frac = round(new_count / len(prev_authors), 4)

        # Advance prev_authors (keep last non-empty set for continuity)
        _prev = curr_authors if curr_authors else prev_authors

        # PR metrics
        pq = pr_data.get(qname, {})
        total_prs     = pq.get("total", 0)
        refactor_prs  = pq.get("refactor", 0)
        latencies     = pq.get("latencies", [])
        labeled_count = pq.get("labeled_count", 0)

        refactor_ratio = round(refactor_prs / total_prs, 4) if total_prs > 0 else None
        lat_median     = _round2(_median(latencies))
        lat_p75        = _round2(_percentile(latencies, 75))

        label_coverage_warn = (
            1 if total_prs >= 10 and (labeled_count / total_prs) < 0.05 else 0
        )

        # Code churn
        adds, dels = freq.get(qname, (0, 0))
        churn_ratio = round(dels / (adds + dels + 1), 4)

        # Issues
        iq = issue_data.get(qname, {})
        issues_opened = iq.get("opened", 0)
        issues_closed = iq.get("closed", 0)
        backlog_delta = issues_opened - issues_closed

        commits   = commits_by_q.get(qname) or 0
        n_authors = len(curr_authors)

        row = {
            "repo":                      repo,
            "event_type":                event_type,
            "quarter":                   qname,
            "commits":                   commits,
            "pr_count_total":            total_prs,
            "pr_count_refactor":         refactor_prs,
            "pr_refactor_ratio":         refactor_ratio if refactor_ratio is not None else "",
            "pr_review_latency_median":  lat_median if lat_median is not None else "",
            "pr_review_latency_p75":     lat_p75 if lat_p75 is not None else "",
            "additions":                 adds,
            "deletions":                 dels,
            "churn_ratio":               churn_ratio,
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
