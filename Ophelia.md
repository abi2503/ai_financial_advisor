# Ophelia Interview Prep — Alex AI Project Mapping

> **Created:** June 13, 2026 · **Updated:** June 13, 2026  
> **Purpose:** Interview preparation for Ophelia — personalized for **Abhishek Suresh** (`Abhishek_Resume.pdf`).  
> **Call format:** 30–60 min phone/video screen — see [§ Phone Call Playbook](#phone-call-playbook-3060-min).  
> **Sources:** Resume, `ITP Final PPT.pdf` (NYU ITP — Robothons/CITI), [opheliaos.com](https://www.opheliaos.com/), Bo Brainerd origin story, Alex codebase.

---

## Table of Contents

0. [**Your Profile & Career Story**](#your-profile--career-story) ← start here
1. [Phone Call Playbook (30–60 min)](#phone-call-playbook-3060-min)
2. [Founder Origin Story (Know This Cold)](#founder-origin-story-know-this-cold)
3. [Company Basics](#company-basics)
4. [Ophelia's Thesis](#ophelias-thesis)
5. [What Ophelia Builds](#what-ophelia-builds)
6. [Market & Sector Talking Points](#market--sector-talking-points)
7. [Alex → Ophelia: The Core Analogy](#alex--ophelia-the-core-analogy)
8. [Pillar-by-Pillar Mapping](#pillar-by-pillar-mapping)
9. [Suggested Intro (30s / 2min)](#suggested-intro-30s--2min)
10. [STAR Stories (Resume + Alex)](#star-stories-resume--alex)
11. [Ophelia-Specific Talking Points](#ophelia-specific-talking-points)
12. [**Solving Core Issues as a Founding Member**](#solving-ophelias-core-issues-as-a-founding-member)
13. [**Archemy Use Cases (ITP + Resume)**](#archemy-use-cases-itp--resume)
14. [Resume → Ophelia Mapping (Every Bullet)](#resume--ophelia-mapping-every-bullet)
15. [Interview Prep Guide](#interview-prep-guide)
16. [Technical Questions You Might Get](#technical-questions-you-might-get)
17. [Questions to Ask Ophelia](#questions-to-ask-ophelia)
18. [Gaps to Acknowledge (Honestly)](#gaps-to-acknowledge-honestly)
19. [Pre-Interview Checklist](#pre-interview-checklist)

---

## Your Profile & Career Story

### At a Glance

| Field | Detail |
|-------|--------|
| **Name** | Abhishek Suresh |
| **Location** | New York, USA (same city as Ophelia) |
| **Contact** | 551-229-8434 · as18757@nyu.edu |
| **Education** | MS Information Systems, NYU (Sep 2023 – May 2025) · BTech CSE, SRM (2015 – 2019) |
| **Current role** | AI Engineer, Archemy Inc, NYC (Aug 2025 – Present) |
| **Total experience** | ~6 years (Infosys → Bread Financial → Archemy) + Alex side project |
| **Ophelia fit headline** | Production orchestration + agent execution + eval/reliability — not prompt engineering |

### Your Career Arc (The Story You Tell)

**One thread across every job:** turning non-deterministic AI/ML outputs into **reliable, confirmed production outcomes** across fragmented systems.

```
2019–2022  Infosys        → Orchestration + recovery (bots, checkpoints, Airflow validation)
2023       Bread Financial → Production scale (100+ UiPath bots, queues, CI/CD, monitoring)
2023–2025  NYU MS         → Information systems + agentic AI depth
2025–now   Archemy        → RAG pipelines, RAGAS/LangSmith eval, Terraform Aurora
Side       Alex (project) → Full agentic execution layer — MCP, SQS, ECS, confirmed digests
```

**30-second career narrative:**

> *"I've spent six years climbing from RPA orchestration to agentic execution. At Bread I ran 100+ production bots with UiPath Orchestrator — queues, triggers, SLA monitoring — which taught me that the hard part is never the logic, it's durable execution under failure. At Archemy I build RAG pipelines with RAGAS evaluation and Terraform-provisioned Aurora. Alex is where I combined all of it: multi-agent SQS pipelines, Playwright MCP, confirmed outcomes in Aurora — the same execution-layer problem Ophelia solves for bookings."*

### Why You're a Strong Fit for Ophelia (Internalize This)

| Ophelia needs | Your proof |
|---------------|------------|
| Execution layer, not chatbot | Alex: confirmed `portfolio_digests`, not chat-only; Bread: 100+ bots with confirmed task completion |
| Orchestration at scale | Bread Orchestrator + Alex SQS pipeline + **Robothons RabbitMQ execution pipeline (ITP/CITI)** |
| Platform-owned execution | **Robothons: platform owns trade execution**, not bot strategy — same as Ophelia owning confirm |
| Third-party fragility | Alex: SEC EDGAR, Playwright MCP, ECS fallbacks; Bread: multi-source REST/SQL feeds |
| Reliability / retries | Infosys checkpoint recovery; Alex Aurora retry + ECS→Bedrock fallback |
| Eval on outcomes | Archemy RAGAS + LangSmith; Alex `test_ragas.py` + `/observe` |
| MCP / agent tooling | Alex Playwright MCP; resume lists MCP, OpenAI Agents SDK, LangGraph |
| NYC early-stage startup | You're in NYC, just finished NYU, currently at NYC startup Archemy |
| IaC / production deploy | Terraform (Archemy Aurora + Alex 12 AWS services); GitHub Actions CI/CD from Infosys/Bread |

### What NOT to Lead With

- Fine-tuning LLaMA on Amazon prices (interesting, but not Ophelia-relevant)
- MetaML taxonomy dashboard (knowledge graph — mention only if they ask about RAG/search)
- "I'm a new grad" — frame as **6 years production engineering** + fresh MS in agentic AI

---

## Phone Call Playbook (30–60 min)

Early-stage startup screens are usually conversational, not LeetCode. Expect: background → one deep project → fit → your questions.

### Likely Call Structure

| Time | Segment | What to do |
|------|---------|------------|
| **0–3 min** | Warm open | Thank them, confirm audio, brief "I'm in NYC, MS NYU, AI Engineer at Archemy" |
| **3–5 min** | "Tell me about yourself" | Use [§ 30-Second Intro](#30-second-intro-opener) → offer to go deeper |
| **5–15 min** | Resume walkthrough | Hit Archemy → Alex → Bread (reverse chronological, execution framing) |
| **15–30 min** | Deep dive | They'll pick **Alex** or **Archemy** — have both ready (see below) |
| **30–40 min** | Technical / scenario | "How would you handle retries?" "Design a booking flow" — use orchestrator sketch |
| **40–50 min** | Why Ophelia + culture | Bo's story + your NYC/startup timing + execution thesis |
| **50–60 min** | Your questions | Pick 3 from [§ Questions](#questions-to-ask-ophelia); ask about role + next steps |

### If the Call Is Only 30 Minutes

**Prioritize this order (cut the rest):**

1. 30s intro + career arc (1 min)
2. Alex project — execution layer only, not full feature tour (5–7 min)
3. One Bread proof point — 100+ production bots, orchestration (2 min)
4. Why Ophelia — Bo's story + execution bottleneck (2 min)
5. One technical answer — booking orchestrator sketch OR idempotency (3 min)
6. Two smart questions + close (3 min)

### Deep-Dive A: Alex (Lead Project — ~8 min script)

Use if they say *"Tell me about your financial platform"* or *"Walk me through a recent project."*

> *"Alex is an autonomous financial research platform I built on AWS — 12 services, all Terraform. The core problem was the same one Bo describes: the LLM could reason about stocks, but the system wasn't useful until execution was reliable.*
>
> *There are two paths. **Sync:** user asks a question → ECS researcher streams an answer, uses Playwright MCP to browse live SEC EDGAR and market data, ingests confirmed documents into Aurora pgvector. **Async:** EventBridge fires every 2 hours → scheduler reads each user's portfolio → planner decomposes holdings into research tasks → tagger → reporter executes on ECS → writes confirmed digest cards to `portfolio_digests` → dashboard updates.*
>
> *I also built a 6-agent trading debate — five specialists vote in parallel via ThreadPool, executor synthesizes a structured BUY/SELL/HOLD with Pydantic models. Everything lands in an observability page: per-agent cost, latency, guardrail hits.*
>
> *The hardest engineering wasn't prompts — it was execution: Aurora Data API returning NUMERIC as strings so P&L showed zero, ECS cold starts so I added Bedrock fallback, SQS visibility timeouts matched to 900s Lambda limits. That's the muscle I'd bring to Ophelia's confirm step."*

### Deep-Dive B: Archemy (Current Job — ~6 min script)

Use if they focus on *current role*, *RAG/eval*, or *platform/orchestration experience*.

> *"At Archemy I'm the AI Engineer on two interconnected platforms — the **MetaML knowledge layer** and the **Robothons execution platform**.*
>
> *On MetaML, I built production RAG infrastructure: serverless SageMaker embeddings, S3 Vectors, API Gateway + Lambda — sub-3-second semantic search at ~90% lower cost than managed vector DBs. I also built a SQL-to-vector knowledge graph syncing MySQL ontology into ChromaDB with NetworkX — 648 nodes, 1,200 edges — fine-tuned MiniLM for +70% search accuracy. That's unified search over fragmented domain data — same abstraction problem as Ophelia over fragmented booking supply.*
>
> *On evaluation, LangSmith + RAGAS track retrieval precision, faithfulness, and latency; low-confidence outputs route to human review — +30% reliability. I provisioned Aurora Serverless v2 via Terraform with RDS Data API for serverless audit trails.*
>
> *My NYU ITP capstone — documented in our Robothons presentation — was the **CITI Global Markets competition platform**: a modular execution system where participant bots in C++, Java, and Python connect through **RabbitMQ**, run through validation and dynamic market simulation, and execute trades through a pipeline: initialization → market events → strategy → **trade execution**. We redesigned monolithic bot architectures into adapter-style modules so new languages plug in without rewriting the orchestrator.*
>
> *Robothons is Archemy's competition-and-simulation platform for crowdsourcing reusable components — banking, healthcare, supply chain. The through-line to Ophelia: I build the layer that turns agent/bot **intent** into **confirmed execution** — whether that's a trade fill, a RAG answer grounded in ontology, or a booking confirmation."*

**Shorter version (3 min):** MetaML RAG + KG unification + RAGAS eval + Robothons CITI execution pipeline with RabbitMQ and multi-language adapters.

### Deep-Dive C: Bread Financial (Orchestration Credibility — ~3 min)

Use if they ask *"Have you run things in production at scale?"* or *"Experience with workflows?"*

> *"Before Archemy, at Bread Financial I led 100+ enterprise UiPath bots in production — Orchestrator, queues, triggers, unattended runners. I mentored junior devs and enforced REFramework standards for SLA compliance.*
>
> *I integrated SageMaker REST APIs into bot workflows for real-time fraud scoring, combining anomaly signals, SQL, and REST feeds — 18% fraud recall improvement. I also implemented CI/CD-style promotion across DEV/QA/PROD with version-controlled packages.*
>
> *That's where I learned orchestration isn't glamorous — it's queues, retries, monitoring, and escalation when a third-party feed fails. Ophelia's retry/proxy logic for booking providers is the same discipline at a different layer."*

### Phone-Specific Tips

- **Stand up, smile** — energy carries on audio-only calls
- **Pause after 60–90 sec** — *"Happy to go deeper on any of that"*
- **No screen share assumed** — describe systems verbally; offer GitHub/demo for round 2
- **Have water + resume PDF open** — don't read it verbatim
- **Quiet room** — mention NYC if small talk comes up (shared city with Ophelia)
- **Close strong:** *"I'm excited about the execution-layer problem — it's what I've been building toward from RPA through agents. What are next steps?"*

### Likely Questions & One-Line Answers

| Question | Your answer (anchor) |
|----------|----------------------|
| Tell me about yourself | Career arc § + current Archemy + Alex execution layer |
| Why Ophelia? | Bo's story + **Archemy Robothons execution platform** (CITI) + Alex |
| What would you do first 90 days? | § Solving Core Issues — idempotency → adapters → observability |
| Why founding member vs big co? | Alex 0→1 solo + Bread 100+ prod + want to own execution path end-to-end |
| Hardest technical problem? | Aurora `stringValue` bug OR ECS timeout fallback |
| Experience with MCP? | Playwright MCP (Alex); Archemy MetaML tool/RAG layer |
| Orchestration / queues? | **RabbitMQ** (Robothons ITP); SQS (Alex); UiPath Orchestrator (Bread) |
| How do you ensure reliability? | Retries, idempotent upserts, SQS decoupling, eval gates (RAGAS) |
| Production scale? | Bread 100+ bots; Alex 12 AWS services, EventBridge every 2h |
| Why leave Archemy? | *(If asked)* Frame as seeking execution-layer infra at agentic AI frontier — don't badmouth current employer |
| Salary / start date? | Be ready: "Flexible on timing; prioritizing right fit on execution-layer engineering" |

---

## Founder Origin Story (Know This Cold)

**This is the emotional core of Ophelia.** Mention it naturally in "Why Ophelia?" — it shows you did homework beyond the homepage.

**Bo Brainerd** (CEO/founder) built an **IRL dating app** while at **Boston College**. The product worked in demos — but the back-end **broke the moment two users tried to coordinate an actual date**.

The failure mode was execution, not matching:
- Confirming a reservation required **manual workarounds** at the highest conversion moment, **or**
- Waiting **months** for exclusive partner APIs

Every team Bo asked about in-app planning or booking hit the same wall:
- **Kill the feature**, or
- Spend **~$2M** building brittle integrations around fragmented supply

**Bo shut down the dating app and built Ophelia instead.**

**Result:** Ophelia went live across **10 platforms in 6 months** — proof that a unified execution layer beats per-platform integration hell.

**How to use this in your interview:**

> *"What resonated with me is Bo's origin story — the dating app didn't fail on matching, it failed the moment two people tried to coordinate a real-world outcome. That's exactly what I ran into building Alex: the LLM could reason about NVDA all day, but the system only became useful when I built durable execution — confirmed digests in Aurora, idempotent ingest, SQS pipelines that survive timeouts. Ophelia is solving that same class of problem for bookings at a much larger scale."*

**Alex parallel to Bo's story:**

| Bo's dating app pain | Your Alex pain |
|----------------------|----------------|
| Two users coordinate a date → backend breaks | User asks for research → chat works, but no confirmed digest in DB |
| Manual reservation workarounds | Manual scheduler enable, ECS env sync via `start_session.sh` |
| $2M for partner APIs | Would need custom integrations per data source (SEC, news, brokers) |
| Killed feature or built around it | Built unified execution layer (planner → reporter → `portfolio_digests`) |

---

## Company Basics

| Field | Detail |
|-------|--------|
| **What** | Execution layer for real-world coordination — **not** another chatbot or frontend |
| **HQ** | New York City |
| **Stage** | Early-stage, venture-backed (~2024 founding) |
| **Team** | Small (2–10 people) |
| **CEO** | Bo Brainerd |
| **Sector** | AI infrastructure / agentic AI — specifically the **action/execution layer** |
| **Customers** | Consumer platforms (dating, social, travel) + AI agents |
| **Product** | Unified API + SDK (+ MCP server for agents) |
| **Traction signal** | Live across 10 platforms in 6 months |

**What they are NOT:**
- Not a foundational LLM company (no model training)
- Not a consumer-facing booking app
- Not a single-vertical point solution (restaurants only, etc.)

**What they ARE:**
- Backend plumbing that turns digital intent into **confirmed physical-world outcomes**
- Infrastructure for the messy middle: real-time inventory, retries, payments, confirmations, exceptions, reconciliation

---

## Ophelia's Thesis

Four themes — memorize these. Every interview answer should trace back to one of them.

### 1. The Physical-Digital Gap

AI lives in chat, reasoning, planning. The real world (restaurants, events, fitness, tickets) is **messy, fragmented, and partially offline**. This gap kills most agent attempts.

> *Alex version:* Financial data lives across SEC EDGAR, news sites, broker APIs, and live web pages — equally fragmented.

### 2. Intent vs. Execution

Agents excel at *"book dinner for 2 on Friday"* or *"plan a date near campus"*. They fail at:
- Real-time availability checks
- Supplier API calls
- Payments
- Retries after timeout
- Confirmations and exception handling

> *Alex version:* Agents excel at *"what are NVDA's risks?"* but fail without ingest → vector store → dashboard card confirmation.

### 3. Intelligence Is Solved — Execution Is the Bottleneck

LLMs handle thinking. The **new bottleneck is reliable real-world execution at scale.**

Their line: *"The next bottleneck in AI isn't intelligence — it's execution at scale."*

> *This is Ophelia's #1 line. Use it verbatim once, then demonstrate you live it via Alex examples.*

### 4. Unified Execution Layer

One clean API/SDK abstracts thousands of fragmented suppliers (OpenTable, Ticketmaster, Mindbody, Resy, Calendly, etc.) so platforms and agents turn intent into confirmed outcomes **without brittle custom integrations or manual ops**.

**Network effect:** More platforms + suppliers → smarter, more reliable unified layer.

---

## What Ophelia Builds

| Capability | What it means |
|--------------|---------------|
| **Search** | Real-time availability across fragmented booking surfaces |
| **Create / manage / cancel** | One API call — not a redirect, not "we'll try" |
| **Payments** | Handle money movement in the execution flow |
| **Confirmations** | Return a durable `booking_id` + reconciliation state |
| **Retries & proxy logic** | Survive brittle third-party surfaces without humans in the loop |
| **Exception handling** | Cancellations, modifications, partial failures |
| **MCP server** | `mcp.ophelia.so` — native agent tool calls (search, create, list, cancel) |
| **SDK** | Drop into consumer apps or agent runtimes — one integration |

**Example verticals:** OpenTable-style reservations, Ticketmaster/StubHub events, Mindbody/ClassPass fitness, appointments, travel experiences.

**Positioning:** Solving the **#1 bottleneck** for AI agents moving beyond chat to real actions — and unlocking **agentic commerce** for consumer platforms.

This is the frame for every answer: you didn't build a chatbot — you built **infrastructure that turns agent intent into durable, confirmed outcomes**.

---

## Market & Sector Talking Points

Use 2–3 of these when they ask about market opportunity or "why now?" — tie each back to Ophelia's thesis.

### Agentic AI (Macro Context)

| Stat | Source / framing |
|------|------------------|
| **~$7–9B** agentic AI market in 2025/26 → **$50–200B+** by 2030–34 (CAGR 40–46%) | MarketsandMarkets, Mordor, IDC |
| **40%** of enterprise apps will include task-specific AI agents by end of **2026** (vs <5% in 2025) | Gartner |
| **>1B** AI agents worldwide estimated by end of 2026 | IBM / Salesforce |
| **Key shift:** Reasoning advances fast; **execution** remains #1 bottleneck | Ophelia's core bet |

**Your line:**

> *"The market is pouring billions into agent intelligence, but Bo's origin story and Ophelia's positioning are right — the winner in agentic AI won't be the best chatbot, it'll be whoever owns reliable execution. That's the layer I'm most excited to build."*

### Agentic Commerce & Execution Infrastructure

| Stat | Framing |
|------|---------|
| **$1T** US B2C retail orchestrated by agents by 2030; **$3–5T** globally | McKinsey / agentic commerce projections |
| **~$10B** AI agent orchestration infrastructure market in 2025 → **$150B+** by 2034 (CAGR ~42%) | MarketIntelo |
| **Real-world action gap:** Agents plan well, fail on availability → pay → confirm → exception | Exactly Ophelia's wedge |

**Your line:**

> *"Agentic commerce is a trillion-dollar wave, but it doesn't happen without an execution layer. Ophelia sits at the last mile — the same way payment rails enabled e-commerce, execution rails enable agentic commerce."*

### Booking / Real-World Services (Ophelia's Core Vertical)

| Stat | Framing |
|------|---------|
| Online event ticketing: **~$53–58B** in 2026 → **$70–118B** by 2030–35 | TBRC |
| Reservations/booking software: **10–12% CAGR** in North America | Restaurants, events, experiences |
| Online travel booking: hundreds of billions, mobile/agent flows accelerating | End-to-end agent booking |
| **Fragmentation:** Thousands of suppliers with brittle APIs | Ophelia's single-API value prop |

**Your line:**

> *"Every platform Bo talked to faced the same fork: kill in-app booking or spend millions on integrations. A unified execution layer isn't a nice-to-have — it's the only scalable path as agents move from prototypes to production."*

### Why Now (2026 Timing)

1. **Agentic AI moves from chat → production execution** this year
2. Dating/social/travel platforms need **in-app booking rails** now (conversion at peak)
3. **Competitive landscape heating up** — early-stage, but execution-layer plays are raising significant seed/Series A
4. Ophelia differentiates on **IRL experiences/bookings** vs. pure e-commerce checkout

**Competitive awareness (don't oversell):** Mention you know the space is heating up; Ophelia's defensibility is **network effects + integration depth + confirmation reliability**, not being first to say "agents."

---

## Alex → Ophelia: The Core Analogy

```
┌─────────────────────────────────────────────────────────────────────────┐
│  OPHELIA                           │  ALEX (your project)               │
├────────────────────────────────────┼────────────────────────────────────┤
│  User intent: "book dinner 8pm"    │  User intent: "research NVDA"      │
│  Intelligence: LLM + routing       │  Intelligence: router + planner     │
│  Execution: book on OpenTable      │  Execution: ECS research + ingest  │
│  Confirmation: booking_id          │  Confirmation: digest card / vote  │
│  Fragmented supply: 50+ platforms  │  Fragmented data: SEC, news, MCP │
│  MCP tools: search, create, cancel │  MCP: Playwright + market tools    │
│  Durability: retry, proxy, track   │  Durability: SQS, Aurora retry     │
│  Observability: dashboard + export │  Observability: /observe + CW       │
└────────────────────────────────────┴────────────────────────────────────┘
```

**One-liner for interviews:**

> *"Ophelia closes the gap between AI intent and confirmed bookings. Alex closes the gap between AI intent and confirmed financial intelligence — sourced research, portfolio digests, and trade decisions — across fragmented market data, SEC filings, and web sources. I built the orchestration and execution layer, not just the reasoning layer."*

---

## Pillar-by-Pillar Mapping

### 1. Intelligence & Agent Orchestration Layers

| Ophelia need | What Alex already has | Evidence in codebase |
|--------------|-------------------------|----------------------|
| Route intent to right execution path | Fast vs deep vs multi-agent paths | `backend/researcher/server.py`, trading orchestrator |
| Multi-step coordination | SQS pipeline: scheduler → planner → tagger → reporter | `backend/agents/scheduler.py`, `planner.py`, `reporter.py` |
| Parallel specialist agents | 5 trading agents debate in parallel (ThreadPool) | `backend/agents/trading/core/debate_engine.py` |
| Task decomposition | Planner breaks portfolio into dimension-rotated research tasks | `backend/agents/planner.py` (portfolio_research mode) |
| Deterministic workflow around LLMs | Pydantic models for votes, debate results, trade actions | `backend/agents/trading/models.py` |

**Talking point:**

> *"I treat LLMs as non-deterministic workers inside deterministic orchestration. The planner emits typed tasks; the reporter executes them and writes confirmed outcomes to Aurora. Trading debates use structured `AgentVote` outputs — not free-form text — so downstream execution can act on them."*

**Planned (cite as roadmap, not shipped):** Query router (P1), async deep sub-agents (P15), RL-weighted debate votes (P8).

---

### 2. CI/CD & Deployment Infrastructure

| Ophelia need | What Alex already has | Evidence |
|--------------|-------------------------|----------|
| Automated deploy on change | 6 GitHub Actions workflows | `.github/workflows/` |
| Path-based service deploys | `deploy_agents.yml`, `deploy_trading.yml`, `deploy_researcher.yml` | Separate workflows per service |
| Smoke tests post-deploy | `scripts/test_trading.sh` invoked after trading deploy | `deploy_trading.yml` |
| IaC | 9 Terraform modules (VPC → trading floor → guardrails) | `terraform/0_vpc` through `terraform/9_trading_floor` |
| Packaging | `package.sh`, `deploy_trading.sh` | Lambda zip + env sync |
| Session bootstrap | `scripts/start_session.sh` — ECS discovery, env sync, scheduler enable | End-to-end dev/prod parity script |

**Talking point:**

> *"I deploy a hybrid stack — Lambda agents, ECS researcher, SageMaker embeddings — with path-filtered GitHub Actions. Trading deploys run a live orchestrator smoke test before we consider the release healthy. Terraform owns the EventBridge schedulers and SQS topology."*

**Implementable next (shows you think like them):** Unified `deploy_all.yml`, RAGAS eval gate in CI, `DEPLOY_VERSION` git SHA in Lambda env (see `Alex_Master_Implementation_Plan.md` → Production Engineering Pillars).

---

### 3. MCPs & Agent Tooling

| Ophelia need | What Alex already has | Evidence |
|--------------|-------------------------|----------|
| MCP as execution interface | Playwright MCP on ECS deep researcher | `backend/researcher/mcp_servers.py` |
| Native tool calls for agents | `get_stock_data`, `get_sec_filings`, `ingest_financial_document` | `backend/researcher/tools.py` |
| Tool budget management | Fast agent avoids MCP (Bedrock tool cap); deep agent gets Playwright | Documented split in researcher server |
| Tool observability (partial) | `agent_observations.data_used` | Observe API |

**Talking point:**

> *"Ophelia exposes booking as MCP tools — search, create, cancel. I did the same pattern for financial execution: Playwright MCP for live web research, Python tools for structured market/SEC data, and an ingest tool that writes confirmed vectors to Aurora. The hard part isn't calling tools — it's deciding which agent gets which tools under latency and reliability constraints."*

**Bridge to Ophelia MCP:**

> *"Your MCP server is the product boundary. I'd think about tool schemas, idempotency keys on `create`, and per-tool latency SLOs the same way I think about `ingest_financial_document` — did it succeed, how long, what source?"*

**Planned:** `mcp_gateway.py` (P7/P13) — central registry, same pattern as Ophelia's unified API over fragmented supply.

---

### 4. Reliability Engineering

| Ophelia need | What Alex already has | Evidence |
|--------------|-------------------------|----------|
| Retry on transient failures | Aurora `execute_sql` 3x retry; RDS Data API retry in frontend | `db_helper.py`, portfolio API |
| Automatic retry & proxy logic | Reporter ECS fallback to direct Bedrock on timeout | `backend/agents/reporter.py` |
| Guardrails on outputs | Bedrock guardrail (Terraform 7); trading confidence caps | `terraform/7_guardrails`, debate engine |
| Health checks | `health_check.sh`, `start_session.sh`, ops_agent | `scripts/`, `backend/agents/ops_agent.py` |
| Idempotent writes | Portfolio upsert, `cost_snapshots` upsert, `portfolio_digests` upsert | Aurora patterns |
| Async decoupling | SQS queues with visibility timeouts | `terraform/6_agents/main.tf` |

**Talking point:**

> *"Execution at scale means assuming every external call fails. I wrapped Aurora in retry logic, gave the reporter an ECS→Bedrock fallback, and use SQS so a slow research job doesn't block the scheduler. Ophelia's retry/proxy logic for booking surfaces is the same class of problem — brittle third parties, unpredictable latency."*

**Gap to name proactively:** Trading queue DLQ not yet wired; simulated trades need idempotency keys (P4). Shows maturity to admit and fix.

**SLOs you can propose:**

| Metric | Target |
|--------|--------|
| Fast query P95 | < 15s |
| Deep query P95 | < 90s |
| Trading debate success | > 95% |
| Ingest success | > 99% |

---

### 5. Inference Engineering

| Ophelia need | What Alex already has | Evidence |
|--------------|-------------------------|----------|
| Tiered models by task | Nova Pro (research, debate), Nova Lite (tagger, cost, ops) | Agent Lambdas + ECS |
| Embeddings endpoint | SageMaker `alex-embedding` (MiniLM 384-dim) | Terraform 2_sagemaker |
| Streaming responses | SSE on fast/deep research routes | `backend/researcher/server.py` |
| Token/cost tracking | `agent_observations` — per-call tokens, cost, latency | `/observe` page |
| Parallel inference | ThreadPool for 5 debate agents | `debate_engine.py` |
| Smart guardrail skip | `should_apply_guardrail()` — keyword heuristic | Researcher server |

**Talking point:**

> *"Inference engineering isn't picking the biggest model — it's matching model tier to SLA. Tagging runs on Nova Lite; deep research runs Nova Pro with MCP tools and streams tokens. I log every call to `agent_observations` so I can see cost-per-route and latency-per-agent, same way you'd track cost-per-booking-confirmation."*

**Planned:** `query_latency_metrics` (P15) — P50/P95 per route, first-token latency, sub-agent breakdown. Directly parallels Ophelia's latency focus.

---

### 6. Evaluation & Benchmarking Frameworks

| Ophelia need | What Alex already has | Evidence |
|--------------|-------------------------|----------|
| Quality measurement beyond "it works" | RAGAS eval script — relevancy, faithfulness | `scripts/tests/test_ragas.py` |
| Stored eval results | `ragas_evaluations` table in Aurora | RAGAS script |
| Agent accuracy tracking | `agent_performance` table (schema ready) | Trading floor design |
| Regression tests | `test_trading.sh`, `test_planner.py`, `test_multi_agent.py` | `scripts/tests/` |
| Observability as eval surface | `/observe` — cost, guardrails, agent stats | `frontend/app/observe/page.tsx` |

**Talking point:**

> *"Execution layers need evals on outcomes, not vibes. I run RAGAS against our RAG pipeline with target thresholds — relevancy > 0.87, faithfulness > 0.91. For trading, I'm building outcome-based scoring: did the debate's BUY/SELL align with subsequent price movement? That's analogous to Ophelia measuring booking confirmation rate vs. search-to-book drop-off."*

**Implementable next:** Wire RAGAS into weekly CI; block deploy if faithfulness drops below threshold (`eval_suite.sh` in master plan).

---

### 7. Distributed Systems & Production-Scale Architecture

| Ophelia need | What Alex already has | Evidence |
|--------------|-------------------------|----------|
| Hybrid compute | Lambda + ECS + SageMaker | Full stack |
| Async messaging | SQS (research, results, trading, frontend-results) | Terraform agents + trading |
| Scheduled orchestration | EventBridge — 2h portfolio research, daily cost | `terraform/6_agents/main.tf` |
| Serverless DB + vectors | Aurora Serverless v2 + pgvector | Ingest/search APIs |
| Multi-tenant isolation | `user_id` on portfolios, digests, sessions | Portfolio + dashboard APIs |
| API gateway pattern | API Gateway (ingest/search) + ALB (ECS) + Next.js routes | Multi-entry architecture |
| Custom metrics | CloudWatch `AlexAI/*`, `ResearchLatency` | Researcher server |

**Architecture you can whiteboard:**

```
Users → Next.js (Vercel)
          ↓
       ALB → ECS Researcher (SSE, MCP, tools)
          ↓                    ↓
    API Gateway            SQS Pipelines
    (ingest/search)     (research + trading)
          ↓                    ↓
    Lambda Ingest         Lambda Agents
          ↓                    ↓
    Aurora pgvector ←── RDS Data API ──→ 24+ tables
          ↑
    SageMaker Embeddings
          ↑
    EventBridge Schedulers
```

**Talking point:**

> *"I deliberately split sync paths (ECS streaming for user-facing research) from async paths (SQS for portfolio digests and trading debates). That mirrors how Ophelia likely separates low-latency search from durable booking execution — different consistency and timeout requirements."*

---

## Suggested Intro (30s / 2min)

### 30-Second Intro (Opener) — Personalized

> *"I'm Abhishek — AI Engineer at Archemy in New York, NYU MS Information Systems. I've spent six years in production orchestration: at Bread Financial I ran 100+ UiPath bots with queues and SLA monitoring, and now I build agentic systems — at Archemy, serverless RAG with RAGAS evaluation, and on the side, Alex, a full AWS agent platform with Playwright MCP and multi-agent SQS pipelines that write confirmed research digests to Aurora. I was drawn to Ophelia because of Bo's story — the dating app broke the moment two users tried to coordinate a real date, not at matching. That's the execution gap I've been solving: intelligence is easy, confirmed outcomes across fragmented systems is hard. I'd love to bring that to Ophelia's booking infrastructure."*

### Alternative Intro (Shorter — if they seem rushed)

> *"Abhishek — AI Engineer in NYC, six years from RPA orchestration to agentic execution. I build the layer between LLM reasoning and confirmed outcomes: SQS pipelines, MCP tools, idempotent writes, RAGAS eval. Ophelia's thesis — execution at scale — is exactly what I've been doing in Alex and Archemy. Excited to talk."*

### Alternative Intro (If Interviewing with Bo / Leadership)

> *"I followed Ophelia from the LinkedIn posts on agentic reality — the line that stuck was 'the next bottleneck isn't intelligence, it's execution at scale.' That matched my arc: at Bread I learned execution with 100+ production bots; at Archemy and Alex I learned it for agents — confirmed digests in Aurora, not chat-only responses. Bo's decision to shut down the dating app and build infrastructure instead of another feature is the same decomposition I'd make. I'd love to help scale that execution layer."*

### 2-Minute "Tell Me About Yourself" (Full Call Version)

> *"I'm Abhishek, based in New York. I have an MS in Information Systems from NYU and about six years of production engineering.*
>
> *I started at Infosys building automation with checkpoint-based recovery and ML inference pipelines — Docker, GitHub Actions, Airflow validation. That taught me reliability first.*
>
> *At Bread Financial I led 100+ enterprise RPA bots in production — UiPath Orchestrator, queues, triggers, CI/CD promotion across environments, and SageMaker integration for fraud scoring. That's where I learned orchestration at scale.*
>
> *Now at Archemy I'm the AI Engineer: serverless RAG with SageMaker embeddings and S3 Vectors, a knowledge graph pipeline with 70% search improvement, and RAGAS/LangSmith evaluation with automated human-review loops.*
>
> *My main side project, Alex, is a full agentic financial platform — ECS researcher with Playwright MCP, autonomous SQS pipeline every 2 hours, 6-agent trading debates, 12 AWS services via Terraform. The through-line across everything is the same problem Ophelia solves: turning agent intent into confirmed, durable outcomes. That's why I'm here."*

---

## STAR Stories (Resume + Alex)

Use 2 from Alex + 1 from Archemy/Bread depending on what they dig into.

### Story 1: Portfolio Research Pipeline — Alex (Orchestration + Execution)

| STAR | Content |
|------|---------|
| **Situation** | Dashboard showed stale "autonomous research" — semantic search returned old vectors, scheduler was disabled |
| **Task** | Build a pipeline that reads live portfolios and produces fresh, per-user digest cards |
| **Action** | Wired scheduler → planner (dimension rotation) → tagger → reporter → `portfolio_digests`; enabled EventBridge; fixed Aurora `stringValue` parsing; deployed 4 Lambdas |
| **Result** | NVDA + ASML digests confirmed in Aurora; dashboard cards render from `portfolio_digests` not global vector search |

**Ophelia bridge:** *"Same pattern as coordinating search → hold inventory → confirm booking → write to your DB."*

---

### Story 2: Multi-Agent Debate Engine (Parallel Intelligence → Structured Execution)

| STAR | Content |
|------|---------|
| **Situation** | Single-model trade recommendations lack diversity and auditability |
| **Task** | Build a debate system where specialists vote, executor decides, all logged |
| **Action** | ThreadPool parallel inference; Pydantic `AgentVote`/`DebateResult`; mode-weighted voting (aggressive/neutral/safe); guardrail on confidence |
| **Result** | 6-agent debates run in production; votes visible on trading floor UI; observability tracks per-agent cost and action distribution |

**Ophelia bridge:** *"Multiple agents coordinating on one outcome — like resolving availability across providers before one confirmed booking."*

---

### Story 3: Reliability — ECS Fallback + Aurora Retry (Execution Under Failure)

| STAR | Content |
|------|---------|
| **Situation** | ECS researcher cold starts and timeouts caused reporter failures |
| **Task** | Ensure portfolio research completes even when ECS is slow |
| **Action** | Reporter tries ECS first, falls back to direct Bedrock; Aurora SQL wrapped in 3x retry; SQS visibility timeout matched to Lambda timeout (900s) |
| **Result** | Pipeline completes end-to-end; manual trigger verified; no silent failures |

**Ophelia bridge:** *"Your retry/proxy logic for brittle booking sites — I solved the same class of problem for research execution."*

---

### Story 4: Observability as Product (Not Afterthought)

| STAR | Content |
|------|---------|
| **Situation** | No visibility into agent cost, latency, or guardrail triggers |
| **Task** | Build operator-facing observability without a third-party APM budget |
| **Action** | `agent_observations` table + `/observe` UI — per-agent tokens, cost, latency, guardrail log, action counts |
| **Result** | 7-day rolling stats; can answer "which agent is expensive?" and "are guardrails firing too often?" |

**Ophelia bridge:** *"Execution layers need dashboards on confirmation rate, latency, and failure modes — I built that for agents."*

---

### Story 5: RAGAS Eval (Quality Gates for Agent Output)

| STAR | Content |
|------|---------|
| **Situation** | RAG answers could hallucinate or miss the question |
| **Task** | Quantify RAG quality before shipping changes |
| **Action** | `test_ragas.py` — 5 standard queries, relevancy + faithfulness via Bedrock judge, results to `ragas_evaluations` |
| **Result** | Repeatable benchmark; targets defined (relevancy > 0.87, faithfulness > 0.91) |

**Ophelia bridge:** *"You'd measure search-to-book conversion — I measure answer relevancy and faithfulness."*

---

### Story 6: RAGAS Eval at Archemy (Current Job — Eval + Human Loop)

| STAR | Content |
|------|---------|
| **Situation** | RAG outputs at Archemy had no systematic quality gate before reaching users |
| **Task** | Build evaluation framework to catch low-confidence outputs before they ship |
| **Action** | LangSmith + RAGAS for retrieval precision, faithfulness, latency; automated feedback loops routing low-confidence outputs to human review |
| **Result** | RAG reliability improved 30%; repeatable eval pipeline in production workflow |

**Ophelia bridge:** *"Execution layers need outcome metrics — confirmation rate for you, faithfulness for me. Same discipline."*

---

### Story 7: 100+ Production Bots — Bread (Scale + Orchestration)

| STAR | Content |
|------|---------|
| **Situation** | Enterprise needed high-volume automated workflows with SLA compliance |
| **Task** | Lead design and delivery of production bot fleet with governance |
| **Action** | 100+ UiPath bots via Orchestrator (queues, triggers, unattended runners); CI/CD promotion DEV→QA→PROD; centralized monitoring with alert escalation |
| **Result** | 20% reduction in manual intervention; mentored juniors on REFramework standards |

**Ophelia bridge:** *"I ran 100+ orchestrated workflows in production before agents existed — queues, retries, escalation. Ophelia's booking orchestration is that at API scale."*

---

### Story 8: Knowledge Graph RAG — Archemy (Unified Layer Over Fragmented Data)

| STAR | Content |
|------|---------|
| **Situation** | Domain knowledge scattered across MySQL ontology tables — no unified semantic search |
| **Task** | Build SQL-to-vector pipeline with graph structure for taxonomy discovery |
| **Action** | Synced MySQL → ChromaDB + NetworkX graph (648 nodes, 1,200+ edges); fine-tuned MiniLM on contrastive pairs |
| **Result** | 70% improvement in semantic search accuracy |

**Ophelia bridge:** *"Ophelia unifies fragmented booking suppliers — I unified fragmented ontology tables into one search layer. Same abstraction problem."*

---

## Ophelia-Specific Talking Points

### If they ask: "Why Ophelia?"

**Lead with Bo's story, then your proof:**

1. **Origin resonates:** Bo killed a dating app because execution broke at the highest-conversion moment — you've felt that building Alex (chat works, confirmed outcomes don't without infrastructure)
2. **Same problem, different vertical:** Fragmented booking supply ≈ fragmented financial data (SEC, news, brokers, live web)
3. **You build execution layers, not demos:** Alex has SQS pipelines, idempotent Aurora writes, MCP tools, `/observe` — confirmed outcomes, not chat-only
4. **Timing:** 2026 is when agents move from prototypes to production execution — you want to be on the infrastructure side
5. **Technical fit:** MCP-native (Playwright), API design, retries/idempotency, third-party fragility — your daily work in Alex

**Strong one-liner:**

> *"Every team Bo talked to either killed in-app booking or spent millions on integrations. I built Alex because I hit the same wall — and I chose to build the execution layer instead of working around it."*

### If they ask: "How would you design our booking orchestrator?"

Sketch this (they'll appreciate systems thinking — mirrors their search → pay → confirm → reconcile flow):

```
Intent → Router (sync search vs async book)
      → Availability aggregator (parallel provider calls, timeout per provider)
      → Hold / reserve (short TTL lock on inventory)
      → Pay (if required — idempotent charge_id)
      → Execute (idempotency key on create — survive agent retries)
      → Confirm (booking_id, provider, timestamp, reconciliation state)
      → Persist (your DB + webhook to customer platform)
      → Exception path (cancel, modify, refund, partial failure)
      → Observability (latency per stage, confirmation rate, retry count)
```

Say: *"I'd steal patterns from my SQS reporter pipeline — parallel gather with per-task timeout for search, but all-or-nothing for confirm. Bo's dating app broke at confirm — that's the step you never half-succeed on."*

### If they ask: "MCP vs REST API?"

> *"MCP is the right agent-facing boundary — typed schemas, discoverable tools, works across Claude/Cursor/custom runtimes. REST/SDK is the right customer-facing boundary. Ophelia exposing both (SDK + MCP server) is correct. I used MCP internally for Playwright; external users hit REST/SSE."*

### If they ask: "How do you handle scale?"

- **Sync path:** ECS + ALB for user-facing streaming (low latency)
- **Async path:** SQS + Lambda for durable background work (portfolio digests, debates)
- **DB:** Aurora Serverless scales with cold-start warmup discipline
- **Per-tenant:** `user_id` scoping ready for multi-tenant growth

### If they ask: "What's the hardest bug you fixed?"

**Aurora Data API `stringValue` vs `doubleValue`:** NUMERIC columns returned as strings; portfolio P&L showed $0, ASML missing. Built `parseNumber()` helper, applied across portfolio API. *"Execution layers fail in boring ways — type coercion, not model quality."*

### If they ask: "What would you do as a founding engineer?" / "First 90 days?"

> *"I'd focus on three things that compound: adapter velocity, confirm reliability, and observability. Month one — provider adapter interface + idempotency on create + per-provider metrics. Month two — booking state machine, webhook delivery, MCP/SDK parity tests. Month three — eval harness on confirmation rate, chaos tests on top providers, CI gates before adapter deploys. I've done each piece before — Bread for orchestration discipline, Alex for execution pipelines, Archemy for eval — just not yet in bookings. That's the job."*

**Full detail:** [§ Solving Core Issues as a Founding Member](#solving-ophelias-core-issues-as-a-founding-member)

---

## Solving Ophelia's Core Issues as a Founding Member

> **Purpose:** Show you understand what a **2–10 person, NYC, post-seed execution-layer startup** actually needs — not generic "I'm hardworking," but *here are your bottlenecks and here's what I'd ship*.

### The Founding Member Pitch (60 seconds)

> *"Ophelia's core challenge isn't AI intelligence — it's shipping reliable confirm at integration speed across fragmented supply. As a founding engineer I'd own three layers:*
>
> *First, **adapter velocity** — a standard provider interface so you add OpenTable, Resy, Mindbody without rewriting orchestration each time. I built the same abstraction in Alex over SEC APIs, Playwright MCP, and market data providers.*
>
> *Second, **confirm reliability** — idempotency, state machine, retry/proxy with circuit breakers. Bo's dating app died at confirm; I'd make that step boring and auditable. Bread taught me 100+ production workflows only work with queues, escalation, and idempotent checkpoints.*
>
> *Third, **observability + eval** — confirmation rate, P95 time-to-confirm, per-provider failure modes. At Archemy, RAGAS gates improved reliability 30%; on Robothons I built outcome evaluation into the CITI platform after trade execution. Ophelia needs the same discipline on booking outcomes.*
>
> *I'm in NYC, I've shipped full stacks solo on Alex, and I want to build infrastructure — not features that get killed when two users coordinate a real date."*

---

### Ophelia's Core Issues → Your Solutions

| # | Ophelia's core issue | Why it hurts (Bo's world) | What you'd build | Your proof |
|---|----------------------|---------------------------|------------------|------------|
| **1** | **Fragmented provider integrations** | Every platform faces $2M or kill-the-feature | **Provider adapter SDK** — `SearchProvider` / `BookingProvider` interfaces; new supplier = new adapter, not new orchestrator | Alex `market_data.py` + MCP; **Archemy MetaML** MySQL→ChromaDB; **Robothons ITP** C++/Java/Python adapters |
| **2** | **Confirm step breaks** | Dating app failed when two users coordinated a date | **Booking state machine** — `pending → held → paid → confirmed → reconciled`; confirm is all-or-nothing; never return success without `booking_id` | Alex `portfolio_digests` — confirmed cards, not chat; Pydantic `DebateResult` for structured outcomes |
| **3** | **Agent/customer retries create duplicates** | Agents retry on timeout aggressively | **Idempotency layer** — `Idempotency-Key` on `create`, DynamoDB/Postgres cache, return cached response on replay | Aurora upserts in Alex; Bread queue item deduplication patterns |
| **4** | **Retry/proxy on brittle surfaces** | Internet wasn't built for autonomous execution | **Resilience middleware** — per-provider circuit breaker, exponential backoff + jitter, proxy fallback with `source: proxy` metadata | Alex ECS→Bedrock fallback; Infosys checkpoint recovery |
| **5** | **No visibility into what fails** | Can't improve confirm rate blind | **Execution observability** — `correlation_id` tracing, per-provider P95, confirmation rate dashboard, DLQ alerts | Alex `/observe` + `agent_observations`; Bread centralized monitoring + escalation |
| **6** | **Integration speed vs. quality** | 10 platforms in 6 months — move fast without breaking | **Contract tests + sandbox fixtures** per adapter; smoke test before adapter promote; Terraform for env parity | **Robothons bot validation** gate; Alex `test_trading.sh`; Bread DEV→QA→PROD promotion |
| **7** | **MCP + SDK drift** | Agents and apps must hit same execution engine | **Single execution core** — MCP tools map 1:1 to SDK methods; shared Pydantic schemas | Alex: MCP tools + REST ingest share same Aurora backend |
| **8** | **Multi-user coordination** | Dating: 3 people, one reservation | **Workflow engine** for draft → RSVP → pay → confirm; correlation ID across participants; step timeouts | Alex SQS multi-step pipeline; Bread multi-bot coordination |
| **9** | **Payments + reconciliation** | Money moves before confirm is certain | **Saga pattern** — pay step with compensating refund; `reconciliation_state` field; stale `pending` poller | Bread SageMaker + multi-source fraud pipeline; financial data accuracy focus in Alex |
| **10** | **Stale availability** | "No stale data" is product promise | **Freshness SLO** — `fetched_at` on search; re-validate on hold/create; short TTL cache | Real-time market data in Alex `market_data.py`; RAG freshness at Archemy |
| **11** | **Small team, huge surface area** | 2–10 people can't afford rewrites | **IaC + serverless defaults** — Terraform modules, Lambda for adapters where possible, ECS only for browser/proxy paths | Alex 12 services Terraform; Archemy Aurora via Terraform |
| **12** | **Execution quality unknown** | Is the layer actually working for customers? | **Outcome eval harness** — confirmation rate, search-to-book funnel, provider regression suite weekly | **Archemy RAGAS +30%**; **Robothons performance evaluation**; Alex `test_ragas.py` |

---

### What You Own as Founding Member (Role Clarity)

Early-stage founding engineers wear 2–3 hats. Be explicit about what you'd own vs. collaborate on:

| You'd **own** (day 1) | You'd **collaborate** with Bo/product | You'd **grow into** (months 2–6) |
|------------------------|----------------------------------------|-----------------------------------|
| Provider adapter framework + first 2–3 adapters | Provider prioritization (which vertical next) | Payment/reconciliation service |
| Booking orchestrator + state machine | Customer SDK ergonomics | Multi-party workflow engine |
| Idempotency + retry middleware | GTM / platform partnerships | Rate-limit + cache layer at scale |
| Observability (metrics, logs, alerts) | MCP tool surface design with product | Hiring + mentoring engineer #2–3 |
| CI/CD + contract tests for adapters | Legal/compliance on scrape vs API | Chaos engineering program |

**Founding member mindset to verbalize:**

> *"I'm not joining to own one microservice in a big org. I'd own the execution path end-to-end — adapter interface, confirm logic, observability — and ship integrations weekly. I've done zero-to-one on Alex solo; I know how to move fast without skipping idempotency."*

---

### 30 / 60 / 90 Day Plan

Use this if they ask *"What would your first three months look like?"* — adjust based on what they say is burning today.

#### Days 1–30: Make confirm boring and measurable

| Week | Deliverable | Why |
|------|-------------|-----|
| **1** | Map current architecture; instrument `correlation_id` + per-stage latency on existing book path | You can't fix what you can't see |
| **2** | Ship **idempotency on `create`** — key store + replay cached response | #1 agent retry bug class |
| **3** | Define **`BookingProvider` interface** + refactor one existing provider behind it | Unblocks integration velocity |
| **4** | Dashboard v0: **confirmation rate**, **P95 time-to-confirm**, **per-provider error rate** | Archemy/Alex observability pattern |

**30-day success metric:** Zero duplicate bookings on retry in staging; confirmation rate visible per provider.

---

#### Days 31–60: Scale integrations without $2M per partner

| Week | Deliverable | Why |
|------|-------------|-----|
| **5** | **Adapter #2 + #3** behind same interface; contract test suite with recorded fixtures | Prove framework isn't one-off |
| **6** | **Booking state machine** in DB — `booking_events` append-only audit log | Reconciliation + debug |
| **7** | **Webhook delivery** — at-least-once, HMAC signature, retry + DLQ | Customer platforms need confirm signal |
| **8** | **MCP ↔ SDK parity tests** — same `create` path, same response schema | Agent and app can't diverge |

**60-day success metric:** New provider adapter in < 1 week; webhook delivery > 99%.

---

#### Days 61–90: Production hardening at startup speed

| Week | Deliverable | Why |
|------|-------------|-----|
| **9** | **Circuit breakers** per provider; auto-failover to alternate where possible | Bo's retry/proxy story |
| **10** | **Weekly eval harness** — confirmation rate regression, search latency benchmarks | Archemy RAGAS discipline applied to bookings |
| **11** | **Chaos tests** — provider timeout, 500, stale inventory in CI | Bread/Alex production maturity |
| **12** | **Hold/TTL** on inventory for race conditions (last table problem) | Dating app coordination failure mode |

**90-day success metric:** Confirmation rate ↑ measurable; integration lead time ↓; on-call playbook exists.

---

### How Your Background Maps to Founding Work

```
Bread (100+ bots)     →  Orchestration discipline, CI/CD, monitoring, mentoring juniors
Infosys (recovery)    →  Checkpoint/retry patterns, validation before execution
Archemy (MetaML + Robothons) →  RAG eval, KG unification, **CITI execution platform** (RabbitMQ, adapters, confirm step)
Alex (solo 0→1)       →  Full execution stack, MCP, multi-agent, 12-service Terraform
NYU MS + NYC          →  Local, no relocation; agentic AI depth; startup context (Archemy)
```

**What makes you different from a senior hire at a big company:**

| Big-co senior | You as founding member |
|---------------|------------------------|
| Owns one service | Owns search → confirm path |
| Waits for platform team | Ships Terraform + CI yourself |
| Specs idempotency | Implemented it in Alex + Bread |
| Reads about MCP | Shipped Playwright MCP in production |
| Needs 3 months onboarding | Alex is a working reference architecture |

---

### Solving Bo's Original Dating App Failures (Explicit Map)

Use this if you want to show you understand the **founding mission**, not just the API:

| Dating app failure | Ophelia needs | You'd deliver |
|--------------------|---------------|---------------|
| Two users coordinate → backend breaks | Multi-party workflow with correlation ID | Draft booking + RSVP state machine (day 60+) |
| Manual reservation at conversion peak | Automated confirm in < N seconds | Sync confirm path + async webhook fallback |
| Months for partner APIs | Adapter framework + proxy path | Provider interface week 3; proxy with metadata week 9 |
| Teams spend $2M on integrations | One integration, many suppliers | Adapter #2–3 by day 60 proves the model |
| Feature killed entirely | Reliable execution = feature stays | Idempotency + observability week 2–4 |

**Emotional close:**

> *"Bo shut down the app and built the layer the industry needed. I'd help make sure no platform has to make that choice again — because confirm just works."*

---

### What You Won't Promise (Credibility)

Say these proactively — founding teams respect honesty:

| Don't overpromise | Say instead |
|-------------------|-------------|
| "I know OpenTable's API" | "I know adapter patterns; I'll learn each provider's quirks in days not months" |
| "I'll fix payments day one" | "I'll nail confirm + idempotency first; payments is month 2–3 with your domain experts" |
| "Alex is production at Ophelia scale" | "Alex is my proving ground for execution patterns; Ophelia is where we harden them for bookings" |
| "I can do everything solo" | "I'll own the execution core; I'll need Bo on partnerships and legal on scrape boundaries" |

---

### Founding Member Questions to Ask Them

Shows you're thinking like an owner, not an employee:

1. *"What's the #1 thing breaking confirm rate today — provider timeouts, payment, or inventory races?"*
2. *"Of the 10 platforms live, which integration pattern repeats most — can we templatize it?"*
3. *"Where do you want the founding engineer to spend week one — new provider, reliability, or MCP surface?"*
4. *"How do you measure success for this hire at 90 days?"*
5. *"What's still manual that shouldn't be?"*

---

### One-Page Cheat Sheet (Print for Call)

```
FOUNDING MEMBER VALUE PROP
──────────────────────────
Problem:  Intelligence solved → execution at scale is the bottleneck
My lane:  Adapter framework + confirm reliability + observability/eval

30 days:  Idempotency + provider interface + confirm metrics dashboard
60 days:  3 adapters + state machine + webhooks + MCP/SDK parity
90 days:  Circuit breakers + eval harness + chaos tests + inventory holds

Proof:    Bread 100+ bots | Archemy RAGAS +30% | Alex 12-service execution stack
Why me:   Already built the layer once — want to build it where Bo's thesis matters most
```

---

## Interview Prep Guide

### Night Before (Phone Call)

| Step | Time | Action |
|------|------|--------|
| 1 | 15 min | Read § Phone Call Playbook + rehearse 30s intro out loud |
| 2 | 15 min | Practice Deep-Dive A (Alex) — time yourself, stay under 8 min |
| 3 | 10 min | Practice **Deep-Dive B (Archemy + Robothons ITP)** — 5–6 min version |
| 4 | 10 min | Memorize Bo's story + one market stat |
| 5 | 10 min | Skim § Technical Questions — pick 5 most likely, rehearse answers |
| 6 | 5 min | Open resume PDF, `Ophelia.md`, GitHub Alex repo |

### Day Of — 15 Min Before Call

1. Water, quiet room, phone charged / Zoom tested
2. Resume PDF + this doc open (don't read verbatim)
3. Stand or sit upright — energy on phone matters
4. Close Slack/notifications
5. Deep breath → 30s intro once more

### Week Before (If You Have Time)

| Day | Focus | Actions |
|-----|-------|---------|
| **D-7** | Ophelia product + story | Read opheliaos.com/product; rehearse Bo's origin story in 30s; read LinkedIn posts on "agentic reality"; list 5 questions |
| **D-6** | Alex architecture | Whiteboard the diagram in §7 from memory; record yourself explaining 2min pitch |
| **D-5** | Pillar deep-dive | Pick 3 pillars (orchestration, reliability, MCP) — rehearse one STAR story each |
| **D-4** | Code walkthrough | Be ready to screen-share: `debate_engine.py`, `reporter.py`, `server.py`, `/observe` |
| **D-3** | Systems design | Practice: "Design booking execution for 10k concurrent agents" — use § sketch |
| **D-2** | Resume sync | Fill § Resume Alignment Template; every bullet should trace to a file or metric |
| **D-1** | Mock interview | 45min: intro, 2 STAR stories, 1 system design, 5 questions for them |

### Day Of (Call)

1. Lead with **execution**, not "I fine-tuned a model"
2. Bridge every answer: *"Same class of problem Ophelia solves for bookings..."*
3. When stuck: Bread 100+ bots OR Archemy RAGAS — don't only cite Alex
4. Ask about **next steps** before hanging up
5. Send thank-you email within 24h — mention one specific thing they said + your execution-layer fit

### Role-Specific Emphasis

| If role leans… | Lead with… |
|----------------|------------|
| **Backend / platform** | SQS topology, idempotency, DLQ, Terraform, deploy pipelines |
| **AI / agents** | Debate engine, planner decomposition, MCP tool design, RAGAS |
| **Infra / SRE** | Reliability patterns, SLOs, CloudWatch, fallback paths |
| **Full-stack** | Next.js + API routes + live dashboard + end-to-end portfolio pipeline |

### Topics to Study (Ophelia-adjacent)

- MCP spec: tool schemas, SSE transport, auth headers
- Idempotency keys for `create` operations
- Saga vs workflow for multi-step booking (hold → pay → confirm)
- Rate limiting across fragmented providers
- Web scraping ethics vs official APIs (Ophelia uses live web availability)

---

## Archemy Use Cases (ITP + Resume)

> **Sources:** `Abhishek_Resume.pdf` (Archemy AI Engineer role) · `ITP Final PPT.pdf` (NYU MS ITP — *Robothons-Web*, supervised by Prof. Jean-Claude Franchitti, team: Abhishek Suresh, Sai Krishna Bommavaram, Parth Chaturvedi)
>
> **Archemy context:** NYC asset-based consultancy ([archemy.com](https://www.archemy.com/)) — **Archemy Platform** (knowledge management, reusable Archifacts) + **Robothons Platform** (competition/simulation for crowdsourcing reusable solution components across banking, healthcare, supply chain, etc.). Your ITP delivered the **CITI Global Markets (Robothons — Banking & Financial Services)** execution stack.

### Archemy → Ophelia at a Glance

| Archemy use case | What you solved | Ophelia parallel |
|------------------|-----------------|------------------|
| **Robothons CITI execution platform** (ITP) | Multi-language bot orchestration → validated → simulated → **trade executed** | Multi-provider search → validated → **booking confirmed** |
| **RabbitMQ message broker** (ITP) | Decouple bot init, market events, strategy, trade execution | SQS/EventBridge between search, hold, pay, confirm |
| **C++/Java/Python adapter architecture** (ITP) | New participant language = new adapter, same orchestrator | New booking supplier = new adapter, same Ophelia API |
| **Bot validation gate** (ITP) | Bots must pass validation before entering live simulation | Provider adapter contract tests before production traffic |
| **Dynamic market simulation** (ITP) | Test strategies against live-like events before real execution | Sandbox/staging availability before customer-facing confirm |
| **Performance evaluation** (ITP) | Score bot outcomes after execution | Confirmation rate, P95 time-to-confirm per provider |
| **Serverless RAG pipeline** (Resume) | Sub-3s semantic search, 90% cost reduction vs managed vector DB | Low-latency availability search at scale |
| **MetaML knowledge graph** (Resume) | Unified search over fragmented MySQL ontology (+70% accuracy) | Unified API over fragmented OpenTable/Resy/Ticketmaster |
| **RAGAS + LangSmith eval** (Resume) | Faithfulness/relevancy gates, human review loop (+30% reliability) | Booking outcome eval — confirm rate, not just LLM quality |
| **Aurora + Terraform** (Resume) | Durable audit trails, RDS Data API for serverless | Booking state machine + reconciliation DB |

---

### Use Case 1: Robothons CITI Competition Platform (ITP Final PPT)

**What Archemy/Robothons needed**

Archemy's **Robothons Platform** runs industry competitions where participants submit bots that must execute reliably against dynamic market conditions — starting with **CITI Global Markets**. The ITP problem: monolithic C++ and Java bot architectures couldn't scale to multi-language participants or modular reuse.

**What you built** (`ITP Final PPT.pdf`)

| Component | Your solution |
|-----------|---------------|
| **Business challenge** | Hybrid C++ + Python components — performance where needed, flexibility where needed |
| **Execution workflow** | `Bot Initialization` → `Load Market Events` → `Strategy Execution` → **`Trade Execution`** |
| **CITI platform flow** | `Participant Bot Development` → **`Bot Validation`** → `Dynamic Market Simulation` → **`Performance Evaluation`** |
| **Architecture** | Redesigned C++ and Java bots from monolithic → **modular proposed architecture** with clear execution results |
| **Messaging** | **RabbitMQ** message broker — C++ performance + async decoupling between pipeline stages |
| **Multi-language** | Adapter pattern for C++, Java, and other language bots behind one orchestration layer |
| **Future work identified** | Cloud deployment, containerization, web dashboard, risk management, security/compliance |

**Execution workflow (from ITP — memorize this sequence):**

```
Bot Initialization
      ↓
Load Market Events      ← real-time / dynamic feed (like live availability)
      ↓
Strategy Execution      ← agent/LLM reasoning (like "book dinner Friday 8pm")
      ↓
Trade Execution         ← CONFIRMED OUTCOME (like booking confirm — cannot half-succeed)
```

**Ophelia bridge (say this on the call):**

> *"At Archemy I worked on Robothons — a competition execution platform for CITI Global Markets. The pipeline is structurally identical to Ophelia: participant bots connect through RabbitMQ, pass validation, run against a dynamic simulation, and the platform owns the final **trade execution** step. Ophelia owns **booking confirm**. In both cases, reasoning happens upstream; the platform's value is reliable, auditable execution. I also redesigned multi-language bot architectures into modular adapters — that's the same pattern as Ophelia adding OpenTable vs Resy without rewriting orchestration."*

**Founding member relevance:** You've already built **platform-side execution** (not participant-side bots) — validation gates, message-broker orchestration, confirmed execution step, performance scoring.

---

### Use Case 2: Serverless RAG Pipeline (Resume — MetaML / Archemy Platform)

**Problem:** Enterprise taxonomy and document search needed semantic retrieval without managed-vector-DB cost and latency.

**Solution:**
- SageMaker Serverless endpoint (MiniLM-L6-v2) → embeddings
- AWS S3 Vectors for storage
- API Gateway + Lambda trigger
- **Sub-3-second** semantic search
- **~90% lower cost** than managed vector DB alternatives

**Ophelia bridge:**

> *"Ophelia's search availability endpoint needs low P95 latency at startup-friendly cost. I hit sub-3s search on serverless SageMaker + S3 Vectors — same engineering tradeoff: latency SLO without over-provisioning."*

---

### Use Case 3: MetaML Knowledge Graph — SQL-to-Vector (Resume + Project)

**Problem:** Domain knowledge fragmented across MySQL ontology tables (domains, dimensions, areas) — no unified semantic discovery.

**Solution:**
- Sync MySQL ontology → ChromaDB vectors
- NetworkX knowledge graph: **648 nodes, 1,200+ edges**
- Fine-tuned MiniLM-L6-v2 on domain-specific contrastive pairs
- **+70% semantic search accuracy**
- Streamlit dashboard: semantic search, graph navigation, concept similarity, classification, coverage auditing

**Ophelia bridge:**

> *"Ophelia's core abstraction is unified search over fragmented suppliers. I built unified semantic search over fragmented ontology tables — same adapter-and-index problem, different domain. The MetaML dashboard is also an operator-facing validation UI — like a dashboard showing per-provider confirmation health."*

---

### Use Case 4: LLM Evaluation Framework (Resume — Archemy)

**Problem:** RAG answers could ship without quality guarantees — no systematic faithfulness or relevancy checks.

**Solution:**
- LangSmith + RAGAS: retrieval precision, answer faithfulness, latency
- Automated feedback loops → low-confidence outputs flagged for **human review**
- **+30% RAG reliability** improvement

**Ophelia bridge:**

> *"Ophelia can't just measure LLM quality — you need execution outcome metrics. I built the eval discipline at Archemy: define thresholds, automate regression, human-in-the-loop on failures. I'd apply the same to confirmation rate and search-to-book funnel, not just answer relevancy."*

---

### Use Case 5: Aurora Serverless + Terraform (Resume — Archemy)

**Problem:** Serverless agents and Lambdas need durable audit/operational data without connection pool exhaustion.

**Solution:**
- Aurora Serverless v2 PostgreSQL provisioned via **Terraform**
- Normalized schemas for audit trails and operational data
- **RDS Data API** — no persistent connections from serverless compute

**Ophelia bridge:**

> *"Booking state — pending, held, confirmed, reconciled — needs a durable source of truth. I provisioned Aurora at Archemy with the same serverless-access pattern I use in Alex. That's the reconciliation DB behind Ophelia's `booking_id`."*

---

### Robothons Execution ↔ Ophelia Booking (Side-by-Side)

| Robothons (ITP / CITI) | Ophelia |
|------------------------|---------|
| Participant bot submits intent | Consumer app / AI agent submits booking intent |
| Bot validation gate | Request validation + provider adapter health |
| RabbitMQ queues between stages | SQS / internal job queue |
| Load market events (dynamic feed) | Search availability (real-time inventory) |
| Strategy execution (bot logic) | LLM planning / user preferences |
| **Trade execution** (platform-owned) | **Booking confirm** (platform-owned) |
| Dynamic market simulation | Staging / sandbox provider testing |
| Performance evaluation | Confirmation rate, P95, per-provider dashboard |
| C++ / Java / Python adapters | OpenTable / Resy / Mindbody adapters |
| Modular architecture (reusable Archifacts) | Unified API over reusable provider adapters |

---

### STAR Stories — Archemy / ITP (Add to Your Rotation)

#### Story 9: Robothons Modular Architecture (ITP — Multi-Language Execution)

| STAR | Content |
|------|---------|
| **Situation** | CITI Robothons needed multi-language bot support; monolithic C++/Java architectures blocked reuse and new participants |
| **Task** | Redesign bot architecture for modular, adapter-style integration with shared execution orchestration |
| **Action** | Proposed modular architectures for C++ and Java bots; integrated **RabbitMQ** for decoupled pipeline stages; hybrid C++/Python split for performance + flexibility; defined execution workflow through trade execution |
| **Result** | Modular, adaptable trading platform; foundation for cloud deployment and multi-language expansion (per ITP conclusion) |

**Ophelia bridge:** *"New provider = new adapter, not new platform — I proved that on Robothons with C++/Java/Python."*

---

#### Story 10: CITI Platform Validation Gate (ITP — Don't Execute Bad Inputs)

| STAR | Content |
|------|---------|
| **Situation** | Competition platform can't let unvalidated bots into live market simulation |
| **Task** | Build validation step between bot submission and execution |
| **Action** | Designed CITI flow: bot development → **bot validation** → dynamic simulation → performance evaluation |
| **Result** | Only vetted bots reach trade execution — protects platform integrity |

**Ophelia bridge:** *"Ophelia shouldn't hit a provider with a malformed book request — validate at the gate, same as bot validation before simulation."*

---

### How to Weave Archemy Into "Why Ophelia" / Founding Member

**Single paragraph:**

> *"At Archemy I'm not only building RAG and knowledge graphs — I'm on the **Robothons execution platform**, which is Archemy's competition-and-simulation layer for industries including banking. My NYU ITP delivered the CITI Global Markets stack: RabbitMQ-orchestrated pipeline from bot init through **trade execution**, with multi-language adapters and validation gates. That's the same job Ophelia does for bookings: own the confirm step, abstract fragmented participants/providers, measure outcomes. Combined with MetaML's unified search (+70% over fragmented ontology) and RAGAS eval (+30% reliability), I've been building execution-layer infrastructure at Archemy before I found Ophelia's thesis articulated it."*

---

### Archemy Talking Points by Ophelia Interview Topic

| If they ask about… | Lead with Archemy example |
|--------------------|---------------------------|
| Execution vs intelligence | Robothons: strategy is bot's job; **trade execution** is platform's job |
| Message queues / async | RabbitMQ in Robothons ITP; SQS in production Alex |
| Multi-provider integration | C++/Java/Python adapters; MetaML MySQL → ChromaDB unification |
| Validation before production | CITI bot validation gate |
| Latency / cost at scale | Sub-3s SageMaker Serverless RAG, 90% cost savings |
| Outcome metrics | RAGAS +30%; Robothons performance evaluation |
| IaC / audit | Terraform Aurora, audit trail schemas |
| Founding member 0→1 | ITP modular redesign + MetaML pipeline + Robothons platform context |

---

### What NOT to Confuse on the Call

| Say | Don't say |
|-----|-----------|
| "Robothons is Archemy's competition **execution** platform" | "Robothons is a trading bot I built for CITI" (you built the **platform**, not just a bot) |
| "ITP was my NYU capstone **for** the Robothons/CITI use case" | "ITP was unrelated to Archemy" (it's directly aligned with Archemy's Robothons service line) |
| "Trade execution = platform-owned confirm step" | Deep dive into trading strategy alpha — stay on **infrastructure** |

---

## Resume → Ophelia Mapping (Every Bullet)

### Archemy Inc — AI Engineer (Aug 2025 – Present) + ITP Robothons (NYU)

| Resume / ITP bullet | Proof / detail | Ophelia parallel |
|---------------------|----------------|------------------|
| Serverless RAG — SageMaker, S3 Vectors, sub-3s, 90% cost savings | MetaML / Archemy Platform search | Low-latency availability search |
| SQL-to-vector KG — 648 nodes, 1,200 edges, +70% accuracy | MetaML ontology unification | Unified API over fragmented suppliers |
| LangSmith + RAGAS, human-review loops, +30% reliability | Production eval gates | Confirmation-rate regression harness |
| Aurora Serverless v2 via Terraform, RDS Data API | Audit + operational schemas | Booking state + reconciliation DB |
| **ITP: Robothons CITI execution platform** | Init → events → strategy → **trade execution** | Search → hold → pay → **confirm** |
| **ITP: RabbitMQ orchestration** | Decoupled pipeline stages | SQS between orchestration steps |
| **ITP: C++/Java/Python modular adapters** | Multi-language bot integration | Multi-provider booking adapters |
| **ITP: Bot validation → simulation → evaluation** | Gated execution + outcome scoring | Adapter tests + confirm metrics |

### Bread Financial — RPA Developer (Jan – Aug 2023)

| Resume bullet | Proof / detail | Ophelia parallel |
|---------------|----------------|------------------|
| 100+ enterprise UiPath bots — Orchestrator, queues, triggers, SLA compliance | Production orchestration at scale | Multi-step booking workflow orchestration |
| SageMaker REST in UiPath — fraud scoring, multi-source reasoning, +18% recall | ML inference in production workflows | Payment/risk scoring in booking flow |
| CI/CD bot promotion DEV/QA/PROD — version-controlled packages | Release governance | Safe deploy of execution-layer changes |
| Centralized monitoring + alert escalation, −20% manual intervention | Ops discipline | Retry/escalation when provider fails |

### Infosys — Systems Engineer (Sep 2019 – Jan 2022)

| Resume bullet | Proof / detail | Ophelia parallel |
|---------------|----------------|------------------|
| Automation Anywhere + ML inference REST, event-driven routing | Event-driven execution | Event-driven booking state machine |
| Checkpoint-based recovery, workload balancing, −20s recovery/incident | Reliability engineering | Retry + recovery on failed booking step |
| Docker + GitHub Actions ML CI/CD | Deploy automation | CI/CD for execution API |
| Airflow validation pipelines → RPA layers, −30% pipeline failures | Validation before execution | Pre-confirm validation (availability still live?) |

### Alex — Autonomous Financial Research Platform (Project)

| Resume bullet | Proof / detail | Ophelia parallel |
|---------------|----------------|------------------|
| ECS researcher + Playwright MCP + SEC EDGAR browsing | MCP execution on live web | MCP search/book on live booking surfaces |
| SQS pipeline (Tagger + Reporter), EventBridge 2h, structured reports | Async orchestration → confirmed output | Async book → confirmed `booking_id` |
| 12 AWS services via Terraform, <60s research turnaround | Full IaC production stack | Production infra for execution API |
| Next.js dashboard surfacing reports | Customer-facing confirmed outcomes | Platform dashboard showing booking state |

### Skills → Ophelia Pillars (Quick Reference)

| Skill on resume | Ophelia pillar |
|-----------------|----------------|
| MCP, Playwright, OpenAI Agents SDK | MCPs & agent tooling |
| LangSmith, RAGAS, LLM Evaluation | Evaluation & benchmarking |
| SQS, EventBridge, Lambda, ECS | Distributed systems & orchestration |
| Terraform, Docker, GitHub Actions | CI/CD & deployment |
| Guardrails, Tool Use | Reliability + inference engineering |

---

## Technical Questions You Might Get

> **How to use this section:** Don't memorize verbatim — internalize the **structure**: (1) direct answer, (2) Alex/Archemy/Bread proof, (3) Ophelia bridge. On a phone call, 60–90 seconds per answer is ideal.

### Quick Index

| Category | Likelihood on phone screen |
|----------|----------------------------|
| [Execution & orchestration](#execution--orchestration) | Very high |
| [API design & idempotency](#api-design--idempotency) | Very high |
| [Reliability & failure handling](#reliability--failure-handling) | Very high |
| [Third-party integrations](#third-party-integrations) | High |
| [MCP & agent tooling](#mcp--agent-tooling) | High |
| [System design scenarios](#system-design-scenarios) | Medium–high |
| [Distributed systems / AWS](#distributed-systems--aws) | Medium |
| [Inference & LLMs in production](#inference--llms-in-production) | Medium |
| [Evaluation & quality](#evaluation--quality) | Medium |
| [Databases & state](#databases--state) | Medium |
| [CI/CD & observability](#cicd--observability) | Lower on first screen |

---

### Execution & Orchestration

**Q: What's the difference between an intelligence layer and an execution layer?**

> *"Intelligence turns unstructured input into intent — 'book dinner Friday 8pm' or 'research NVDA risks.' Execution turns intent into a **confirmed, durable outcome** — a `booking_id` in your DB or a digest card in Aurora. Intelligence is probabilistic; execution must be deterministic enough to reconcile, retry, and audit. In Alex, Nova Pro is intelligence; the SQS pipeline that writes `portfolio_digests` is execution."*

---

**Q: How would you design a multi-step booking flow?**

> *"I'd split sync vs async. **Search** is sync-ish — parallel provider calls with per-provider timeouts, return partial results OK. **Book** is async-durable — idempotency key on create, state machine: `pending → held → paid → confirmed → reconciled`. Confirm is all-or-nothing — Bo's dating app broke there. I'd persist state after every transition, emit webhooks to the customer platform, and log latency per stage. I used the same split in Alex: ECS for streaming user queries, SQS for durable portfolio research jobs."*

---

**Q: How do you orchestrate multiple agents working on one outcome?**

> *"Three patterns I've used:*
> 1. * **Pipeline** — scheduler → planner → tagger → reporter (Alex SQS). Good when steps are sequential and each output feeds the next.*
> 2. * **Parallel + synthesize** — 5 trading agents vote in parallel via ThreadPool, executor aggregates (Alex debate engine). Good when you want diverse opinions, one decision.*
> 3. * **Queue-based** — Bread's 100+ UiPath bots via Orchestrator queues and triggers. Good for high-volume, SLA-governed work.*
>
> *For Ophelia, search across providers is parallel gather; book is pipeline with a single confirm gate."*

---

**Q: How do you pass state between orchestration steps?**

> *"Typed message bodies — I'd use Pydantic schemas on SQS messages: `correlation_id`, `user_id`, `step`, `payload`, `idempotency_key`. In Alex, the planner emits JSON tasks; the reporter carries `ticker`, `dimension`, `user_id` through the queue. Never rely on LLM memory between steps — persist to DB at each boundary."*

---

**Q: Sync vs async — when do you use each?**

| Sync | Async |
|------|-------|
| User waiting (search availability, stream research) | Background work (portfolio digests, post-confirm reconciliation) |
| Low latency SLA (< 3–15s) | Can tolerate seconds–minutes |
| Partial results acceptable (search) | Must complete or explicit failure (book) |
| ECS + ALB + SSE in Alex | SQS + Lambda + EventBridge in Alex |

> *"Ophelia search is likely sync; confirm may be sync for fast providers and async webhook for slow ones — I'd ask where you draw that line."*

---

### API Design & Idempotency

**Q: What is idempotency and why does it matter for agent execution?**

> *"An operation is idempotent if calling it twice has the same effect as once. Agents retry aggressively — timeout, network blip, user double-tap. Without idempotency, a retry creates duplicate bookings. I'd require clients pass `Idempotency-Key` on `create`; store key → response in DB with TTL; on duplicate key, return cached response. In Alex I use upserts on `portfolio_digests` and `cost_snapshots` — same principle."*

---

**Q: How do you design APIs for both human apps and AI agents?**

> *"Two surfaces, one backend:*
> - * **REST/SDK** for customer platforms — stable contracts, versioning, webhooks.*
> - * **MCP** for agents — typed tool schemas, discoverable at runtime.*
>
> *Same execution engine underneath. I did this in Alex: Next.js hits REST/SSE; the ECS researcher uses MCP tools internally. Ophelia's dual API + MCP server is the right split."*

---

**Q: How do you version an execution API without breaking integrations?**

> *"URL or header versioning (`/v1/bookings`), additive schema changes only, deprecate with sunset headers. Never change confirm response shape without a new version — that's the contract customers reconcile against. At Bread we version-controlled UiPath packages across DEV/QA/PROD — same discipline."*

---

**Q: What should a `create booking` response always include?**

> *"Minimum: `booking_id` (your canonical ID), `status` (confirmed | pending | failed), `provider` + `provider_reference`, `created_at`, `idempotency_key` echo. Optional: `expires_at` for holds, `reconciliation_state`, `retryable` boolean on failure. The customer platform stores `booking_id` — that's the anchor for cancel/modify/webhooks."*

---

### Reliability & Failure Handling

**Q: How do you handle retries without making things worse?**

> *"Four rules:*
> 1. * **Idempotency** on all mutating ops — safe to retry.*
> 2. * **Exponential backoff with jitter** — avoid thundering herd on a failing provider.*
> 3. * **Retry budget** — max N attempts, then dead-letter + alert.*
> 4. * **Classify errors** — 429/503 retry; 400/404 don't (fix the request).*
>
> *In Alex, Aurora SQL retries 3x on transient RDS errors; reporter falls back ECS → Bedrock after timeout. Bread bots had alert-based escalation when retries exhausted."*

---

**Q: What happens when a provider confirms async (webhook later)?**

> *"Return `status: pending` immediately with your `booking_id`. Store `pending` in DB. On webhook: transition to `confirmed`, emit customer webhook, idempotent on duplicate webhooks (provider may send twice). Reconciliation job polls stale `pending` > N minutes. Saga compensation if pay succeeded but confirm never arrives — refund path."*

---

**Q: Explain saga vs workflow for booking (hold → pay → confirm).**

> *"**Workflow** (Temporal/Cadence): orchestrator owns state, durable timers, built-in retry — good for long-running booking flows.*
>
> * **Saga**: each step has a compensating action — hold expires → release; pay succeeds → confirm fails → refund. Good when steps span independent services.*
>
> *For Ophelia I'd lean workflow for orchestration visibility, saga pattern for payment rollback. In Alex my SQS pipeline is a lightweight workflow — each Lambda is a step, DLQ is the failure sink."*

---

**Q: How do you prevent duplicate bookings when an agent retries?**

> *"Idempotency key on `create`, keyed by `(client_id, idempotency_key)` unique in DB. Agent passes same key on retry. Optionally: short TTL **hold** on inventory before confirm — second request with same key returns existing hold. Never rely on the LLM to 'remember' it already booked."*

---

**Q: What's a dead-letter queue and when do you use it?**

> *"DLQ receives messages that failed processing after max retries. Prevents poison messages from blocking the queue. Alert on DLQ depth > 0. In Alex I have SQS for research/trading — DLQ is on my roadmap (P18). At Bread, failed bot jobs escalated via Orchestrator alerts — same ops instinct."*

---

### Third-Party Integrations

**Q: How do you integrate fragmented third-party systems behind one API?**

> *"Adapter pattern — one interface per capability:*
> ```
> SearchProvider.search(location, time, party_size) → Availability[]
> BookingProvider.create(hold) → Confirmation
> ```
> *Each supplier (OpenTable, Resy, etc.) gets an adapter. Your unified API routes to adapters. Log per-adapter latency and success rate. In Alex, `market_data.py` abstracts yfinance/NewsAPI; Playwright MCP handles sites without APIs — same fragmentation problem Ophelia solves for bookings."*

---

**Q: Official API vs scrape/proxy — how do you decide?**

> *"Official API when available — stable schema, ToS-safe, rate limits known. Proxy/scrape when API doesn't exist or partner deal takes months — Bo's story. Mitigate scrape with: rotating proxies, circuit breakers, aggressive caching of availability, legal review. Return `source: proxy` in metadata so customers know freshness limits. I'd ask Ophelia where they draw this line today."*

---

**Q: How do you handle rate limits across many providers?**

> *"Per-provider token bucket, request queuing, prioritize by customer SLA. Cache availability briefly (30–60s) to absorb search spikes. Circuit breaker: if provider returns 429 N times, open circuit, fail fast, route to alternate provider. In Alex, I tier models by cost — same resource-budget thinking."*

---

**Q: How do you know availability data isn't stale?**

> *"TTL on cache, `fetched_at` timestamp in response, re-validate on hold/create (not just search). For high-stakes confirms, fresh check immediately before `create`. Ophelia markets 'no stale data' — that's a freshness SLO, not a one-time fetch."*

---

### MCP & Agent Tooling

**Q: What is MCP and why would Ophelia expose one?**

> *"Model Context Protocol — open standard for agents to discover and call tools with typed schemas. Ophelia's MCP server (`mcp.ophelia.so`) lets any MCP-compatible agent (Claude, Cursor, custom) call search/book/cancel without custom integration per runtime. I use Playwright MCP in Alex for the same reason — one tool interface, multiple agent frameworks."*

---

**Q: How do you design MCP tools vs REST endpoints?**

| MCP tool | REST endpoint |
|----------|---------------|
| Agent-native (`search_availability`) | Platform-native (`POST /v1/availability`) |
| Rich schema descriptions for LLM | OpenAPI for devs |
| Coarse-grained (compound actions) | Fine-grained CRUD |
| SSE transport common | HTTP + webhooks |

> *"Same execution backend. MCP tools should map 1:1 to SDK methods where possible — no divergent logic."*

---

**Q: How do you limit tool calls so agents don't run wild?**

> *"Tool budgets per request: max N searches, 1 create. Timeouts per tool call. Guardrails on inputs (party_size < 20). In Alex, fast agent gets no MCP (Bedrock tool cap); deep agent gets Playwright — deliberate budget by route."*

---

**Q: Have you used Playwright / browser automation in production?**

> *"Yes — Alex ECS deep researcher uses Playwright MCP to browse SEC EDGAR and live market pages when no clean API exists. Challenges: latency (10–30s), brittle DOM selectors, headless infra on ECS. Mitigations: timeout per page, fallback to API-only path, cache ingested documents. Same tradeoffs Ophelia faces on booking surfaces without APIs."*

---

### System Design Scenarios

**Q: Design Ophelia's booking system for 10,000 concurrent agent requests.**

> *"Layers:*
> 1. * **Edge** — API Gateway, rate limit per API key, auth.*
> 2. * **Router** — classify search vs create; search → sync pool, create → queue.*
> 3. * **Search workers** — horizontally scaled, parallel provider adapters, 2s timeout each, merge results.*
> 4. * **Create workers** — SQS + idempotency store (DynamoDB or Redis), state machine in Postgres.*
> 5. * **Provider adapters** — isolated per supplier, circuit breakers.*
> 6. * **Observability** — P95 per stage, confirmation rate, DLQ depth.*
>
> *Bottleneck is provider rate limits, not your compute — queue and backoff. I ran 100+ Bread bots on the same principle: Orchestrator queues absorb spikes."*

---

**Q: Two users try to book the last table — how do you handle it?**

> *"Optimistic concurrency: hold/reserve with short TTL (60–120s). First `create` with valid hold wins; second gets `409 conflict` or alternate suggestions. Don't check-then-act without a hold — race condition. Dating app coordination failed here — two users, one reservation."*

---

**Q: How would you coordinate a multi-person booking (3 friends, one pays)?**

> *"Workflow with steps: create draft booking → send hold invites → collect RSVPs → single payer confirms → execute. State machine with timeouts per step; expire draft if incomplete. Correlation ID links all participant actions. Ophelia mentions multi-step coordination across users — this is a workflow problem, not a single API call."*

---

**Q: Design webhook delivery to customer platforms.**

> *"At-least-once delivery: persist event → attempt POST → retry with backoff → DLQ after N failures. Customer acknowledges with 200; signature (HMAC) on payload. Idempotent `event_id` so customer dedupes. Expose replay API for missed events."*

---

### Distributed Systems & AWS

**Q: Why SQS between orchestration steps?**

> *"Decoupling — slow reporter doesn't block scheduler. Durability — message survives Lambda crash. Backpressure — queue depth signals overload. Retry — visibility timeout + redrive. In Alex: scheduler → planner → tagger → reporter all on SQS. Alternative: Step Functions for visual workflows — I'd use that if steps need complex branching."*

---

**Q: Lambda vs ECS — when do you pick each?**

| Lambda | ECS |
|--------|-----|
| Short jobs (< 15 min), event-driven | Long-running, streaming, MCP/Playwright |
| Planner, tagger, ingest | Researcher with SSE + browser |
| Auto-scale to zero | Persistent connections, warm pools |

> *"Ophelia search might be Lambda; browser-based provider adapters might be ECS — same split I use in Alex."*

---

**Q: How do you handle Aurora cold starts in serverless?**

> *"Periodic warmup ping (Alex ECS pings every 4 min), min ACU on Serverless v2 if latency-critical, RDS Data API to avoid connection pooling issues in Lambda. I provisioned Aurora via Terraform at Archemy with Data API for the same reason."*

---

### Inference & LLMs in Production

**Q: How do you choose which model for which task?**

> *"Match model tier to SLA and complexity:*
> - * **Nova Lite** — tagging, routing, cost monitoring (fast, cheap).*
> - * **Nova Pro** — deep research, multi-agent debate (quality).*
> *Log cost-per-task in `agent_observations`. Ophelia may use LLMs for intent parsing but execution confirm is deterministic code — don't let the model 'guess' a booking succeeded."*

---

**Q: Should the LLM call booking APIs directly?**

> *"No — LLM calls **tools** (MCP/SDK), tools call execution layer, execution layer calls providers. The LLM never holds payment credentials or bypasses idempotency. Structured tool outputs (`booking_id`, `status`) — not free text. In Alex, agents output Pydantic `AgentVote`, not prose, for downstream execution."*

---

**Q: How do you apply guardrails in an agent pipeline?**

> *"Bedrock guardrails on output (Terraform in Alex), confidence thresholds on trade votes, `should_apply_guardrail()` keyword skip for latency. For Ophelia: guardrail on PII in requests, block booking params outside sane bounds (party of 500). Execution layer validates schema before hitting providers."*

---

### Evaluation & Quality

**Q: How do you measure if an execution layer is working?**

| Metric | Ophelia | Alex |
|--------|---------|------|
| Success rate | Confirmation rate | Pipeline completion rate |
| Latency | Time-to-confirm P95 | Query P95, per-agent latency |
| Quality | Search-to-book conversion | RAGAS faithfulness |
| Cost | Cost per confirmed booking | Cost per query in `/observe` |
| Failure | Retry rate, DLQ depth | Guardrail hits, ECS fallback rate |

> *"At Archemy, RAGAS + LangSmith improved reliability 30%. I'd propose the same outcome metrics for Ophelia's confirm step."*

---

**Q: How would you test a booking integration before production?**

> *"Sandbox providers, recorded fixtures for unit tests, contract tests on adapter interfaces, chaos tests (timeout, 500, stale inventory), load test on search aggregator. `test_trading.sh` in Alex is my smoke test pattern — post-deploy invoke orchestrator, assert success."*

---

### Databases & State

**Q: What do you store about a booking?**

> *"`booking_id`, `idempotency_key`, `client_id`, `status`, `provider`, `provider_ref`, `user_id`, `party_size`, `time`, `location`, `payment_id`, `created_at`, `confirmed_at`, `reconciliation_state`, raw provider response (JSONB for debug). Immutable event log for audit — append-only `booking_events` table."*

---

**Q: Why RDS Data API instead of direct Postgres connections from Lambda?**

> *"Lambda doesn't hold connection pools well — Data API is HTTP-based, no pool exhaustion. Tradeoff: slightly higher latency, some type quirks (Aurora returns NUMERIC as `stringValue` — I hit that bug in Alex). Worth it for serverless agents at Archemy and Alex."*

---

### CI/CD & Observability

**Q: How do you deploy execution-layer changes safely?**

> *"Path-based GitHub Actions (Alex has `deploy_agents.yml`, `deploy_trading.yml`), smoke test post-deploy (`test_trading.sh`), Terraform for infra. Bread did DEV→QA→PROD package promotion. For Ophelia: canary provider adapter deploys — route 5% traffic before full rollout."*

---

**Q: What do you log for debugging a failed booking?**

> *"`correlation_id` across all steps, per-provider request/response (redact PII), latency per adapter, retry count, idempotency key, final status. Structured JSON logs → CloudWatch. Alex `agent_observations` captures tokens, cost, latency per agent call — same per-booking trace idea."*

---

### Tricky / Curveball Questions

**Q: You haven't worked on bookings — why should we hire you?**

> *"Bread orchestrated 100+ production workflows with queues, SLAs, and third-party API failures. Alex built an execution layer over fragmented financial supply with MCP, retries, and confirmed outcomes. Archemy built eval gates on production AI outputs. The domain is bookings; the engineering is orchestration, reliability, and third-party abstraction — that's my six-year thread."*

---

**Q: What's the hardest bug you've debugged?**

> *"Aurora Data API returned NUMERIC columns as `stringValue` not `doubleValue` — portfolio P&L showed $0, holdings like ASML disappeared from UI. Root cause was type coercion at the API boundary, not business logic. Built `parseNumber()` and applied everywhere. Execution layers fail at boundaries between systems."*

---

**Q: How would you improve Ophelia's product technically?** *(if they invite critique)*

> *"I'd instrument per-provider confirmation rate and P95 latency publicly for customers, add OpenTelemetry traces across search→hold→confirm, and gate adapter deploys with contract tests. Those are gaps I'm closing in Alex too (P17 eval harness, P19 tracing) — I'd bring that discipline."*

---

### System Design Cheat Sheet (Verbal Whiteboard)

If they ask you to "talk through architecture" on a phone call without a whiteboard, narrate in this order:

```
1. Client (app or agent via SDK/MCP)
2. API Gateway — auth, rate limit, idempotency key extraction
3. Router — search (sync) vs create (async queue)
4. Search aggregator — parallel adapters, timeout, merge, cache
5. Booking worker — state machine, hold, pay, confirm
6. Provider adapters — one per supplier, circuit breaker
7. DB — bookings + idempotency + event log
8. Webhooks — customer notification
9. Observability — metrics, DLQ, alerts
```

---

## Questions to Ask Ophelia

Shows you think like a builder, not a candidate:

1. *"Where do you draw the line between sync confirmation API and async webhook for slow providers?"*
2. *"How do you handle idempotency when an agent retries `create` after a timeout?"*
3. *"What's your MCP tool surface today — is search separate from book, or one compound tool?"*
4. *"How do you measure execution success — confirmation rate, time-to-confirm, retry rate?"*
5. *"What's the hardest fragmented provider you've integrated, and what broke at scale?"*
6. *"How do you think about proxy/retry vs. giving up and returning partial availability?"*
7. *"Bo's story mentions teams spending $2M on integrations — where does Ophelia draw the line between proxy/scrape vs. official partner API?"*
8. *"You went live on 10 platforms in 6 months — what broke most often in those early integrations?"*
9. *"How do you handle payments in the execution flow — sync with booking confirm, or separate saga step?"*
10. *"What's your reconciliation model when a provider confirms async or disputes a booking state?"*

---

## Gaps to Acknowledge (Honestly)

Interviewers respect self-awareness. Frame as "built in Alex, ready to apply here":

| Gap | Honest framing | Alex roadmap |
|-----|----------------|--------------|
| No booking domain | Financial execution is same orchestration problem | N/A |
| Paper trades not fully executed | Advisory votes exist; P4 executor planned | Trading Floor 2.0 |
| RAGAS not in CI yet | Script exists, not gated | P17 eval harness |
| No OpenTelemetry traces | Custom metrics + logs | P19 |
| `context_service.py` bugs | Known P0 fix | Foundation fixes |
| Global-only research vectors | Per-user scoping planned | P2 RAG engine |

**Never say:** "I haven't thought about reliability."  
**Say:** "I have retry, fallback, and idempotency in production paths; DLQ and distributed tracing are the next layer I'd add."

---

## Pre-Interview Checklist

- [ ] Rehearse **personalized 30s intro** (§ Suggested Intro) — out loud twice
- [ ] Time **Deep-Dive A (Alex)** — under 8 minutes
- [ ] Time **Deep-Dive B (Archemy + Robothons)** — under 6 minutes
- [ ] Review **§ Archemy Use Cases** — Robothons trade execution ↔ Ophelia confirm
- [ ] Memorize Bo's origin story (dating app → 10 platforms in 6 months)
- [ ] Rehearse **founding member 60s pitch** (§ Solving Core Issues)
- [ ] Know **30/60/90 day plan** at high level (idempotency → adapters → hardening)
- [ ] Resume PDF open; know every bullet's Ophelia parallel (§ Resume Mapping)
- [ ] Prepare answer if asked "Why leave Archemy?" — positive framing only
- [ ] Test Zoom/phone audio 10 min before
- [ ] Optional: pull `/observe` metrics if they ask for numbers

---

## Quick Reference: File → Interview Topic

| Interview topic | Open this file |
|-----------------|----------------|
| Agent orchestration | `backend/agents/planner.py`, `reporter.py`, `scheduler.py` |
| Trading debate | `backend/agents/trading/core/debate_engine.py`, `orchestrator.py` |
| MCP + streaming | `backend/researcher/server.py`, `mcp_servers.py` |
| Reliability | `backend/agents/reporter.py`, `db_helper.py` |
| Observability | `frontend/app/observe/page.tsx`, `agent_observations` |
| CI/CD | `.github/workflows/deploy_*.yml`, `scripts/start_session.sh` |
| Eval | `scripts/tests/test_ragas.py` |
| Roadmap / production pillars | `Alex_Master_Implementation_Plan.md` |
| Business context | `Startup.md` |

---

*Good luck. Lead with execution, show the code, bridge every answer to Ophelia's "intent → confirmed outcome" thesis.*
