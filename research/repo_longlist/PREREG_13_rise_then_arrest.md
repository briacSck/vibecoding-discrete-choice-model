# Pre-registration 13 — is "rise-then-arrest" real or mechanical?

Locked by commit BEFORE any of the analyses below are run (2026-11-21).
Results go to `13_robustness_raw.md` (script output) and are annotated
separately; this file is not edited after the run.

## Claim under test

Preprint v3 §7.3: CQI-F rises into the six verified debt events and plateaus
after them ("arrests rather than resets"), read as a narrow (S,s) band.

## Two mechanical alternatives that could produce the same picture

- **M1 — PIM persistence.** With delta = 0.09 a stock retains 91% per quarter.
  Even if friction *flows* fell sharply at tau = 0, the stock would look flat
  for several quarters. "Arrest" may be built into the measure.
- **M2 — PIM burn-in.** Stocks start at zero in 2023-Q1 and rise mechanically
  toward steady state f/delta. Four of six events fall in 2023-Q4..2024-Q3,
  so "rise into events" may be burn-in, not degradation.

## Fixed inputs

- Panel: `11_cqi_v2_panel.csv`; signals f_latency, f_refactor, f_churn,
  f_backlog exactly as built in `build_cqi_v2.py` (no re-definition).
- Events: the six debt events in `events.csv` (debt_event == 1).
  qdrant@2026-Q2 has no post-period: it enters pre-window statistics only.
- Windows: pre = tau in [-4, -1]; post = tau in [0, +4]; truncated by panel edges.
- Seed: zlib.crc32(b"prereg13"); placebo draws N = 5000.

## Tests and decision rules

**T1 — flow event study (addresses M1).** Within-repo z-scored flows, plus
the composite formed with the CQI-F loadings applied to z-scored flows.
Statistic: Delta_post = mean(post) − mean(tau in [-2, -1]).
"Arrest is not mechanical" requires the flow composite to show
Delta_post <= 0 (flows stop rising or fall after the event).
If flows keep rising post-event, the plateau in the stock is NOT evidence of
arrest.

**T2 — placebo event dates (addresses both).** For each event repo, draw a
pseudo-event quarter uniformly from quarters with >= 4 pre and >= 2 post
quarters available, excluding true event ±4. Recompute on stock CQI-F:
- RISE = mean(tau in [-1, 0]) − mean(tau in [-4, -3])
- KINK = (post slope over [0, +4]) − (pre slope over [-4, -1])
Claim survives only if the true RISE exceeds the 95th placebo percentile AND
the true KINK is below the 5th placebo percentile (one-sided each).

**T3 — burn-in correction (addresses M2).** Re-initialise every PIM stock at
its steady state, S_0 = mean(first 4 quarterly flows) / delta, rebuild CQI-F
with the same loadings procedure, and re-run T2.

## Pre-stated expectations and what each outcome means for the paper

- With six events, low power is expected. A null placebo result is the
  *likely* outcome and will be reported as a finding, not re-run.
- T1 fails or T2/T3 fail → §7.3 is downgraded to: "the stock pattern is not
  distinguishable from PIM persistence/burn-in at pilot scale"; the narrow
  (S,s) band reading moves to a hypothesis for the scaled sample.
- All three pass → claim stays, with placebo percentiles reported.
- No changes to delta, windows, event set, or signals after seeing results.
  Any additional analysis is labelled exploratory.
