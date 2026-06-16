# Agentic AI Platform — Use Cases, Startup Ideas & Beginner Setup Guide

> **Status:** Strategic reference document  
> **Created:** June 14, 2026  
> **Derived from:** Alex AI production stack (`Alex_report.md`, `Alex_Master_Implementation_Plan.md`, `Startup.md`)  
> **Purpose:** Map what the Alex infrastructure pattern can solve beyond finance, justify agentic AI vs single-chatbot approaches, and provide a beginner replication plan

---

## Table of Contents

1. [Why Agentic AI (Not Just a Chatbot)](#1-why-agentic-ai-not-just-a-chatbot)
2. [The Reusable Alex Pattern](#2-the-reusable-alex-pattern)
3. [Cross-Industry Use Cases](#3-cross-industry-use-cases)
4. [Feature Extensions per Domain](#4-feature-extensions-per-domain)
5. [Startup Ideas That Solve Real Problems](#5-startup-ideas-that-solve-real-problems)
6. [Beginner Plan — Build a Similar Setup](#6-beginner-plan--build-a-similar-setup)
7. [Cost & Economics by Stage](#7-cost--economics-by-stage)
8. [Decision Framework — Pick Your First Product](#8-decision-framework--pick-your-first-product)
9. [Ophelia Integrations — Execution-Layer Projects on Alex](#9-ophelia-integrations--execution-layer-projects-on-alex)
10. [Document Index](#10-document-index)

---

## 1. Why Agentic AI (Not Just a Chatbot)

A single LLM chatbot fails in production because it cannot **remember**, **act**, **specialize**, **schedule**, or **prove** what it did. Alex’s architecture solves five production gaps:

| Gap | Chatbot-only | Agentic pattern (Alex) |
|-----|--------------|------------------------|
| **Specialization** | One general prompt | Named agents with roles (researcher, risk, quant, ops) |
| **Autonomy** | User must ask every time | EventBridge schedules (2h research, daily cost, trading debates) |
| **Memory** | Stateless or ad-hoc | pgvector RAG + session metadata + debate intelligence store |
| **Tools & data** | Hallucinates or stale | MCP/tool gateway with pass/fail observability per call |
| **Trust** | Black box | `/observe` — latency, cost, guardrails, agent votes, tool traces |

**When agentic AI is justified:** The problem needs **ongoing monitoring**, **multi-perspective decisions**, **external data**, **auditable actions**, or **async work** the user shouldn’t trigger manually.

**When it is overkill:** One-off Q&A, simple form filling, static FAQ — use a router + single model instead.

---

## 2. The Reusable Alex Pattern

Alex is a **template for production agentic systems**, not only a finance app. Strip the domain prompts and you get:

```
┌─────────────────────────────────────────────────────────────────┐
│  LAYER 1 — Brain (on-demand intelligence)                        │
│  Query router → fast/deep/multi paths → SSE streaming chat       │
│  Session RAG + synthesizer + guardrails                          │
└────────────────────────────┬────────────────────────────────────┘
                             │
┌────────────────────────────▼────────────────────────────────────┐
│  LAYER 2 — Hands (autonomous action)                             │
│  Orchestrator → SQS → specialist agents → structured outputs     │
│  Simulation / recommendations (not always real execution)        │
└────────────────────────────┬────────────────────────────────────┘
                             │
┌────────────────────────────▼────────────────────────────────────┐
│  LAYER 3 — Observe (ops as product)                              │
│  Per-query metrics, cost agent, agent accuracy, eval gates       │
└─────────────────────────────────────────────────────────────────┘

Data plane: Aurora + pgvector | Messaging: SQS | Compute: Lambda + ECS
Models: Bedrock Nova Lite/Pro | Embeddings: SageMaker | IaC: Terraform
```

### Infrastructure components (reusable as-is)

| Component | Alex implementation | Reuse in other domains |
|-----------|---------------------|------------------------|
| **Query router** | Nova Lite intent classification | Route to support vs research vs action |
| **ECS researcher** | Long-running MCP + streaming | Any tool-heavy agent (legal, medical chart review) |
| **Lambda agents** | Planner, tagger, reporter, debate | Short burst specialists |
| **SQS pipelines** | Research queue, trading queue, results | Decouple ingest → process → notify |
| **EventBridge** | 2h portfolio, 30min ops, daily cost | Cron monitors, digest emails, SLA checks |
| **pgvector RAG** | `research_vectors`, `portfolio_digests` | Docs, tickets, EMR snippets, contracts |
| **Multi-agent debate** | 6 trading personas | Any committee decision (credit, hiring, diagnosis assist) |
| **Paper simulation** | `simulated_trades` | Dry-run workflows before real commits |
| **Ops + cost agents** | `ops_agent`, P21 cost agent | FinOps for any AI product |
| **Guardrails** | Bedrock + policy flags | Regulated domains (finance, health, legal) |
| **Terraform modules** | `0_vpc` … `9_trading_floor` | Reproducible envs per customer/tenant |

---

## 3. Cross-Industry Use Cases

Each use case maps to Alex layers and explains **why agents** beat a single model.

### 3.1 Healthcare — Clinical Ops & Prior Authorization

**Problem:** Prior auth forms take nurses 45+ minutes per case; denials cost hospitals $50B/year in admin waste.

| Alex layer | Adaptation |
|------------|------------|
| Brain | Clinician asks: "Does this patient meet criteria for MRI lumbar?" |
| Hands | Autonomous agent pulls payer policy PDFs, maps ICD/CPT, drafts auth letter |
| Observe | Log which policy clause supported approval — audit for compliance |

**Agents:** Policy agent, clinical criteria agent, documentation agent, denial-risk agent, billing agent, compliance guardrail agent.

**Features to add:** HIPAA BAA, PHI redaction in RAG, FHIR MCP, human-in-the-loop approval before submit.

**Why agentic:** Multi-payer rules + document evidence + scheduled resubmission — not one prompt.

---

### 3.2 Legal — Contract Review & Obligation Monitoring

**Problem:** SMBs sign SaaS contracts without understanding auto-renewal, liability caps, or data processing terms.

| Alex layer | Adaptation |
|------------|------------|
| Brain | "What are my termination obligations in the Acme MSA?" |
| Hands | Nightly scan of uploaded contracts → flag renewals in 90 days |
| Observe | Clause-level attribution (which paragraph triggered alert) |

**Agents:** Definition extractor, liability/risk agent, renewal calendar agent, comparison agent (vs market standard), plain-English summarizer.

**Features to add:** Document ingest pipeline, clause-type vector store, calendar integrations, e-sign webhook.

**Why agentic:** Contracts need **specialists** (IP vs indemnity vs SLA) and **ongoing monitoring**, not one-shot summary.

---

### 3.3 Cybersecurity — SOC Triage & Incident Copilot

**Problem:** SOC analysts drown in alerts; 40%+ are false positives; mean time to triage is hours.

| Alex layer | Adaptation |
|------------|------------|
| Brain | Analyst pastes alert JSON → get ranked hypothesis |
| Hands | Hourly correlation across CloudTrail, GuardDuty, SIEM |
| Observe | Tool pass/fail per enrichment (VirusTotal, WHOIS, CMDB) |

**Agents:** Triage agent, threat-intel agent, asset-context agent, escalation agent, runbook agent, false-positive scorer.

**Features to add:** SIEM MCP, automated ticket creation (Jira/ServiceNow), severity-based paging, immutable audit log.

**Why agentic:** Parallel enrichment + debate ("benign scan vs lateral movement") mirrors trading floor logic.

---

### 3.4 Supply Chain — Supplier Risk & Disruption Monitor

**Problem:** Manufacturers learn about supplier bankruptcy from the news, not before POs fail.

| Alex layer | Adaptation |
|------------|------------|
| Brain | "Which of our Tier-2 suppliers are exposed to Taiwan disruption?" |
| Hands | Daily scrape + news MCP on supplier list → risk score updates |
| Observe | Data freshness dashboard per supplier signal |

**Agents:** Geopolitical agent, financial health agent, logistics delay agent, alternative supplier scout, inventory impact simulator.

**Features to add:** ERP connector (SAP/NetSuite), BOM graph, simulation of lead-time impact.

**Why agentic:** Multi-source fusion + scheduled monitoring + what-if simulation.

---

### 3.5 HR / Talent — Hiring Committee Simulation

**Problem:** Hiring managers make gut-feel decisions; bias and inconsistency; no structured debate record.

| Alex layer | Adaptation |
|------------|------------|
| Brain | "Should we advance this candidate for Staff Engineer?" |
| Hands | Multi-agent debate on resume + work sample (culture, technical, growth, risk) |
| Observe | Vote distribution + which competencies drove outcome |

**Agents:** Technical depth, system design, culture fit, red-flag, growth trajectory, compensation band checker.

**Features to add:** ATS integration, blind-review mode, DEI bias guardrails, structured scorecards.

**Why agentic:** Hiring **is** a committee — mirrors Alex trading floor transparency.

**Regulatory note:** Decision support only; human makes final hire/reject.

---

### 3.6 Real Estate — Investment Committee for Rentals

**Problem:** Individual investors analyze deals in spreadsheets; miss market rent shifts and expense surprises.

| Alex layer | Adaptation |
|------------|------------|
| Brain | "Underwrite 123 Main St at $450k" |
| Hands | Weekly rent comp refresh + expense inflation monitor on watchlist |
| Observe | Assumption trail (cap rate source, vacancy assumption) |

**Agents:** Comps agent, capex estimator, cash-flow agent, neighborhood trend agent, financing agent, downside stress agent.

**Features to add:** Zillow/Redfin MCP, county tax records, simulation vs actual after purchase.

---

### 3.7 Customer Support — Tier-2 Resolution Autopilot

**Problem:** L2 support repeats the same investigation (logs + billing + repro) — 24h SLA breaches.

| Alex layer | Adaptation |
|------------|------------|
| Brain | Customer issue in chat → routed fast (macro) vs deep (logs) |
| Hands | Agent pulls Stripe + Datadog + CRM → drafts resolution or escalation |
| Observe | Resolution time, tools failed, cost per ticket |

**Agents:** Triage router, billing agent, technical logs agent, empathy/drafting agent, escalation agent.

**Features to add:** Zendesk/Intercom MCP, auto-draft with human approve, CSAT loop into RL weights.

**Why agentic:** Support tickets need **tool use** and **specialists**, not generic apologies.

---

### 3.8 Compliance — Regulatory Change Monitor (Finance, Privacy, ESG)

**Problem:** Compliance teams manually track SEC, GDPR, state privacy laws — reactive, not proactive.

| Alex layer | Adaptation |
|------------|------------|
| Brain | "What changed for us when SEC adopted rule XYZ?" |
| Hands | Daily ingest of regulatory feeds → map to internal control library |
| Observe | RAGAS faithfulness on legal citations |

**Agents:** Reg-parser, impact mapper, control-gap agent, remediation planner, legal disclaimer guardrail.

**Features to add:** Jurisdiction filters, control framework mapping (SOC2, ISO), task export to GRC tools.

---

### 3.9 Education — Personalized Research Tutor

**Problem:** Students use ChatGPT for homework — no sources, no memory of their learning gaps, no Socratic method.

| Alex layer | Adaptation |
|------------|------------|
| Brain | Socratic chat with citations |
| Hands | Weekly digest of topics struggled with + practice set generation |
| Observe | Hallucination rate, source attribution |

**Agents:** Tutor, fact-checker, curriculum aligner, quiz generator, plagiarism-safe guardrail.

**Features to add:** LMS integration, citation-required mode, parent/teacher dashboard.

---

### 3.10 Personal Finance (Alex native) — Extended verticals

Already built; highest reuse of existing code:

| Sub-use case | Alex feature | Extension |
|--------------|--------------|-----------|
| Portfolio research | 2h scheduler + digests | Push notifications on material news |
| Trading education | Paper simulation | Prop league (Startup Idea 7) |
| Tax-loss harvesting hints | Context bridge | CPA export packet (not advice) |
| Estate / beneficiary review | Multi-agent debate | Document checklist agent |
| Small business owner | Mixed personal + business holdings | Separate entity simulations |

---

### 3.11 FP&A & Board Reporting — Startup Finance Copilot

**Problem:** Seed–Series B CFOs spend 2–3 days/month on board decks, variance narratives, and investor updates — pulling from Stripe, QuickBooks, HubSpot, and spreadsheets manually.

| Alex layer | Adaptation |
|------------|------------|
| Brain | "Why did gross margin drop 4pts in March?" |
| Hands | EventBridge monthly close → auto-ingest metrics → draft board memo |
| Observe | Source attribution per metric (Stripe MRR vs QB COGS) |

**Agents:** Revenue agent, burn/runway agent, cohort agent, headcount cost agent, narrative synthesizer, downside scenario agent.

**Alex reuse:** Scheduler + reporter + digest cards → **85%** (swap yfinance for Stripe/QB MCP).

**Startup:** **FP&A Copilot** — $199–499/mo per company.

---

### 3.12 Family Office — Multi-Entity Wealth Intelligence

**Problem:** Family offices manage 5–20 entities (trusts, LLCs, personal, charity) with no unified research layer; each advisor uses different tools.

| Alex layer | Adaptation |
|------------|------------|
| Brain | Entity-scoped chat: "How does the REIT position affect trust liquidity?" |
| Hands | Per-entity 2h research + cross-entity concentration debate |
| Observe | Entity-level audit log (like RIA `compliance_audit_log`) |

**Agents:** Liquidity agent, tax exposure agent, concentration risk, philanthropy aligner, macro agent, estate planning context agent.

**Alex reuse:** RIA Copilot tenancy model + trading debate → **80%**. See `RIA.md` extended to `family_office_id`.

**Startup:** **Family Office Copilot** — $500–2,000/mo per family office.

---

### 3.13 Commercial Real Estate — Credit & Underwriting Committee

**Problem:** Community bank CRE officers write credit memos from scratch; 5–10 hours per loan; inconsistent stress testing.

| Alex layer | Adaptation |
|------------|------------|
| Brain | "Underwrite Class-B office at 8.5% cap in Austin" |
| Hands | Weekly rent roll + comp refresh on pipeline deals |
| Observe | Assumption log (NOI source, vacancy, rate stress) |

**Agents:** NOI agent, tenant credit agent, market vacancy agent, rate stress agent, collateral agent, policy exception agent.

**Alex reuse:** Real estate use case (3.6) + debate committee + memo approval (RIA pattern) → **75%**.

**Startup:** **CRE Credit Memo AI** — $400/loan officer/mo or $50/memo.

---

### 3.14 Amazon / E-commerce — Seller Intelligence Floor

**Problem:** 7-figure Amazon sellers monitor 50+ SKUs across competitors, PPC, inventory, and reviews — no systematic bull/bear on product bets.

| Alex layer | Adaptation |
|------------|------------|
| Brain | "Should I increase inventory on SKU-4421 before Q4?" |
| Hands | Daily competitor price scrape + review sentiment + inventory simulation |
| Observe | Tool trace per Keepa/SP-API call |

**Agents:** Demand forecast agent, competitor pricing agent, PPC efficiency agent, review sentiment agent, inventory risk agent, margin agent.

**Alex reuse:** Scout agent + scheduler + simulation (inventory dry-run) → **70%**.

**Startup:** **SellerFloor** — $99–299/mo per seller account.

---

### 3.15 DevOps / SRE — Incident Commander

**Problem:** On-call engineers context-switch across PagerDuty, Datadog, GitHub, and runbooks; MTTR measured in hours for complex incidents.

| Alex layer | Adaptation |
|------------|------------|
| Brain | Paste alert → ranked root-cause hypotheses with evidence |
| Hands | Hourly correlation during active incident; auto-draft postmortem |
| Observe | Tool pass/fail per enrichment (same as SOC 3.3) |

**Agents:** Triage agent, logs agent, deploy-diff agent, blast-radius agent, runbook agent, customer-comms drafter.

**Alex reuse:** SOC Sidekick pattern + ops_agent health checks + `/observe` → **80%**.

**Startup:** **Incident Commander AI** — $500/mo per team or $50/incident.

---

### 3.16 Nonprofit — Grant Discovery & Proposal Copilot

**Problem:** Small nonprofits miss grant deadlines; grant writers spend 20+ hours per application re-explaining the same org story.

| Alex layer | Adaptation |
|------------|------------|
| Brain | "Which grants fit our youth STEM program in Ohio?" |
| Hands | Weekly Grants.gov + foundation RSS scan → match score + deadline alerts |
| Observe | Citation to grant eligibility criteria |

**Agents:** Eligibility matcher, narrative drafter, budget aligner, deadline tracker, compliance checklist agent, funder research agent.

**Alex reuse:** Scheduler + reporter memos + RAG org memory → **75%**.

**Startup:** **GrantPulse** — $79/mo (nonprofit) / $299/mo (grant consultant seat).

---

### 3.17 CPA & Tax — Legislative Change Impact Monitor

**Problem:** CPAs with 200+ clients can't proactively explain how new tax law affects each client; reactive April scramble.

| Alex layer | Adaptation |
|------------|------------|
| Brain | "How does Section 174 amortization affect Client X's S-corp?" |
| Hands | Daily IRS + state tax feed ingest → per-client impact memo drafts |
| Observe | Statute citation in `rag_attributions` |

**Agents:** Legislative parser, entity-type mapper, deduction optimizer (informational), client impact scorer, deadline agent, disclaimer guardrail.

**Alex reuse:** Compliance monitor (3.8) + RIA memo pipeline → **70%**.

**Startup:** **TaxImpact AI** — $150/CPA seat/mo.

---

### 3.18 Biotech / Pharma — Clinical Trial Site Selection Committee

**Problem:** CROs evaluate 50+ trial sites using fragmented feasibility data; slow enrollment kills trial timelines.

| Alex layer | Adaptation |
|------------|------------|
| Brain | "Best sites for Phase II oncology in Southeast US?" |
| Hands | Multi-agent debate on site history, PI experience, patient pool, competition |
| Observe | Vote + evidence per site criterion |

**Agents:** Enrollment history agent, PI track record agent, patient demographics agent, competing trial agent, regulatory agent, logistics agent.

**Alex reuse:** Hiring committee (3.5) + debate engine → **65%** (needs clinical data MCPs).

**Startup:** **SiteSelect AI** — $2k/study or $10k/mo CRO subscription.

---

### 3.19 IP / Patent — Prior Art Monitoring Scout

**Problem:** Patent attorneys run expensive prior art searches reactively; miss competitor filings that threaten freedom to operate.

| Alex layer | Adaptation |
|------------|------------|
| Brain | "Any new prior art threatening Claim 3 of our battery patent?" |
| Hands | Weekly USPTO + Google Patents scan on watchlist → alert digest |
| Observe | Document-level citation trail |

**Agents:** Prior art scout, claim-mapping agent, competitor filing agent, novelty scorer, litigation risk agent, plain-English brief agent.

**Alex reuse:** Scout agent (P9) + scheduler + deep doc ingest → **70%**.

**Startup:** **PriorArt Scout** — $300/attorney/mo or $2k/mo firm.

---

### 3.20 Franchise Operations — Multi-Location Health Monitor

**Problem:** Franchisees with 10–50 locations can't systematically track reviews, health inspections, labor compliance, and brand standards.

| Alex layer | Adaptation |
|------------|------------|
| Brain | "Which locations are at risk of brand audit failure?" |
| Hands | Daily review scrape + inspection DB + labor signal → location scorecard |
| Observe | Per-location data freshness + alert history |

**Agents:** Review sentiment agent, inspection history agent, labor compliance agent, competitor proximity agent, ops benchmark agent, remediation planner.

**Alex reuse:** Supplier Pulse pattern + scheduled digests + location tenancy → **65%**.

**Startup:** **FranchisePulse** — $50/location/mo (min 10 locations).

---

### 3.21 Media & Intelligence — Industry Briefing Service

**Problem:** Executives pay $5k+/yr for Gartner/Forrester but still need **daily** synthesized briefings on *their* niche — not quarterly PDFs.

| Alex layer | Adaptation |
|------------|------------|
| Brain | "What happened in fintech infrastructure this week relevant to us?" |
| Hands | Daily news + SEC + blog ingest on user-defined ontology → morning brief |
| Observe | Source diversity score, hallucination gate (RAGAS) |

**Agents:** News scout, competitor agent, regulatory agent, funding/M&A agent, technology trend agent, synthesizer.

**Alex reuse:** Portfolio research pipeline with topic watchlist instead of tickers → **90%**.

**Startup:** **BriefingAI** — $49/mo prosumer / $500/mo team API.

---

### 3.22 Insurance Broker — Policy Comparison Committee

**Problem:** SMB brokers compare 5+ carrier quotes manually; clients don't understand coverage gaps until claim time.

| Alex layer | Adaptation |
|------------|------------|
| Brain | "Compare these three D&O quotes for a 50-person SaaS company" |
| Hands | Multi-agent debate on coverage terms, exclusions, carrier financial strength |
| Observe | Clause-level diff log |

**Agents:** Coverage agent, exclusion risk agent, carrier AM Best agent, premium benchmark agent, client-fit agent, plain-English explainer.

**Alex reuse:** Insurance claims (A4) + debate committee → **70%**.

**Startup:** **CoverageCommittee** — $200/broker/mo.

---

## 4. Feature Extensions per Domain

Generic features that transfer from Alex to any vertical:

| Feature (Alex) | Generic name | Value |
|----------------|--------------|-------|
| Query router | **Intent router** | Cost control — cheap model for simple, Pro for deep |
| `research_vectors` | **Domain memory** | Long-horizon context without stuffing prompts |
| Multi-agent debate | **Committee mode** | Reduces single-model blind spots |
| Paper simulation | **Dry-run mode** | Safe preview before real-world action |
| `query_latency_metrics` | **SLO dashboard** | Prove P95 latency to enterprise buyers |
| P21 cost agent | **Unit economics visibility** | Know margin per user/session |
| Tagger agent (P5.5) | **Event taxonomy** | Searchable observability across tools |
| Tools-only gateway (P5) | **Action audit trail** | Compliance — every mutation logged |
| RAGAS eval (P17) | **Quality gate** | Block bad deploys; trust in regulated domains |
| Fresh Start (P0.6) | **Tenant reset** | Demo environments, GDPR delete |
| EventBridge schedules | **Autonomous loops** | Product works while user sleeps |

---

## 5. Startup Ideas That Solve Real Problems

Criteria used: **acute pain**, **willingness to pay**, **defensible with agentic stack**, **reachable MVP in <8 weeks**, **≥65% Alex architecture reuse**.

### Alex leverage legend

| Reuse % | Meaning |
|---------|---------|
| **90%+** | Swap prompts + data MCPs; same scheduler/reporter/RAG |
| **75–89%** | Add tenancy or approval workflow (RIA pattern) |
| **65–74%** | New domain MCPs; same orchestration + debate + observe |
| **<65%** | Consider only if strategic; heavier custom build |

---

### Tier A — Strongest fit for Alex stack (finance & adjacent)

| # | Startup | Problem solved | Alex reuse | MVP | Monetization |
|---|---------|----------------|------------|-----|--------------|
| **A1** | **Alex** (current) | Retail investors lack research team | **95%** | 3–4 wk | $29/mo Pro |
| **A2** | **RIA Copilot** | Advisors spend 10h/wk on client memos | **85%** | 6–8 wk | $300/advisor/mo |
| **A3** | **Deal Room AI** | PE analysts drown in CIMs / datarooms | **80%** | 6 wk | $500/seat/mo |
| **A4** | **Insurance Claims Intel** | Adjusters re-read policies per claim | **70%** | 8 wk | Per-claim API |
| **A5** | **Agent Sentiment Index** | No market signal from agent consensus | **90%** | 4 wk | $2k/mo data license |
| **A6** | **FP&A Copilot** | CFOs waste days on board decks | **85%** | 5–6 wk | $199–499/co/mo |
| **A7** | **Family Office Copilot** | Multi-entity wealth lacks unified research | **80%** | 8 wk | $500–2k/mo |
| **A8** | **CRE Credit Memo AI** | Bank CRE officers write 5–10hr memos | **75%** | 6–8 wk | $400/officer/mo |
| **A9** | **BriefingAI** | Execs need daily niche intelligence briefs | **90%** | 4 wk | $49–500/mo |
| **A10** | **CoverageCommittee** | Insurance brokers manual quote comparison | **70%** | 6 wk | $200/broker/mo |
| **A11** | **M&A Target Scout** | Corp dev misses signals on watchlist companies | **85%** | 5 wk | $1k/seat/mo |

> **A2 full spec:** [`RIA.md`](RIA.md) — tenancy, compliance, MVP roadmap.

**A6 detail:** Reuse `scheduler.py` → `reporter.py` on monthly close; swap portfolio tickers for Stripe MRR + QuickBooks MCP; output = board memo markdown.

**A9 detail:** Same as Alex portfolio research but `watchlist` = topics/keywords; highest code reuse of any non-finance idea.

**A11 detail:** Scout agent (P9) on acquisition targets — SEC filings, news, leadership changes, product launches — daily digest per target.

---

### Tier B — High pain, strong Alex fit, moderate regulatory friction

| # | Startup | Problem solved | Alex reuse | MVP | Monetization |
|---|---------|----------------|------------|-----|--------------|
| **B1** | **PriorAuth Copilot** | Nurse auth paperwork | **65%** | 8–10 wk | $2k/provider/mo |
| **B2** | **ContractGuard** | SMBs miss contract traps | **75%** | 6 wk | $49/co/mo |
| **B3** | **SOC Sidekick** | SOC alert fatigue | **80%** | 8 wk | $1k/analyst/mo |
| **B4** | **Supplier Pulse** | Supply chain blind spots | **70%** | 6 wk | $500/mo per BOM |
| **B5** | **HireCouncil** | Inconsistent hiring decisions | **75%** | 5 wk | $199/hire |
| **B6** | **Incident Commander** | SRE MTTR too high | **80%** | 6 wk | $500/team/mo |
| **B7** | **GrantPulse** | Nonprofits miss grants | **75%** | 5–6 wk | $79–299/mo |
| **B8** | **TaxImpact AI** | CPAs reactive to law changes | **70%** | 6–8 wk | $150/CPA/mo |
| **B9** | **SellerFloor** | Amazon sellers lack systematic intel | **70%** | 6 wk | $99–299/mo |
| **B10** | **PriorArt Scout** | Patent attorneys reactive search | **70%** | 6 wk | $300/attorney/mo |
| **B11** | **FranchisePulse** | Multi-location ops blind spots | **65%** | 7 wk | $50/location/mo |
| **B12** | **SiteSelect AI** | CRO site selection slow | **65%** | 8–10 wk | $2k/study |

---

### Tier C — Large market, crowded — need sharp wedge

| # | Startup | Problem solved | Wedge | Alex reuse | Risk |
|---|---------|----------------|-------|------------|------|
| **C1** | Support autopilot | Ticket cost | Tool-traced resolutions | 75% | Zendesk incumbents |
| **C2** | Legal research | Billable hour pressure | Citation + monitor | 70% | Harvey, Casetext |
| **C3** | RE underwriter | Slow deal analysis | Simulation + comps | 75% | Data cost |
| **C4** | EdTech tutor | Homework cheating concerns | Citation-required Socratic | 80% | School procurement |
| **C5** | General GRC | Compliance checkbox fatigue | Reg change → control map | 70% | Vanta, Drata |

---

### Tier D — Platform plays (sell the Alex engine)

| # | Startup | Problem solved | Model | Alex reuse |
|---|---------|----------------|-------|------------|
| **D1** | **AgenticOS** | Teams can't build production agents | White-label Alex infra per vertical | **100%** |
| **D2** | **Observe.ai Ops** | AI products lack cost/quality visibility | Package `/observe` + P21 + RAGAS | **95%** |
| **D3** | **Debate API** | Products want committee decisions | API: `POST /debate` → votes + reasoning | **90%** |

**D1 GTM:** Fork Alex terraform + backend; vertical packs (finance, legal, ops) as prompt/MCP bundles. Price: $2k/mo platform + usage.

---

### Recommended launch order (updated)

| Priority | Startup | Why |
|----------|---------|-----|
| 1 | **A1 Alex B2C** | Codebase ~70% done; fastest revenue proof |
| 2 | **A2 RIA Copilot** | Highest ARPU; same infra — see `RIA.md` |
| 3 | **A9 BriefingAI** | **Fastest non-finance pivot** — 90% reuse, broad TAM |
| 4 | **A5 Sentiment Index** | Unique data moat once debates scale |
| 5 | **A6 FP&A Copilot** | Hot market (every startup CFO); Stripe MCP swap |

See `Startup.md` for detailed GTM on A1.

---

## 6. Beginner Plan — Build a Similar Setup

A phased path from zero to an Alex-class agentic platform. Assumes one developer, AWS account, basic Python/TypeScript.

### Phase 0 — Prerequisites (Week 0)

| Item | Action |
|------|--------|
| AWS account | Enable Bedrock (Nova Lite + Pro), IAM admin for Terraform |
| Local tools | Docker Desktop, Terraform ≥1.5, Python 3.12, Node 18+, AWS CLI |
| Repo structure | Fork or scaffold from Alex: `terraform/`, `backend/`, `frontend/`, `scripts/` |
| Cost discipline | Copy `start_session.sh` / `stop_session.sh` pattern — destroy ECS/SageMaker when not developing |

**Budget:** ~$12/mo dev (session on/off) per `Startup.md`; ~$0.11/day when stopped.

---

### Phase 1 — Minimal agentic loop (Week 1–2)

**Goal:** One chat + one scheduled agent + one database.

```
User chat (Next.js) → API route → Bedrock Nova Lite
                              ↓
                    Aurora (one table: chat_sessions)
EventBridge daily → Lambda "digest_agent" → email via SES
```

| Step | Deliverable |
|------|-------------|
| 1 | Terraform `5_database` — Aurora Serverless v2 |
| 2 | Terraform `6_agents` — one Lambda + EventBridge schedule |
| 3 | Next.js chat page with Clerk auth |
| 4 | `aurora_warmup.py` — DDL for sessions |
| 5 | Manual test: ask question → get answer; wait for daily email |

**Skip for now:** ECS, pgvector, multi-agent, MCP.

---

### Phase 2 — Router + memory (Week 3–4)

**Goal:** Fast vs deep paths; remember conversations.

| Step | Deliverable |
|------|-------------|
| 1 | `query_router.py` — Nova Lite classifies intent |
| 2 | Terraform `2_sagemaker` — embedding endpoint |
| 3 | `research_vectors` table + ingest on chat save |
| 4 | RAG retrieval in context service |
| 5 | SSE streaming for chat |

**Alex reference:** P0 + P1 + P2 in `Alex_Master_Implementation_Plan.md`.

---

### Phase 3 — Tools & deep research (Week 5–6)

**Goal:** Ground answers in real data.

| Step | Deliverable |
|------|-------------|
| 1 | Terraform `4_researcher` — ECS Fargate + ALB |
| 2 | One MCP or Python tool (e.g. web fetch, domain API) |
| 3 | Log tool pass/fail to `agent_observations` |
| 4 | `/observe` page — cost + latency (read-only) |

**Alex reference:** P7 MCP expansion, P11 observability lite.

---

### Phase 4 — Multi-agent autonomy (Week 7–8)

**Goal:** Scheduled specialist pipeline.

| Step | Deliverable |
|------|-------------|
| 1 | SQS queue + orchestrator Lambda |
| 2 | 3–6 specialist agents (Lambda or ECS) |
| 3 | Debate or planner → reporter pattern |
| 4 | EventBridge schedule (e.g. every 2h) |
| 5 | Dashboard cards for autonomous output |

**Alex reference:** Trading floor (`9_trading_floor`), portfolio scheduler.

---

### Phase 5 — Production hardening (Week 9–12)

| Step | Deliverable |
|------|-------------|
| 1 | Bedrock guardrails (`7_guardrails`) |
| 2 | P21-style daily cost email |
| 3 | RAGAS eval script + CI gate |
| 4 | Terraform-only infra policy (see `Alex_report.md` §22.5) |
| 5 | `test_p0.sh` regression suite |

---

### Beginner Terraform apply order

```bash
# From Alex — do not skip order
cd terraform/0_vpc && terraform apply
cd ../1_permissions && terraform apply
cd ../5_database && terraform apply
cd ../6_agents && terraform apply
cd ../2_sagemaker && terraform apply   # when embeddings needed
cd ../4_researcher && terraform apply  # when ECS needed
cd ../3_ingestion && terraform apply   # optional API ingest
cd ../7_guardrails && terraform apply
```

**Session lifecycle:**

```bash
bash scripts/start_session.sh   # morning — spins ECS + SageMaker
# ... develop ...
bash scripts/stop_session.sh    # evening — saves ~$4.83/day
```

---

### Beginner stack decisions

| Decision | Recommendation | Why |
|----------|----------------|-----|
| Cloud | AWS | Alex modules are AWS-native; Bedrock + Aurora pgvector proven |
| Models | Nova Lite (router/chat), Nova Pro (deep) | 10–50× cheaper than Pro-only |
| DB | Aurora Serverless v2 + RDS Data API | No connection pool pain in Lambda |
| Vectors | pgvector in Aurora | One DB for relational + semantic |
| Auth | Clerk | Fast multi-tenant `user_id` scoping |
| Frontend | Next.js App Router | SSE, API routes, Vercel deploy |
| IaC | Terraform only | Mandatory per Alex policy — reproducible envs |
| Agents | Lambda (burst) + ECS (MCP/long) | Right compute per workload |

---

### What NOT to build first (common beginner traps)

| Trap | Do instead |
|------|------------|
| 10 agents before one works | One router + one deep path |
| Custom vector DB (Pinecone) + Postgres | pgvector in Aurora |
| Real trade execution / medical diagnosis | Paper simulation / decision support |
| Kubernetes | ECS Fargate + Lambda — simpler ops |
| Manual AWS Console resources | Terraform from day one |
| No observability | Log cost + latency from first Bedrock call |

---

## 7. Cost & Economics by Stage

| Stage | Monthly AWS (dev) | Monthly AWS (100 users) | Notes |
|-------|-------------------|-------------------------|-------|
| Phase 1 (Lambda only) | ~$5–10 | ~$50 | No ECS/SageMaker |
| Phase 2 (+ embeddings) | ~$12 | ~$80 | SageMaker serverless |
| Phase 3 (+ ECS) | ~$25 session on | ~$200 | Destroy ECS off-hours |
| Phase 4 (+ multi-agent) | ~$35 session on | ~$300 | Bedrock scales with usage |
| Alex full (observed) | ~$12 dev / ~$0.11 stopped | ~$1.90/user at 1k users | See `Startup.md` |

**Rule:** If gross margin < 70%, tighten router (more Nova Lite), cache quant snapshots, schedule heavy jobs off-peak.

---

## 8. Decision Framework — Pick Your First Product

Score each idea 1–5 on:

1. **Pain acuity** — hair-on-fire vs nice-to-have  
2. **Agentic fit** — needs memory + tools + schedule + debate?  
3. **Code reuse from Alex** — % of infra/prompts transferable  
4. **Regulatory drag** — low = faster launch  
5. **Willingness to pay** — B2B > prosumer > free  

| Idea | Pain | Agentic | Reuse | Regulatory | WTP | **Total** |
|------|------|---------|-------|------------|-----|-----------|
| Alex B2C | 4 | 5 | 5 | 3 | 4 | **21** |
| RIA Copilot | 5 | 5 | 5 | 3 | 5 | **23** |
| BriefingAI | 4 | 5 | 5 | 5 | 4 | **23** |
| FP&A Copilot | 5 | 4 | 5 | 4 | 5 | **23** |
| SOC Sidekick | 5 | 5 | 4 | 3 | 4 | **21** |
| Incident Commander | 5 | 5 | 4 | 4 | 4 | **22** |
| CRE Credit Memo | 4 | 5 | 4 | 3 | 5 | **21** |
| Family Office | 4 | 5 | 4 | 3 | 5 | **21** |
| PriorAuth | 5 | 5 | 3 | 1 | 5 | **19** |
| ContractGuard | 4 | 4 | 4 | 4 | 3 | **19** |
| GrantPulse | 4 | 4 | 4 | 5 | 3 | **20** |
| SellerFloor | 4 | 4 | 4 | 4 | 4 | **20** |
| HireCouncil | 3 | 4 | 4 | 4 | 3 | **18** |

**Top scorers (23):** RIA Copilot, BriefingAI, FP&A Copilot — best combo of reuse + willingness to pay.

**Fastest pivot from Alex (90%+ reuse):** BriefingAI (topic watchlist), Agent Sentiment Index (aggregate debates).

**If starting from Alex today:** Ship **Alex B2C** for velocity; parallel **RIA Copilot** for ARPU; validate **BriefingAI** as lowest-risk non-finance experiment.

---

## 9. Ophelia Integrations — Execution-Layer Projects on Alex

> **Source:** [`Ophelia.md`](Ophelia.md) — Ophelia thesis, Alex pillar mapping, founding-member execution patterns  
> **Purpose:** Concrete projects you can build **on Alex architecture** that demonstrate the same skills Ophelia needs — intent → confirmed real-world outcome across fragmented supply

### 9.1 Ophelia's Thesis (Four Themes)

Ophelia is an **execution layer for real-world coordination** — not a chatbot, not a consumer booking app. Their core line:

> *"The next bottleneck in AI isn't intelligence — it's execution at scale."*

| Theme | What it means | Alex parallel |
|-------|---------------|---------------|
| **1. Physical-digital gap** | AI plans in chat; restaurants/events/fitness are messy, fragmented, partially offline | Financial data fragmented across SEC, news, brokers, live web |
| **2. Intent vs execution** | Agents say "book dinner Friday" but fail on availability, pay, confirm, retry | Agents say "research NVDA" but fail without ingest → digest → dashboard card |
| **3. Intelligence solved** | LLM reasoning is commodity; **reliable execution** is the moat | Nova Pro debates are easy; **confirmed** `portfolio_digests` in Aurora is hard |
| **4. Unified execution layer** | One API/MCP over OpenTable + Resy + Ticketmaster + Mindbody | One pipeline over SEC + Playwright MCP + yfinance + ingest |

**Bo Brainerd origin story (why this matters):** A dating app worked in demos but **broke when two users tried to coordinate a real date** — confirm step failed. Teams either killed in-app booking or spent ~$2M on brittle integrations. Ophelia was built to be that unified layer. Alex was built for the same class of problem in finance.

---

### 9.2 Alex ↔ Ophelia Architecture Map

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  OPHELIA                              │  ALEX (starting point)                 │
├───────────────────────────────────────┼────────────────────────────────────────┤
│  Intent: "book dinner 8pm Friday"     │  Intent: "research NVDA" / portfolio   │
│  Router: search vs create vs cancel     │  Router: fast / deep / multi / debate │
│  Search: parallel provider adapters     │  Deep research: parallel MCP tools     │
│  Execute: hold → pay → confirm          │  Execute: planner → reporter → ingest  │
│  Confirmation: booking_id + reconcile │  Confirmation: portfolio_digests card  │
│  Fragmented supply: 50+ platforms     │  Fragmented data: SEC, news, web, APIs │
│  MCP: search, create, list, cancel    │  MCP: Playwright, get_sec_filings, etc. │
│  Retry/proxy on brittle surfaces      │  ECS→Bedrock fallback, Aurora 3x retry │
│  Observability: confirm rate, P95     │  /observe: cost, latency, guardrails   │
│  Multi-party: 3 friends, 1 reservation│  Multi-agent: 6 votes → one decision   │
└─────────────────────────────────────────────────────────────────────────────┘
```

**Pillar reuse from `Ophelia.md`:**

| Ophelia pillar | Alex evidence today | Gap to close for Ophelia-style demo |
|----------------|---------------------|-------------------------------------|
| Orchestration | `scheduler.py` → `planner.py` → `reporter.py` | Add explicit state machine + `correlation_id` |
| MCP tooling | Playwright MCP on ECS | Add typed tool schemas + idempotency keys |
| Reliability | SQS, retry, fallback, upserts | Add DLQ + circuit breakers (P18) |
| Inference | Nova Lite/Pro tiering, `agent_observations` | Add per-stage latency (P15) |
| Evaluation | RAGAS script, `/observe` | Add **outcome** metrics (confirm rate, not just faithfulness) |
| Distributed systems | Lambda + ECS + EventBridge + Aurora | Same stack — no change |

---

### 9.3 Recommended Projects (Ranked for Portfolio + Alex Reuse)

Each project is a **buildable slice** on Alex that proves execution-layer engineering. Ordered by **Alex reuse %** and **Ophelia interview/demo value**.

---

#### Project 1: **ConfirmGate** — Human-in-the-Loop Before Client Delivery ⭐ Top pick

| Field | Detail |
|-------|--------|
| **Ophelia problem** | Confirm step must never half-succeed; customer needs durable `booking_id` |
| **Alex problem** | Bo's dating parallel — chat works but unconfirmed output is useless |
| **What you build** | Extend RIA `client_memos` pattern to **all** autonomous outputs: research digests, debate summaries, trading recommendations require advisor/user **approve** before publish |
| **Alex components** | `portfolio_digests` → `pending_confirmations` table; memo inbox UI; `compliance_audit_log`; P1.5 approval flow |
| **Ophelia parallel** | `pending → held → confirmed` booking state machine; all-or-nothing confirm |
| **MVP (2 weeks)** | `POST /api/confirm/approve`; dashboard "Inbox" tab; nothing hits client RAG until `status=confirmed` |
| **Demo line** | *"Ophelia can't return success without a booking_id. Alex can't return research to the user without a confirmed digest."* |
| **Alex reuse** | **90%** |

---

#### Project 2: **Provider Adapter SDK** — Fragmented Supply Abstraction

| Field | Detail |
|-------|--------|
| **Ophelia problem** | Every platform spends $2M or kills the feature — need one interface, many suppliers |
| **What you build** | `backend/researcher/providers/` — unified interface over financial data sources |

```python
class DataProvider(Protocol):
    def search(self, query: SearchRequest) -> list[Result]: ...
    def fetch(self, id: str) -> Document: ...
    def health(self) -> ProviderHealth: ...
```

| Implementations | `YFinanceProvider`, `SECProvider`, `PlaywrightWebProvider` |
| **Alex components** | Refactor `market_data.py`, `mcp_servers.py`; per-provider metrics in `/observe` |
| **Ophelia parallel** | `SearchProvider` / `BookingProvider` adapters for OpenTable, Resy |
| **MVP (2 weeks)** | 3 providers behind interface; contract tests with recorded fixtures; P95 per provider on `/observe` |
| **Demo line** | *"New provider = new adapter, not new orchestrator — same pattern I used for MetaML ontology unification and Robothons C++/Java adapters."* |
| **Alex reuse** | **85%** |

---

#### Project 3: **Alex Execution Simulator** — "Paper Book" (mirror Paper Trade)

| Field | Detail |
|-------|--------|
| **Ophelia problem** | Platforms need to test booking flows without real money or inventory |
| **What you build** | **Paper booking simulation** — user says "book dinner Friday 8pm"; agents search (Playwright/public pages), debate venue choice, simulate hold/confirm → write to `simulated_bookings` (like `simulated_trades`) |
| **Alex components** | Trading floor debate engine (rebrand agents: Venue, Budget, Distance, Reviews, Availability, Risk); `simulated_trades` schema → `simulated_bookings`; replay UI on `/trading` |
| **Ophelia parallel** | Staging/sandbox before production confirm; dynamic market simulation in Robothons ITP |
| **MVP (3 weeks)** | 6-agent "dinner committee" + simulated confirm card; no real reservation |
| **Demo line** | *"Paper trade proved debate + simulation in finance. Paper book proves search → committee → confirm without touching OpenTable production."* |
| **Alex reuse** | **80%** |

---

#### Project 4: **Multi-Party Coordinator** — Bo's Dating App Fix

| Field | Detail |
|-------|--------|
| **Ophelia problem** | Two (or three) users coordinate one reservation — backend breaks at conversion peak |
| **What you build** | **Group research session** — 3 users RSVP to a shared "research plan" on a ticker; correlation ID links participants; workflow: `draft → rsvp → research_run → confirm_digest` |
| **Alex components** | New `workflow_runs` + `workflow_participants` tables; SQS messages carry `correlation_id`; EventBridge timeout per step |
| **Ophelia parallel** | Draft booking → RSVP → pay → confirm for group dates |
| **MVP (3–4 weeks)** | Shared watchlist debate; all must RSVP before scheduler runs portfolio research |
| **Demo line** | *"Bo's app failed when two users coordinated a date. I built correlation-ID workflows on the same SQS pipeline Alex uses for portfolio digests."* |
| **Alex reuse** | **75%** |

---

#### Project 5: **Idempotent Action Gateway** — P5 Tools-Only for Mutating Ops

| Field | Detail |
|-------|--------|
| **Ophelia problem** | Agent retries on timeout create duplicate bookings without idempotency |
| **What you build** | Implement P5 `tool_gateway.py` — every mutation (ingest, portfolio update, trade vote persist) requires `Idempotency-Key`; cache in Aurora; replay returns cached response |
| **Alex components** | `tool_invocations` table (P5); gateway wraps all writes; tests prove double-submit = single row |
| **Ophelia parallel** | `Idempotency-Key` on `create booking` |
| **MVP (1–2 weeks)** | Gateway on `ingest_financial_document` + portfolio upsert; log to `tool_invocations` |
| **Demo line** | *"Agents retry aggressively. Idempotency on create is week-one Ophelia founding work — I built it for ingest and portfolio writes."* |
| **Alex reuse** | **85%** (implements planned P5) |

---

#### Project 6: **Execution Observability v2** — Confirm-Rate Dashboard

| Field | Detail |
|-------|--------|
| **Ophelia problem** | Can't improve confirm rate blind — need per-provider P95, retry count, funnel |
| **What you build** | Extend `/observe` with **execution funnel**: intent → tool calls → ingest success → digest confirmed; per-route P50/P95; **confirmation rate** = digests written / research jobs started |
| **Alex components** | `query_latency_metrics` (P15); `agent_observations`; new panels: Confirmation Rate, Per-Tool P95, Retry Count, DLQ depth |
| **Ophelia parallel** | Search-to-book funnel; time-to-confirm P95 per provider |
| **MVP (2 weeks)** | SQL rollups + 4 new `/observe` panels; daily email from P21 cost agent includes confirm rate |
| **Demo line** | *"Ophelia measures confirmation rate. I measure pipeline completion rate and cost-per-confirmed-digest — same ops discipline."* |
| **Alex reuse** | **90%** |

---

#### Project 7: **MCP Execution Gateway** — Ophelia-Style Tool Surface

| Field | Detail |
|-------|--------|
| **Ophelia problem** | Agents need MCP (`search`, `create`, `cancel`) + platforms need REST — same backend |
| **What you build** | `mcp_gateway.py` exposing Alex tools as MCP server **and** REST — `search_research`, `create_digest`, `list_sessions`, `cancel_job` map 1:1 |
| **Alex components** | P7 MCP expansion; shared Pydantic schemas; MCP ↔ REST parity tests |
| **Ophelia parallel** | `mcp.ophelia.so` + customer SDK |
| **MVP (2–3 weeks)** | 4 tools with JSON schemas; Claude/Cursor can call; Next.js uses same backend |
| **Demo line** | *"MCP is the agent boundary; REST is the platform boundary. One execution core — I did this with Playwright MCP internally and REST externally in Alex."* |
| **Alex reuse** | **80%** |

---

#### Project 8: **BriefingAI** — Fastest Non-Finance Ophelia Parallel

| Field | Detail |
|-------|--------|
| **Ophelia problem** | Consumer platforms need ongoing intelligence, not one-shot chat |
| **What you build** | Swap portfolio tickers for **topic watchlist** (e.g. "agentic AI", "Ophelia competitors"); same 2h scheduler → reporter → morning brief email |
| **Alex components** | `scheduler.py` loop on watchlist; `portfolio_digests` → `topic_briefs`; reporter prompt swap only |
| **Ophelia parallel** | Scheduled availability refresh + digest for platform ops teams |
| **MVP (1 week)** | One watchlist, daily SES email, dashboard card |
| **Demo line** | *"90% code reuse — proves Alex is an execution OS, not a finance-only app."* |
| **Alex reuse** | **90%** |

---

#### Project 9: **Resilience Lab** — Retry, Circuit Breaker, Fallback Demo

| Field | Detail |
|-------|--------|
| **Ophelia problem** | Brittle third-party surfaces need retry/proxy without humans |
| **What you build** | `scripts/chaos_test.sh` — kill ECS mid-request, provider timeout, Aurora pause; verify fallback paths; per-provider circuit breaker in `market_data.py` |
| **Alex components** | Reporter ECS→Bedrock fallback; Aurora 3x retry; add circuit breaker + DLQ (P18) |
| **Ophelia parallel** | Proxy fallback with `source: proxy` metadata |
| **MVP (1–2 weeks)** | Chaos script + circuit breaker on 2 data providers; document in `Alex_report.md` |
| **Demo line** | *"Bread taught me 100+ bots need escalation. Alex chaos tests prove the reporter completes when ECS dies."* |
| **Alex reuse** | **85%** |

---

#### Project 10: **Outcome Eval Harness** — RAGAS → Confirmation Rate

| Field | Detail |
|-------|--------|
| **Ophelia problem** | Execution quality = outcomes, not LLM vibes |
| **What you build** | Extend P17 RAGAS to **execution outcomes**: pipeline job started → digest confirmed → dashboard rendered (end-to-end); weekly CI gate; block deploy if confirm rate < 95% |
| **Alex components** | `scripts/tests/test_ragas.py` + new `test_execution_outcomes.py`; `ragas_evaluations` + `execution_evaluations` tables |
| **Ophelia parallel** | Weekly provider regression suite; confirmation rate gate before adapter deploy |
| **MVP (1 week)** | 5 synthetic portfolio jobs; assert digest row exists; CI workflow |
| **Demo line** | *"Archemy RAGAS improved reliability 30%. I'd run the same gates on Ophelia's confirm step."* |
| **Alex reuse** | **85%** |

---

### 9.4 Project Selection Matrix

| Project | Weeks | Alex reuse | Ophelia demo value | Best for interview story |
|---------|-------|------------|--------------------|-------------------------|
| **ConfirmGate** | 2 | 90% | ⭐⭐⭐⭐⭐ | "Confirm is all-or-nothing" |
| **Provider Adapter SDK** | 2 | 85% | ⭐⭐⭐⭐⭐ | "New supplier = new adapter" |
| **Idempotent Action Gateway** | 1–2 | 85% | ⭐⭐⭐⭐⭐ | "Agent retries don't duplicate" |
| **Execution Observability v2** | 2 | 90% | ⭐⭐⭐⭐ | "Confirmation rate dashboard" |
| **BriefingAI** | 1 | 90% | ⭐⭐⭐ | "Execution OS, not finance-only" |
| **Paper Book Simulator** | 3 | 80% | ⭐⭐⭐⭐ | "Paper trade → paper book" |
| **Multi-Party Coordinator** | 3–4 | 75% | ⭐⭐⭐⭐⭐ | "Bo's dating app fix" |
| **MCP Execution Gateway** | 2–3 | 80% | ⭐⭐⭐⭐ | "MCP + SDK same backend" |
| **Resilience Lab** | 1–2 | 85% | ⭐⭐⭐⭐ | "Chaos + circuit breaker" |
| **Outcome Eval Harness** | 1 | 85% | ⭐⭐⭐ | "Eval on outcomes not vibes" |

**Recommended 30-day Ophelia portfolio sprint on Alex:**

```
Week 1: Idempotent Action Gateway + Outcome Eval Harness
Week 2: Provider Adapter SDK + Execution Observability v2
Week 3: ConfirmGate + BriefingAI demo
Week 4: Paper Book Simulator OR Multi-Party Coordinator (pick one narrative)
```

---

### 9.5 How to Present These in an Ophelia Conversation

**Bridge phrase (use after any Alex demo):**

> *"The domain here is finance; the engineering is execution — fragmented supply, idempotent confirm, observable outcomes. That's the same layer Ophelia builds for bookings. I'd bring the adapter framework, confirm gate, and observability patterns; you'd bring provider partnerships and booking state machines."*

**Map to Ophelia's 30/60/90 day plan** (`Ophelia.md` § Solving Core Issues):

| Ophelia 90-day item | Alex project that proves it |
|---------------------|----------------------------|
| Idempotency on `create` (week 2) | **Idempotent Action Gateway** |
| `BookingProvider` interface (week 3) | **Provider Adapter SDK** |
| Confirm metrics dashboard (week 4) | **Execution Observability v2** |
| Booking state machine (week 6) | **ConfirmGate** |
| MCP ↔ SDK parity (week 8) | **MCP Execution Gateway** |
| Chaos tests (week 11) | **Resilience Lab** |
| Multi-party workflow (week 12) | **Multi-Party Coordinator** |

---

### 9.6 New Schema Stubs (Shared Across Projects)

Add to `aurora_warmup.py` when implementing Ophelia-style projects:

```sql
-- ConfirmGate + execution tracking
CREATE TABLE IF NOT EXISTS pending_confirmations (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL,
  resource_type VARCHAR(50) NOT NULL,  -- digest | memo | trade | booking_sim
  resource_id UUID,
  status VARCHAR(20) DEFAULT 'pending',  -- pending | approved | rejected
  payload JSONB NOT NULL,
  correlation_id UUID,
  idempotency_key VARCHAR(128) UNIQUE,
  approved_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Provider adapter observability
CREATE TABLE IF NOT EXISTS provider_call_metrics (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  provider_name VARCHAR(100) NOT NULL,
  operation VARCHAR(50) NOT NULL,
  success BOOLEAN NOT NULL,
  latency_ms INTEGER,
  error_code VARCHAR(50),
  correlation_id UUID,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Multi-party workflows (Project 4)
CREATE TABLE IF NOT EXISTS workflow_runs (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  correlation_id UUID NOT NULL UNIQUE,
  workflow_type VARCHAR(50) NOT NULL,
  status VARCHAR(30) DEFAULT 'draft',
  current_step VARCHAR(50),
  payload JSONB DEFAULT '{}',
  expires_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ DEFAULT NOW()
);
```

---

### 9.7 Related Documents

| Document | Use |
|----------|-----|
| [`Ophelia.md`](Ophelia.md) | Full thesis, interview prep, 30/60/90 plan, STAR stories |
| [`RIA.md`](RIA.md) | ConfirmGate extends RIA memo approval pattern |
| [`Alex_Master_Implementation_Plan.md`](Alex_Master_Implementation_Plan.md) | P5 tools gateway, P15 latency, P17 RAGAS, P18 DLQ |
| [`Alex_Trading_Floor_2.0.md`](Alex_Trading_Floor_2.0.md) | Paper Book Simulator debate engine |

---

## 10. Document Index

| Document | Purpose |
|----------|---------|
| `usecases.md` | **This file** — cross-industry use cases, startups, beginner plan, Ophelia projects |
| `Agentic_Usecase.md` | Agentic use cases on **live Alex** — finance-native workflows, demos, build order |
| `Ophelia.md` | Ophelia thesis, Alex pillar mapping, interview prep, 30/60/90 execution plan |
| `RIA.md` | RIA Copilot — white-label Alex for advisors; full product + architecture leverage |
| `Startup.md` | Alex monetization, pricing, GTM, unit economics |
| `Alex_Master_Implementation_Plan.md` | Engineering phases P0–P21 |
| `Alex_report.md` | Production audit trail, infra, APIs, §33 change log |
| `Alex_Trading_Floor_2.0.md` | Multi-agent debate + simulation spec |
| `Alex_AI_2.0.md` | Router, RAG, MCP, chat spec |
| `scripts/TEST_PLAYBOOK.md` | Verification after each feature |

---

## Summary

The Alex stack is a **general-purpose agentic AI operating system**: router brain, scheduled hands, observable ops, Terraform-proven infra. Finance is the first vertical because portfolio context, market data MCPs, and paper trading map cleanly — but the same pattern solves **prior auth, contracts, SOC/SRE triage, supplier risk, hiring committees, compliance monitoring, FP&A board decks, grant discovery, CRE underwriting, Amazon seller intel, franchise ops, patent prior art, and daily industry briefings** where the pain is **ongoing, multi-source, and audit-sensitive**.

**22 cross-industry use cases** (§3.1–3.22) and **30+ startup ideas** (Tiers A–D) documented with Alex reuse %.

**Beginner path:** Week 1–2 single agent + DB → Week 3–4 router + RAG → Week 5–6 ECS + tools → Week 7–8 SQS multi-agent → Week 9–12 guardrails + cost + eval. Use `start_session.sh` / `stop_session.sh` to keep dev costs under ~$12/mo.

**Best startup bets from this platform:**

| Tier | Picks |
|------|-------|
| Revenue speed | Alex B2C, BriefingAI |
| ARPU | RIA Copilot, Family Office Copilot, CRE Credit Memo |
| Data moat | Agent Sentiment Index |
| Non-finance pivot | BriefingAI (90% reuse), Incident Commander (80%) |
| **Ophelia execution portfolio** | ConfirmGate + Provider Adapter SDK + Idempotent Gateway (§9) |

---

*For implementation changes, log in `Alex_report.md` §33. For infra, Terraform only — see §22.5.*
