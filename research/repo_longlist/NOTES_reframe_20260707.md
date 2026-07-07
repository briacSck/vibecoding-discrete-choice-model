# Reframe notes — 2026-07-07 (paper-ready content, versioned with the data)

Decisions confirmed by PI after the pilot-panel rebuild and CQI v1 results.
These four items MUST appear in the paper. Companion memory:
`paper-two-channel-ai-mechanism.md` (Claude project memory).

## 1. Two-channel AI mechanism (model section addition)

AI-assisted development shifts **both** structural objects of the Rust (1987)
replacement problem:

- **Transition channel** — the codebase state degrades faster per unit of
  feature output: AI generation is fast but produces inconsistent
  abstractions and redundant modules, so the debt-accumulation process
  F(q'|q, a=0) shifts toward faster degradation.
- **Cost channel** — the replacement cost RC falls: AI agents execute very
  large rewrites at a fraction of pre-AI engineering cost (exhibit: the Bun
  AI-rewrite PR oven-sh/bun#30412 and its HN discussion, flagged by a
  multi-startup CTO in the 2026-05-28 validation call).

Comparative statics: both channels lower the replacement threshold, so the
model's sharp testable prediction is that **rationalizations become more
frequent and less lumpy after AI adoption** — but the effect on total
maintenance share depends on which channel dominates, which is the empirical
question. This keeps the DDC model load-bearing (PI constraint: the Rust
component must not degrade into a toy section).

## 2. Continuous-maintenance result (limit case of 1)

The flat CQI v1 event study is consistent with the limit of prediction 1:
in mature AI-era repositories, debt paydown is continuous rather than lumpy
(Qdrant's "iterative storage-engine evolution" as archetype). If the lumpy
replacement margin is dissolving, that is an IT-management-economics finding
in its own right — the Rust-style stopping problem describes a vanishing
regime, and the relevant model becomes a continuous maintenance-intensity
choice (or an (S,s) band whose width shrinks with AI adoption).

## 3. Reflection path stays in the paper (results-analysis narrative)

Narrate, in order: (i) locked pre-registration-style CQI spec (5 signals →
PIM δ=0.09 → single scalar via first PC); (ii) pilot construction on the
rebuilt panel; (iii) falsification — PC1 carries 41.5% of variance with
mixed signs (latency +0.57, refactor +0.54 vs churn −0.49, backlog −0.38),
i.e. the first PC confounds an *activity/scale* factor with a *friction*
factor, and the aligned event study is flat; (iv) rebuild — scale-adjusted
signals, two-factor model, friction factor CQI-F as the state candidate;
(v) interpretation per §2. The epistemic trail is the point: the single-
scalar sufficiency assumption was flagged ex ante (PAPER_ENHANCEMENTS P0
item 3) and the pilot adjudicated it.

## 4. Identification: tool-release instrument (demotes SOC 2)

Adoption timing is plausibly driven by AI **tool releases interacted with
repo-level exposure** (language/stack suitability, monorepo structure), not
by the repo's current debt state. Evidence in-sample: PostHog's CLAUDE.md
first committed 2025-02-25, ≈3 weeks after Claude Code's public launch;
adoption dates are sharply staggered 2024-Q4→2025-Q4 across 12/14 repos.
Because adoption is dated from repository artifacts (config markers,
co-author trailers), the design scales to samples far beyond the
contact-constrained pilot **without per-organization confirmation** — the
14-repo panel was sized for org outreach, not by data availability. SOC 2
timing moves to a cost-shifter robustness role at most.

## Data-provenance corrections logged 2026-07-07 (cite carefully)

- Dagger's rewrite is **Project Zenith** (v0.9.0, 2023-10-20); the
  "Project Theseus" name in early research notes was erroneous.
- Trigger.dev v3 stable: 2024-Q3 (tags 2024-09-18), not Q2.
- Turso pivot announced 2023-01-30 (2023-Q1).
- Appwrite v2.0: right-censoring confirmed — no 2.x tag through 2026-06.
- Inngest's documented "v1→v2 SDK rewrite" lives in inngest-js, not the
  panel repo; server v1.0.0 (2024-09-20) used as the panel-repo anchor.
- Zed's published history includes pre-2024 commits (not left-censored in
  commits; issues/PRs only).
- PostHog "rewrite" commits cluster 2026-05/06 — candidate in-window event
  after the panel extension to 2026-Q2.
- Astral/OpenAI acquisition announced 2026-03-19 → 2026-Q1 structural-break
  flag for ruff in the extended panel.
