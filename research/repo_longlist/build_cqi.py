#!/usr/bin/env python3
"""
build_cqi.py

Constructs the paper's Codebase Quality Index (CQI) state variable from the
pilot panel, per the locked spec (WhenToCleanTheMachine v2, §4 "CQI as State
Variable" / §"CQI State Variable Construction"):

  flows -> PIM stocks  S_t = (1-δ) S_{t-1} + f_t,  δ = 0.09/quarter
        -> per-signal [0,1] normalization
        -> first principal component (pooled pilot panel)
        -> CQI (oriented so higher = more degraded)

Signals implemented (paper's five, minus test coverage — not observable for
these repos; documented as dropped in the pilot):
  1. PR review latency        (median days; API panel)
  2. Refactor PR ratio        (label OR title match; API panel)
  3. Relative code churn      ((adds+dels)/repo size in bytes; git metrics)
  4. Issue backlog growth     (net delta / trailing-4q mean of opened; API)

Also computes:
  - Mockus-style core-team turnover from 09_git_contributors.csv
    (core = smallest author set covering 80% of the quarter's commits;
     turnover = share of previous core absent from current core)
  - Fuzzy event quarters (peak refactor-ratio quarter) where events.csv
    says dating_method = peak_refactor

Outputs:
  10_cqi_panel.csv            — repo × quarter: flows, stocks, CQI, turnover
  10_repo_size.csv            — cached repo size (bytes) per quarter start
  10_cqi_loadings.txt         — PC loadings + variance share + diagnostics
  10_event_study_cqi.png      — aligned event-time CQI (the "money figure")
  10_cqi_small_multiples.png  — per-repo CQI trajectories with event lines

Usage: python build_cqi.py   (requires 08_/09_ CSVs + events.csv + repo_cache)
"""

import os
import subprocess
import sys

import numpy as np
import pandas as pd

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

HERE       = os.path.dirname(os.path.abspath(__file__))
REPO_CACHE = os.path.normpath(os.path.join(HERE, "..", "repo_cache"))
DELTA      = 0.09   # quarterly PIM depreciation (Corrado et al. 2009)

QUARTERS = [f"{y}-Q{q}" for y in (2023, 2024, 2025) for q in (1, 2, 3, 4)]
Q_START  = {q: f"{q[:4]}-{['01','04','07','10'][int(q[-1])-1]}-01" for q in QUARTERS}

P = lambda name: os.path.join(HERE, name)


# --------------------------------------------------------------------------
# Repo size (bytes of tracked blobs) at each quarter start, from bare clones
# --------------------------------------------------------------------------

def repo_size_bytes(repo: str, quarter: str):
    clone = os.path.join(REPO_CACHE, repo.replace("/", "__") + ".git")
    if not os.path.isdir(clone):
        return None
    date = Q_START[quarter]
    sha = subprocess.run(
        ["git", "-C", clone, "rev-list", "-1", f"--before={date}T00:00:00Z", "HEAD"],
        capture_output=True, text=True).stdout.strip()
    if not sha:
        return None
    out = subprocess.run(
        ["git", "-C", clone, "ls-tree", "-r", "--long", sha],
        capture_output=True, text=True, encoding="utf-8", errors="replace").stdout
    total = 0
    for line in out.splitlines():
        # <mode> blob <sha> <size>\t<path>
        parts = line.split("\t", 1)[0].split()
        if len(parts) >= 4 and parts[1] == "blob":
            try:
                total += int(parts[3])
            except ValueError:
                pass
    return total or None


def load_or_build_sizes(repos):
    cache = P("10_repo_size.csv")
    if os.path.exists(cache):
        return pd.read_csv(cache)
    rows = []
    for repo in repos:
        print(f"sizing {repo} ...", flush=True)
        for q in QUARTERS:
            rows.append({"repo": repo, "quarter": q,
                         "size_bytes": repo_size_bytes(repo, q)})
    df = pd.DataFrame(rows)
    df.to_csv(cache, index=False)
    return df


# --------------------------------------------------------------------------
# Mockus core-team turnover
# --------------------------------------------------------------------------

def core_set(group: pd.DataFrame, threshold=0.80):
    g = group.sort_values("commits", ascending=False)
    cum = g["commits"].cumsum() / g["commits"].sum()
    # smallest prefix reaching the threshold (include the crossing author)
    idx = int(np.searchsorted(cum.values, threshold)) + 1
    return set(g["author_id"].iloc[:idx])


def mockus_turnover(contrib: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for repo, g in contrib.groupby("repo"):
        prev_core = None
        for q in QUARTERS:
            gq = g[g["quarter"] == q]
            if gq.empty or gq["commits"].sum() == 0:
                rows.append({"repo": repo, "quarter": q,
                             "core_size": 0, "turnover_core": np.nan})
                continue
            core = core_set(gq)
            if prev_core:
                gone = len(prev_core - core) / len(prev_core)
            else:
                gone = np.nan
            rows.append({"repo": repo, "quarter": q,
                         "core_size": len(core),
                         "turnover_core": round(gone, 4) if gone == gone else np.nan})
            prev_core = core
    return pd.DataFrame(rows)


# --------------------------------------------------------------------------
# PIM + PCA
# --------------------------------------------------------------------------

def pim_stock(flows: pd.Series, delta=DELTA) -> pd.Series:
    stock, prev = [], None
    for f in flows:
        if prev is None:
            prev = f if pd.notna(f) else 0.0
        else:
            prev = (1 - delta) * prev + (f if pd.notna(f) else 0.0)
        stock.append(prev)
    return pd.Series(stock, index=flows.index)


def build():
    api  = pd.read_csv(P("08_panel_data.csv"))
    git  = pd.read_csv(P("09_git_metrics.csv"))
    con  = pd.read_csv(P("09_git_contributors.csv"))
    ev   = pd.read_csv(P("events.csv"))

    df = api.merge(git, on=["repo", "quarter"], how="left", suffixes=("", "_git"))
    sizes = load_or_build_sizes(sorted(df["repo"].unique()))
    df = df.merge(sizes, on=["repo", "quarter"], how="left")
    df["qidx"] = df["quarter"].map({q: i for i, q in enumerate(QUARTERS)})
    df = df.sort_values(["repo", "qidx"]).reset_index(drop=True)

    # ---- flows -----------------------------------------------------------
    df["f_latency"]  = pd.to_numeric(df["pr_review_latency_median"], errors="coerce")
    df["f_refactor"] = pd.to_numeric(df["pr_refactor_ratio"], errors="coerce")
    df["f_churn"]    = (df["additions"] + df["deletions"]) / df["size_bytes"]
    opened_ma = (df.groupby("repo")["issues_opened"]
                   .transform(lambda s: s.rolling(4, min_periods=2).mean().shift(1)))
    df["f_backlog"]  = df["issue_backlog_delta"] / opened_ma.replace(0, np.nan)

    signals = ["f_latency", "f_refactor", "f_churn", "f_backlog"]

    # ---- PIM stocks ------------------------------------------------------
    for s in signals:
        df["S_" + s[2:]] = df.groupby("repo")[s].transform(pim_stock)

    stocks = ["S_" + s[2:] for s in signals]

    # ---- normalize to [0,1] per signal (pooled panel) ---------------------
    Z = df[stocks].copy()
    for c in stocks:
        lo, hi = Z[c].min(), Z[c].max()
        Z[c] = (Z[c] - lo) / (hi - lo) if hi > lo else 0.0

    # ---- first PC of the correlation matrix -------------------------------
    X = Z.fillna(Z.mean())
    Xs = (X - X.mean()) / X.std(ddof=0)
    corr = np.corrcoef(Xs.T)
    eigval, eigvec = np.linalg.eigh(corr)
    w = eigvec[:, -1]
    if w[stocks.index("S_latency")] < 0:   # orient: higher = more degraded
        w = -w
    var_share = eigval[-1] / eigval.sum()
    df["CQI"] = Xs.values @ w

    # ---- Mockus turnover ---------------------------------------------------
    turn = mockus_turnover(con)
    df = df.merge(turn, on=["repo", "quarter"], how="left")

    # ---- event quarters (incl. computed fuzzy peaks) -----------------------
    ev = ev.set_index("repo")
    event_q = {}
    for repo in df["repo"].unique():
        if repo not in ev.index:
            continue
        row = ev.loc[repo]
        if isinstance(row.get("event_quarter"), str) and row["event_quarter"]:
            event_q[repo] = row["event_quarter"]
        elif row.get("dating_method") == "peak_refactor":
            sub = df[df["repo"] == repo]
            if sub["f_refactor"].notna().any():
                event_q[repo] = sub.loc[sub["f_refactor"].idxmax(), "quarter"]
    df["event_quarter"] = df["repo"].map(event_q)

    df.to_csv(P("10_cqi_panel.csv"), index=False)

    with open(P("10_cqi_loadings.txt"), "w", encoding="utf-8") as f:
        f.write("CQI first principal component (pooled pilot panel)\n")
        f.write(f"variance share of PC1: {var_share:.3f}\n\n")
        for c, wi in zip(stocks, w):
            f.write(f"  {c:<12} {wi:+.4f}\n")
        f.write("\nsignal coverage (non-missing flow shares):\n")
        for s in signals:
            f.write(f"  {s:<12} {df[s].notna().mean():.2%}\n")
        f.write("\nNOTE: test-coverage signal (paper signal 5) unavailable in "
                "pilot; CQI built on 4 signals.\n")

    print(f"PC1 variance share: {var_share:.3f}; loadings: "
          + ", ".join(f"{c}={wi:+.3f}" for c, wi in zip(stocks, w)))
    return df, event_q


# --------------------------------------------------------------------------
# Figures
# --------------------------------------------------------------------------

INK    = "#33322E"   # primary text
MUTED  = "#8A8782"   # secondary
LINE   = "#4C7C7C"   # single-series hue (teal, mid-lightness)
ACCENT = "#B0483E"   # event marker / emphasis (warm, clearly separated)
GRID   = "#E4E2DD"


def _style(ax):
    ax.spines[["top", "right"]].set_visible(False)
    ax.spines[["left", "bottom"]].set_color(MUTED)
    ax.tick_params(colors=MUTED, labelsize=8)
    ax.grid(True, axis="y", color=GRID, linewidth=0.7)
    ax.set_axisbelow(True)


def figures(df: pd.DataFrame, event_q: dict):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    qidx = {q: i for i, q in enumerate(QUARTERS)}

    # ---- small multiples ---------------------------------------------------
    repos = sorted(df["repo"].unique())
    ncol = 4
    nrow = int(np.ceil(len(repos) / ncol))
    fig, axes = plt.subplots(nrow, ncol, figsize=(12, 2.1 * nrow),
                             sharex=True, sharey=True)
    for ax, repo in zip(axes.flat, repos):
        sub = df[df["repo"] == repo].sort_values("qidx")
        ax.plot(sub["qidx"], sub["CQI"], color=LINE, linewidth=1.8)
        if repo in event_q:
            ax.axvline(qidx[event_q[repo]], color=ACCENT, linewidth=1.2,
                       linestyle=(0, (4, 3)))
        ax.set_title(repo.split("/")[-1], fontsize=9, color=INK, pad=3)
        _style(ax)
        ax.set_xticks([0, 4, 8, 11])
        ax.set_xticklabels(["23Q1", "24Q1", "25Q1", "25Q4"], fontsize=7)
    for ax in axes.flat[len(repos):]:
        ax.axis("off")
    fig.suptitle("CQI trajectories by repository "
                 "(dashed line = rationalization event quarter)",
                 fontsize=11, color=INK)
    fig.supylabel("CQI (higher = more degraded)", fontsize=9, color=MUTED)
    fig.tight_layout(rect=[0.02, 0, 1, 0.96])
    fig.savefig(P("10_cqi_small_multiples.png"), dpi=200)
    plt.close(fig)

    # ---- aligned event study ----------------------------------------------
    fig, ax = plt.subplots(figsize=(8, 5))
    aligned = []
    for repo, eq in event_q.items():
        sub = df[df["repo"] == repo].sort_values("qidx")
        tau = sub["qidx"] - qidx[eq]
        ax.plot(tau, sub["CQI"], color=MUTED, linewidth=0.9, alpha=0.55)
        aligned.append(pd.DataFrame({"tau": tau, "CQI": sub["CQI"].values}))
        ax.annotate(repo.split("/")[-1], (tau.iloc[-1], sub["CQI"].iloc[-1]),
                    fontsize=7, color=MUTED, xytext=(3, 0),
                    textcoords="offset points", va="center")
    if aligned:
        al = pd.concat(aligned)
        mean = al.groupby("tau")["CQI"].agg(["mean", "count"])
        mean = mean[mean["count"] >= 3]
        ax.plot(mean.index, mean["mean"], color=LINE, linewidth=2.6,
                label=f"mean across treated repos (n≥3 per τ)")
    ax.axvline(0, color=ACCENT, linewidth=1.4, linestyle=(0, (4, 3)))
    ax.annotate("event quarter", (0, ax.get_ylim()[1]), color=ACCENT,
                fontsize=8, ha="center", va="bottom")
    _style(ax)
    ax.set_xlabel("quarters relative to rationalization event (τ)",
                  fontsize=9, color=INK)
    ax.set_ylabel("CQI (higher = more degraded)", fontsize=9, color=INK)
    ax.legend(frameon=False, fontsize=8, loc="upper left")
    ax.set_title("Codebase quality index around rationalization events",
                 fontsize=11, color=INK)
    fig.tight_layout()
    fig.savefig(P("10_event_study_cqi.png"), dpi=200)
    plt.close(fig)
    print("figures written: 10_cqi_small_multiples.png, 10_event_study_cqi.png")


if __name__ == "__main__":
    df, event_q = build()
    figures(df, event_q)
    print("done: 10_cqi_panel.csv")
