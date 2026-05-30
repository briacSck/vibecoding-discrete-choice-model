# Top Candidates — Codebase Rationalization Paper

## Section A — Top 10 for Pilot Scrape

These repos combine the highest weighted scores (≥ 4.45) with confirmed panel feasibility ≥ 4 from Agent E, making them the best starting point for quarterly panel construction. Rankings reflect corrected arithmetic scores from 03_scored_candidates.csv.

---

### 1. PostHog
**GitHub:** https://github.com/PostHog/posthog  
**Country:** UK  
**Product type:** Product Analytics (Mature startup, YC W20, Series C)  
**Weighted score:** 4.90

**Rationale:** PostHog is the strongest candidate in the sample. With 43,516 total commits and over 10,256 refactor-labeled PRs, the repo has exceptional data density across the full 2023–2025 panel window. The AI architecture was documented as rebuilt twice, giving the paper at least two identifiable treatment dates with pre- and post-event quarter coverage. Tim Glaser (CTO) is publicly identifiable via YC network and LinkedIn, making validation interviews tractable.

**Key signals to scrape:** Quarterly commit volume, PR labels (refactor/cleanup/migration), issue backlog growth, CI workflow file changes, code churn per quarter, contributor concentration around event dates.

**Main risk:** The repo is very large (582+ CI workflows), which may create noise in automated scraping; careful label filtering will be needed to isolate rationalization events from routine feature work.

---

### 2. Infisical
**GitHub:** https://github.com/Infisical/infisical  
**Country:** USA  
**Product type:** Secret Management (Growth startup, YC W23, Series A)  
**Weighted score:** 4.85

**Rationale:** Infisical has one of the cleanest rationalization events in the sample — a documented MongoDB-to-PostgreSQL migration with blog-level write-up and traceable PRs. With 23,166 commits and 894 postgres/migration PRs, the event is temporally pinned and quantitatively strong. Maidul Islam (CEO) and the YC network provide a direct outreach route. The panel window coverage is confirmed active across 2023–2025.

**Key signals to scrape:** MongoDB/PostgreSQL-labeled PRs by quarter, code deletion volume during migration window, CI test coverage changes pre/post migration, contributor count around migration sprint.

**Main risk:** Secret management is a narrower niche; if the paper needs product-type diversity, Infisical pairs best with infra-adjacent candidates rather than standing alone.

---

### 3. Dagger
**GitHub:** https://github.com/dagger/dagger  
**Country:** USA  
**Product type:** CI/CD Engine (Growth, Company-backed OSS, Series B)  
**Weighted score:** 4.85

**Rationale:** Dagger's "Project Theseus" rewrite is a named, documented, and unusually philosophically deliberate rationalization event — the team publicly committed to rewriting the entire execution engine from scratch in Go while keeping the API surface stable. Solomon Hykes (Docker creator, founder/CTO) is among the most identifiable and outreach-accessible technical leaders in open-source. The 11,257-commit base with 1,062 refactor PRs and 157 Project Theseus-specific PRs provides clean event labeling.

**Key signals to scrape:** Project Theseus branch/PR labels by quarter, Go SDK commit surge timing, deprecated SDK removal PRs, contributor count during rewrite, CI failure rate pre/post rewrite.

**Main risk:** Solomon Hykes' public profile may mean the team receives many academic requests; response rate uncertain despite high identifiability.

---

### 4. Trigger.dev
**GitHub:** https://github.com/triggerdotdev/trigger.dev  
**Country:** Ireland  
**Product type:** Workflow Automation (Growth startup, YC W23, Series A)  
**Weighted score:** 4.75

**Rationale:** Trigger.dev's v3 rewrite is documented in changelog, blog posts, and 1,625 v3/rewrite-labeled PRs — one of the highest event-signal densities in the sample. The 7,274-commit base and 892 refactor PRs provide rich quarterly variation. Ireland HQ adds geographic diversity (only Irish representative in the sample). Matt Aitken (CEO) is active on GitHub and identifiable via YC alumni network.

**Key signals to scrape:** v3-labeled PR counts by quarter, new runtime commit volume, deprecated v2 code deletion pattern, test suite restructuring PRs, commit velocity discontinuity around v3 launch.

**Main risk:** Ireland HQ may affect survey response logistics (time zone, institutional IRB cross-jurisdiction) but this is minor.

---

### 5. Appwrite
**GitHub:** https://github.com/appwrite/appwrite  
**Country:** Israel  
**Product type:** Backend-as-a-Service (Growth startup, Series A)  
**Weighted score:** 4.65

**Rationale:** Appwrite's 35,346-commit base and confirmed v2.0 execution engine rewrite place it among the strongest treated units in the sample. With 102+ CI workflows and active quarterly velocity, the panel is well-supported. Eldad Fux (CEO/founder) is highly active in OSS communities and on GitHub, making validation outreach tractable. The backend-as-a-service product type is distinct from other high-scoring infra candidates.

**Key signals to scrape:** v2.0 rewrite PR labels by quarter, execution engine commit surge, function runtime deprecation patterns, SDK migration PRs, contributor concentration during rewrite sprint.

**Main risk:** Israel HQ adds a mild IRB cross-jurisdiction note; v2.0 completion date needs pinning to confirm the event falls within the 2023–2025 panel window (see 06_open_questions.md item 1.7).

---

### 6. Airbyte
**GitHub:** https://github.com/airbytehq/airbyte  
**Country:** USA  
**Product type:** ETL/Data Integration (Mature, Company-backed OSS, Series B ~$150M)  
**Weighted score:** 4.60

**Rationale:** Airbyte combines the highest raw commit count among active candidates (46,659) with a documented Python CDK v2 migration and very rich CI infrastructure (505+ workflows). The organization is well-funded with an identifiable CEO (Michel Tricot) and a substantial engineering team whose rationalization decisions are likely driven by organizational rather than individual factors — which is the causal story the paper needs. The ETL/data integration product type is distinct from other high-scoring candidates.

**Key signals to scrape:** CDK v2 migration PR timeline, connector-level refactor burst by quarter, Python deprecation pattern, CI config changes, issue closure rate during migration window.

**Main risk:** Very large repo may require filtering to the core engine rather than all connectors; breadth of codebase could dilute signal.

---

### 7. Zed Industries
**GitHub:** https://github.com/zed-industries/zed  
**Country:** USA  
**Product type:** Code Editor (Growth startup, Sequoia Series B)  
**Weighted score:** 4.60

**Rationale:** Zed's full OSS transition in January 2024 is a distinct rationalization event type — not a debt-driven refactor but an architectural and licensing decision to fully open the codebase. With 38,051 commits in the available window and 664 open PRs, the repo is data-dense. Nathan Sobo (CEO) is highly identifiable and has discussed the OSS decision publicly. Sequoia-backing provides institutional credibility for outreach.

**Key signals to scrape:** Pre/post-OSS-transition commit velocity, contributor count growth post-transition, CI infrastructure additions, licensing file changes, code cleanup PRs immediately pre-transition.

**Main risk:** Pre-2024 commit history is absent from the public repo (the codebase was private before Jan 2024), creating left-censoring that limits pre-event state variable estimation.

---

### 8. LedgerHQ (ledger-live)
**GitHub:** https://github.com/LedgerHQ/ledger-live  
**Country:** France  
**Product type:** Crypto Wallet (Mature startup, Series C)  
**Weighted score:** 4.55

**Rationale:** LedgerHQ's monorepo migration (multi-repo to turborepo) is a well-defined architectural rationalization event with strong commit-level traceability. The 54,230-commit base is the highest in the sample, and 1,735 refactor PRs provide excellent quarterly variation. France HQ adds geographic diversity. Charles Guillemet (CTO) is publicly identifiable.

**Key signals to scrape:** Turborepo migration PR timeline, monorepo consolidation commit burst, package.json structure changes, CI refactoring events, pre/post migration PR review latency.

**Main risk:** Crypto domain may introduce product-specific confounds (regulatory shocks, token price cycles) that are hard to separate from architectural rationalization timing.

---

### 9. Weaviate
**GitHub:** https://github.com/weaviate/weaviate  
**Country:** Netherlands  
**Product type:** Vector Database (Growth, Company-backed OSS, Series B ~$50M)  
**Weighted score:** 4.50

**Rationale:** Weaviate has a confirmed dual rationalization event: a storage layer rewrite and a Python client v4 API migration (gRPC). The Netherlands HQ is the only Dutch representative in the sample. With 25,821 commits and high contactability, this is a strong candidate for both panel scraping and outreach. The vector database product type is directly relevant to AI-native infrastructure.

**Key signals to scrape:** gRPC migration PR timeline, storage engine rewrite commits, Python v3/v4 client deprecation, module system changes, CI infrastructure additions around migration.

**Main risk:** Vector database ecosystem is crowded (Milvus, Qdrant also in sample) — may want to select only one or two vector DB candidates to avoid over-representing this product type.

---

### 10. Astral (ruff/uv)
**GitHub:** https://github.com/astral-sh/ruff  
**Country:** USA  
**Product type:** Python Tooling (Growth, Company-backed OSS, Accel-backed)  
**Weighted score:** 4.45

**Rationale:** Astral represents a distinct rationalization pattern: greenfield Rust rewrites of existing Python tools (flake8, black, isort → ruff; pip → uv). This is a technology-stack rationalization rather than architectural refactoring, which adds methodological diversity. With 15,364 commits, rich CI, and 134+ workflows, the repo is data-dense. The OpenAI acquisition/partnership (~2025) is flagged but does not invalidate the pre-acquisition panel data.

**Key signals to scrape:** Rust LOC growth trajectory by quarter, Python tool deprecation PRs, GitHub stars growth inflection (as a user-adoption proxy), benchmark PR additions, contributor org changes post-acquisition.

**Main risk:** OpenAI acquisition in ~2025 may confound the org decision-making structure in the latter part of the panel; treat last 2–3 quarters carefully. Note also: pass-culture (4.45) ties this score but is placed in the heterogeneity section given its gov-tech category.

---

## Section B — Top 10 for Outreach / Validation Interviews

These candidates combine high contactability with identifiable technical leads and clear organizational structure, making them the best targets for 20-minute validation interviews.

---

### 1. PostHog
**Contact lead:** Tim Glaser, CTO  
**Contact route:** LinkedIn (https://www.linkedin.com/in/timgl/), GitHub (@timgl), YC alumni directory  
**Why useful:** Tim Glaser has written publicly about PostHog's architecture decisions. An interview could validate whether their AI architecture rebuilds were reactive (debt-driven) or proactive, confirming the paper's behavioral assumptions.

---

### 2. Dagger
**Contact lead:** Solomon Hykes, Founder/CTO  
**Contact route:** Twitter/X (@solomonstre), GitHub (@shykes), LinkedIn; direct email via company website  
**Why useful:** Solomon Hykes articulated the Project Theseus philosophy publicly. He can clarify the cost-benefit calculation that preceded the decision — exactly the structural parameters the Rust model needs to identify.

---

### 3. Infisical
**Contact lead:** Maidul Islam, CEO  
**Contact route:** GitHub (@maidul98), YC alumni network, LinkedIn  
**Why useful:** Maidul Islam was publicly involved in the MongoDB→PostgreSQL migration decision. A short interview could confirm the timing trigger (team size threshold? performance threshold?) which pins the state variable.

---

### 4. Trigger.dev
**Contact lead:** Matt Aitken, CEO (also active as engineer)  
**Contact route:** GitHub (@mattaitken), Twitter/X (@mattaitken_), YC alumni network  
**Why useful:** Matt Aitken has discussed v3 architecture publicly in GitHub Discussions and blog posts. Can validate whether v3 was triggered by user-scale pressure or developer-debt accumulation — a key identification question.

---

### 5. Airbyte
**Contact lead:** Michel Tricot, CEO/co-founder  
**Contact route:** LinkedIn (https://www.linkedin.com/in/micheltricot/), company website, GitHub  
**Why useful:** As a $150M+ funded company, Airbyte's CDK v2 migration was an organizational decision involving multiple stakeholders. Michel Tricot can describe the internal threshold that triggered it — useful for validating the organizational-level decision model.

---

### 6. Weaviate
**Contact lead:** Bob van Luijt, CEO (or Etienne Dilocker, CTO)  
**Contact route:** LinkedIn, GitHub, company website (weaviate.io/company)  
**Why useful:** Netherlands-based; can provide European startup perspective on rationalization timing. Two distinct events (storage layer + gRPC migration) make this a rich interview case.

---

### 7. Appwrite
**Contact lead:** Eldad Fux, CEO/founder  
**Contact route:** GitHub (@eldadfux), Twitter/X (@eldadfux), LinkedIn  
**Why useful:** Eldad Fux is highly active in open-source community and has discussed Appwrite's architecture evolution publicly. The v2.0 rewrite decision is recent enough (2024) that recall bias is low.

---

### 8. Turso / ChiselStrike
**Contact lead:** Glauber Costa, CEO  
**Contact route:** GitHub (@glauberc), Twitter/X (@glcst), LinkedIn  
**Why useful:** The ChiselStrike→Turso pivot involved a full product rationalization, not just a codebase refactor. Glauber Costa has written extensively about the decision. Seed-stage perspective adds maturity heterogeneity to the interview sample.

---

### 9. Qdrant
**Contact lead:** Andrey Vasnetsov, CTO  
**Contact route:** GitHub (@generall), LinkedIn, company website (qdrant.tech/about)  
**Why useful:** Andrey Vasnetsov is the technical decision-maker for Qdrant's iterative Rust storage engine evolution. His perspective on when iterative refactoring is preferred over a ground-up rewrite is directly relevant to the paper's decision threshold analysis.

---

### 10. Langfuse
**Contact lead:** Clemens Rohler or Marc Klingen, co-founders  
**Contact route:** GitHub, YC alumni network, LinkedIn, company website (langfuse.com/about)  
**Why useful:** Both co-founders are identifiable and active in the YC community. As an LLM observability tool built AI-native, their rationalization decisions (including the ClickHouse migration) reflect the paper's core population. Germany HQ provides European voice.

---

## Section C — 5 Edge Candidates for Heterogeneity

These candidates score lower overall but add dimensions of diversity that improve the generalizability of the paper's findings.

---

### 1. ma-cantine (beta.gouv.fr)
**GitHub:** https://github.com/betagouv/ma-cantine  
**Weighted score:** 3.05  
**Diversity dimension:** Gov-tech category; French digital government context; non-startup organizational incentives

**Why include:** The beta.gouv.fr portfolio is the only large-scale publicly observable panel of government software projects in the Western world. ma-cantine has 11,806 commits and 731 refactor PRs — more data than many startup candidates. Including one gov-tech representative allows the paper to test whether rationalization dynamics differ under non-profit-maximizing incentives (a natural experiment on the cost-benefit structure). The absence of funding pressure and VC timelines is itself a treatment variation.

---

### 2. Decidim
**GitHub:** https://github.com/decidim/decidim  
**Weighted score:** 3.10  
**Diversity dimension:** Civic-tech / municipal government origin; Spain HQ; Ruby on Rails stack; collective/multi-principal governance

**Why include:** Decidim originated in Barcelona City Hall and is governed by a civic association — a unique institutional structure where rationalization decisions involve democratic deliberation, not a single CTO. The modular engine refactor provides a partial event, and the Ruby/Rails stack is the only Rails-dominant candidate in the high-scoring stratum. Spain HQ is the only Spanish geographic representation.

---

### 3. Plane
**GitHub:** https://github.com/makeplane/plane  
**Weighted score:** 3.90  
**Diversity dimension:** India-based engineering operations; React→Next.js migration as a framework-migration rationalization type; emerging market startup context

**Why include:** Plane's 1,924 refactor PRs constitute one of the strongest quantitative rationalization signals in the sample. India HQ/engineering adds geographic and labor-cost-structure diversity. The React→Next.js migration is a framework-driven rationalization (external tool evolution forces internal cleanup) rather than a debt-driven or pivot-driven event — a distinct causal mechanism worth capturing.

---

### 4. Maybe Finance
**GitHub:** https://github.com/maybe-finance/maybe  
**Weighted score:** 3.40  
**Diversity dimension:** Failed startup → OSS revival pattern; unique organizational discontinuity; personal finance product type

**Why include:** Maybe Finance's trajectory — original VC-backed team wound down, then OSS revival by a different team in 2023 with 45k+ stars — is a unique rationalization pattern: full organizational replacement rather than incremental refactoring. This "phoenix" case tests whether the paper's model generalizes beyond incumbent team rationalization. Personal finance is the only consumer fintech representative in the sample.

---

### 5. Milvus/Zilliz
**GitHub:** https://github.com/milvus-io/milvus  
**Weighted score:** 3.90  
**Diversity dimension:** Dual USA/China operational structure; CNCF governance layer; mature vector database with ground-up v2.0 rebuild; largest-scale rewrite in the sample

**Why include:** The Milvus v2.0 rebuild (Python→Go+Rust, ground-up architecture) is the most complete and best-documented ground-up rewrite in the entire sample — even more dramatic than Dagger's Project Theseus. The CNCF governance and dual US/China structure add complexity, but Zilliz as the commercial backer remains identifiable. Including this case tests whether foundation-governed projects show different rationalization timing than fully-owned startups.
