#!/usr/bin/env python3
"""
collect_git_metrics.py

Local-clone complement to collect_panel_data.py. The GitHub
stats/code_frequency endpoint 422s on repos of this size, so code churn
comes from `git log --numstat` on shallow bare clones instead. The local
history also yields three things the REST API can't give us cleanly:

  1. Exact per-quarter additions/deletions (churn), excluding lockfiles,
     vendored code, and generated assets.
  2. Refactor-commit share from commit subjects (label coverage on PRs is
     too low for label-only detection).
  3. AI-adoption markers per repo:
       - quarterly count of commits with an AI co-author trailer
         (Co-authored-by: Claude / Copilot / Cursor / Devin / aider ...)
       - first-added date of AI config artifacts (CLAUDE.md, .cursorrules,
         .cursor/, .github/copilot-instructions.md, AGENTS.md, ...)
     These date each repo's AI-assisted-development adoption, making the
     paper's AI margin empirical rather than asserted.

Also writes per-author-quarter commit counts (by canonicalized email) for
the Mockus-style core-team turnover measure computed downstream.

Clones live in research/repo_cache/ (gitignored), shallow since 2022-10-01
(one quarter of buffer before the 2023-Q1 panel start; graft-boundary
pseudo-diffs land outside the panel window and are dropped).

Outputs (same directory as this script):
  09_git_metrics.csv       — repo × quarter churn/refactor/AI-commit metrics
  09_ai_markers.csv        — repo × marker file first-added dates
  09_git_contributors.csv  — repo × quarter × author_id × commits
  09_git_collection_log.txt

Usage:  python collect_git_metrics.py
"""

import csv
import os
import re
import subprocess
import sys
from collections import defaultdict
from datetime import datetime, timezone

for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

from collect_panel_data import (  # noqa: E402
    TIER_A_REPOS, QUARTERS, PANEL_START_TS, PANEL_END_TS,
    REFACTOR_TITLE_RE, _is_bot,
)

HERE       = os.path.dirname(os.path.abspath(__file__))
REPO_CACHE = os.path.normpath(os.path.join(HERE, "..", "repo_cache"))
SHALLOW_SINCE = "2022-10-01"

METRICS_CSV  = os.path.join(HERE, "09_git_metrics.csv")
MARKERS_CSV  = os.path.join(HERE, "09_ai_markers.csv")
CONTRIB_CSV  = os.path.join(HERE, "09_git_contributors.csv")
LOG_FILE     = os.path.join(HERE, "09_git_collection_log.txt")

# Paths excluded from churn: lockfiles, vendored/generated code, assets.
CHURN_EXCLUDE_PATHSPECS = [
    ":(exclude,glob)**/package-lock.json",
    ":(exclude,glob)**/pnpm-lock.yaml",
    ":(exclude,glob)**/yarn.lock",
    ":(exclude,glob)**/Cargo.lock",
    ":(exclude,glob)**/poetry.lock",
    ":(exclude,glob)**/uv.lock",
    ":(exclude,glob)**/composer.lock",
    ":(exclude,glob)**/Gemfile.lock",
    ":(exclude,glob)**/go.sum",
    ":(exclude,glob)**/*.min.js",
    ":(exclude,glob)**/*.map",
    ":(exclude,glob)**/*.svg",
    ":(exclude,glob)**/*.snap",
    ":(exclude,glob)**/node_modules/**",
    ":(exclude,glob)**/vendor/**",
    ":(exclude,glob)**/dist/**",
    ":(exclude,glob)**/__snapshots__/**",
]

# AI co-author trailer detection (Copilot commit suggestions, Claude Code,
# Cursor, Devin, aider, ChatGPT/Codex, Gemini, Windsurf ...)
# NOTE: matched against %(trailers:key=Co-authored-by,valueonly) output,
# i.e. "Name <email>" values WITHOUT the "Co-authored-by:" prefix.
AI_COAUTHOR_RE = re.compile(
    r"\b(copilot|claude|cursor(?:\s*ai)?|devin|aider"
    r"|chatgpt|openai|codex|gemini|windsurf|sweep-ai|sourcery|coderabbit"
    r"|anthropic\.com|openai\.com|cursor\.sh|devin\.ai)\b",
    re.IGNORECASE,
)

# AI tooling config artifacts whose first-added date proxies adoption.
AI_MARKER_PATHS = [
    "CLAUDE.md", ".claude", ".cursorrules", ".cursor",
    ".github/copilot-instructions.md", "AGENTS.md", "AGENT.md",
    ".aider.conf.yml", ".windsurfrules", ".continue", ".sourcegraph",
    "GEMINI.md", ".junie",
]

METRICS_FIELDS = [
    "repo", "quarter",
    "commits_git", "commits_git_bot",
    "additions", "deletions", "churn_ratio", "net_growth",
    "files_touched",
    "refactor_commit_count", "refactor_commit_share",
    "ai_coauthored_commits",
]
MARKER_FIELDS  = ["repo", "marker_path", "first_added_utc", "first_added_quarter"]
CONTRIB_FIELDS = ["repo", "quarter", "author_id", "commits"]


def log(msg: str):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] {msg}"
    print(line, flush=True)
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(line + "\n")


def run_git(clone_dir: str, args: list, check: bool = True) -> str:
    proc = subprocess.run(
        ["git", "-C", clone_dir] + args,
        capture_output=True, text=True, encoding="utf-8", errors="replace",
    )
    if check and proc.returncode != 0:
        raise RuntimeError(f"git {' '.join(args[:3])}... failed: {proc.stderr[:300]}")
    return proc.stdout


def ensure_clone(repo: str) -> str:
    """Bare shallow clone (or reuse existing). Returns clone dir."""
    os.makedirs(REPO_CACHE, exist_ok=True)
    safe = repo.replace("/", "__")
    clone_dir = os.path.join(REPO_CACHE, f"{safe}.git")
    if os.path.isdir(clone_dir):
        # Refresh: bare clones don't fetch by default — pull new branch tips
        # and tags so panel extensions see post-clone history.
        log(f"  clone exists — fetching updates: {clone_dir}")
        subprocess.run(
            ["git", "-C", clone_dir, "fetch", "origin",
             "+refs/heads/*:refs/heads/*", "--tags", "--prune"],
            capture_output=True, text=True)
        return clone_dir
    log(f"  cloning {repo} (bare, --shallow-since={SHALLOW_SINCE}) ...")
    proc = subprocess.run(
        ["git", "clone", "--bare", f"--shallow-since={SHALLOW_SINCE}",
         f"https://github.com/{repo}.git", clone_dir],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
    )
    if proc.returncode != 0:
        raise RuntimeError(f"clone failed for {repo}: {proc.stderr[:300]}")
    return clone_dir


def _ts_to_quarter(ts: int):
    dt = datetime.fromtimestamp(ts, tz=timezone.utc)
    return f"{dt.year}-Q{(dt.month - 1) // 3 + 1}"


_NOREPLY_RE = re.compile(r"^(?:\d+\+)?([^@]+)@users\.noreply\.github\.com$", re.I)

def canonical_author(email: str, name: str) -> str:
    """Stable author id: GitHub login from noreply emails, else lowercased
    email, else name."""
    email = (email or "").strip().lower()
    m = _NOREPLY_RE.match(email)
    if m:
        return m.group(1).lower()
    if email:
        return email
    return f"_name:{(name or 'unknown').strip().lower()}"


def author_is_bot(email: str, name: str) -> bool:
    blob = f"{email} {name}".lower()
    return ("[bot]" in blob or _is_bot(email or "") or _is_bot(name or ""))


def collect_repo(repo: str):
    clone_dir = ensure_clone(repo)
    quarters = {q for q, _, _ in QUARTERS}

    per_q = {q: {"commits": 0, "bot_commits": 0, "adds": 0, "dels": 0,
                 "files": 0, "refactor": 0, "ai_co": 0}
             for q in quarters}
    authors_q = defaultdict(int)   # (quarter, author_id) -> commits

    # --- single history pass: header + trailers + numstat ----------------
    # %ct committer time (matches the REST API since/until semantics),
    # %ae/%an author identity, %s subject, trailers for AI co-authors.
    fmt = "@@C@@%ct%x09%ae%x09%an%x09%s%x09%(trailers:key=Co-authored-by,valueonly,separator=;)"
    out = run_git(clone_dir, [
        "log", "--no-merges", f"--pretty=format:{fmt}", "--numstat", "--",
        ".", *CHURN_EXCLUDE_PATHSPECS,
    ])

    n_parsed = 0
    cur = None  # dict for the commit currently being parsed
    for line in out.splitlines():
        if line.startswith("@@C@@"):
            try:
                ct_s, email, name, subject, trailers = line[5:].split("\t", 4)
                ct = int(ct_s)
            except ValueError:
                cur = None
                continue
            q = _ts_to_quarter(ct)
            in_panel = PANEL_START_TS <= ct < PANEL_END_TS and q in quarters
            is_bot = author_is_bot(email, name)
            cur = {"q": q, "in_panel": in_panel, "bot": is_bot}
            if not in_panel:
                continue
            n_parsed += 1
            if is_bot:
                per_q[q]["bot_commits"] += 1
                continue
            per_q[q]["commits"] += 1
            authors_q[(q, canonical_author(email, name))] += 1
            if REFACTOR_TITLE_RE.search(subject or ""):
                per_q[q]["refactor"] += 1
            if AI_COAUTHOR_RE.search(trailers or ""):
                per_q[q]["ai_co"] += 1
        elif line and cur and cur["in_panel"] and not cur["bot"]:
            # numstat line: "adds\tdels\tpath" ("-" for binary)
            parts = line.split("\t")
            if len(parts) == 3 and parts[0] != "-" and parts[1] != "-":
                try:
                    per_q[cur["q"]]["adds"] += int(parts[0])
                    per_q[cur["q"]]["dels"] += int(parts[1])
                    per_q[cur["q"]]["files"] += 1
                except ValueError:
                    pass

    log(f"  parsed {n_parsed} in-panel commits")

    # --- AI marker files: first-added dates -------------------------------
    markers = []
    out = run_git(clone_dir, [
        "log", "--diff-filter=A", "--pretty=format:@@C@@%ct",
        "--name-only", "--", *AI_MARKER_PATHS,
    ], check=False)
    cur_ts = None
    first_added = {}
    for line in out.splitlines():
        if line.startswith("@@C@@"):
            try:
                cur_ts = int(line[5:])
            except ValueError:
                cur_ts = None
        elif line.strip() and cur_ts:
            path = line.strip()
            # log is newest-first; keep the OLDEST add per path
            if path not in first_added or cur_ts < first_added[path]:
                first_added[path] = cur_ts
    for path, ts in sorted(first_added.items(), key=lambda kv: kv[1]):
        markers.append({
            "repo": repo,
            "marker_path": path,
            "first_added_utc": datetime.fromtimestamp(
                ts, tz=timezone.utc).strftime("%Y-%m-%d"),
            "first_added_quarter": _ts_to_quarter(ts),
        })
    if markers:
        log(f"  AI markers: " + ", ".join(
            f"{m['marker_path']}@{m['first_added_quarter']}" for m in markers[:6]))
    else:
        log("  AI markers: none found")

    # --- rows --------------------------------------------------------------
    metric_rows = []
    for qname, _, _ in QUARTERS:
        d = per_q[qname]
        adds, dels = d["adds"], d["dels"]
        commits = d["commits"]
        metric_rows.append({
            "repo": repo,
            "quarter": qname,
            "commits_git": commits,
            "commits_git_bot": d["bot_commits"],
            "additions": adds,
            "deletions": dels,
            "churn_ratio": round(dels / (adds + dels), 4) if (adds + dels) else "",
            "net_growth": adds - dels,
            "files_touched": d["files"],
            "refactor_commit_count": d["refactor"],
            "refactor_commit_share": round(d["refactor"] / commits, 4) if commits else "",
            "ai_coauthored_commits": d["ai_co"],
        })

    contrib_rows = [
        {"repo": repo, "quarter": q, "author_id": a, "commits": n}
        for (q, a), n in sorted(authors_q.items())
    ]
    return metric_rows, markers, contrib_rows


def main():
    done_repos = set()
    if os.path.exists(METRICS_CSV):
        with open(METRICS_CSV, encoding="utf-8") as f:
            for row in csv.DictReader(f):
                done_repos.add(row["repo"])

    m_exists = os.path.exists(METRICS_CSV)
    k_exists = os.path.exists(MARKERS_CSV)
    c_exists = os.path.exists(CONTRIB_CSV)

    with open(METRICS_CSV, "a", newline="", encoding="utf-8") as mf, \
         open(MARKERS_CSV, "a", newline="", encoding="utf-8") as kf, \
         open(CONTRIB_CSV, "a", newline="", encoding="utf-8") as cf:

        mw = csv.DictWriter(mf, fieldnames=METRICS_FIELDS)
        kw = csv.DictWriter(kf, fieldnames=MARKER_FIELDS)
        cw = csv.DictWriter(cf, fieldnames=CONTRIB_FIELDS)
        if not m_exists: mw.writeheader()
        if not k_exists: kw.writeheader()
        if not c_exists: cw.writeheader()

        for repo, _event in TIER_A_REPOS:
            if repo in done_repos:
                log(f"skipping {repo} (already collected)")
                continue
            log(f"=== {repo} ===")
            try:
                metric_rows, markers, contrib_rows = collect_repo(repo)
            except RuntimeError as e:
                log(f"  !! {e}")
                continue
            mw.writerows(metric_rows); mf.flush()
            kw.writerows(markers);     kf.flush()
            cw.writerows(contrib_rows); cf.flush()
            log(f"  done: {len(metric_rows)} quarters, "
                f"{len(contrib_rows)} author-quarters, {len(markers)} AI markers")

    log("All done.")


if __name__ == "__main__":
    main()
