#!/usr/bin/env python3
"""
verify_feasibility.py

Queries the GitHub REST API to count commits per quarter (2023 Q1 – 2025 Q4)
for 11 repos whose Panel Feasibility scores were estimated (not directly
verified) during the initial candidate screening.

Outputs:
  07_feasibility_panel.csv   — long format: repo × quarter commit counts
  07_feasibility_scores.csv  — per-repo feasibility score + verdict

Usage:
  $env:GITHUB_TOKEN = "ghp_..."   # Windows PowerShell
  python verify_feasibility.py

Without GITHUB_TOKEN the script falls back to unauthenticated requests
(10 req/min) and adds a 6s inter-call sleep — runtime ~15 min instead of ~2.
"""

import csv
import json
import math
import os
import re
import ssl
import sys
import time
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

# Windows Python 3.13 ships without the system CA bundle wired in;
# disable host verification for the GitHub API (HTTPS, token-authenticated).
_SSL_CTX = ssl.create_default_context()
_SSL_CTX.check_hostname = False
_SSL_CTX.verify_mode = ssl.CERT_NONE

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

TARGET_REPOS = [
    ("Helicone/helicone",         3, "B"),
    ("hoppscotch/hoppscotch",     3, "C"),
    ("chatwoot/chatwoot",         3, "B"),
    ("formbricks/formbricks",     3, "C"),
    ("documenso/documenso",       3, "C"),
    ("maybe-finance/maybe",       3, "B"),
    ("qdrant/qdrant",             3, "B"),
    ("tursodatabase/libsql",      3, "B"),
    ("inngest/inngest",           3, "B"),
    ("milvus-io/milvus",          4, "B"),
    ("oven-sh/bun",               4, "B"),
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

OUT_DIR = os.path.dirname(os.path.abspath(__file__))
PANEL_CSV  = os.path.join(OUT_DIR, "07_feasibility_panel.csv")
SCORES_CSV = os.path.join(OUT_DIR, "07_feasibility_scores.csv")

GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN", "")
BASE_URL = "https://api.github.com"

# ---------------------------------------------------------------------------
# GitHub API helpers
# ---------------------------------------------------------------------------

def _headers():
    h = {"Accept": "application/vnd.github+json",
         "X-GitHub-Api-Version": "2022-11-28",
         "User-Agent": "vibecoding-feasibility-check/1.0"}
    if GITHUB_TOKEN:
        h["Authorization"] = f"Bearer {GITHUB_TOKEN}"
    return h


def _sleep_until_reset(headers_dict):
    reset = headers_dict.get("X-RateLimit-Reset")
    if reset:
        wait = max(0, int(reset) - int(time.time())) + 5
        print(f"  [rate limit] sleeping {wait}s ...", flush=True)
        time.sleep(wait)


def fetch_commit_count(repo: str, since: str, until: str) -> int:
    """
    Returns the number of commits to the default branch for `repo`
    in the half-open interval [since, until).

    Uses the Link-header trick: request per_page=1 and read the `last`
    page number from the Link header — that equals the total count.
    If there is no Link header the response has 0 or 1 commits.
    """
    url = (f"{BASE_URL}/repos/{repo}/commits"
           f"?since={since}&until={until}&per_page=1")
    req = Request(url, headers=_headers())

    for attempt in range(2):
        try:
            with urlopen(req, timeout=30, context=_SSL_CTX) as resp:
                link = resp.headers.get("Link", "")
                body = resp.read()
                if not link:
                    # 0 or 1 commits — check body
                    data = json.loads(body) if body else []
                    return len(data)
                # Parse last page number from Link header
                # Example: <url?page=42>; rel="last"
                m = re.search(r'[?&]page=(\d+)>;\s*rel="last"', link)
                if m:
                    return int(m.group(1))
                # Fallback: only a rel="prev" exists, meaning we're on last page
                data = json.loads(body) if body else []
                return len(data)
        except HTTPError as e:
            if e.code in (403, 429):
                _sleep_until_reset(dict(e.headers))
                continue
            if e.code == 409:
                # 409 = empty repo
                return 0
            raise
        except URLError as e:
            print(f"  [network error] {e} — retrying in 10s", flush=True)
            time.sleep(10)
            continue

    return 0  # give up after 2 attempts


# ---------------------------------------------------------------------------
# Scoring logic (mirrors 05_screening_rubric.md)
# ---------------------------------------------------------------------------

def compute_feasibility(counts: list[int]) -> dict:
    """
    counts: list of 12 integers (commits per quarter, 2023-Q1 … 2025-Q4)
    Returns a dict with scoring breakdown.
    """
    active_quarters = sum(1 for c in counts if c > 0)
    total_commits   = sum(counts)

    # Longest run of consecutive zero-commit quarters
    max_gap = 0
    current_gap = 0
    for c in counts:
        if c == 0:
            current_gap += 1
            max_gap = max(max_gap, current_gap)
        else:
            current_gap = 0

    # Coefficient of variation on non-zero quarters only
    active_vals = [c for c in counts if c > 0]
    if len(active_vals) >= 2:
        mean = sum(active_vals) / len(active_vals)
        variance = sum((x - mean) ** 2 for x in active_vals) / len(active_vals)
        cv = math.sqrt(variance) / mean if mean > 0 else 0.0
    else:
        cv = 0.0

    # Score mapping
    if active_quarters == 12 and cv < 0.50:
        score = 5
    elif active_quarters >= 11 and max_gap <= 1:
        score = 4
    elif active_quarters >= 10 and max_gap <= 1:
        score = 3
    elif active_quarters >= 8 and max_gap <= 2:
        score = 2
    else:
        score = 1

    g2_fail = max_gap >= 4
    g3_warn = total_commits < 1000  # lower bound (same-branch counts only)

    return {
        "active_quarters": active_quarters,
        "total_commits_lb": total_commits,
        "max_gap": max_gap,
        "cv_commits": round(cv, 3),
        "feasibility_score": score,
        "g2_fail": g2_fail,
        "g3_warn": g3_warn,
    }


def recommendation(result: dict, estimated: int, tier: str) -> str:
    score = result["feasibility_score"]
    if result["g2_fail"]:
        return "EXCLUDE — G2 gate fail (gap >= 4 quarters)"
    if result["g3_warn"]:
        return "REVIEW — G3 gate concern (total commits in window < 1,000)"
    if score > estimated:
        return f"UPGRADE from {estimated} → {score}"
    if score < estimated:
        return f"DOWNGRADE from {estimated} → {score}"
    return f"CONFIRMED at {score}"


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    if not GITHUB_TOKEN:
        print("WARNING: GITHUB_TOKEN not set — using unauthenticated API "
              "(10 req/min). Expected runtime ~15 min.\n"
              "Set $env:GITHUB_TOKEN = 'ghp_...' for ~2 min runtime.\n",
              flush=True)
        call_sleep = 6.1   # stay under 10 req/min
    else:
        print(f"Using authenticated GitHub API (token: ...{GITHUB_TOKEN[-4:]})\n",
              flush=True)
        call_sleep = 0.1   # courtesy pause only

    panel_rows  = []  # (repo, quarter, commits, is_active)
    score_rows  = []  # one per repo

    for repo, estimated_score, tier in TARGET_REPOS:
        print(f"-- {repo}", flush=True)
        counts = []

        for qname, since, until in QUARTERS:
            count = fetch_commit_count(repo, since, until)
            counts.append(count)
            panel_rows.append({
                "repo":      repo,
                "quarter":   qname,
                "commits":   count,
                "is_active": 1 if count > 0 else 0,
            })
            print(f"   {qname}: {count:>5} commits", flush=True)
            time.sleep(call_sleep)

        result = compute_feasibility(counts)
        rec    = recommendation(result, estimated_score, tier)
        changed = result["feasibility_score"] != estimated_score

        score_rows.append({
            "repo":               repo,
            "tier":               tier,
            "estimated_score":    estimated_score,
            "feasibility_score":  result["feasibility_score"],
            "score_changed":      changed,
            "active_quarters":    result["active_quarters"],
            "max_gap":            result["max_gap"],
            "cv_commits":         result["cv_commits"],
            "total_commits_lb":   result["total_commits_lb"],
            "g2_fail":            result["g2_fail"],
            "g3_warn":            result["g3_warn"],
            "recommendation":     rec,
        })
        print(f"   → score {result['feasibility_score']} "
              f"(estimated {estimated_score}) | {rec}\n", flush=True)

    # Write panel CSV
    with open(PANEL_CSV, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["repo", "quarter", "commits", "is_active"])
        writer.writeheader()
        writer.writerows(panel_rows)
    print(f"Wrote {PANEL_CSV}")

    # Write scores CSV
    score_fields = [
        "repo", "tier", "estimated_score", "feasibility_score",
        "score_changed", "active_quarters", "max_gap", "cv_commits",
        "total_commits_lb", "g2_fail", "g3_warn", "recommendation",
    ]
    with open(SCORES_CSV, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=score_fields)
        writer.writeheader()
        writer.writerows(score_rows)
    print(f"Wrote {SCORES_CSV}")

    # Summary table
    print("\n" + "=" * 70)
    print(f"{'Repo':<35} {'Est':>3} {'Got':>3} {'Changed':>8}  Recommendation")
    print("-" * 70)
    for row in score_rows:
        changed_str = "YES" if row["score_changed"] else "—"
        print(f"{row['repo']:<35} {row['estimated_score']:>3} "
              f"{row['feasibility_score']:>3} {changed_str:>8}  {row['recommendation']}")
    print("=" * 70)


if __name__ == "__main__":
    main()
