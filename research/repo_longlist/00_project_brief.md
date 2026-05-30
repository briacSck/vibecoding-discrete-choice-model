# Project Brief: Codebase Rationalization in AI-Native Startups

## Study Goal

This paper asks: when do AI-native startups decide to clean up, rewrite, or systematically refactor the codebases they built using AI-assisted coding tools? The phenomenon — "codebase rationalization" — arises because AI code generation is fast but produces debt: inconsistent abstractions, redundant modules, fragile integrations. At some threshold of accumulated technical debt, the expected future cost of carrying forward the existing codebase exceeds the cost of rewriting it. The paper models this as a discrete replacement decision.

## Rust (1987) Model Context

Rust's (1987) bus engine replacement model is the structural template. In Rust's original setting, a transit authority decides each period whether to replace a bus engine (irreversible, costly) or continue operating with accumulated mileage. The decision depends on current mileage state, replacement cost, and expectations about future costs and shocks.

The adaptation here maps:
- **Bus engine** → the existing codebase (or a major architectural subsystem)
- **Mileage state** → accumulated technical debt proxy (code churn, PR latency, issue backlog growth, test coverage erosion)
- **Replacement decision** → a named rationalization event: migration, rewrite, deprecation, re-architecture
- **Operating cost** → per-period developer friction (PR review time, CI failure rate, issue resolution lag)
- **Replacement cost** → one-time cost of the refactor sprint / v2 rewrite (measurable by commit velocity and PR burst)

The key structural identification challenge is separating the state variable (debt accumulation) from the replacement threshold (organizational tolerance), which requires panel data and exogenous variation in replacement cost (e.g., new frameworks, founder/CTO transitions, funding shocks).

## Why GitHub Repo Panel Data

GitHub provides the only publicly observable, quarterly-resolution panel on codebase evolution for private companies. Key data layers:

- **Commits per quarter**: proxy for development intensity; pre/post-event patterns reveal replacement cost
- **Pull requests by label/title**: refactor/cleanup/rewrite/migration PRs are filterable; they proxy maintenance vs. feature work ratio
- **Issue tracker dynamics**: open issue backlog growth proxies operational friction / accumulated debt
- **CI/CD workflow changes**: addition of new test suites, linters, or migration tooling signals reorganization events
- **Code churn** (additions + deletions per quarter): high symmetric churn in non-feature quarters signals rationalization
- **Contributor concentration**: rationalization events often show temporary contributor concentration (core team doing cleanup)
- **Branch/PR naming conventions**: v2/, migration/, refactor/, rewrite/ branches are detectable

The panel window is **2023 Q1 through 2025 Q4** — 12 quarters. This window captures the AI coding tool adoption wave (Copilot GA: Oct 2022; GPT-4: Mar 2023) and a sufficient post-adoption horizon to observe debt accumulation and first rationalization cycles.

## What Signals Matter

**Primary signals (directly observable):**
1. Named rewrite/migration commits or PRs with temporal anchor (quarter identifiable)
2. Code churn spikes: quarters with deletions > additions suggest cleanup, not feature growth
3. Issue backlog level and growth rate per quarter
4. PR merge latency (proxy for reviewer friction)
5. CI workflow additions / restructuring (test coverage infrastructure investment)

**Secondary signals (contextual):**
6. Major version bumps (v1→v2, v2→v3) coincident with commit pattern breaks
7. Changelogs, blog posts, or release notes referencing architectural decisions
8. Contributor count changes around events (outsourcing rationalization to new hires)

**Identification strategy:**
Rationalization events must be distinguishable from normal feature velocity. The paper uses a difference-in-discontinuities approach: repos with confirmed events serve as treated units; repos with similar pre-event debt trajectories but no event serve as controls within the panel.

## Panel Window

**2023 Q1 (January 1, 2023) — 2026 Q1 (March 31, 2026)**

All sampled repos must show active commit history across this window. Repos that went OSS only after this window (e.g., Zed: Jan 2024 OSS release) are included but flagged for truncated pre-period.

## Target Sample Size

**Target: 20–30 repos** for the pilot scrape panel; **15–20** for the full econometric sample after feasibility verification.

Rationale: The structural model requires at least 8–10 treated units (confirmed rationalization events) and an equal number of clean controls. With 12 quarters per repo and quarterly-level observations, a 20-repo panel gives ~240 firm-quarter observations — sufficient for GMM/NFXP estimation given 5–7 state variables.

## Sampling Logic

Three strata:
1. **High-confidence treated** (confirmed rationalization event, high panel feasibility): target 10–12 repos
2. **High-confidence control** (active, mature, no confirmed event): target 6–8 repos
3. **Heterogeneity additions** (non-US, non-startup, unusual category): target 4–6 repos

Within each stratum, preference for:
- Open-core or fully OSS repos (public commit history)
- Repos with ≥ 3,000 commits in the panel window
- Organizations with identifiable technical leadership (for validation interviews)
- Geographic and product-type diversity (avoid all-US, all-infra samples)

## Contact Strategy

**Primary channel: GitHub Issues / Discussions**
Open a respectful academic inquiry issue citing the paper topic and requesting 20-min interview. Response rate ~15–25% for YC-backed founders.

**Secondary channel: LinkedIn**
CTO/tech lead direct message. Effective for Series A+ companies with professional profiles.

**Tertiary: Email via company website / academic network**
For gov-tech and civic-tech repos: use institutional contact pages.

**IRB note:** All contact is non-deceptive academic outreach. No PII collected beyond publicly available founder/CTO names. Repo commit metadata is public.
