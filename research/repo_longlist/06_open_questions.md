# Open Questions & Follow-Up Actions

## Status as of 2026-05-30 (post verify_feasibility.py run)

This document tracks unresolved uncertainties, data gaps, and methodological questions that must be addressed before pilot scraping begins. Items are grouped by type and include a recommended action and priority.

---

## 1. Metadata Gaps Requiring Follow-Up

### 1.1 Helicone — rationalization event unconfirmed
**Gap:** No documented rationalization event identified. The repo is YC-backed and active, but Agent D and E found no named rewrite or migration.
**Action:** Manually inspect PR titles and commit messages 2023–2025 for refactor/migration patterns. Check Helicone blog (helicone.ai/blog) for architecture posts.
**Priority:** Medium — potential control unit even without event; worth confirming before assignment to control group.

### 1.2 Langfuse — ClickHouse migration status unclear
**Gap:** Agent D flagged a "partial" ClickHouse migration but did not confirm completion date or PR count.
**Action:** Search GitHub for PRs containing "clickhouse" in Langfuse/langfuse repo. Check release notes for migration announcement. Confirm whether event falls in 2023–2025 window.
**Priority:** High — if confirmed, Langfuse moves from partial-event to confirmed-treated unit.

### 1.3 Dub.co — no rationalization event signal
**Gap:** 24,702 commits and 3 Agent E feasibility but no known rationalization event. Could be a clean control or have undocumented event.
**Action:** Sample 50–100 PRs from 2023–2025 for refactor/cleanup labels. Check changelog or blog for architecture announcements.
**Priority:** Low — good control candidate regardless.

### 1.4 Chatwoot — no rationalization event signal
**Gap:** YC W21, mature Ruby/Rails product, no known event. Panel feasibility estimated but not Agent E-verified.
**Action:** Check Chatwoot GitHub for migration PRs (e.g., Ruby version upgrades, DB migrations, API rewrites). Check blog for v3 or rewrite announcements.
**Priority:** Low — potentially a good control; confirm event-free status before assigning to control group.

### 1.5 Formbricks — no event and no verified commit counts
**Gap:** GitHub Accelerator cohort; no Agent E data; no known event. Repo size and activity unknown.
**Action:** Retrieve total commit count and quarterly activity for 2023–2025. Assess whether repo meets G3 gate (≥ 1,000 commits).
**Priority:** Medium — may need to be downgraded to Tier C or excluded if commit count is too low.

### 1.6 Documenso — no event and no Agent E verification
**Gap:** OSS Capital-backed eSignature tool; no confirmed event; no panel feasibility rating from Agent E.
**Action:** Retrieve commit counts, PR history. Check for monorepo restructuring or stack migration PRs.
**Priority:** Medium — useful control candidate if feasibility confirmed.

### 1.7 Appwrite v2.0 rewrite — announcement vs. completion
**Gap:** v2.0 rewrite was "announced" per Agent D but completion date is unclear. If still in progress during panel window, the event may be right-censored.
**Action:** Check Appwrite GitHub releases and blog for v2.0 launch date. Determine whether v2.0 shipped within 2023–2025 window.
**Priority:** High — affects whether Appwrite is treated (event completed) or in-progress (event right-censored) in the panel.

### 1.8 Novu v2.0 — inbox/workflows layer timing
**Gap:** v2 rewrite confirmed for 2024 but specific quarter is unverified.
**Action:** Check Novu GitHub releases for v2.0 release tag date. Pin to specific quarter.
**Priority:** High — needed to anchor treatment timing.

---

## 2. Repos Where GitHub Feasibility Was Not Fully Verified (Rate-Limited)

**STATUS: RESOLVED — verify_feasibility.py run on 2026-05-30.**  
Raw data: `07_feasibility_panel.csv` (132 repo-quarter rows), `07_feasibility_scores.csv` (11 summaries).  
All scores updated in `03_scored_candidates.csv`; tier promotions and exclusions reflected in `04_top_candidates.md`.

| Repo | Estimated | Verified | Score changed | Outcome |
|------|-----------|----------|---------------|---------|
| Helicone/helicone | 3 | **5** | YES | B stays B; ws 3.25→3.75 |
| Hoppscotch/hoppscotch | 3 | **5** | YES | C→B; ws 3.20→3.70 |
| Chatwoot/chatwoot | 3 | **5** | YES | B stays B; ws 3.40→3.90 |
| Formbricks/formbricks | 3 | **5** | YES | C→B; ws 3.00→3.50 |
| Documenso/documenso | 3 | **4** | YES | C stays C; ws 3.20→3.45 |
| maybe-finance/maybe | 3 | **1** | YES | **EXCLUDED — G2 gate fail** (zero commits 2023 Q1–Q4 + 2025-Q4) |
| Qdrant/qdrant | 3 | **5** | YES | **B→A**; ws 3.70→4.20 |
| Turso/libsql | 3 | **4** | YES | **B→A**; ws 3.95→4.20 |
| Inngest/inngest | 3 | **5** | YES | **B→A**; ws 3.95→4.45 |
| Milvus/milvus | 4 | **5** | YES | **B→A**; ws 4.15→4.40 |
| Bun/bun | 4 | **5** | YES | **B→A**; ws 4.05→4.30 |

**Net result:** 5 repos promoted to Tier A (qdrant, turso, inngest, milvus, bun); 2 repos promoted from Tier C to B (hoppscotch, formbricks); 1 excluded (maybe-finance); 0 downgrades. Tier A pool grows from 12 → 17 repos.

---

## 3. Borderline Geographic/Category Cases Requiring Interpretive Decisions

### 3.1 Gov-tech candidates (pass-culture, ma-cantine, mon-entreprise, rdv-service-public)
**Issue:** Four French gov-tech repos from the beta.gouv.fr and pass-culture programs are in the screened sample. The paper's model assumes cost-benefit rationalization by a profit-maximizing org. Gov-tech may rationalize for compliance or political reasons, not debt-cost reasons.
**Decision needed:** Should gov-tech be a separate stratum with different structural assumptions, or excluded from the main panel and analyzed descriptively? If included, how does the paper model the replacement cost for an org without a funding constraint?
**Recommendation:** Include 1–2 as a heterogeneity stratum; exclude from primary identification sample. pass-culture has the strongest data (49,061 commits, 9,228 refactor PRs) and is the most defensible inclusion.

### 3.2 Milvus/Zilliz — CNCF governance vs. Zilliz commercial principal
**Issue:** Milvus is CNCF-hosted, meaning the formal governance is a foundation committee. But Zilliz employees make most commits and the v2.0 rewrite was a Zilliz-driven decision.
**Decision needed:** Is Zilliz an acceptable "org" for the paper's purposes, or does CNCF governance make causal attribution too uncertain?
**Recommendation:** Include with flag; treat Zilliz as the decision-maker and document the CNCF wrapper as a causal complexity rather than a disqualifier.

### 3.3 Decidim — Barcelona City Council origin
**Issue:** Decidim is now governed by a civic association (Metadecidim) and has contributions from multiple municipalities. The "company" making rationalization decisions is a multi-principal civic body.
**Decision needed:** Is Decidim too multi-principal to support causal identification? Or is it a useful edge case for multi-stakeholder rationalization?
**Recommendation:** Downgrade to Tier C (heterogeneity only); do not use as a primary treated unit. Include if the paper has a section on non-firm rationalization contexts.

### 3.4 Maybe Finance — org discontinuity *(MOOT — EXCLUDED 2026-05-30)*
**Issue:** The original Maybe Finance team wound down ~2022; a different team revived the project as OSS in 2023. Are these the same "organization" for panel purposes?
**Resolution:** Excluded by G2 gate fail. verify_feasibility.py confirmed zero commits in all four 2023 quarters — the revival team built on a private fork before going OSS in early 2024. The public repo's 2023 history is entirely absent, making a 12-quarter panel impossible. No interpretive decision needed; excluded from sample.

### 3.5 Astral (ruff/uv) — OpenAI acquisition/partnership ~2025
**Issue:** If Astral was acquired by or formally partnered with OpenAI in ~2025, the post-acquisition quarters may reflect OpenAI's organizational priorities rather than Astral's. This is a structural break in the panel.
**Decision needed:** Confirm acquisition date. If acquisition falls within panel window (e.g., mid-2025), truncate panel at acquisition date or add acquisition as a covariate.
**Action:** Verify Astral/OpenAI deal date and structure from news sources.
**Priority:** High.

---

## 4. Methodological Open Questions for Panel Construction

### 4.1 How to define the "codebase state" variable
The Rust (1987) model requires a scalar or low-dimensional state variable (analogous to mileage). For this paper, the state variable is "accumulated technical debt." Candidates for measurement:
- PR review latency (median days from open to merge per quarter)
- Ratio of refactor PRs to feature PRs per quarter
- Code churn ratio (deletions / additions per quarter)
- Issue backlog growth rate
- Test coverage (if tracked in CI)

**Open question:** Which of these is most observable via GitHub API, and which best maps to the theoretical state variable? None captures debt directly — this is a measurement model question requiring literature review and/or instrument validation.

### 4.2 How to identify the rationalization event date
For repos with named events (e.g., Trigger.dev v3, Infisical MongoDB→Postgres), the event date can be pinned to a specific PR merge or release tag. For partial events (iterative refactors), there is no clean date.

**Open question:** Should partial-event repos be included as "fuzzy treated" units (with event date estimated as the quarter of peak refactor PR volume)? Or excluded from the treated group and used as controls?

### 4.3 Confounders: funding rounds vs. rationalization
Many rationalization events coincide with Series A/B funding (Trigger.dev v3 ~ Series A; Airbyte CDK v2 ~ post-Series B). Funding rounds increase engineering headcount and may mechanically increase refactoring capacity.

**Open question:** Should funding rounds be included as covariates in the structural model? Source: Crunchbase/PitchBook. Risk: funding data is often imprecise in timing.

### 4.4 Multi-repo organizations
Several candidates have activity spread across multiple repos (e.g., Astral has ruff, uv, rye; Dagger has dagger, dagfun, SDKs). Should the unit of analysis be a single primary repo, the org's total GitHub activity, or the relevant subsystem repo?

**Recommendation:** Primary repo as unit of analysis; note secondary repos for cross-referencing event signals. Document multi-repo structures in panel metadata.

### 4.5 Contributor identification and turnover
The Rust model treats the decision-maker as a stable agent. In practice, CTO/lead engineer turnover may shift the rationalization threshold mid-panel.

**Open question:** Should contributor turnover (measurable via GitHub author history) be included as a covariate? How to handle cases like Maybe Finance (full team replacement)?

### 4.6 Right-censoring: in-progress rewrites at panel end
Several candidates (Appwrite v2.0, some gov-tech repos) may have events that are still in progress as of 2025 Q4. These are right-censored in the panel.

**Open question:** How to handle right-censored rationalization events in the NFXP estimator? Standard survival analysis techniques may apply, but the structural model may need modification.

---

## 5. Next Steps Before Pilot Scraping Begins

Listed in recommended execution order:

1. **Resolve metadata gaps** (Section 1 items): Confirm ClickHouse migration for Langfuse; confirm Appwrite v2.0 launch date; pin Novu v2.0 to specific quarter. Estimated time: 2–3 hours manual GitHub inspection.

2. ~~**Verify GitHub feasibility for 11 unrated repos** (Section 2)~~ **DONE (2026-05-30)** — verify_feasibility.py run; all 11 scores updated in 03_scored_candidates.csv. See Section 2 above for results table.

3. **Make interpretive decisions on borderline cases** (Section 3): Decide gov-tech stratum treatment; confirm Astral/OpenAI acquisition date; decide on Milvus/CNCF inclusion. Requires PI decision, not research assistant work.

4. **Define measurement model for state variable** (Section 4.1): Settle on 2–3 observable proxies for technical debt accumulation. Requires literature review of software engineering metrics (e.g., Tornhill 2015 on code hotspots; Lehman's Laws of software evolution).

5. **Write GitHub API scraping script** for pilot: Target the 10 Tier-A candidates. Collect quarterly commit counts, PR label distributions, issue backlog snapshots, and code churn (additions + deletions) per quarter for 2023–2025. Implement rate-limit handling.

6. **Conduct 3–5 validation interviews** with Section B contacts (PostHog, Dagger, Infisical, Trigger.dev as first targets) to validate measurement model assumptions before full data collection.

7. **Finalize panel structure** after pilot: Based on interview findings and pilot data, confirm event dates, adjust state variable operationalization, and finalize the 20–25 repo panel.
