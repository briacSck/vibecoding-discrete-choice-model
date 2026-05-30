# Screening Rubric — Codebase Rationalization Paper
## Mechanical Candidate Inclusion/Exclusion Guide

Use this rubric to evaluate new candidates as they are identified after the initial longlist. Apply the gatekeeping checklist first; if any hard gate fails, exclude immediately without scoring.

---

## Part 1: Gatekeeping Checklist (Hard Yes/No)

Fail **any one** of these questions → **EXCLUDE immediately**

| # | Gate Question | Fail Condition |
|---|--------------|----------------|
| G1 | Is the primary repo publicly accessible on GitHub? | Repo is private, archived before 2023, or deleted |
| G2 | Is there commit activity within the 2023 Q1 – 2025 Q4 window? | Zero commits in any 4+ consecutive quarters during panel window |
| G3 | Does the repo have ≥ 1,000 total commits? | Fewer than 1,000 total commits — insufficient data density for panel |
| G4 | Is the organization an identifiable legal entity (startup, company, gov agency)? | Anonymous collective, personal account without org, or purely community-governed without identifiable sponsor |
| G5 | Is the repo the organization's primary or core product repo (not peripheral OSS tooling)? | Repo is a side library, design system only, or documentation repo with no application logic |
| G6 | Is the organization headquartered or operating in a country where English-language academic outreach is feasible? | HQ in country with significant outreach barriers (e.g., China, Iran) AND no English-speaking technical lead identified |
| G7 | Is the repo's primary codebase within the panel window (not retroactively OSS'd with no pre-OSS history)? | Repo went OSS after Dec 2024, giving fewer than 2 quarters of history |
| G8 | Does the organization have ≥ 3 identifiable contributors in the panel window? | Fewer than 3 contributors — solo project not eligible |

---

## Part 2: Seven-Dimension Scoring Guide

For each dimension, assign a score of 1, 3, or 5 using the anchors below. Intermediate values (2, 4) are permitted when a candidate clearly falls between anchors.

### Dimension 1: Repo Richness (weight 20%)

Measures: commit density, PR/issue depth, CI quality.

| Score | Anchor description |
|-------|--------------------|
| 5 | ≥ 20,000 total commits; ≥ 100 open PRs or documented PR history; CI with ≥ 50 workflow files; active issue tracker with ≥ 200 issues |
| 3 | 5,000–19,999 commits; moderate PR history; CI present with 10–49 workflows; issue tracker with 50–199 issues |
| 1 | < 5,000 commits; sparse PR history; CI absent or < 10 workflows; issue tracker empty or < 50 issues |

### Dimension 2: Panel Feasibility (weight 25%)

Measures: steady quarterly activity across 2023 Q1 – 2025 Q4.

| Score | Anchor description |
|-------|--------------------|
| 5 | Active every quarter in panel window; commit velocity consistent (< 50% quarter-to-quarter variance); no dormant periods |
| 3 | Active in ≥ 10 of 12 quarters; some variance in velocity but no multi-quarter gaps; Agent E rating ≥ 3 if available |
| 1 | Active in < 8 of 12 quarters; major gaps; repo may have been dormant or pre-dated panel window |

### Dimension 3: Rationalization Event Visibility (weight 20%)

Measures: named/documented refactor or rewrite event with temporal marker.

| Score | Anchor description |
|-------|--------------------|
| 5 | Named event with blog post, changelog, or public announcement; ≥ 100 PRs explicitly labeled with event name/type; event dates pinnable to specific quarter |
| 3 | Partial evidence — architectural changes visible in commit history or PR titles but no formal announcement; event timing estimable but not certain |
| 1 | No evidence of named rationalization event; repo shows steady feature development with no visible architectural discontinuity; score 1 for unknown, 1 for confirmed no-event (potential control unit) |

### Dimension 4: External Metadata Availability (weight 10%)

Measures: funding data, website, LinkedIn, founding year linkable.

| Score | Anchor description |
|-------|--------------------|
| 5 | Crunchbase/PitchBook funding data available; company website with about page; founding year confirmed; ≥ 2 named founders/executives with LinkedIn profiles |
| 3 | Partial metadata — some funding info available (e.g., YC batch known but round sizes uncertain); website exists; ≥ 1 named founder |
| 1 | Minimal metadata — no funding data; no website; founding year unknown; no named executives |

### Dimension 5: Contactability (weight 5%)

Measures: identified CTO or tech lead with accessible contact route.

| Score | Anchor description |
|-------|--------------------|
| 5 | Named CTO/tech lead with LinkedIn + GitHub profile; YC or academic network connection exists; company email pattern known; prior public media/blog presence |
| 3 | Named founder/tech lead identifiable via GitHub or company website; no direct academic network connection; contact requires cold outreach |
| 1 | No named technical lead; anonymous GitHub org; contact only via generic info@ email |

### Dimension 6: Causal Interpretability (weight 15%)

Measures: company is the identifiable decision-maker; not foundation/CNCF/DAO-governed.

| Score | Anchor description |
|-------|--------------------|
| 5 | Single startup or company owns the repo; all architectural decisions traceable to internal engineering team; no external governance layer; clear principal hierarchy |
| 3 | Company is primary decision-maker but shares governance (e.g., CNCF incubation, OSS foundation with corporate sponsor); or company has multiple subsidiary teams with unclear authority |
| 1 | Foundation or community governance without clear corporate principal; decisions made by committee or democratic vote; no identifiable single decision-maker |

### Dimension 7: Heterogeneity Value (weight 5%)

Measures: adds geographic, product-type, maturity, or category diversity to the sample.

| Score | Anchor description |
|-------|--------------------|
| 5 | Adds 2+ distinct dimensions of diversity (e.g., non-US + non-startup category + unusual maturity level) not already represented in the priority-tier-A sample |
| 3 | Adds 1 clear dimension of diversity not already well-represented (e.g., only European representative in a product type, or only gov-tech representative) |
| 1 | Substantially duplicates existing sample (e.g., another US startup infra tool with similar maturity and stack) |

---

## Part 3: Scoring Formula

```
weighted_score = (0.20 × repo_richness)
              + (0.25 × panel_feasibility)
              + (0.20 × rationalization_event_visibility)
              + (0.10 × external_metadata_availability)
              + (0.05 × contactability_score)
              + (0.15 × causal_interpretability)
              + (0.05 × heterogeneity_value)
```

Maximum possible score: 5.00  
Minimum meaningful score: 1.00

---

## Part 4: Decision Rules

| Weighted Score | Panel Feasibility Score | Decision |
|---------------|------------------------|----------|
| ≥ 4.00 | ≥ 4 | **INCLUDE — Priority Tier A** |
| 3.50 – 3.99 | ≥ 3 | **INCLUDE — Priority Tier B** (flag any concerns) |
| 3.00 – 3.49 | ≥ 3 | **INCLUDE — Priority Tier C** (heterogeneity only; do not use as primary treated unit) |
| 3.00 – 3.49 | < 3 | **HOLD** — verify panel feasibility before including |
| < 3.00 | any | **EXCLUDE** — insufficient quality for panel construction |
| Any score | Panel feasibility = 1 | **EXCLUDE** regardless of other scores — cannot build quarterly panel |

**Override rule:** A candidate with weighted score < 3.50 may be included as a Tier C heterogeneity candidate if it is the *only* representative of a geographic region or product category in the sample. Document the override reasoning explicitly.

---

## Part 5: Worked Examples

### Example A — High-scoring candidate: PostHog

| Dimension | Score | Rationale |
|-----------|-------|-----------|
| Repo richness | 5 | 43,516 commits; 10,256+ refactor PRs; 582+ CI workflows; 3,040 open issues |
| Panel feasibility | 5 | Continuously active 2023–2025; Agent E rating = 5 |
| Rationalization event visibility | 5 | AI arch rebuilt twice; blog posts; PR labels; dates pinnable |
| External metadata | 5 | YC W20; Series C; Crunchbase; website; named CTO |
| Contactability | 5 | Tim Glaser publicly active; LinkedIn + GitHub + YC network |
| Causal interpretability | 5 | Single startup; Tim Glaser + James Hawkins as identifiable decision-makers |
| Heterogeneity value | 3 | UK adds geo diversity; product analytics distinct from infra tools |

**Weighted score:** 0.20(5) + 0.25(5) + 0.20(5) + 0.10(5) + 0.05(5) + 0.15(5) + 0.05(3) = 1.00 + 1.25 + 1.00 + 0.50 + 0.25 + 0.75 + 0.15 = **4.90**  
**Decision: INCLUDE — Priority Tier A**

---

### Example B — High-scoring candidate with flag: Trigger.dev

| Dimension | Score | Rationale |
|-----------|-------|-----------|
| Repo richness | 4 | 7,274 commits; 892 refactor PRs; 190+ CI workflows; rich event labeling |
| Panel feasibility | 5 | Continuously active; Agent E rating = 5; 62 open PRs |
| Rationalization event visibility | 5 | v3 rewrite documented; 1,625 v3/rewrite PRs; changelog published |
| External metadata | 5 | YC W23; Series A; identifiable CEO |
| Contactability | 5 | Matt Aitken active on GitHub + Twitter; YC alumni |
| Causal interpretability | 5 | Single startup; Matt Aitken identifiable as tech decision-maker |
| Heterogeneity value | 4 | Ireland is the only Irish representative; workflow automation distinct |

**Weighted score:** 0.20(4) + 0.25(5) + 0.20(5) + 0.10(5) + 0.05(5) + 0.15(5) + 0.05(4) = 0.80 + 1.25 + 1.00 + 0.50 + 0.25 + 0.75 + 0.20 = **4.75**  
**Decision: INCLUDE — Priority Tier A** (Ireland HQ flag noted but does not lower decision)

Note: Minor rounding differences from the scored CSV reflect conservative estimation choices made during batch scoring. The worked example is intended to illustrate anchor application, not precisely reproduce batch scores.

---

### Example C — Low-scoring candidate (excluded): OpenStatus

| Dimension | Score | Rationale |
|-----------|-------|-----------|
| Repo richness | 2 | Small repo; limited PR depth; thin CI |
| Panel feasibility | 2 | 2-person team; activity likely sporadic |
| Rationalization event visibility | 1 | No known event |
| External metadata | 2 | Bootstrapped; no funding data |
| Contactability | 1 | No identifiable institutional leader |
| Causal interpretability | 2 | Indie project; decisions not organizationally interpretable |
| Heterogeneity value | 3 | France adds geo; uptime monitoring is distinct |

**Weighted score:** 0.20(2) + 0.25(2) + 0.20(1) + 0.10(2) + 0.05(1) + 0.15(2) + 0.05(3) = 0.40 + 0.50 + 0.20 + 0.20 + 0.05 + 0.30 + 0.15 = **1.80**  
**Decision: EXCLUDE — score < 3.00; also fails G8 (< 3 identifiable contributors)**

---

## Part 6: Quick-Reference Flag Taxonomy

These flags do not automatically exclude but must be documented and considered in interpretation:

| Flag | Meaning | Handling |
|------|---------|---------|
| `geo:nonUS-EU` | HQ outside US/EU (India, Israel, Brazil) | Keep if contactability ≥ 3; note in panel documentation |
| `org:govtech` | Government or quasi-public entity | Lower causal interpretability score; keep for heterogeneity |
| `org:foundation` | CNCF, Apache, or similar foundation governance | Lower causal interpretability; require identifiable corporate sponsor |
| `event:truncated` | OSS'd mid-panel; pre-event history missing | Keep if ≥ 6 post-event quarters; flag in panel as left-censored |
| `event:bydesign` | Rewrite was intentional from project inception (e.g., Bun) | Different causal mechanism; keep but distinguish from reactive rationalization |
| `domain:crypto` | Crypto/blockchain domain | Flag for regulatory confounds; keep if architectural event is domain-agnostic |
| `org:dissolved` | Original team dissolved; OSS revival | Keep if revival is itself the rationalization event of interest; flag for org discontinuity |
| `acquisition` | Acquired or pivoted during panel window | Treat acquisition date as structural break in panel; keep with care |
