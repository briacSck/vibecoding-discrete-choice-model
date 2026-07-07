#!/usr/bin/env python3
"""
build_adoption_did.py — staggered AI-adoption event study (design prototype).

Treatment: repo-level adoption of AI-assisted development, dated two ways
from the repo's own history (09_* files):
  (a) marker_q   — first quarter an AI config artifact was committed
                   (CLAUDE.md, .cursorrules, copilot-instructions, ...)
  (b) coauthor_q — first of >=2 consecutive quarters with ai_coauthored
                   commits > 0 (sustained visible agentic use)
  adoption_q = earlier of the two; both stored for robustness.

Outcomes: refactor_commit_share, pr_refactor_ratio, latency median,
churn per human commit, backlog delta per contributor, Mockus core turnover.

HONESTY CONSTRAINTS (paper language should mirror these):
  - 14 units. This is a DESIGN PROTOTYPE: adoption-time-aligned event
    studies + a TWFE illustration with unit and quarter fixed effects.
    The Callaway–Sant'Anna estimator belongs to the scaled sample; with a
    handful of units group-time ATTs are not credible and are not run.
  - Trailers measure VISIBLE agentic usage (Claude Code / Copilot agent
    commits) — a lower bound on AI assistance; silent autocomplete is
    unobserved. Markers measure org-level workflow adoption.
  - Adoption is not random (dev-tool firms adopt first). The tool-release
    instrument (adoption timing driven by Claude Code / Copilot releases
    x repo exposure; e.g. PostHog CLAUDE.md 2025-02-25 ~3 weeks after
    Claude Code launch) is the scaled-sample identification strategy —
    noted, not estimated here.

Outputs: 12_adoption_dates.csv, 12_adoption_event_study.png,
         12_adoption_twfe.txt
"""

import os
import sys

import numpy as np
import pandas as pd

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

HERE = os.path.dirname(os.path.abspath(__file__))
P = lambda name: os.path.join(HERE, name)

from collect_panel_data import QUARTERS as QTRIPLES  # noqa: E402
from build_cqi import mockus_turnover                # noqa: E402

QUARTERS = [q for q, _, _ in QTRIPLES]
QIDX = {q: i for i, q in enumerate(QUARTERS)}

INK, MUTED, LINE, ACCENT, GRID = (
    "#33322E", "#8A8782", "#4C7C7C", "#B0483E", "#E4E2DD")

OUTCOMES = {
    "refactor_commit_share": "refactor share of commits (git)",
    "pr_refactor_ratio":     "refactor share of PRs (API)",
    "pr_review_latency_median": "PR review latency, median days",
    "churn_per_commit":      "churn per human commit",
    "backlog_per_contrib":   "issue backlog delta per contributor",
    "turnover_core":         "core-team turnover (Mockus 80%)",
}


def _date_to_q(datestr):
    y, m = int(datestr[:4]), int(datestr[5:7])
    return f"{y}-Q{(m - 1) // 3 + 1}"


def adoption_dates():
    markers = pd.read_csv(P("09_ai_markers.csv"))
    git = pd.read_csv(P("09_git_metrics.csv"))

    rows = []
    for repo in git["repo"].unique():
        m = markers[markers["repo"] == repo]
        marker_q = None
        if len(m):
            first = m["first_added_utc"].min()
            q = _date_to_q(first)
            marker_q = q if q in QIDX else None  # markers can post-date panel

        g = git[git["repo"] == repo].sort_values(
            "quarter", key=lambda s: s.map(QIDX))
        co = g["ai_coauthored_commits"].values
        coauthor_q = None
        for i in range(len(co) - 1):
            if co[i] > 0 and co[i + 1] > 0:
                coauthor_q = g["quarter"].iloc[i]
                break

        cands = [q for q in (marker_q, coauthor_q) if q]
        adoption_q = min(cands, key=lambda q: QIDX[q]) if cands else None
        rows.append({"repo": repo, "marker_q": marker_q,
                     "coauthor_q": coauthor_q, "adoption_q": adoption_q})
    return pd.DataFrame(rows)


def load_outcomes():
    api = pd.read_csv(P("08_panel_data.csv"))
    git = pd.read_csv(P("09_git_metrics.csv"))
    con = pd.read_csv(P("09_git_contributors.csv"))
    df = api.merge(git, on=["repo", "quarter"], how="left")
    df = df.merge(mockus_turnover(con), on=["repo", "quarter"], how="left")
    df["qidx"] = df["quarter"].map(QIDX)
    df = df.dropna(subset=["qidx"]).sort_values(["repo", "qidx"])

    df["pr_refactor_ratio"] = pd.to_numeric(df["pr_refactor_ratio"], errors="coerce")
    df["pr_review_latency_median"] = pd.to_numeric(
        df["pr_review_latency_median"], errors="coerce")
    df["churn_per_commit"] = (df["additions"] + df["deletions"]) / \
        df["commits_git"].replace(0, np.nan)
    df["backlog_per_contrib"] = df["issue_backlog_delta"] / \
        df["contributor_count"].replace(0, np.nan)
    return df


def twfe(df, outcome):
    """Within-transformed OLS of outcome on post-adoption dummy with unit
    and quarter FE. Illustration only — naive (non-clustered) SE, 14 units."""
    d = df.dropna(subset=[outcome, "post"]).copy()
    if d.empty or d["post"].nunique() < 2:
        return None
    y = d[outcome].astype(float)
    x = d["post"].astype(float)
    # two-way within transformation (one iteration is enough for balanced-ish)
    for _ in range(3):
        for g in ("repo", "quarter"):
            y = y - y.groupby(d[g]).transform("mean")
            x = x - x.groupby(d[g]).transform("mean")
    denom = (x ** 2).sum()
    if denom < 1e-12:
        return None
    beta = (x * y).sum() / denom
    resid = y - beta * x
    k = d["repo"].nunique() + d["quarter"].nunique() + 1
    dof = max(len(d) - k, 1)
    se = float(np.sqrt((resid ** 2).sum() / dof / denom))
    return beta, se, len(d)


def _style(ax):
    ax.spines[["top", "right"]].set_visible(False)
    ax.spines[["left", "bottom"]].set_color(MUTED)
    ax.tick_params(colors=MUTED, labelsize=8)
    ax.grid(True, axis="y", color=GRID, linewidth=0.7)
    ax.set_axisbelow(True)


def main():
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    ad = adoption_dates()
    ad.to_csv(P("12_adoption_dates.csv"), index=False)
    print(ad.to_string(index=False))

    df = load_outcomes()
    df = df.merge(ad[["repo", "adoption_q"]], on="repo", how="left")
    df["adopt_idx"] = df["adoption_q"].map(QIDX)
    df["tau"] = df["qidx"] - df["adopt_idx"]
    df["post"] = (df["tau"] >= 0).where(df["adopt_idx"].notna(), 0.0)

    adopters = ad.dropna(subset=["adoption_q"])["repo"].tolist()
    controls = ad[ad["adoption_q"].isna()]["repo"].tolist()

    # ---- adoption-time-aligned event studies -----------------------------
    fig, axes = plt.subplots(2, 3, figsize=(13, 7), sharex=True)
    for ax, (col, label) in zip(axes.flat, OUTCOMES.items()):
        aligned = []
        for repo in adopters:
            sub = df[df["repo"] == repo].sort_values("qidx")
            ax.plot(sub["tau"], sub[col], color=MUTED, linewidth=0.7, alpha=0.45)
            aligned.append(sub[["tau", col]].rename(columns={col: "v"}))
        if aligned:
            al = pd.concat(aligned)
            mean = al.groupby("tau")["v"].agg(["mean", "count"])
            mean = mean[mean["count"] >= 4]
            ax.plot(mean.index, mean["mean"], color=LINE, linewidth=2.4,
                    label="adopters, mean (n≥4 per τ)")
        ax.axvline(0, color=ACCENT, linewidth=1.2, linestyle=(0, (4, 3)))
        ax.set_title(label, fontsize=9, color=INK)
        _style(ax)
    axes[0, 0].legend(frameon=False, fontsize=7, loc="upper left")
    axes[1, 1].set_xlabel("quarters relative to AI adoption (τ)",
                          fontsize=9, color=INK)
    fig.suptitle(f"Maintenance outcomes around AI adoption — {len(adopters)} "
                 f"adopters, {len(controls)} never-adopters "
                 f"({', '.join(r.split('/')[-1] for r in controls) or 'none'}) "
                 "— design prototype, 14 units", fontsize=11, color=INK)
    fig.tight_layout(rect=[0, 0, 1, 0.94])
    fig.savefig(P("12_adoption_event_study.png"), dpi=200)
    plt.close(fig)

    # ---- TWFE illustration ------------------------------------------------
    with open(P("12_adoption_twfe.txt"), "w", encoding="utf-8") as f:
        f.write("TWFE illustration: outcome ~ post_adoption + repo FE + "
                "quarter FE\n")
        f.write("NAIVE SEs, 14 units — design prototype ONLY; the CS "
                "estimator is reserved for the scaled sample.\n\n")
        f.write(f"{'outcome':<28}{'beta':>10}{'se':>9}{'n':>6}\n")
        for col in OUTCOMES:
            r = twfe(df, col)
            if r:
                f.write(f"{col:<28}{r[0]:>10.4f}{r[1]:>9.4f}{r[2]:>6}\n")
            else:
                f.write(f"{col:<28}{'—':>10}\n")
        f.write("\nAdoption dates (adoption_q = min(marker_q, coauthor_q)):\n")
        f.write(ad.fillna("—").to_string(index=False) + "\n")
        f.write("\nIdentification note for the paper: adoption timing is "
                "plausibly driven by AI tool releases x repo exposure "
                "(PostHog CLAUDE.md 2025-02-25, ~3 weeks after Claude Code "
                "launch). Marker-based dating scales to samples far beyond "
                "the contact-constrained pilot without per-org "
                "confirmation.\n")

    df.to_csv(P("12_adoption_panel.csv"), index=False)
    print("done: 12_adoption_dates.csv, 12_adoption_event_study.png, "
          "12_adoption_twfe.txt")


if __name__ == "__main__":
    main()
