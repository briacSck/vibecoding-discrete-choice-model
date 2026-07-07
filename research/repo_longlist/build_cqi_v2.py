#!/usr/bin/env python3
"""
build_cqi_v2.py — second-generation state-variable construction.

REPRODUCIBILITY NOTE: this script does NOT touch any 10_* output. CQI v1
(build_cqi.py) remains runnable and its artifacts stay in place/git history.
Every deviation from v1 is listed here so the paper can narrate the path
from the locked spec to the revised index (user decision 2026-07-07: the
falsification-and-rebuild sequence is itself a reported result).

Deviations from v1, motivated by the v1 diagnosis (PC1 = 41.5% of variance
with mixed signs: latency +0.57, refactor +0.54 vs churn −0.49, backlog
−0.38 — i.e. PC1 confounded a scale/activity factor with a friction factor):

  1. SCALE ADJUSTMENT before aggregation. v1 fed raw-scale flows into
     pooled normalization, so big-active-repo variation dominated:
       - churn:  (adds+dels)/size_bytes  ->  (adds+dels) per human commit
       - backlog: delta / trailing-4q opened  ->  delta per contributor
       - latency, refactor share: already scale-free (unchanged)
     plus per-repo z-scoring of PIM stocks (v1 pooled min-max), which
     removes repo-level heterogeneity the DDC state should not carry.
  2. TWO-FACTOR MODEL. PCA retains two components; the component loading
     positively on latency+refactor is reported as CQI-F (friction — the
     debt-state candidate), the other as ACT (activity). v1 forced one PC.
  3. 2-SIGNAL ROBUSTNESS INDEX: mean of z-scored latency & refactor stocks.
  4. SENSITIVITY GRID: delta in {0.05, 0.09, 0.15} and stocks-vs-raw-flows,
     reported for CQI-F sign/shape stability.
  5. EVENT SET: only events.csv rows with debt_event == 1 (v1 used every
     dated event, including Zed's OSS transition and Turso's pivot).
  6. EVENT STUDIES ON COMPONENTS as well as composites (a flat composite
     can hide moving components).

Outputs (all new, 11_*):
  11_cqi_v2_panel.csv, 11_cqi_v2_loadings.txt,
  11_event_study_composites.png, 11_event_study_components.png,
  11_cqi_f_small_multiples.png, 11_sensitivity_grid.txt
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
QUARTERS = [q for q, _, _ in QTRIPLES]
QIDX = {q: i for i, q in enumerate(QUARTERS)}

DELTA_BASE = 0.09
DELTA_GRID = [0.05, 0.09, 0.15]

INK, MUTED, LINE, ACCENT, GRID = (
    "#33322E", "#8A8782", "#4C7C7C", "#B0483E", "#E4E2DD")


def pim(flows: pd.Series, delta: float) -> pd.Series:
    stock, prev = [], None
    for f in flows:
        if prev is None:
            prev = f if pd.notna(f) else 0.0
        else:
            prev = (1 - delta) * prev + (f if pd.notna(f) else 0.0)
        stock.append(prev)
    return pd.Series(stock, index=flows.index)


def zscore_by_repo(df, col):
    return df.groupby("repo")[col].transform(
        lambda s: (s - s.mean()) / s.std(ddof=0) if s.std(ddof=0) > 0 else s * 0)


def load_panel() -> pd.DataFrame:
    api = pd.read_csv(P("08_panel_data.csv"))
    git = pd.read_csv(P("09_git_metrics.csv"))
    df = api.merge(git, on=["repo", "quarter"], how="left")
    df["qidx"] = df["quarter"].map(QIDX)
    df = df.dropna(subset=["qidx"]).sort_values(["repo", "qidx"]).reset_index(drop=True)

    # ---- scale-adjusted flows (deviation 1) ----
    df["f_latency"]  = pd.to_numeric(df["pr_review_latency_median"], errors="coerce")
    df["f_refactor"] = pd.to_numeric(df["pr_refactor_ratio"], errors="coerce")
    df["f_churn"]    = (df["additions"] + df["deletions"]) / df["commits_git"].replace(0, np.nan)
    df["f_backlog"]  = df["issue_backlog_delta"] / df["contributor_count"].replace(0, np.nan)
    return df


SIGNALS = ["f_latency", "f_refactor", "f_churn", "f_backlog"]


def build_index(df: pd.DataFrame, delta: float, use_stocks: bool = True):
    """Returns (Z dataframe of per-repo z-scored series, loadings, varshares)."""
    cols = []
    for s in SIGNALS:
        col = ("S_" if use_stocks else "F_") + s[2:]
        if use_stocks:
            df[col] = df.groupby("repo")[s].transform(lambda x: pim(x, delta))
        else:
            df[col] = df[s]
        df["z" + col] = zscore_by_repo(df, col)
        cols.append("z" + col)

    X = df[cols].fillna(0.0).values
    corr = np.corrcoef(X.T)
    eigval, eigvec = np.linalg.eigh(corr)
    order = np.argsort(eigval)[::-1]
    eigval, eigvec = eigval[order], eigvec[:, order]

    # Friction component = the one of the top two loading most positively
    # on latency+refactor (deviation 2); orient both for interpretability.
    i_lat, i_ref = cols.index("z" + ("S_" if use_stocks else "F_") + "latency"), \
                   cols.index("z" + ("S_" if use_stocks else "F_") + "refactor")
    scores = [eigvec[i_lat, k] + eigvec[i_ref, k] for k in range(2)]
    k_f = int(np.argmax(np.abs(scores)))
    k_a = 1 - k_f
    w_f = eigvec[:, k_f] * np.sign(scores[k_f])
    w_a = eigvec[:, k_a]
    i_churn = cols.index("z" + ("S_" if use_stocks else "F_") + "churn")
    if w_a[i_churn] < 0:
        w_a = -w_a

    df["CQI_F"] = X @ w_f
    df["ACT"]   = X @ w_a
    df["CQI_2SIG"] = df[[cols[0], cols[1]]].mean(axis=1)  # latency+refactor
    var_shares = eigval / eigval.sum()
    return cols, (w_f, w_a), var_shares, (k_f, k_a)


def load_events():
    ev = pd.read_csv(P("events.csv"))
    debt = ev[(ev["debt_event"] == 1)].copy()
    return ev, debt


def event_quarter_map(df, debt_events):
    m = {}
    for _, row in debt_events.iterrows():
        repo = row["repo"]
        if isinstance(row["event_quarter"], str) and row["event_quarter"]:
            m[repo] = row["event_quarter"]
        elif row["dating_method"] == "peak_refactor":
            sub = df[df["repo"] == repo]
            if sub["f_refactor"].notna().any():
                m[repo] = sub.loc[sub["f_refactor"].idxmax(), "quarter"]
    return m


def _style(ax):
    ax.spines[["top", "right"]].set_visible(False)
    ax.spines[["left", "bottom"]].set_color(MUTED)
    ax.tick_params(colors=MUTED, labelsize=8)
    ax.grid(True, axis="y", color=GRID, linewidth=0.7)
    ax.set_axisbelow(True)


def aligned_plot(ax, df, ev_map, col, label):
    aligned = []
    for repo, eq in ev_map.items():
        sub = df[df["repo"] == repo].sort_values("qidx")
        tau = sub["qidx"] - QIDX[eq]
        ax.plot(tau, sub[col], color=MUTED, linewidth=0.8, alpha=0.5)
        aligned.append(pd.DataFrame({"tau": tau.values, "v": sub[col].values}))
    if aligned:
        al = pd.concat(aligned)
        mean = al.groupby("tau")["v"].agg(["mean", "count"])
        mean = mean[mean["count"] >= 3]
        ax.plot(mean.index, mean["mean"], color=LINE, linewidth=2.4)
    ax.axvline(0, color=ACCENT, linewidth=1.2, linestyle=(0, (4, 3)))
    ax.set_title(label, fontsize=9, color=INK)
    _style(ax)


def main():
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    df = load_panel()
    ev, debt = load_events()

    cols, (w_f, w_a), var_shares, (k_f, k_a) = build_index(df, DELTA_BASE, True)
    ev_map = event_quarter_map(df, debt)
    df["event_quarter_debt"] = df["repo"].map(ev_map)

    df.to_csv(P("11_cqi_v2_panel.csv"), index=False)

    with open(P("11_cqi_v2_loadings.txt"), "w", encoding="utf-8") as f:
        f.write("CQI v2 two-factor model (per-repo z-scored PIM stocks, "
                f"delta={DELTA_BASE})\n")
        f.write(f"variance shares (all PCs): "
                + ", ".join(f"{v:.3f}" for v in var_shares) + "\n")
        f.write(f"friction component = PC{k_f+1}, activity = PC{k_a+1}\n\n")
        f.write(f"{'signal':<14}{'CQI-F (friction)':>18}{'ACT (activity)':>16}\n")
        for c, wf, wa in zip(cols, w_f, w_a):
            f.write(f"{c:<14}{wf:>18.4f}{wa:>16.4f}\n")
        f.write("\ndebt-event set (events.csv debt_event==1): "
                + ", ".join(f"{r}@{q}" for r, q in sorted(ev_map.items())) + "\n")

    # sensitivity grid (deviation 4)
    with open(P("11_sensitivity_grid.txt"), "w", encoding="utf-8") as f:
        f.write("CQI-F loading stability across delta and stocks-vs-flows\n\n")
        for use_stocks in (True, False):
            for d in (DELTA_GRID if use_stocks else [None]):
                d2 = df.copy()
                cols2, (wf2, _), vs2, (kf2, _) = build_index(
                    d2, d if d else DELTA_BASE, use_stocks)
                tag = f"stocks delta={d}" if use_stocks else "raw flows"
                f.write(f"[{tag}] PC{kf2+1} var={vs2[kf2]:.3f}  loadings: "
                        + ", ".join(f"{c.split('_')[-1]}={w:+.3f}"
                                    for c, w in zip(cols2, wf2)) + "\n")

    # composites event study
    fig, axes = plt.subplots(1, 3, figsize=(12, 4), sharex=True)
    for ax, (col, lab) in zip(axes, [
            ("CQI_F", "CQI-F (friction factor)"),
            ("ACT", "Activity factor"),
            ("CQI_2SIG", "2-signal index (latency+refactor)")]):
        aligned_plot(ax, df, ev_map, col, lab)
    axes[0].set_ylabel("index (per-repo z units)", fontsize=9, color=INK)
    axes[1].set_xlabel("quarters relative to debt event (τ)", fontsize=9, color=INK)
    fig.suptitle("CQI v2 composites around verified debt events "
                 f"(n={len(ev_map)} treated repos)", fontsize=11, color=INK)
    fig.tight_layout(rect=[0, 0, 1, 0.94])
    fig.savefig(P("11_event_study_composites.png"), dpi=200)
    plt.close(fig)

    # components event study (deviation 6)
    comp_cols = [c for c in df.columns if c.startswith("zS_")]
    fig, axes = plt.subplots(1, len(comp_cols), figsize=(3.2 * len(comp_cols), 3.6),
                             sharex=True)
    for ax, c in zip(np.atleast_1d(axes), comp_cols):
        aligned_plot(ax, df, ev_map, c, c.replace("zS_", "stock: "))
    np.atleast_1d(axes)[0].set_ylabel("z units", fontsize=9, color=INK)
    fig.suptitle("CQI v2 components around verified debt events",
                 fontsize=11, color=INK)
    fig.tight_layout(rect=[0, 0, 1, 0.92])
    fig.savefig(P("11_event_study_components.png"), dpi=200)
    plt.close(fig)

    # CQI-F small multiples
    repos = sorted(df["repo"].unique())
    ncol, nrow = 4, int(np.ceil(len(repos) / 4))
    fig, axes = plt.subplots(nrow, ncol, figsize=(12, 2.1 * nrow),
                             sharex=True, sharey=True)
    for ax, repo in zip(axes.flat, repos):
        sub = df[df["repo"] == repo].sort_values("qidx")
        ax.plot(sub["qidx"], sub["CQI_F"], color=LINE, linewidth=1.7)
        if repo in ev_map:
            ax.axvline(QIDX[ev_map[repo]], color=ACCENT, linewidth=1.1,
                       linestyle=(0, (4, 3)))
        ax.set_title(repo.split("/")[-1], fontsize=9, color=INK, pad=3)
        _style(ax)
    for ax in axes.flat[len(repos):]:
        ax.axis("off")
    fig.suptitle("CQI-F (friction factor) by repository — dashed = verified "
                 "debt event", fontsize=11, color=INK)
    fig.tight_layout(rect=[0.01, 0, 1, 0.95])
    fig.savefig(P("11_cqi_f_small_multiples.png"), dpi=200)
    plt.close(fig)

    print("CQI v2 done. Friction loadings:",
          ", ".join(f"{c}={w:+.3f}" for c, w in zip(cols, w_f)))
    print("Debt-event set:", ev_map)


if __name__ == "__main__":
    main()
