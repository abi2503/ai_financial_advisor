# Alex Master Implementation Plan

> **Status:** PARKED — awaiting approval  
> **Created:** June 13, 2026  
> **Source documents:**
> - `Alex_Trading_Floor_2.0.md` — Autonomous paper-trading simulation, scout agents, RL learning
> - `Alex_AI_2.0.md` — Intelligent conversational AI, query routing, session RAG, MCP, synthesis
> - `Startup.md` — Business model, monetization, startup ideas, unit economics
>
> **Infrastructure rule (mandatory):** All AWS resource provisioning and configuration changes go through **Terraform** (`terraform/0_vpc` … `terraform/9_trading_floor`). No ad-hoc `aws lambda create-function`, EventBridge schedules, IAM policies, or new queues via CLI/Console. Application code deploys (`deploy.sh`, `deploy_trading.sh`) update artifacts on Terraform-managed resources only.

---

## Table of Contents

1. [Unified Vision](#unified-vision)
2. [How the Two Systems Connect](#how-the-two-systems-connect)
3. [Current State Summary](#current-state-summary)
4. [Foundation Fixes (P0 — Do First)](#foundation-fixes-p0)
5. [Implementation Phases](#implementation-phases)
6. [Phase Details](#phase-details)
7. [Quant Intelligence Layer (P13)](#quant-intelligence-layer-p13)
8. [Trading Floor Intelligence Vector Store (P14)](#trading-floor-intelligence-vector-store-p14)
9. [Async Deep Research Sub-Agents (P15)](#async-deep-research-sub-agents-p15)
10. [RAGAS Evaluation Framework (P17)](#ragas-evaluation-framework-p17)
11. [Alex Comprehensive Cost Agent (P21)](#alex-comprehensive-cost-agent-p21)
12. [Aurora Schema Master List](#aurora-schema-master-list)
13. [API Master List](#api-master-list)
14. [Frontend Master List](#frontend-master-list)
15. [Infrastructure Master List](#infrastructure-master-list) — **Terraform-first policy**
16. [Observability Master Map](#observability-master-map)
17. [Effort Estimates](#effort-estimates)
18. [Recommended Implementation Order](#recommended-implementation-order)
19. [Decision Checklist for Approval](#decision-checklist-for-approval)
20. [Production Engineering Pillars](#production-engineering-pillars-implementable-from-current-setup)
21. [Test After Every Phase](#test-after-every-phase)
22. [LangChain Family — LangChain, LangGraph, LangSmith](#langchain-family--langchain-langgraph-langsmith)
23. [Agentic RAG](#agentic-rag)
24. [Document Index](#document-index)

---

## Unified Vision

Alex becomes a **complete financial intelligence platform** with three interconnected intelligence layers:

```
┌─────────────────────────────────────────────────────────────────────┐
│                        ALEX AI 2.0 (Brain)                          │
│  Conversational intelligence — ask anything about any stock         │
│  Routes to fast/deep/multi research, remembers everything             │
│  Deep = parallel sub-agents (SEC, News, Quant, Earnings…) — faster      │
│  Synthesizes hedge-fund-quality commentary, stores in vector DB       │
└────────────────────────────┬────────────────────────────────────────┘
                             │ shared intelligence
                             ▼
┌─────────────────────────────────────────────────────────────────────┐
│                   QUANT INTELLIGENCE (Numbers)                       │
│  Charts, indicators, options flow, macro data via MCP                  │
│  Powers Zara (quant agent) + Alex chart/technical queries            │
└────────────────────────────┬────────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────────┐
│                   TRADING FLOOR 2.0 (Hands)                         │
│  6 autonomous agents debate and execute paper trades                  │
│  Collective debate memory → trading_floor_intelligence vector store    │
│  Learns from outcomes via RL weight scoring                           │
└────────────────────────────┬────────────────────────────────────────┘
                             │ everything visible
                             ▼
┌─────────────────────────────────────────────────────────────────────┐
│                   OBSERVABILITY (/observe)                            │
│  Costs, guardrails, agent accuracy, RAG, quant MCP usage,             │
│  query response speed (P50/P95, first token, sub-agent breakdown),   │
│  RAGAS quality scores (relevancy, faithfulness, hallucination),        │
│  trading floor intelligence retrieval, simulation P&L                  │
│  + daily FinOps email synthesized by Alex Cost Agent (P21)            │
└─────────────────────────────────────────────────────────────────────┘
```

**User journey:**
1. Ask Alex anything → get intelligent, remembered, sourced commentary
2. Alex's research enriches trading floor agent debates automatically
3. Trading floor autonomously paper-trades a simulation seeded from user's portfolio
4. Alex proactively tells user when simulation outperforms their real holdings
5. Everything is visible on the observability page

---

## How the Two Systems Connect

### Intelligence Flow (Bidirectional)

```mermaid
flowchart LR
    subgraph ai [Alex AI 2.0]
        CHAT[User Chat]
        ROUTER[Query Router]
        RAG[RAG Engine]
        VECTORS[(research_vectors)]
        SYNTH[Synthesizer]
        DEEP[Deep Orchestrator]
        SUB[Sub-Agents parallel]
        LAT[(query_latency_metrics)]
    end

    subgraph research [Portfolio Research Pipeline]
        SCHED[Scheduler 2h]
        DIGESTS[(portfolio_digests)]
    end

    subgraph trading [Trading Floor 2.0]
        ORCH[Orchestrator]
        DEBATE[6-Agent Debate]
        EXEC[Paper Trade Executor]
        RL[RL Weight Updater]
        SIM[(simulated_trades)]
        TFI[(trading_floor_intelligence)]
    end

    subgraph quant [Quant Intelligence]
        QNT[Quant MCP Layer]
        CHARTS[Charts + Indicators]
    end

    subgraph observe [Observability]
        OBS[/observe page]
    end

    CHAT --> ROUTER --> RAG
    ROUTER -->|deep| DEEP --> SUB --> SYNTH
    RAG --> VECTORS
    RAG --> DIGESTS
    RAG --> SIM
    ROUTER --> SYNTH --> VECTORS
    DEEP --> LAT
    ROUTER --> LAT
    SYNTH --> LAT

    SCHED --> DIGESTS
    DIGESTS --> RAG
    VECTORS --> DEBATE
    DIGESTS --> DEBATE
    SIM --> RAG

    ORCH --> DEBATE --> EXEC --> SIM
    DEBATE --> TFI
    EXEC --> RL
    RL --> DEBATE
    QNT --> CHARTS
    QNT --> DEBATE
    QNT --> ROUTER
    TFI --> RAG
    TFI --> DEBATE

    CHAT -.->|proactive comparison| SIM
    DEBATE --> OBS
    RAG --> OBS
    EXEC --> OBS
    RL --> OBS
    LAT --> OBS
```

### Shared Data Layer

| Table | Written By | Read By |
|-------|-----------|---------|
| `portfolios` | User (portfolio page) | AI RAG, Trading orchestrator, Scout |
| `portfolio_digests` | Portfolio research reporter | AI RAG, Trading context_builder |
| `research_vectors` | AI chat ingest, portfolio research | AI RAG, Trading context_builder |
| `chat_sessions` | AI chat turns | AI RAG (conversation history) |
| `research_sessions` | AI chat (full Q&A) | AI history page, RAG |
| `simulated_trades` | Trading debate + executor | AI RAG (trading context), Observe |
| `agent_positions` | Trading executor | AI RAG, Trading UI, Observe |
| `trading_simulations` | Trading orchestrator | AI synthesizer (comparison), Observe |
| `user_trading_config` | User settings UI | Trading orchestrator, EventBridge |
| `agent_performance` | RL evaluator | Trading debate weights, Observe |
| `rl_weights` | RL updater | Trading debate_engine, Observe |
| `agent_observations` | All agents (AI + trading) | Observe |
| `trading_events` | All trading subsystems | Observe timeline |
| `rag_attributions` | AI RAG engine | Observe |
| `ragas_evaluations` | RAGAS eval runner (P17) | Observe, CI gates |
| `query_latency_metrics` | Latency tracker (all routes) | Observe, product analytics |
| `session_metadata` | AI chat sessions | Observe, AI suggestions |
| `trading_floor_intelligence` | Debate ingest pipeline | AI RAG, Trading Historian, Zara, Observe |
| `quant_snapshots` | Quant MCP layer | Zara, Alex chat, Observe |

### Cross-System Features

| Feature | AI 2.0 Provides | Trading Floor 2.0 Provides | User Sees |
|---------|----------------|---------------------------|-----------|
| **Ticker intelligence** | Chat research → vectors | Debate decisions → simulated_trades | Research page + Trading page |
| **Portfolio awareness** | "You hold 10 ASML @ $1500" | Position context in debates | Both pages |
| **Proactive comparison** | "Sim +2.3% vs portfolio +0.8%" | Simulation P&L data | Chat responses |
| **Memory** | Session RAG | Historian agent reads vectors | Follow-up questions work |
| **Learning** | — | RL weights improve agent trust | Observe accuracy leaderboard |
| **Guardrails** | Financial-only gate + Bedrock | Confidence caps + action validation | Observe guardrail log |

---

## Current State Summary

### Working

- Fast/deep/multi research (with manual toggle)
- 6-agent trading debate (manual trigger)
- Portfolio CRUD + portfolio research digests (2h)
- Cost/guardrail observability (7-day)
- `alex-cost-monitor` + `alex-ops-agent` — **fragmented** cost reporting (AWS only vs ops digest; email only on alert or Monday)
- Ingest pipeline → pgvector
- RAGAS eval script (`scripts/tests/test_ragas.py`) — local run, JSON report only
- `ragas_evaluations` table DDL in `aurora_warmup.py`
- AWS infrastructure (ECS, Lambda, Aurora, EventBridge)

### Broken / Incomplete

- `context_service.py` — 4 SQL bugs, wrong table name
- Deep research routes — no user_id/session_id
- Stream responses — not saved to DB
- research_vectors — global only, no user scoping
- Trading trades — advisory only, positions never update
- Multi-agent reporter — Bedrock only, no live tools
- Guardrails — not on all paths
- Observer Lambda — not deployed
- **Comprehensive Cost Agent (P21)** — not built; no unified daily cost email across all agents/sessions
- EventBridge trading schedule — permission only, no schedule
- RAGAS — not persisted to Aurora, not in CI, no `/observe` panel, no deploy gate

---

## Foundation Fixes (P0)

**Must complete before any feature work. Both systems depend on this.**

| # | Fix | File(s) | System |
|---|-----|---------|--------|
| 1 | Fix SQL typos in context_service | `context_service.py` | AI |
| 2 | `portfolio_stocks` → `portfolios` | `context_service.py` | AI |
| 3 | Add `user_id`, `session_id` to `research_vectors` | `aurora_warmup.py`, `ingest_pgvector.py` | AI |
| 4 | Pass `user_id` + `session_id` through all API routes | `api/research/deep/*`, `api/research/stream/*` | AI |
| 5 | Add `agent_observations` DDL to warmup | `aurora_warmup.py` | Both |
| 6 | Fix `simulated_trades` schema (target_price, stop_loss, pnl) | `aurora_warmup.py` | Trading |
| 7 | Remove `MessageGroupId` from orchestrator SQS send | `orchestrator.py` | Trading |
| 8 | Add `chat_sessions` unique index | `aurora_warmup.py` | AI |
| 9 | Create all new tables (master list below) | `aurora_warmup.py` | Both |

**Effort:** 2–3 days  
**Blocks:** Everything else

### P0 Verification (run after every P0 change)

```bash
# After implementing P0 (or any P0 fix):
./scripts/test_p0.sh              # static + unit + Aurora schema (recommended)
./scripts/test_p0.sh --static     # CI-safe, no AWS
./scripts/test_p0.sh --full       # + trading orchestrator SQS smoke
```

| Test file | What it checks |
|-----------|----------------|
| `scripts/tests/test_p0_foundation.py` | Static regressions (typos, MessageGroupId), unit helpers, Aurora tables/columns |
| `scripts/test_p0.sh` | Wrapper: syntax compile → foundation tests → optional orchestrator smoke |

**CI:** `.github/workflows/ci.yml` runs `test_p0_foundation.py --static` on every PR.

---

## Implementation Phases

| Phase | Name | System | Effort | Depends On |
|-------|------|--------|--------|------------|
| **P0** | Foundation Fixes | Both | 2–3 days | — |
| **P1** | Alex Query Router + Unified Chat | AI | 3–4 days | P0 |
| **P2** | RAG Engine + Session Memory | AI | 4–5 days | P0, P1 |
| **P3** | Alex Synthesizer + Chunked Ingest | AI | 3–4 days | P1, P2 |
| **P4** | Paper Trade Executor + Simulation UI | Trading | 3–4 days | P0 |
| **P5** | User Trading Config + Autonomous Schedule | Trading | 2–3 days | P4 |
| **P6** | Context Bridge (AI ↔ Trading) | Both | 2–3 days | P2, P4 |
| **P7** | MCP Expansion (SEC, News, Earnings) | AI | 4–5 days | P1 |
| **P8** | RL Learning Loop | Trading | 3–4 days | P4 |
| **P9** | Scout + Sentinel Agents | Trading | 4–5 days | P5, P6 |
| **P10** | Unified Guardrails | Both | 2–3 days | P1, P4 |
| **P11** | Full Observability Expansion | Both | 3–4 days | P1–P10 |
| **P12** | Observer Lambda + Daily Digests | Both | 2 days | P4, P11 |
| **P13** | Quant Intelligence + MCP Data Layer | Both | 4–5 days | P1, P7 |
| **P14** | Trading Floor Intelligence Vector Store | Trading | 3–4 days | P4, P6 |
| **P15** | Async Deep Research Sub-Agents + Latency Observability | AI | 4–5 days | P1, P3, P7 |
| **P17** | RAGAS Evaluation Framework | AI / Both | 2–3 days | P2, P3 |
| **P21** | Alex Comprehensive Cost Agent (FinOps) | Both | 3–4 days | P11, P15 |
| **P22** | LangSmith Tracing + Eval (LangChain Family) | AI / Both | 2–3 days | P1, P11 |
| **P23** | LangGraph Orchestration (selective) | AI | 3–5 days | P2, P22 |
| **P24** | Agentic RAG Engine | AI | 4–6 days | P2, P23 (optional) |

---

## Phase Details

### P1 — Alex Query Router + Unified Chat

**From:** Alex AI 2.0, Phase A + API changes

**Deliverables:**
- `backend/researcher/query_router.py` — Nova Lite intent classifier
- `frontend/app/api/alex/chat/route.ts` — unified SSE endpoint
- `frontend/app/research/page.tsx` — remove Fast/Deep toggle, show router reasoning
- `frontend/components/AlexChat.tsx` — reusable chat component
- Deprecate separate `/api/research/fast`, `/deep`, `/stream` paths

**User sees:** Single chat box. Alex automatically picks fast or deep. Reasoning steps visible.

---

### P2 — RAG Engine + Session Memory

**From:** Alex AI 2.0, Phase E

**Deliverables:**
- `backend/researcher/rag_engine.py` — hybrid retrieval pipeline
- `backend/researcher/chunking.py` — markdown-aware chunking
- Fix all `context_service.py` bugs
- `session_metadata` table + API
- Hydrate chat from Aurora on page load
- MMR + reranking + context compression
- `rag_attributions` logging

**User sees:** Follow-up questions work. "What about ASML?" after NVDA discussion understands context.

---

### P3 — Alex Synthesizer + Chunked Ingest

**From:** Alex AI 2.0, Phase D + Phase F

**Deliverables:**
- `backend/researcher/synthesizer.py` — fast/deep/multi commentary styles
- Proactive trading floor comparison in synthesizer
- Chunked ingest (query + response chunks → research_vectors with user_id)
- Link `research_sessions.vector_id` to first chunk
- Save stream responses to DB

**User sees:** Polished commentary, not raw agent dumps. Deep answers read like hedge fund memos.

---

### P4 — Paper Trade Executor + Simulation UI

**From:** Trading Floor 2.0, Phase 1

**Deliverables:**
- `backend/agents/trading/core/trade_executor.py`
- BUY/SELL/TRIM/HOLD actually updates `agent_positions` + `cash_balance`
- Virtual account seeded from real portfolio value
- `/trading` Simulation tab with replay mode
- `GET /api/trading/simulation`

**User sees:** Agents actually trade in simulation. Replay shows step-by-step decisions.

---

### P5 — User Trading Config + Autonomous Schedule

**From:** Trading Floor 2.0, Phase 2

**Deliverables:**
- Wire `user_trading_config` table (UI + API)
- Agent Settings panel on `/trading`
- EventBridge schedule (single loop or per-user)
- Debate interval: 2h / 3h / 4h / manual
- Market hours gate (configurable)

**User sees:** "Autonomous Trading ON, debates every 2 hours." No manual run needed.

---

### P6 — Context Bridge (AI ↔ Trading)

**From:** Both docs, Phase G (AI) + Phase 3 (Trading)

**Deliverables:**
- `backend/agents/trading/core/context_builder.py`
- Trading debates read: portfolio_digests + research_vectors + session memory
- AI chat reads: simulated_trades + agent votes for trading queries
- `agent_observations.data_used` logs context sources
- Historian agent (trade history in debate prompts)

**User sees:** Trading agents reference Alex's prior research. Alex answers "what did agents decide on NVDA?"

---

### P7 — MCP Expansion

**From:** Alex AI 2.0, Phase C

**Deliverables:**
- `backend/researcher/mcp/sec_edgar_mcp.py`
- `backend/researcher/mcp/financial_news_mcp.py`
- `backend/researcher/mcp/earnings_mcp.py`
- `backend/researcher/mcp/mcp_gateway.py`
- Deep researcher gets Playwright + SEC + News MCP
- Scout agent gets Playwright MCP (when P9 implemented)
- MCP servers reused by **P15 deep sub-agents** (SEC, News, Earnings agents)

**User sees:** "Jensen Huang said X" queries get verified against real news/SEC sources.

---

### P8 — RL Learning Loop

**From:** Trading Floor 2.0, Phase 5

**Deliverables:**
- `backend/agents/trading/learning/trade_evaluator.py` — daily outcome scoring
- `backend/agents/trading/learning/weight_updater.py` — adaptive agent weights
- `rl_weights` table populated
- Debate engine uses dynamic weights
- Accuracy leaderboard on `/observe`

**User sees:** "Marcus 72% accuracy this month" — agents that perform better get more influence.

---

### P9 — Scout + Sentinel Agents

**From:** Trading Floor 2.0, Phase 3 + Phase 8

**Deliverables:**
- `backend/agents/trading/agents/scout.py` — find attractive stocks
- `backend/agents/trading/agents/sentinel.py` — stop-loss monitor
- `scout_candidates` table
- Scout UI panel on `/trading`
- Hourly sentinel EventBridge schedule

**User sees:** Agents discover and paper-trade stocks not in portfolio (if enabled).

---

### P10 — Unified Guardrails

**From:** Alex AI 2.0, Phase H

**Deliverables:**
- `backend/shared/guardrails.py` — shared layer
- Financial-only gate at router (reject off-topic)
- Bedrock guardrail on synthesizer + reporter + all trading agents
- Input PII detection
- Output disclaimer injection
- Ingest gate (don't store failed guardrail responses)

**User sees:** Alex politely declines non-financial questions. All responses have advice disclaimer.

---

### P11 — Full Observability Expansion

**From:** Both docs, observability sections

**Deliverables:**
- Extend `/api/observe` with all new panels
- `trading_events` timeline on `/observe`
- Query routing distribution chart
- RAG performance metrics
- MCP tool usage panel
- Simulation health + daily P&L chart
- Agent accuracy leaderboard
- RL weights evolution chart
- Scout activity panel
- Context bridge attribution
- **Query response speed dashboard** (P50/P95, first token, sub-agent breakdown) — see P15

**User sees:** Complete visibility into every agent action, cost, decision, and **how fast Alex responds**.

---

### P12 — Observer Lambda + Daily Digests

**From:** Trading Floor 2.0, Phase 6 (observer) + AI daily summary

**Deliverables:**
- Deploy `observer_agent.py` Lambda
- Daily trading P&L digest email
- `trading_daily_pnl` populated
- AI session summary (optional weekly email)

**User sees:** Daily email: "Your simulation +1.2% today. Marcus was most accurate."

---

## Alex Comprehensive Cost Agent (P21)

**Goal:** One **Alex FinOps agent** that aggregates every cost signal across the platform — AWS infra, Bedrock tokens per agent, per-session API costs, MCP/tool calls, trading debate spend, embeddings, external APIs — synthesizes a human-readable report via Alex (Nova Lite), and emails it **daily** to `abhishek.suresh2503@gmail.com` via EventBridge + SES.

### Problem Today (Fragmented FinOps)

| Component | What it tracks | Email behavior | Gap |
|-----------|----------------|----------------|-----|
| `alex-cost-monitor` (`cost_monitor.py`) | AWS Cost Explorer only | Alert if daily > $10; Monday weekly digest | No agent/session/API breakdown |
| `alex-ops-agent` (`ops_agent.py`) | Health + AWS + LLM metrics + API cost estimates | Alert on issues; Monday weekly ops digest | Not daily; no per-user/per-session attribution |
| `agent_observations` | Per-call tokens, cost, agent name | None (dashboard only) | Not rolled into email |
| `query_latency_metrics` | Per-query cost, route, tools | None | Not in daily report |
| Dashboard `OpsCostWidget` | 7-day `cost_snapshots` | None | AWS infra only |

**User requirement:** Single daily email with **full system cost picture** — infra + intelligence + per-agent + per-session — synthesized by Alex.

### Architecture

```mermaid
flowchart TB
    EB[EventBridge Scheduler\ncron 0 7 * * ? * ET]
    CA[alex-cost-agent Lambda]
    SYN[Alex Synthesizer\nNova Lite digest]

    subgraph collectors [Cost Collectors]
        CE[AWS Cost Explorer\ninfra by service]
        OPS[ops_snapshots\nhealth + API traffic]
        AO[agent_observations\nper-agent tokens + cost]
        QLM[query_latency_metrics\nper-session / per-route]
        AO_TR[Trading agent_observations\ndebate cost]
        CW[CloudWatch AlexAI/*\nBedrock + SageMaker]
        EXT[External API estimator\nSEC, yfinance, Playwright]
    end

    subgraph persist [Aurora]
        CDR[(cost_daily_reports)]
        CS[(cost_snapshots)]
    end

    SES[Amazon SES\nabhishek.suresh2503@gmail.com]

    EB --> CA
    CA --> collectors
    collectors --> CA
    CA --> SYN
    SYN --> CDR
    CA --> CS
    CA --> SES
```

### Cost Data Sources (Complete Inventory)

#### Layer 1 — AWS Infrastructure (Cost Explorer)

| Source | Collector | Granularity |
|--------|-----------|-------------|
| ECS Fargate | `ce.get_cost_and_usage` GROUP BY SERVICE | Daily + MTD |
| Lambda (all agents) | Cost Explorer + invocation counts | Per function |
| Aurora Serverless | Cost Explorer | Daily |
| SageMaker endpoint | Cost Explorer + `InvocationsPerInstance` | Daily |
| ALB, NAT, VPC | Cost Explorer | Daily |
| SQS, SES, S3, CloudWatch | Cost Explorer | Daily |
| API Gateway | Cost Explorer | Daily |

**Reuses:** `get_daily_cost()`, `get_mtd_cost()`, `get_weekly_costs()` from `ops_agent.py` / `cost_monitor.py`.

#### Layer 2 — LLM / Bedrock (Per Agent)

| Agent / Path | Source table / metric | Fields |
|--------------|----------------------|--------|
| Alex chat (fast/deep/multi) | `query_latency_metrics` | `cost_usd`, `route`, `model`, `user_id`, `session_id` |
| Research reporter | `agent_observations` WHERE `agent_name='reporter'` | `tokens_in`, `tokens_out`, `cost_usd` |
| Planner / Tagger | `agent_observations` + Lambda invocations | tokens, cost |
| Trading debate (6 agents) | `agent_observations` WHERE `domain='trading'` | per-agent BUY/SELL votes + cost |
| Ops / Cost / Observer digests | Lambda Bedrock calls | Nova Lite token estimate |
| Guardrails | `agent_observations.guardrail_hits` | Bedrock guardrail API cost |
| Embeddings (ingest + RAG) | SageMaker `alex-embedding` invocations | calls × $0.0001/1K |

**Aggregation SQL (daily rollup):**

```sql
-- Per-agent LLM cost (last 24h)
SELECT agent_name,
       COUNT(*) AS calls,
       SUM(tokens_in) AS tokens_in,
       SUM(tokens_out) AS tokens_out,
       SUM(cost_usd) AS cost_usd
FROM agent_observations
WHERE created_at >= NOW() - INTERVAL '24 hours'
GROUP BY agent_name;

-- Per-route session cost (last 24h)
SELECT route,
       COUNT(*) AS queries,
       SUM(cost_usd) AS cost_usd,
       AVG(total_ms) AS avg_latency_ms,
       COUNT(DISTINCT user_id) AS active_users,
       COUNT(DISTINCT session_id) AS sessions
FROM query_latency_metrics
WHERE created_at >= NOW() - INTERVAL '24 hours'
GROUP BY route;
```

#### Layer 3 — External APIs & MCP Tools

| API / Tool | Estimator | Source |
|------------|-----------|--------|
| Yahoo Finance (`yfinance`) | $0 (free) | `query_latency_metrics.data_sources` |
| SEC EDGAR | $0 (free) | tool call logs |
| Playwright MCP | compute-only (ECS) | CloudWatch ECS logs |
| Polygon / Alpha Vantage / Finnhub | tiered $/call | `EXTERNAL_API_COSTS` map in `ops_agent.py` |
| Unusual Whales / Benzinga | tiered $/call | future P13 MCP registry |

**Reuses:** `get_external_api_costs()` from `ops_agent.py` — extend to read `query_latency_metrics.data_sources` JSON for pass/fail + call counts.

#### Layer 4 — Trading Floor Specific

| Item | Source | Cost driver |
|------|--------|-------------|
| Debate cycles | `trading_events` + orchestrator invocations | 6× Nova Lite/Pro per debate |
| Scout scans | `scout_candidates` (P9) | MCP + LLM |
| Trade evaluator | `alex-trade-evaluator` (P8) | Lambda + Bedrock |
| Paper trades | `simulated_trades` | $0 execution (simulation) |

#### Layer 5 — Per-User / Per-Session Attribution (Optional P21.1)

| Dimension | Use |
|-----------|-----|
| `user_id` | Top 5 costliest users (for unit economics) |
| `session_id` | Most expensive sessions (debug runaway chats) |
| Clerk tier (future) | Margin per subscription tier |

### Alex Synthesis (Report Generation)

**Model:** `us.amazon.nova-lite-v1:0` (cost-efficient; ~$0.0003/report)

**Prompt structure:**

```
You are Alex FinOps — synthesize yesterday's platform cost report.

SECTIONS REQUIRED:
1. Executive summary (3 sentences): total spend, vs yesterday, vs MTD budget
2. AWS infrastructure breakdown (top 5 services with $)
3. Intelligence layer: LLM spend by agent (table: agent, calls, tokens, $)
4. Per-route chat cost: fast vs deep vs multi (queries, avg cost/query, P95 latency)
5. External API & MCP: calls and estimated $ by source
6. Trading floor: debate runs, tokens, cost per debate cycle
7. Cost per active user / session (if data available)
8. Anomalies: anything >2× 7-day average
9. 3 actionable optimization recommendations (specific, not generic)
10. Status: ON TRACK | MONITOR | ALERT (based on $10/day threshold)

Be specific with numbers. Audience: platform owner (developer).
```

**Output formats:**
- **Email body:** Markdown-style plain text (SES `Text` part)
- **Stored JSON:** Full structured payload in `cost_daily_reports.report_json`
- **Dashboard:** `/observe` panel + `/api/costs` extended with latest report

### New Lambda: `alex-cost-agent`

**File:** `backend/agents/cost_agent.py` (evolve + supersede `cost_monitor.py`)

```python
def lambda_handler(event, context):
    window = collect_cost_window(hours=24)      # all layers above
    report = synthesize_report(window)           # Nova Lite
    store_daily_report(report)                   # cost_daily_reports
    upsert_cost_snapshots(window.aws)            # backward compat
    send_daily_email(
        to="abhishek.suresh2503@gmail.com",
        subject=f"Alex Daily Cost Report — {date} — ${report.grand_total:.2f}",
        body=report.email_body,
    )
    if report.grand_total >= DAILY_THRESHOLD:
        store_cost_alert(report)
    return {"status": "ok", "total": report.grand_total}
```

**Consolidation plan:**

| Existing | After P21 |
|----------|-----------|
| `cost_monitor.py` daily schedule | **Replaced** by `cost_agent.py` (same EventBridge slot) |
| `ops_agent.py` weekly cost email | **Removed** — ops emails issues/alerts only |
| `ops_agent.py` `store_cost_snapshot()` | **Kept** — 30-min dashboard refresh unchanged |

### Aurora Schema: `cost_daily_reports`

```sql
CREATE TABLE IF NOT EXISTS cost_daily_reports (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  report_date DATE NOT NULL UNIQUE,
  grand_total NUMERIC(12,6) NOT NULL,
  aws_infra_total NUMERIC(12,6) DEFAULT 0,
  llm_total NUMERIC(12,6) DEFAULT 0,
  external_api_total NUMERIC(12,6) DEFAULT 0,
  trading_total NUMERIC(12,6) DEFAULT 0,
  report_json JSONB NOT NULL,          -- full structured collectors output
  synthesis TEXT NOT NULL,             -- Alex-generated narrative
  email_sent BOOLEAN DEFAULT false,
  email_sent_at TIMESTAMPTZ,
  recipient VARCHAR(255) DEFAULT 'abhishek.suresh2503@gmail.com',
  status VARCHAR(20) DEFAULT 'ok',       -- ok | alert | error
  created_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS cdr_date_idx ON cost_daily_reports (report_date DESC);
```

Add to `aurora_warmup.py` in P21.

### EventBridge + SES Configuration

| Resource | Value |
|----------|-------|
| Schedule | `cron(0 7 * * ? *)` — **7:00 AM ET daily** |
| Lambda | `alex-cost-agent` (replaces `alex-cost-monitor` target) |
| SES verified identity | `abhishek.suresh2503@gmail.com` (sender + recipient — existing) |
| Env `ALERT_EMAIL` | `abhishek.suresh2503@gmail.com` |
| Env `DAILY_COST_THRESHOLD` | `10.0` (alert section in email if exceeded) |
| Terraform | `terraform/6_agents/main.tf` — update schedule target + rename function |

**Email sections (daily):**

```
Subject: Alex Daily Cost Report — 2026-06-13 — $4.82

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
ALEX FINOPS — Daily Platform Cost
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

[Alex synthesis — executive summary]

── AWS Infrastructure ($X.XX) ──
  ECS Fargate:     $X.XX
  Aurora:          $X.XX
  Lambda:          $X.XX
  ...

── Intelligence Layer ($X.XX) ──
  Agent          Calls   Tokens    Cost
  reporter       12      45,200    $0.18
  debate-marcus  6       8,400     $0.02
  ...

── Chat Routes (24h) ──
  fast:  23 queries, $0.04 total, $0.002/query
  deep:   8 queries, $0.31 total, $0.039/query
  ...

── External APIs ($X.XX) ──
  yfinance: 142 calls ($0)
  sec_edgar: 18 calls ($0)
  ...

── Trading Floor ──
  Debates: 3 cycles, $0.12 total

── MTD: $XX.XX | 7-day avg: $X.XX/day ──
Status: ON TRACK

View live: {FRONTEND_URL}/observe
```

### Deliverables (P21)

| # | Deliverable | File(s) |
|---|-------------|---------|
| 1 | Cost collector module (all layers) | `backend/agents/cost_agent.py`, `backend/agents/cost_collectors.py` |
| 2 | Alex synthesis prompt + fallback template | `cost_agent.py` |
| 3 | `cost_daily_reports` DDL | `scripts/aurora_warmup.py` |
| 4 | EventBridge daily schedule → cost-agent | `terraform/6_agents/main.tf` |
| 5 | Deprecate `cost_monitor.py` schedule (merge logic) | `cost_monitor.py` → thin wrapper or remove |
| 6 | Ops agent: remove weekly cost email; keep 30-min health | `ops_agent.py` |
| 7 | API: latest daily report | `frontend/app/api/costs/route.ts` — add `?report=daily` |
| 8 | `/observe` panel: **Daily Cost Report** | `frontend/app/observe/page.tsx` |
| 9 | Static tests | `scripts/tests/test_p21_cost_agent.py` |
| 10 | SES + EventBridge verification script | `scripts/test_cost_agent.sh` |

### Dependencies

| Depends on | Why |
|------------|-----|
| **P11** | `agent_observations` panels populated; observability baseline |
| **P15** | `query_latency_metrics.cost_usd` per session (accurate chat attribution) |
| P0 schema | `agent_observations`, `cost_snapshots` DDL |

Can ship **P21-lite** before P15 using CloudWatch estimates for chat cost; full accuracy after P15.

### Effort & Priority

| Item | Estimate |
|------|----------|
| Collectors + SQL rollups | 1.5 days |
| Synthesis + email template | 0.5 day |
| Terraform + deploy + SES test | 0.5 day |
| `/observe` panel + API | 1 day |
| Tests | 0.5 day |
| **Total** | **3–4 days** |

**Priority:** High for production FinOps — unblocks unit economics visibility and `$29/mo` margin tracking from `Startup.md`.

### Verification (P21)

```bash
# 1. Infra — Terraform only (no manual Lambda/schedule creation)
cd terraform/6_agents && terraform plan   # PR review
cd terraform/6_agents && terraform apply  # provisions alex-cost-agent + schedule

# 2. Application code
cd backend/agents && bash package.sh       # builds cost_agent.zip
cd terraform/6_agents && terraform apply  # if filename/env changed

# 3. Static tests
python3 scripts/tests/test_p21_cost_agent.py --static

# 4. Live smoke — invoke existing TF-managed function only
aws lambda invoke --function-name alex-cost-agent \
  --payload '{"source":"manual-test"}' /tmp/cost_out.json

# 5. Confirm email, cost_daily_reports row, /api/costs?report=daily
```

**User sees:** Every morning, one email from Alex with complete platform cost — infra, every agent, every chat session, every API — plus optimization tips.

---

## Quant Intelligence Layer (P13)

**Goal:** Give Alex and the trading floor agents institutional-grade quantitative context — charts, indicators, options flow, macro numbers — all accessible via MCP tools. Primarily powers **Zara Patel (Quant Strategist)** and quant-routed Alex chat queries.

### Why a Separate Quant Layer

| Problem today | Quant layer solves |
|---------------|-------------------|
| Zara gets text prompts only | Zara gets live RSI, MACD, IV rank, put/call ratio |
| "Will NVDA go up?" lacks chart context | Alex router can attach technical snapshot |
| Market data is ad-hoc Python calls | Standardized MCP tools with observability |
| No chart images for user | Chart MCP generates shareable PNG/SVG URLs |
| Macro context missing from debates | FRED MCP injects rates, CPI, yield curve |

### Architecture

```
User query OR Debate cycle
        │
        ▼
┌───────────────────┐
│  Quant Orchestrator│  (decides which data sources to fetch)
└─────────┬─────────┘
          │
    ┌─────┴─────┬─────────┬──────────┬──────────┐
    ▼           ▼         ▼          ▼          ▼
 Price MCP  Technical  Options   Macro MCP  Chart MCP
 (OHLCV)     MCP       Flow MCP  (FRED)     (render)
    │           │         │          │          │
    └───────────┴─────────┴──────────┴──────────┘
                        │
                        ▼
              quant_snapshots table (structured numbers)
              + optional ingest → research_vectors (narrative)
                        │
                        ▼
              Zara / Alex / Reid debate prompts
```

### Recommended Data Sources & MCP Mapping

#### Tier 1 — MVP (low cost, already partially integrated)

| Data Source | API / Access | MCP Server | Tools | Used By | Cost |
|-------------|-------------|------------|-------|---------|------|
| **Yahoo Finance** | `yfinance` (existing) | `market_price_mcp` | `get_ohlcv`, `get_quote`, `get_fundamentals`, `get_analyst_targets` | Fast Alex, Zara, Scout | Free |
| **CNN Fear & Greed** | HTTP scrape (existing) | `sentiment_mcp` | `get_fear_greed_index`, `get_market_mood` | Reid, Elena | Free |
| **SEC EDGAR** | `edgartools` (existing) | `sec_edgar_mcp` | `get_filings`, `get_insider_trades` | Deep Alex, Victoria | Free |
| **pandas-ta / numpy** | Local compute on OHLCV | `technical_mcp` | `calc_rsi`, `calc_macd`, `calc_bollinger`, `calc_atr`, `detect_support_resistance` | Zara | Free (compute) |

#### Tier 2 — Growth (paid APIs, high signal)

| Data Source | API | MCP Server | Tools | Used By | Est. Cost |
|-------------|-----|------------|-------|---------|-----------|
| **Polygon.io** | REST + WebSocket | `polygon_mcp` | `get_aggregates`, `get_options_chain`, `get_unusual_volume`, `get_snapshot` | Zara, Scout | $29–199/mo |
| **Alpha Vantage** | REST (key in .env) | `alpha_vantage_mcp` | `get_technical_indicator`, `get_earnings`, `get_sector_performance` | Zara, Reid | Free tier → $50/mo |
| **Finnhub** | REST | `finnhub_mcp` | `get_realtime_quote`, `get_earnings_calendar`, `get_recommendation_trends` | Fast Alex, Marcus | Free → $50/mo |
| **FRED (Federal Reserve)** | REST API | `fred_mcp` | `get_fed_funds_rate`, `get_cpi`, `get_yield_curve`, `get_unemployment` | Reid, Elena | Free |
| **Nasdaq Data Link (Quandl)** | REST | `quandl_mcp` | `get_commodity_prices`, `get_economic_indicators` | Reid | $0–50/mo |

#### Tier 3 — Pro / Institutional signal (higher cost, differentiation)

| Data Source | API | MCP Server | Tools | Used By | Est. Cost |
|-------------|-----|------------|-------|---------|-----------|
| **Unusual Whales** | REST | `options_flow_mcp` | `get_unusual_options`, `get_dark_pool_prints`, `get_congress_trades` | Zara, Scout | $50–200/mo |
| **Benzinga / NewsAPI** | REST | `financial_news_mcp` | `search_news`, `get_earnings_headlines` | Marcus, Deep Alex | $30–100/mo |
| **TradingView (unofficial / chart-img)** | Chart render API | `chart_mcp` | `render_chart`, `add_indicators_overlay`, `get_chart_url` | Alex UI, Zara | $0–30/mo |
| **CBOE** | Public data | `volatility_mcp` | `get_vix`, `get_vvix`, `get_put_call_ratio` | Elena, Zara | Free |
| **ETF.com / sector ETFs** | yfinance + mapping | `sector_mcp` | `get_sector_etf_performance`, `get_relative_strength` | Reid, Scout | Free |

### MCP Tool Catalog (Quant)

**File:** `backend/researcher/mcp/quant/`

```
quant/
  market_price_mcp.py      # OHLCV, quotes, volume
  technical_mcp.py         # RSI, MACD, BB, ATR, SMA/EMA, support/resistance
  options_flow_mcp.py      # IV rank, put/call, unusual activity
  macro_mcp.py             # FRED: rates, CPI, yields, GDP
  chart_mcp.py             # Render candlestick + indicator overlays → S3 URL
  volatility_mcp.py        # VIX, realized vol, beta vs SPY
  sector_mcp.py            # Sector rotation, relative strength
  quant_gateway.py         # Selects tools per query intent
```

### Example Tool Signatures

```python
# technical_mcp
calc_rsi(ticker, period=14, interval="1d") → { rsi: 68.2, signal: "overbought", history: [...] }
calc_macd(ticker) → { macd: 2.1, signal: 1.8, histogram: 0.3, crossover: "bullish" }
detect_support_resistance(ticker, lookback=90) → { support: [120, 115], resistance: [135, 142] }

# options_flow_mcp (Polygon / Unusual Whales)
get_iv_rank(ticker) → { iv_rank: 72, percentile_1y: 0.85 }
get_put_call_ratio(ticker) → { ratio: 0.82, signal: "bullish" }
get_unusual_options(ticker, min_premium=100000) → [{ strike, expiry, type, premium, sentiment }]

# chart_mcp
render_chart(ticker, indicators=["RSI", "MACD"], period="6mo") → { chart_url: "s3://...", thumbnail_url }

# macro_mcp
get_yield_curve() → { "2y": 4.2, "10y": 4.5, spread: 0.3, inverted: false }
get_fed_funds_rate() → { rate: 5.25, next_meeting: "2026-07-31", expectation: "hold" }
```

### Quant Query Routing (extends Alex Router)

| User / Agent Query | Quant tools auto-fetched |
|------------------|-------------------------|
| "Will NVDA go up?" | RSI, MACD, support/resistance, analyst targets, fear/greed |
| "Is NVDA overbought?" | RSI, Bollinger, IV rank, relative strength vs SOX |
| "What's the macro backdrop?" | Yield curve, Fed funds, CPI, VIX |
| "Options activity on TSLA" | Put/call ratio, unusual options, IV rank |
| "Show me NVDA chart" | chart_mcp render → display in chat |
| Zara debate prompt | Full technical snapshot + sector relative strength |

### Storage: `quant_snapshots` Table

Structured numbers (not vectors) for fast agent access without re-fetching:

```sql
CREATE TABLE quant_snapshots (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID REFERENCES users(id),
  ticker VARCHAR(10) NOT NULL,
  snapshot_type VARCHAR(30),  -- 'technical', 'options', 'macro', 'chart'
  data JSONB NOT NULL,        -- structured indicator values
  chart_url TEXT,             -- S3 URL if chart rendered
  source VARCHAR(50),         -- 'polygon', 'yfinance', 'fred'
  fetched_at TIMESTAMPTZ DEFAULT NOW(),
  expires_at TIMESTAMPTZ      -- cache TTL (e.g. 15 min for quotes, 24h for macro)
);
```

### Who Consumes Quant Intelligence

| Consumer | What it gets |
|----------|-------------|
| **Zara (Quant agent)** | Full technical + options snapshot in every debate |
| **Alex chat** | Auto-attached when router detects `price_opinion` or `technical` intent |
| **Marcus / Victoria** | Key levels (support/resistance) as evidence |
| **Reid (Macro)** | FRED data + sector ETF performance |
| **Elena (Risk)** | VIX, beta, IV rank, position sizing inputs |
| **Scout agent** | Unusual volume + momentum screeners |
| **Trading floor intelligence** | Quant snapshot IDs referenced in debate chunks |
| **/observe** | MCP call counts, latency, data freshness |

### Deliverables (P13)

- `backend/researcher/mcp/quant/*` — MCP servers listed above
- `backend/agents/trading/tools/quant_context.py` — debate engine integration
- Extend `query_router.py` with `quant_tools_needed: list[str]`
- `quant_snapshots` table + cache layer (15min quotes, 24h macro)
- Chart rendering → S3 with CloudFront URL in chat response
- Zara prompt upgrade to cite specific numbers from MCP tools
- `/observe` panel: Quant MCP usage + data freshness

**Effort:** 4–5 days (Tier 1 only: 2–3 days)

---

## Trading Floor Intelligence Vector Store (P14)

**Goal:** Store the **collective intelligence of every trading floor debate** in a dedicated vector store — separate from `research_vectors` (user chat / research). This becomes the institutional memory of how agents reasoned, disagreed, and decided.

### Why a Separate Store

| `research_vectors` | `trading_floor_intelligence` |
|--------------------|------------------------------|
| User questions + Alex answers | Agent debates + votes + executor decisions |
| Conversational tone | Structured bull/bear/quant arguments |
| Per session | Per debate cycle per ticker |
| Written by chat ingest | Written by debate_engine after each debate |
| Global + user scoped | User scoped + ticker scoped |

Keeping them separate prevents chat noise from diluting trading debate retrieval and allows different chunking strategies.

### Architecture

```
debate_engine.run_debate(ticker)
        │
        ├── Marcus vote + reasoning
        ├── Victoria vote + reasoning
        ├── Zara vote + reasoning (includes quant snapshot refs)
        ├── Reid vote + reasoning
        ├── Elena vote + reasoning
        └── Executor synthesis + final action
                │
                ▼
    debate_ingest_pipeline.chunk_and_embed()
                │
                ▼
    trading_floor_intelligence table (pgvector)
                │
        ┌───────┴────────┐
        ▼                ▼
   AI RAG engine    Historian agent
   (trading Qs)     (next debate context)
        │                │
        ▼                ▼
   Alex chat          Zara/Marcus prompts
   "What did agents   "Last debate: Marcus
    decide on NVDA?"   argued BUY citing RSI 68..."
```

### Schema

```sql
CREATE TABLE trading_floor_intelligence (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID REFERENCES users(id) NOT NULL,
  simulation_id UUID REFERENCES trading_simulations(id),
  debate_id UUID NOT NULL,              -- links all chunks from one debate
  ticker VARCHAR(10) NOT NULL,
  agent_name VARCHAR(50),               -- 'marcus', 'victoria', 'zara', 'reid', 'elena', 'executor', 'collective'
  chunk_type VARCHAR(30) NOT NULL,      -- 'vote', 'reasoning', 'evidence', 'counter', 'synthesis', 'quant_ref'
  content TEXT NOT NULL,
  embedding vector(384),
  metadata JSONB DEFAULT '{}',
  -- metadata examples:
  -- { "action": "BUY", "confidence": 82, "final": true, "trade_id": "uuid",
  --   "quant_snapshot_id": "uuid", "data_sources": ["polygon", "yfinance"] }
  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX tfi_user_ticker_idx ON trading_floor_intelligence (user_id, ticker, created_at DESC);
CREATE INDEX tfi_debate_idx ON trading_floor_intelligence (debate_id);
CREATE INDEX tfi_embedding_idx ON trading_floor_intelligence
  USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);
```

### Chunking Strategy (Debate-Specific)

Each debate produces ~8–12 chunks:

| Chunk | agent_name | chunk_type | Content |
|-------|-----------|------------|---------|
| 1 | marcus | vote | "BUY NVDA 82% — AI capex cycle intact" |
| 2 | marcus | reasoning | Full bull argument (500 tokens) |
| 3 | marcus | evidence | Key evidence bullets + data sources used |
| 4 | victoria | vote + reasoning | Bear counter-argument |
| 5 | zara | vote + quant_ref | Quant analysis citing RSI, MACD, IV |
| 6 | reid | reasoning | Macro context |
| 7 | elena | reasoning | Risk assessment + position sizing |
| 8 | executor | synthesis | Final decision + rationale |
| 9 | collective | synthesis | One-paragraph debate summary for fast retrieval |

### Ingest Pipeline

**File:** `backend/agents/trading/intelligence/debate_ingest.py`

```python
def ingest_debate(debate_result: DebateResult, user_id: str, simulation_id: str):
    debate_id = str(uuid4())
    chunks = []

    for vote in debate_result.votes:
        chunks.append(chunk_vote(vote, debate_id, user_id, ticker))
        chunks.append(chunk_reasoning(vote, debate_id, user_id, ticker))
        if vote.key_evidence:
            chunks.append(chunk_evidence(vote, debate_id, user_id, ticker))

    chunks.append(chunk_executor_synthesis(debate_result, debate_id, user_id))
    chunks.append(chunk_collective_summary(debate_result, debate_id, user_id))

    for chunk in chunks:
        embedding = embed_text(chunk.content)
        INSERT INTO trading_floor_intelligence (...)

    # Link to simulated_trades
    UPDATE simulated_trades SET debate_vector_id = debate_id WHERE id = trade_id
```

### Retrieval Patterns

| Query | Retrieval strategy |
|-------|-------------------|
| Alex: "What did agents decide on NVDA?" | `WHERE user_id AND ticker='NVDA' AND chunk_type='synthesis' ORDER BY created_at DESC LIMIT 3` |
| Historian (pre-debate) | Semantic search on ticker + last 5 debate collective summaries |
| RL evaluator | Fetch vote chunks + outcomes for accuracy attribution |
| Observe: "Agent reasoning transparency" | Browse by debate_id |
| Scout: "How did we analyze similar stocks?" | Cross-ticker semantic search |

### Integration with Other Systems

```
trading_floor_intelligence
    ├── AI RAG engine (route=trading queries)
    ├── Historian agent (pre-debate injection)
    ├── Alex synthesizer (proactive comparison)
    ├── RL evaluator (vote → outcome attribution)
    ├── quant_snapshots (cross-reference via metadata.quant_snapshot_id)
    ├── portfolio_digests (complementary, not duplicated)
    └── /observe (debate intelligence browser)
```

### Performance Attribution Enhancement

Extend `agent_observations.data_used` when debate chunks are retrieved:

```json
{
  "data_used": [
    { "source": "trading_floor_intelligence", "debate_id": "uuid", "agent": "marcus", "relevance": 0.91 },
    { "source": "quant_snapshot", "ticker": "NVDA", "indicators": ["RSI", "MACD"] },
    { "source": "portfolio_digest", "ticker": "NVDA", "dimension": "news" }
  ]
}
```

Visible on `/observe` → "Context sources that influenced this agent's vote."

### Deliverables (P14)

- `trading_floor_intelligence` table + indexes in `aurora_warmup.py`
- `backend/agents/trading/intelligence/debate_ingest.py` — chunk + embed pipeline
- `backend/agents/trading/intelligence/debate_retrieval.py` — semantic + structured search
- Hook into `debate_engine.store_trade()` — ingest after every debate
- Extend AI `rag_engine.py` — third vector source (alongside research_vectors + portfolio_digests)
- `/observe` panel: Debate Intelligence Browser (search by ticker, agent, date)
- `GET /api/trading/intelligence?ticker=NVDA` — frontend debate memory API

**Effort:** 3–4 days

---

## Async Deep Research Sub-Agents (P15)

**Goal:** Replace the current **single sequential deep agent** (one Bedrock agent, 20 turns, 2–5 min) with a **parallel sub-agent orchestrator** that decomposes deep queries into independent tasks, runs them asynchronously, streams partial results to the user, and synthesizes when complete — dramatically improving **time-to-first-insight** and **total response time**.

### Problem Today

| Metric | Current deep research | Target with P15 |
|--------|----------------------|-----------------|
| Architecture | 1 agent, sequential tool calls | 4–6 sub-agents, parallel |
| Time to first content | 30–90s (waits for full agent loop) | **3–8s** (first sub-agent streams) |
| Total response time | 120–300s | **45–90s** (parallel wall-clock) |
| User experience | Spinner → full dump | Progressive sections appearing live |
| Observability | Single `ResearchLatency` metric | Per-stage + per-sub-agent breakdown |

### Architecture

```
User query: "Jensen Huang said AI demand is insatiable — what does it mean for NVDA?"
        │
        ▼
┌───────────────────┐
│  Alex Query Router │  route = deep (200ms)
└─────────┬─────────┘
          │
          ▼
┌───────────────────┐
│ Deep Orchestrator  │  Nova Lite decomposes into sub-tasks (300ms)
│ (new)              │
└─────────┬─────────┘
          │
    ┌─────┼─────┬─────────┬──────────┬──────────┐
    │     │     │         │          │          │
    ▼     ▼     ▼         ▼          ▼          ▼
  SEC   News  Earnings  Quant    Sentiment  Macro
 Agent  Agent  Agent    Agent     Agent     Agent
    │     │     │         │          │          │
    └─────┴─────┴────┬────┴──────────┴──────────┘
                     │  asyncio.gather / ThreadPoolExecutor
                     │  each sub-agent streams partial → SSE
                     ▼
            ┌─────────────────┐
            │ Partial Results  │  → user sees sections as they complete
            │ Buffer           │
            └────────┬────────┘
                     │ all done OR timeout (90s) with partial
                     ▼
            ┌─────────────────┐
            │ Alex Synthesizer │  hedge-fund memo merging all sections
            └────────┬────────┘
                     │
                     ▼
            ingest + query_latency_metrics
```

### Deep Sub-Agent Roster

| Sub-Agent | Task scope | Tools / MCP | Typical latency | Streams first? |
|-----------|-----------|-------------|-----------------|----------------|
| **SEC Agent** | 10-K/10-Q risks, insider trades, material events | `sec_edgar_mcp` | 15–30s | No (usually slower) |
| **News Agent** | Headlines, CEO quotes, event verification | `financial_news_mcp`, Playwright | 8–15s | **Yes — often first** |
| **Earnings Agent** | Last earnings, guidance, consensus, surprises | `earnings_mcp`, yfinance | 10–20s | Yes |
| **Quant Agent** | RSI, MACD, support/resistance, IV rank | `technical_mcp`, `options_flow_mcp` | 5–10s | **Yes — fastest** |
| **Sentiment Agent** | Analyst ratings, fear/greed, social tone | `sentiment_mcp`, Finnhub | 8–12s | Yes |
| **Macro Agent** | Rates, sector context, peer comparison | `fred_mcp`, `sector_mcp` | 10–15s | No |

Orchestrator picks **3–5 sub-agents** per query based on intent — not all six every time.

### Orchestrator Decomposition

**File:** `backend/researcher/deep_orchestrator.py`

```python
class DeepSubTask(BaseModel):
    agent_id:   str           # 'sec', 'news', 'earnings', 'quant', 'sentiment', 'macro'
    topic:      str           # specific sub-question
    priority:   int           # 1 = stream first
    timeout_s:  int = 45
    tools:      list[str]

class DeepOrchestratorResult(BaseModel):
    query_id:       str
    sub_tasks:      list[DeepSubTask]
    partial_results: dict[str, str]   # agent_id → raw research
    timings:        dict[str, float]  # agent_id → seconds
    first_token_ms: int
    total_ms:       int
    synthesis:      str
```

**Example decomposition** for *"Jensen Huang said AI demand is insatiable — NVDA?"*:

```json
[
  { "agent_id": "news",     "topic": "Verify Jensen Huang GTC keynote quotes on AI demand", "priority": 1 },
  { "agent_id": "quant",    "topic": "NVDA technical snapshot and price context",         "priority": 1 },
  { "agent_id": "earnings", "topic": "NVDA latest earnings, guidance, consensus",         "priority": 2 },
  { "agent_id": "sec",      "topic": "NVDA recent 10-K risk factors and MD&A on AI",      "priority": 2 },
  { "agent_id": "sentiment","topic": "Analyst ratings and sentiment shift post-GTC",      "priority": 2 }
]
```

### Parallel Execution Model

```python
async def run_deep_parallel(query, user_id, session_id, on_partial):
    sub_tasks = decompose_deep_query(query)
    query_id  = str(uuid4())
    t0        = time.monotonic()

    async def run_sub(task: DeepSubTask):
        t_start = time.monotonic()
        result  = await SUB_AGENTS[task.agent_id].run(task.topic, user_id)
        elapsed = time.monotonic() - t_start
        await on_partial(task.agent_id, result, elapsed)  # SSE to frontend
        return task.agent_id, result, elapsed

    # Run all sub-agents concurrently
    results = await asyncio.gather(
        *[run_sub(t) for t in sub_tasks],
        return_exceptions=True
    )

    synthesis = await synthesizer.merge_deep(query, results)
    total_ms  = int((time.monotonic() - t0) * 1000)

    await record_query_latency(query_id, user_id, route='deep', ...)
    return synthesis
```

**Key behaviors:**
- Sub-agents are **independent** — one failure doesn't block others
- **Partial SSE events** fire as each sub-agent completes (`type: 'sub_agent_done'`)
- Synthesizer runs on **available results** if any sub-agent times out at 45s
- Quant + News agents prioritized to stream first (lowest latency)

### SSE Stream Events (Frontend)

```typescript
// New event types for /api/alex/chat when route=deep
{ type: 'routing',        route: 'deep', sub_agents: ['news','quant','earnings','sec'] }
{ type: 'sub_agent_start', agent: 'quant', label: 'Technical Analysis' }
{ type: 'sub_agent_done',  agent: 'quant', elapsed_ms: 6200, preview: 'RSI 68...' }
{ type: 'sub_agent_start', agent: 'news',  label: 'News Verification' }
{ type: 'sub_agent_done',  agent: 'news',  elapsed_ms: 11400, preview: 'Jensen Huang at GTC...' }
{ type: 'synthesis_start' }
{ type: 'token',           content: '...' }   // final memo streams
{ type: 'done',            total_ms: 67000, first_token_ms: 6200 }
```

**User sees:** Progress panel with checkmarks per sub-agent, then the synthesized memo streams.

### Latency Observability

Every query (fast, deep, multi, portfolio, trading) records a full timing breakdown.

#### New Table: `query_latency_metrics`

```sql
CREATE TABLE query_latency_metrics (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  query_id VARCHAR(36) NOT NULL,
  user_id UUID REFERENCES users(id),
  session_id VARCHAR(36),
  query TEXT NOT NULL,
  route VARCHAR(20) NOT NULL,           -- fast, deep, multi, portfolio, trading, reject
  intent VARCHAR(50),
  entities JSONB DEFAULT '[]',

  -- Stage timings (milliseconds)
  router_ms INTEGER DEFAULT 0,
  rag_ms INTEGER DEFAULT 0,
  first_token_ms INTEGER,               -- time until user sees first content
  sub_agent_ms JSONB DEFAULT '{}',      -- { "news": 11400, "quant": 6200, "sec": 28000 }
  synthesis_ms INTEGER DEFAULT 0,
  ingest_ms INTEGER DEFAULT 0,
  guardrail_ms INTEGER DEFAULT 0,
  total_ms INTEGER NOT NULL,

  -- Sub-agent metadata (deep route only)
  sub_agents_planned JSONB DEFAULT '[]',
  sub_agents_completed JSONB DEFAULT '[]',
  sub_agents_failed JSONB DEFAULT '[]',

  -- Quality signals
  success BOOLEAN DEFAULT true,
  partial BOOLEAN DEFAULT false,        -- true if timed out with incomplete sub-agents
  token_count INTEGER DEFAULT 0,
  cost_usd NUMERIC(10,6) DEFAULT 0,

  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX qlm_user_created_idx ON query_latency_metrics (user_id, created_at DESC);
CREATE INDEX qlm_route_idx ON query_latency_metrics (route, created_at DESC);
```

#### Recording Hook

**File:** `backend/researcher/latency_tracker.py`

```python
class LatencyTracker:
    def __init__(self, query_id, user_id, session_id, query, route):
        self.stages = {}
        self.t0 = time.monotonic()

    def mark(self, stage: str):
        self.stages[stage] = int((time.monotonic() - self.t0) * 1000)

    def mark_sub_agent(self, agent_id: str, elapsed_ms: int, success: bool):
        ...

    async def flush(self):
        INSERT INTO query_latency_metrics (...)
        cloudwatch.put_metric('QueryLatency', total_ms, dimensions={'Route': route})
        cloudwatch.put_metric('TimeToFirstToken', first_token_ms, dimensions={'Route': route})
```

Called from:
- `/api/alex/chat` (all routes)
- `deep_orchestrator.py` (per sub-agent)
- `synthesizer.py` (synthesis stage)

#### CloudWatch Metrics (supplement Aurora)

| Metric | Dimensions | Purpose |
|--------|-----------|---------|
| `AlexAI/QueryLatency` | Route, Intent | P50/P95 total response time |
| `AlexAI/TimeToFirstToken` | Route | User-perceived speed |
| `AlexAI/SubAgentLatency` | AgentId | Per sub-agent performance |
| `AlexAI/DeepPartialRate` | — | % of deep queries completing with timeout |

### Observability UI — Query Response Speed Panel

**New `/observe` panels (P15):**

| Panel | What it shows | Source |
|-------|--------------|--------|
| **Query Response Speed (7d)** | P50 / P95 / P99 total_ms by route (fast/deep/multi) | `query_latency_metrics` |
| **Time to First Token** | Line chart — how fast users see first content | `first_token_ms` |
| **Deep Sub-Agent Breakdown** | Stacked bar: news / quant / sec / earnings avg ms | `sub_agent_ms` |
| **Slowest Queries** | Table: query preview, route, total_ms, bottleneck stage | `query_latency_metrics` ORDER BY total_ms DESC |
| **Partial Completion Rate** | % deep queries that timed out with incomplete sub-agents | `partial = true` |
| **Route Latency Comparison** | fast avg 8s vs deep avg 67s vs multi avg 120s | aggregated |
| **Latency vs Cost Scatter** | total_ms vs cost_usd — identify expensive slow queries | join with `agent_observations` |

**Example slow query row on /observe:**

```
Query: "Jensen Huang AI demand NVDA"
Route: deep | Total: 67.2s | First token: 6.2s
  Router: 0.2s | RAG: 1.1s | Quant: 6.2s | News: 11.4s | SEC: 28.0s | Synthesis: 4.8s
Bottleneck: SEC Agent (28s) — consider caching 10-K sections
```

### Deliverables (P15)

| File | Purpose |
|------|---------|
| `backend/researcher/deep_orchestrator.py` | Decompose + parallel sub-agent execution |
| `backend/researcher/sub_agents/sec_agent.py` | SEC-focused sub-agent |
| `backend/researcher/sub_agents/news_agent.py` | News + Playwright sub-agent |
| `backend/researcher/sub_agents/earnings_agent.py` | Earnings data sub-agent |
| `backend/researcher/sub_agents/quant_agent.py` | Technical snapshot sub-agent |
| `backend/researcher/sub_agents/sentiment_agent.py` | Sentiment sub-agent |
| `backend/researcher/sub_agents/macro_agent.py` | Macro context sub-agent |
| `backend/researcher/latency_tracker.py` | Stage timing + Aurora flush |
| `query_latency_metrics` table | Aurora schema |
| `/api/observe` extension | Query speed panels |
| `/api/alex/chat` SSE | `sub_agent_start`, `sub_agent_done` events |
| Frontend progress UI | Sub-agent checklist in chat |

**Effort:** 4–5 days (sub-agents + latency observability together)

**Depends on:** P1 (router), P3 (synthesizer), P7 (MCP servers for sub-agents)

---

## RAGAS Evaluation Framework (P17)

> **Goal:** Measure and gate RAG answer quality — not vibes. Aligns with Archemy-style eval discipline (LangSmith + RAGAS) applied to Alex's pgvector + Bedrock pipeline.

### Current State

| Asset | Status |
|-------|--------|
| `scripts/tests/test_ragas.py` | ✅ Exists — 5 NVIDIA benchmark queries, Bedrock Nova Pro answers |
| Metrics computed | Answer relevancy, faithfulness, context recall, hallucination rate |
| Report output | `scripts/tests/ragas_report.json` (local file only) |
| `ragas_evaluations` table | ✅ DDL in `aurora_warmup.py` — not written by script yet |
| CI / scheduled run | ❌ Not in GitHub Actions |
| `/observe` UI | ❌ No RAGAS panel |
| Deploy gate | ❌ No threshold block on researcher/ingest deploy |

### Benchmark Targets (from `test_ragas.py`)

| Metric | Target | Gate threshold (deploy block) |
|--------|--------|-------------------------------|
| Answer Relevancy | > **0.87** | < 0.85 fails |
| Faithfulness | > **0.91** | < 0.88 fails |
| Context Recall | > **0.70** | informational only |
| Hallucination Rate | < **5%** | > 8% fails |
| Overall Score | > **0.85** (grade A) | `passed = false` blocks optional deploy |

### Evaluation Pipeline

```
5 benchmark queries (TEST_QUERIES)
      ↓
POST /search (API Gateway → pgvector)     ← tests retrieval
      ↓
Bedrock Nova Pro answer (temp 0.1)        ← tests generation
      ↓
compute_answer_relevancy()
compute_faithfulness()
compute_context_recall()
compute_hallucination_rate()
      ↓
Per-query + aggregate scores
      ↓
INSERT ragas_evaluations (Aurora)         ← durable history
      ↓
ragas_report.json + eval_report.json      ← CI artifact
      ↓
/observe RAGAS panel + optional deploy gate
```

### Phase 1 — Upgrade `test_ragas.py` (Day 1)

| Task | Detail |
|------|--------|
| Aurora persist | After each run, `INSERT` aggregate + per-query rows into `ragas_evaluations` via RDS Data API |
| `passed` flag | `passed = (avg_relevancy >= 0.85 AND avg_faithfulness >= 0.88 AND avg_hallucination < 0.08)` |
| `gate` column | `'ci'`, `'weekly'`, `'pre_deploy'`, `'manual'` |
| Exit code | `sys.exit(1)` if `passed = false` — enables CI gate |
| Env config | `SEARCH_API`, `API_KEY`, `BEDROCK_MODEL` from env / SSM — remove hardcoded secrets |
| Optional: official RAGAS | Evaluate `ragas` pip package with Bedrock judge for parity with Archemy; keep lightweight heuristics as fast smoke path |

**Extend `ragas_evaluations` schema (if needed):**

```sql
-- Existing columns sufficient; optional additions:
ALTER TABLE ragas_evaluations ADD COLUMN IF NOT EXISTS
  hallucination_rate NUMERIC(4,3),
  query_count INT DEFAULT 5,
  report_json JSONB;  -- full per-query breakdown
```

### Phase 2 — `backend/eval/ragas_runner.py` (Day 1–2)

Refactor eval logic into importable module (callable from Lambda, CI, and CLI):

| File | Purpose |
|------|---------|
| `backend/eval/ragas_runner.py` | Core metrics + `run_evaluation(gate: str) -> EvalResult` |
| `backend/eval/benchmark_queries.py` | `TEST_QUERIES` — extensible per ticker/sector |
| `backend/eval/db.py` | `save_eval_result()`, `get_latest_eval()`, `get_eval_history(7d)` |
| `scripts/tests/test_ragas.py` | Thin CLI wrapper → `ragas_runner.run_evaluation('manual')` |

```python
class EvalResult(BaseModel):
    answer_relevancy:   float
    faithfulness:       float
    context_recall:     float
    hallucination_rate: float
    overall_score:      float
    passed:             bool
    gate:               str
    evaluated_at:       datetime
```

### Phase 3 — CI + Scheduled Eval (Day 2)

| Trigger | Workflow | Action |
|---------|----------|--------|
| **PR / push to main** | `.github/workflows/ci.yml` | Run `test_ragas.py` after syntax check (optional: `continue-on-error: true` until baseline stable) |
| **Weekly** | `.github/workflows/ragas_eval.yml` (new) | Sunday 6 AM ET — full eval, upload `ragas_report.json` artifact |
| **Pre-deploy researcher** | `deploy_researcher.yml` | Run RAGAS smoke (3 queries) — block if `passed = false` |
| **Unified harness** | `scripts/eval_suite.sh` (new) | RAGAS + `test_planner.py` + `test_multi_agent.py` + `test_trading.sh` → `eval_report.json` |

```yaml
# .github/workflows/ragas_eval.yml (sketch)
name: Alex RAGAS Weekly Eval
on:
  schedule:
    - cron: '0 11 * * 0'   # Sunday 6 AM ET
  workflow_dispatch:
jobs:
  ragas:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v4
        with:
          python-version: "3.12"
      - run: pip install boto3 pydantic
      - run: python3 scripts/tests/test_ragas.py
        env:
          SEARCH_API: ${{ secrets.ALEX_SEARCH_API }}
          AWS_ACCESS_KEY_ID: ${{ secrets.AWS_ACCESS_KEY_ID }}
          AWS_SECRET_ACCESS_KEY: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
      - uses: actions/upload-artifact@v4
        with:
          name: ragas-report
          path: scripts/tests/ragas_report.json
```

### Phase 4 — Lambda + EventBridge (Optional, Day 2–3)

| Resource | Purpose |
|----------|---------|
| `alex-ragas-eval` Lambda | Weekly scheduled eval in AWS (same code as CI, runs inside VPC if needed) |
| EventBridge `alex-ragas-weekly` | `cron(0 11 ? * SUN *)` — mirrors GitHub schedule |
| CloudWatch alarm | `passed = false` → SNS email to ops |

Use Lambda if GitHub secrets can't reach production search API; otherwise CI-only is sufficient for MVP.

### Phase 5 — Observability UI (Day 2–3)

**New `/observe` panels (P17):**

| Panel | What it shows | Source |
|-------|--------------|--------|
| **RAG Quality Scorecard (7d)** | Latest avg relevancy, faithfulness, hallucination %, overall grade | `ragas_evaluations` latest |
| **RAGAS Trend Chart** | Line chart of overall_score over last 30 runs | `ragas_evaluations.evaluated_at` |
| **Per-Query Breakdown** | Table: question, relevancy, faithfulness, passed | `report_json` or latest run |
| **Eval Gate Status** | Green/red — last CI run passed? | latest `gate='ci'` row |

**API:**

| Route | Phase |
|-------|-------|
| `GET /api/observe/ragas` | P17 — latest + 7d history |
| `GET /api/observe/ragas/[id]` | P17 — single run detail |

### Phase 6 — Post-RAG Engine Integration (After P2)

Once `rag_engine.py` ships (P2), extend RAGAS to test the **full production path**:

| Test path | What it validates |
|-----------|-------------------|
| **Path A (today)** | Search API → Bedrock — retrieval + generation |
| **Path B (P2+)** | `/api/alex/chat` route=fast — router + RAG + synthesizer end-to-end |
| **Path C (P3+)** | Deep route — includes chunked ingest quality |

Add `route` column to eval runs: `'search_api'`, `'chat_fast'`, `'chat_deep'`.

### Deliverables (P17)

| File | Purpose |
|------|---------|
| `backend/eval/ragas_runner.py` | Importable eval engine |
| `backend/eval/benchmark_queries.py` | 5+ standard queries (extensible) |
| `backend/eval/db.py` | Aurora persist + history |
| `scripts/tests/test_ragas.py` | CLI entrypoint (refactored) |
| `scripts/eval_suite.sh` | Unified regression harness |
| `.github/workflows/ragas_eval.yml` | Weekly scheduled eval |
| `.github/workflows/ci.yml` | Add RAGAS smoke on PR (optional gate) |
| `deploy_researcher.yml` | Pre-deploy eval gate |
| `frontend/app/api/observe/ragas/route.ts` | RAGAS history API |
| `frontend/app/observe/page.tsx` | RAG quality panels |
| `alex-ragas-eval` Lambda (optional) | AWS scheduled runner |
| EventBridge `alex-ragas-weekly` (optional) | Weekly trigger |

**Effort:** 2–3 days

**Depends on:** P2 (RAG engine — for Path B/C integration); Path A can ship immediately on current search API

**Blocks:** Confident RAG deploys; production engineering CI gates (Pillar 6)

### RAGAS + Other Phases

| Phase | How RAGAS connects |
|-------|-------------------|
| **P2** | Eval Path B — test hybrid retrieval + MMR after RAG engine ships |
| **P3** | Add queries that test chunked ingest faithfulness |
| **P11** | RAG Performance panel complements RAGAS scorecard |
| **P15** | Add deep-route eval queries; track if sub-agent timeouts hurt faithfulness |
| **P8** | Trading uses outcome-based eval; RAGAS is the AI-side analogue |

---

## Aurora Schema Master List

---

| Table | Changes |
|-------|---------|
| `research_vectors` | Add: `user_id`, `session_id`, `chunk_index`, `query`, `chunk_type` |
| `research_sessions` | Add: `route`, `intent`, `entities`; populate `vector_id` |
| `simulated_trades` | Add: `target_price`, `stop_loss`, `realized_pnl`, `outcome`, `trigger` |
| `chat_sessions` | Add unique index on `(user_id, session_id)` |
| `agent_observations` | Add DDL to warmup (currently missing) |

### New Tables

| Table | System | Purpose |
|-------|--------|---------|
| `portfolio_digests` | Research | Per-stock research cards (✅ already created) |
| `scout_candidates` | Trading | Scout agent discoveries |
| `rl_weights` | Trading | Learned agent vote weights |
| `trading_events` | Trading | Observability audit log |
| `session_metadata` | AI | Chat session tracking |
| `rag_attributions` | AI | RAG chunk usage logging |
| `trading_floor_intelligence` | Trading | Debate collective memory (pgvector) |
| `quant_snapshots` | Quant | Structured indicator/chart cache |
| `query_latency_metrics` | AI | Per-query response speed breakdown |
| `ragas_evaluations` | AI / Eval | RAGAS run history + deploy gate status (✅ DDL exists) |
| `cost_daily_reports` | FinOps | Alex-synthesized daily cost rollup + email payload (P21) |

### All tables in `aurora_warmup.py` after implementation: **26 tables**

---

## API Master List

### New APIs

| Route | System | Phase |
|-------|--------|-------|
| `POST /api/alex/chat` (SSE) | AI | P1 |
| `GET /api/alex/sessions` | AI | P2 |
| `GET /api/alex/sessions/[id]` | AI | P2 |
| `GET /api/alex/suggestions` | AI | P2 |
| `GET/POST /api/trading/config` | Trading | P5 |
| `GET /api/trading/simulation` | Trading | P4 |
| `GET /api/trading/scout` | Trading | P9 |
| `GET /api/trading/performance` | Trading | P8 |
| `GET /api/trading/intelligence` | Trading | P14 |
| `GET /api/quant/snapshot` | Quant | P13 |
| `GET /api/observe/latency` | AI | P15 (optional dedicated endpoint) |
| `GET /api/observe/ragas` | AI / Eval | P17 |
| `GET /api/observe/ragas/[id]` | AI / Eval | P17 |
| `GET /api/costs?report=daily` | FinOps | P21 |

### Extended APIs

| Route | Changes | Phase |
|-------|---------|-------|
| `GET /api/observe` | +simulation, P&L, RL, scout, events, RAG, routing, **RAGAS** | P11, P17 |
| `GET /api/costs` | +latest `cost_daily_reports` synthesis + JSON breakdown | P21 |
| `GET /api/trading` | +simulation summary, RL weights | P4, P8 |
| `GET /api/portfolio-research` | (existing, no changes) | — |

### Deprecated APIs

| Route | Replaced By |
|-------|-------------|
| `POST /api/research` | `/api/alex/chat` |
| `POST /api/research/stream` | `/api/alex/chat` |
| `POST /api/research/deep` | `/api/alex/chat` |
| `POST /api/research/deep/stream` | `/api/alex/chat` |

---

## Frontend Master List

| Page / Component | Changes | Phase |
|-----------------|---------|-------|
| `/research` | Remove toggle, unified chat, router reasoning, hydrate sessions | P1, P2 |
| `AlexChat.tsx` (new) | Reusable chat with markdown + reasoning steps | P1 |
| `ChatContext.tsx` | Aurora session sync | P2 |
| `/trading` | Simulation tab, replay, agent settings, scout panel, RL badges, intelligence browser | P4, P5, P8, P9, P14 |
| `/research` | Quant chart embeds + deep sub-agent progress checklist | P13, P15 |
| `/observe` | 10+ new panels + **RAGAS scorecard** + **Daily Cost Report** (P21) | P11, P17, P21 |
| `/portfolio` | Agent recommendation badge per holding, link to trading | P6 |
| `/dashboard` | Simulation summary card, contextual Alex suggestions, link to daily cost report | P3, P4, P21 |
| `Navbar` | Add Trading + Observe links | P4 |

---

## Infrastructure Policy (Terraform-First)

**Standing rule:** Infrastructure is **always** updated via Terraform. This applies to every phase (including P21 cost-agent, P5 trading schedules, P17 RAGAS Lambda, DLQs, IAM, EventBridge, SSM parameter resources, etc.).

### What MUST go through Terraform

| Category | Examples | Module(s) |
|----------|----------|-----------|
| **Compute definitions** | New/updated Lambda functions, timeouts, memory, env vars, permissions | `6_agents`, `9_trading_floor`, `3_ingestion` |
| **Scheduling** | EventBridge Scheduler rules, cron expressions, targets | `6_agents`, `9_trading_floor` |
| **Messaging** | SQS queues, DLQs, event source mappings | `6_agents`, `9_trading_floor` |
| **Networking** | VPC, subnets, ALB, security groups | `0_vpc`, `4_researcher` |
| **Data** | Aurora cluster, Secrets Manager | `5_database` |
| **IAM** | Roles, policies, Lambda permissions | `1_permissions`, per-module |
| **Observability** | CloudWatch alarms, log groups, dashboards | `7_guardrails`, per-module |
| **Config** | SSM parameters (as resources), API Gateway | `9_trading_floor`, `3_ingestion` |
| **ML** | SageMaker endpoints | `2_sagemaker` |

### What deploy scripts do (code only — not infra)

| Script | Allowed action | Not allowed |
|--------|----------------|-------------|
| `backend/researcher/deploy.sh` | Docker build → ECR push → ECS rolling deploy | Create ECS cluster/service from scratch |
| `scripts/deploy_trading.sh` | Zip → S3 → `update-function-code` on existing Lambdas | `create-function`, new IAM roles |
| `scripts/deploy_ingest.sh` | Package + update ingest Lambda code | New API Gateway routes without TF |
| `backend/agents/package.sh` | Build `.zip` artifacts for Terraform `filename` | Register Lambdas outside TF |

### Standard infra change workflow

```
1. Edit Terraform in terraform/{module}/main.tf (+ variables.tf if needed)
2. terraform plan  (PR) / terraform apply  (deploy)
3. Package application code (package.sh / deploy_*.sh) if Lambda/ECS code changed
4. terraform apply again if zip paths or env vars reference new artifacts
5. scripts/health_check.sh + phase tests
6. Document in Alex_report.md §33 — include terraform module path
```

### Anti-patterns (do not do)

- `aws lambda create-function` for new agents → add `aws_lambda_function` in TF
- `aws scheduler create-schedule` in shell → add `aws_scheduler_schedule` in TF
- Manual Console changes to IAM, EventBridge, or SQS → export to TF or revert
- `start_session.sh` creating permanent resources → session script may **enable/disable** TF-managed schedules and **deploy code** only

**P21 example:** `alex-cost-agent` Lambda, EventBridge `alex-cost-agent-daily`, SES env vars, and Lambda permissions are all defined in `terraform/6_agents/main.tf` — not created via CLI.

---

## Infrastructure Master List

> **All rows below:** implement resource definitions in Terraform first; use deploy scripts only for application code updates.

| Resource | Action | Phase | Terraform module |
|----------|--------|-------|------------------|
| `alex-trading-orchestrator` Lambda | Update: context_builder, trade_executor | P4, P6 | `9_trading_floor` |
| `alex-debate-agent` Lambda | Update: dynamic RL weights, richer context | P6, P8 | `9_trading_floor` |
| `alex-trade-evaluator` Lambda | **New** — daily outcome scoring | P8 | `9_trading_floor` |
| `alex-trading-observer` Lambda | **New** — daily digest | P12 | `9_trading_floor` |
| `alex-sentinel` Lambda | **New** — hourly stop-loss check | P9 | `9_trading_floor` |
| ECS researcher service | Update: router, synthesizer, RAG, MCP, quant MCP, deep orchestrator | P1–P3, P7, P13, P15 | `4_researcher` |
| `alex-ingest` Lambda | Update: user-scoped vectors | P3 | `3_ingestion` |
| `alex-debate-ingest` (in debate Lambda) | **New** — trading_floor_intelligence writer | P14 | `9_trading_floor` |
| EventBridge: `alex-trading-auto` | **Add** — debate schedule | P5 | `9_trading_floor` |
| EventBridge: `alex-trade-evaluator` | **Add** — daily 5PM ET | P8 | `9_trading_floor` |
| EventBridge: `alex-trading-observer` | **Add** — daily 4:30PM ET | P12 | `9_trading_floor` |
| EventBridge: `alex-sentinel` | **Add** — hourly | P9 | `9_trading_floor` |
| EventBridge: `alex-ragas-weekly` | **Add** — Sunday 6 AM ET (optional) | P17 | `6_agents` |
| `alex-ragas-eval` Lambda | **New** — scheduled RAGAS runner (optional) | P17 | `6_agents` |
| `alex-cost-agent` Lambda | **New** — replaces `alex-cost-monitor`; daily FinOps report + email | P21 | `6_agents` |
| EventBridge: `alex-cost-agent-daily` | **Update** — 7 AM ET → `alex-cost-agent` | P21 | `6_agents` |
| `alex-cost-monitor` Lambda | **Deprecate** — logic merged into `alex-cost-agent` | P21 | `6_agents` |
| SQS DLQ for trading queue | **Add** | P4 | `9_trading_floor` |
| Reporter timeout 900s | ✅ Already done (portfolio research) | — | `6_agents` |

---

## Observability Master Map

Everything reports to `/observe`. Complete panel list after all phases:

| # | Panel | Source Table(s) | Phase |
|---|-------|----------------|-------|
| 1 | Platform Cost (7d) | `agent_observations` | ✅ Exists |
| 2 | Per-Agent Stats | `agent_observations` | ✅ Exists |
| 3 | Guardrail Log | `agent_observations` | ✅ Exists |
| 4 | Monthly Forecast | computed | ✅ Exists |
| 5 | **Query Routing Distribution** | `rag_attributions` | P11 |
| 6 | **RAG Performance** | `rag_attributions` | P11 |
| 7 | **MCP Tool Usage** | `agent_observations.data_used` | P11 |
| 8 | **Session Activity** | `session_metadata` | P11 |
| 9 | **Simulation Health** | `trading_simulations` | P11 |
| 10 | **Daily P&L Chart** | `trading_daily_pnl` | P11 |
| 11 | **Agent Accuracy Leaderboard** | `agent_performance` | P11 |
| 12 | **RL Weights Evolution** | `rl_weights` | P11 |
| 13 | **Scout Activity** | `scout_candidates` | P11 |
| 14 | **Trade Replay Feed** | `simulated_trades` | P11 |
| 15 | **Trading Events Timeline** | `trading_events` | P11 |
| 16 | **Context Bridge Attribution** | `agent_observations.data_used` | P11 |
| 17 | **Synthesis Latency Breakdown** | `agent_observations` | P11 |
| 18 | **Cost per Trade** | computed | P11 |
| 19 | **Quant MCP Usage** | `agent_observations.data_used`, `quant_snapshots` | P13 |
| 20 | **Data Freshness Dashboard** | `quant_snapshots.expires_at` | P13 |
| 21 | **Debate Intelligence Browser** | `trading_floor_intelligence` | P14 |
| 22 | **Chart Gallery** | `quant_snapshots.chart_url` | P13 |
| 23 | **Query Response Speed (P50/P95)** | `query_latency_metrics` | P15 |
| 24 | **Time to First Token** | `query_latency_metrics.first_token_ms` | P15 |
| 25 | **Deep Sub-Agent Latency Breakdown** | `query_latency_metrics.sub_agent_ms` | P15 |
| 26 | **Slowest Queries Log** | `query_latency_metrics` | P15 |
| 27 | **Partial Deep Completion Rate** | `query_latency_metrics.partial` | P15 |
| 28 | **Latency vs Cost** | `query_latency_metrics` + `agent_observations` | P15 |
| 29 | **RAG Quality Scorecard** | `ragas_evaluations` | P17 |
| 30 | **RAGAS Trend (30 runs)** | `ragas_evaluations.overall_score` | P17 |
| 31 | **Eval Gate Status (CI)** | `ragas_evaluations` WHERE `gate='ci'` | P17 |
| 32 | **Daily Cost Report (Alex synthesis)** | `cost_daily_reports` | P21 |
| 33 | **Cost by Route (24h)** | `query_latency_metrics` | P21 |
| 34 | **Cost by Agent (24h)** | `agent_observations` aggregated | P21 |
| 35 | **Per-Session Cost Leaderboard** | `query_latency_metrics` GROUP BY `session_id` | P21 |

---

## Effort Estimates

| Scope | Phases | Calendar Time | Team |
|-------|--------|--------------|------|
| **MVP** | P0 + P1 + P2 + P3 + P4 + P6 + P10 | ~3–4 weeks | 1 developer |
| **Full v2** | All P0–P17 | ~12–14 weeks | 1 developer |
| **MVP + RAGAS** | MVP + P17 | ~3–4 weeks | 1 developer |
| **MVP + Async Deep** | MVP + P15 | ~4–5 weeks | 1 developer |
| **MVP + Quant** | MVP + P13 | ~4–5 weeks | 1 developer |
| **MVP + Debate Memory** | MVP + P14 | ~4 weeks | 1 developer |
| **MVP + FinOps** | MVP + P21 | ~3–4 weeks | 1 developer |
| **Full v2 + FinOps** | P0–P17 + P21 | ~12–14 weeks | 1 developer |

---

## Test After Every Phase

> **Rule:** No addition is "done" until all 3 layers pass. **User oversees frontend steps** — one checkpoint at a time.
> Full playbook: [`scripts/TEST_PLAYBOOK.md`](scripts/TEST_PLAYBOOK.md) · Cursor rule: `.cursor/rules/test-after-every-change.mdc`

### Workflow (every addition)

```
1. Implement the deliverable (minimal diff)
2. Layer 1 — Automated tests (agent runs, see table below)
3. Layer 2 — Deploy touched services (agent runs scripts/deploy_*.sh)
4. Layer 3 — Frontend playbook (user oversees; Pass/Fail per checkpoint)
5. Explain what broke, what we fixed, what it unblocks
6. Only then start the next addition
```

### Phase → Test mapping

| Phase | Test command | What it proves |
|-------|--------------|----------------|
| **P0** | `./scripts/test_p0.sh` | Context service fixed, no MessageGroupId, schema migrated, ingest columns, deep routes |
| **P1** | `scripts/tests/test_p1_router.py` *(create with P1)* | Router classifies fast/deep/multi; `/api/alex/chat` returns SSE |
| **P2** | `scripts/tests/test_p2_rag.py` *(create with P2)* | Session memory, RAG retrieval, follow-up context |
| **P3** | `scripts/tests/test_p3_synthesizer.py` *(create with P3)* | Stream saved to DB, chunked ingest has user_id |
| **P4** | `./scripts/test_trading.sh` | Orchestrator queues, debate runs, trades stored |
| **P5–P15** | Extend `scripts/eval_suite.sh` per phase | Add one test file per phase as built |
| **P17** | `python3 scripts/tests/test_ragas.py` | RAG quality gates |
| **P21** | `python3 scripts/tests/test_p21_cost_agent.py` + `scripts/test_cost_agent.sh` | Collectors, synthesis fallback, SES email, `cost_daily_reports` row |

### Test file conventions

- Location: `scripts/tests/test_p{N}_{name}.py` or `scripts/test_p{N}.sh`
- Layers: **static** (no AWS) → **unit** → **live** (Aurora/Lambda)
- Exit code `1` on failure — CI and humans use the same signal
- Each test prints ✅/❌ with a one-line reason (learning-friendly)

### Master regression (run before any deploy)

```bash
./scripts/test_p0.sh --static    # always
./scripts/test_trading.sh        # if trading touched
python3 scripts/tests/test_ragas.py  # if RAG/ingest touched
```

---

## Recommended Implementation Order

### Sprint 1 (Week 1): Foundation + Alex Chat

```
P0  Foundation fixes (both systems)
P1  Query router + unified chat API
P10 Guardrails (financial-only gate at minimum)
```

**Milestone:** User asks any question → Alex auto-routes → responds conversationally. No toggle.

### Sprint 2 (Week 2): Memory + Simulation

```
P2  RAG engine + session memory
P3  Synthesizer + chunked ingest
P4  Paper trade executor + simulation UI
P24-lite  Agentic RAG for edu_fast only (see [Agentic RAG](#agentic-rag))
```

**Milestone:** Alex remembers conversations. Trading simulation actually executes trades. User sees replay.

### Sprint 3 (Week 3): Autonomy + Bridge

```
P5  User trading config + autonomous schedule
P6  Context bridge (AI ↔ Trading)
P11 Observability (core panels: simulation, RAG, routing)
P17 RAGAS eval — Path A (search API smoke) + `/observe` scorecard
P22 LangSmith tracing (ECS researcher + router + RAG spans)
P21 Alex Comprehensive Cost Agent — daily email to abhishek.suresh2503@gmail.com
```

**Milestone:** Agents debate every 2h autonomously using Alex's research. AI answers trading questions. Observe shows simulation + RAG + **RAG quality scores**. **Daily FinOps email** with full platform cost breakdown.

### Sprint 4 (Week 4): Intelligence Upgrade

```
P7  MCP expansion (SEC, News)
P15 Async deep research sub-agents + latency observability
P8  RL learning loop
P24  Full agentic RAG on chat + fast paths
P17 RAGAS Path B — eval full `/api/alex/chat` RAG path (after P2 live)
P17 RAGAS Path C — agentic RAG education benchmark gate (after P24)
```

**Milestone:** Deep research runs 4–5 sub-agents in parallel. Users see first results in ~6s. `/observe` shows query speed P50/P95.

### Sprint 5 (Week 5–6): Advanced Agents + Quant

```
P9  Scout + Sentinel
P13 Quant intelligence (Tier 1 MCP: technical + macro + charts)
P14 Trading floor intelligence vector store
P11 Full observability (remaining panels)
P12 Observer Lambda + daily digests
P17 RAGAS CI gate on `deploy_researcher.yml` + weekly workflow
```

**Milestone:** Full platform — quant-powered Zara, debate memory in vector store, scout, daily digest, **RAG quality gated in CI**.

### Sprint 6 (Week 7–8): Pro Data Tier (optional)

```
P13 Tier 2 data sources (Polygon, Finnhub, FRED production keys)
P8  RL learning loop (if not done in Sprint 4)
B2B API packaging (see Startup.md)
```

**Milestone:** Production-grade quant data. Ready for paid tier launch.

---

## Decision Checklist for Approval

Please confirm each item before implementation begins:

### Scope

- [ ] **A.** MVP only (Sprints 1–3, ~3 weeks) — recommended starting point
- [ ] **B.** MVP + RL (Sprints 1–4, ~4 weeks)
- [ ] **C.** Full v2 (all sprints, ~8–10 weeks)
- [ ] **D.** MVP + RAGAS gates (Sprints 1–3 + P17, ~3–4 weeks) — recommended for production confidence

### Alex AI 2.0 Decisions

- [ ] **1.** Remove Fast/Deep toggle — Alex auto-routes (recommended: yes)
- [ ] **2.** Router model: Nova Lite (recommended) vs Nova Pro
- [ ] **3.** Deep commentary style: hedge fund manager memo (recommended) vs shorter
- [ ] **4.** MCP day 1: Playwright + SEC + News (recommended) vs Playwright only
- [ ] **5.** Vector memory: user-scoped + global fallback (recommended) vs user-only
- [ ] **6.** Off-topic handling: gentle redirect (recommended) vs hard reject
- [ ] **7.** Trading comparison in chat: when ticker mentioned + sim exists (recommended)

### Trading Floor 2.0 Decisions

- [ ] **8.** Simulation seed: mirror real portfolio value (recommended) vs fixed $100k
- [ ] **9.** Debate interval default: 2h (recommended), user picks 2/3/4/manual
- [ ] **10.** Market hours gate: 9:30 AM–4 PM ET only (recommended) vs 24/7
- [ ] **11.** Scout autonomy: OFF by default, user opt-in (recommended)
- [ ] **12.** Scheduling: single EventBridge looping users (recommended for MVP)
- [ ] **13.** RL approach: lightweight Aurora weights (recommended) vs ML later
- [ ] **14.** Observer daily email: yes (recommended) vs no
- [ ] **21.** Alex Comprehensive Cost Agent (P21): daily FinOps email to `abhishek.suresh2503@gmail.com` (recommended: yes)

### Cross-System

- [ ] **15.** Navbar: add Trading + Observe links (recommended: yes)
- [ ] **16.** "PAPER TRADING SIMULATION" banner on trading pages (recommended: yes)

### Quant & Intelligence

- [ ] **17.** Quant Tier 1 only for MVP (yfinance + technical + FRED free) vs Tier 2 paid APIs
- [ ] **18.** Chart rendering in chat responses (recommended: yes)
- [ ] **19.** Separate `trading_floor_intelligence` vector store (recommended: yes)
- [ ] **20.** Debate chunks per agent vs collective summary only (recommended: both)

### Async Deep Research (P15)

- [ ] **23.** Parallel sub-agents for all deep queries (recommended: yes)
- [ ] **24.** Sub-agent timeout: 45s per agent with partial synthesis fallback (recommended)
- [ ] **25.** Stream sub-agent completion events to frontend (recommended: yes)
- [ ] **26.** Record latency for all routes, not just deep (recommended: yes)

### RAGAS Evaluation (P17)

- [ ] **27.** RAGAS Path A on every PR (search API smoke) vs weekly only (recommended: weekly + pre-deploy gate)
- [ ] **28.** Deploy block if faithfulness < 0.88 (recommended: yes for researcher deploy)
- [ ] **29.** Benchmark queries: 5 NVIDIA fixed set (recommended for regression) vs rotating tickers
- [ ] **30.** Upgrade to official `ragas` pip + Bedrock judge (recommended: Phase 2) vs heuristic metrics (MVP)
- [ ] **31.** `alex-ragas-eval` Lambda in AWS vs GitHub Actions only (recommended: GitHub first)

### LangChain Family (P22–P23)

- [ ] **32.** LangSmith tracing: ECS researcher first (recommended: yes) — see [LangChain Family](#langchain-family--langchain-langgraph-langsmith)
- [ ] **33.** LangGraph scope: 4 graphs only — agentic RAG, edu_fast, committee, PDF (recommended) vs full platform rewrite (not recommended)
- [ ] **34.** LangChain LCEL: retriever utilities inside `rag_engine.py` only (recommended) vs replace OpenAI Agents SDK (not recommended)
- [ ] **35.** Graph checkpoints: Aurora `graph_checkpoints` table (recommended) vs SQLite local

### Agentic RAG (P24)

- [ ] **36.** Agentic RAG: edu_fast first, then chat + fast (recommended) — see [Agentic RAG](#agentic-rag)
- [ ] **37.** Implementation: native Python loop first (recommended for Sprint 2), LangGraph refactor in Sprint 4
- [ ] **38.** Max retrieval loops: 2 (recommended) vs 3
- [ ] **39.** Low-confidence threshold → `needs_review` + LangSmith feedback (recommended: 0.7)
- [ ] **40.** P17 Path C gate on agentic education benchmark (recommended: yes, after P24)

### Business (see Startup.md)

- [ ] **21.** Initial monetization: B2C subscription vs B2B API vs both
- [ ] **22.** Target customer: retail investors vs RIAs vs prop traders

---

## Production Engineering Pillars (Implementable from Current Setup)

> Maps Alex's existing AWS stack to enterprise agent-platform engineering domains. Each pillar includes **what you have today**, **planned additions** (from P0–P17), and **concrete next steps** you can implement without greenfield infrastructure.

### Pillar 1 — Intelligence & Agent Orchestration Layers

| Component | Current (Alex) | Planned | Implement Next |
|-----------|----------------|---------|----------------|
| **Query routing** | Regex fast/deep/multi | Nova Lite router (P1) | `query_router.py` — intent → route |
| **Task decomposition** | `planner.py` — Nova Pro JSON tasks | Portfolio + async deep sub-tasks (P15) | Extend planner for deep orchestrator |
| **Multi-agent debate** | 5 parallel agents + executor (ThreadPool) | RL-weighted votes (P8) | Already production pattern |
| **Pipeline orchestration** | SQS: scheduler → planner → tagger → reporter | Per-user EventBridge (P5) | EventBridge + orchestrator loop |
| **Async sub-agents** | — | SEC/News/Quant parallel (P15) | `asyncio.gather` in deep_orchestrator |
| **State passing** | SQS message bodies with correlationId | `trading_events`, session metadata | Typed Pydantic message schemas |

**Interview talking point:** *"I built a three-tier orchestration model — router (intent), planner (decomposition), executor (tool invocation) — similar to wrapping non-deterministic LLMs in deterministic workflow code."*

**Next implementation (1–2 weeks):**
- P1 query router + P15 deep orchestrator prototype on ECS
- Standardize all SQS payloads with `AlexTaskMessage` Pydantic model
- Add orchestration diagram to `/observe` (which agent ran, in what order)

---

### Pillar 2 — CI/CD & Deployment Infrastructure

| Component | Current (Alex) | Gap | Implement Next |
|-----------|----------------|-----|----------------|
| **GitHub Actions** | `ci.yml`, `deploy_agents.yml`, `deploy_trading.yml`, `deploy_researcher.yml`, `health_check.yml`, `pr_check.yml` | No unified deploy pipeline | Single `deploy_all.sh` orchestrator |
| **Path-based deploys** | Only changed paths trigger deploy | ECS researcher not always redeployed | Add `paths-filter` for all services |
| **Smoke tests** | Trading deploy invokes orchestrator | No smoke test for researcher/ingest | Post-deploy health gate in every workflow |
| **IaC** | 9 Terraform modules (VPC → guardrails) | Manual `start_session.sh` for env sync | **Terraform-first for all infra**; outputs → GitHub env vars |
| **Packaging** | `package.sh`, `deploy_trading.sh` | No version tagging | Git SHA in Lambda env `DEPLOY_VERSION` |
| **Frontend** | Vercel (implied) | No CI build check in `ci.yml` | Add `npm run build` to PR checks |

**Next implementation (3–5 days):**
```yaml
# .github/workflows/deploy_all.yml (new)
- terraform plan (on PR)
- package all Lambdas
- deploy changed services only
- run scripts/health_check.sh
- run scripts/test_trading.sh (smoke)
- fail deploy if health check fails
```

**Files to extend:** `.github/workflows/ci.yml` — add Next.js build, RAGAS eval on schedule (weekly).

---

### Pillar 3 — MCPs & Agent Tooling

| Component | Current (Alex) | Planned | Implement Next |
|-----------|----------------|---------|----------------|
| **Playwright MCP** | ECS deep researcher (`mcp_servers.py`) | Trading scout (P9) | Already live |
| **Python tools** | `get_stock_data`, `get_sec_filings`, `ingest_financial_document` | — | Baseline tool layer |
| **MCP gateway** | — | `mcp_gateway.py` (P7, P13) | Central tool registry + observability |
| **Quant MCPs** | yfinance via `market_data.py` | technical, options, FRED (P13) | Wrap existing providers as MCP |
| **Tool limits** | Fast agent: no MCP (Bedrock tool cap) | Sub-agents each get 1–2 MCPs | Design pattern for tool budget |
| **Tool observability** | `agent_observations.data_used` (partial) | Full MCP call logging (P11) | Log latency + success per tool call |

**Next implementation (1 week):**
- Create `backend/researcher/mcp/mcp_gateway.py` with tool registry
- Standardize tool response schema: `{ tool, latency_ms, success, chars, source }`
- Surface on `/observe` MCP panel

---

### Pillar 4 — Reliability Engineering

| Component | Current (Alex) | Gap | Implement Next |
|-----------|----------------|-----|----------------|
| **Retries** | Aurora `execute_sql` 3x retry on resume; RDS API retry in frontend | No SQS DLQ on trading queue | Add DLQ (P4 terraform) |
| **Guardrails** | Bedrock guardrail (Terraform 7); trading confidence caps | Reporter/multi-agent unguarded | P10 unified guardrails |
| **Health checks** | `health_check.sh`, `start_session.sh`, ops_agent | No automated alerting | CloudWatch alarms → SNS |
| **Idempotency** | Portfolio upsert, cost_snapshots upsert | simulated_trades can duplicate | Add `idempotency_key` on trades |
| **Circuit breaker** | ECS fallback to Bedrock in reporter | No circuit breaker on ECS calls | httpx retry + fallback pattern (exists in reporter) |
| **Cold starts** | Aurora warmup script, debate_agent warmup | — | Documented pattern |
| **Partial failure** | — | P15 sub-agent timeout with partial synthesis | `return_exceptions=True` in gather |

**Next implementation (1 week):**
- SQS DLQ + CloudWatch alarm on DLQ depth > 0
- P10 guardrails on all LLM output paths
- `scripts/chaos_test.sh` — kill ECS mid-request, verify fallback

**SLO targets to define:**
| SLO | Target |
|-----|--------|
| Fast query P95 latency | < 15s |
| Deep query P95 latency | < 90s |
| Trading debate success rate | > 95% |
| Ingest success rate | > 99% |

---

### Pillar 5 — Inference Engineering

| Component | Current (Alex) | Planned | Implement Next |
|-----------|----------------|---------|----------------|
| **Model routing** | Nova Pro (research/debate), Nova Lite (tagger/cost/ops) | Router uses Nova Lite (P1) | Tiered model selection by task |
| **Embeddings** | SageMaker `alex-embedding` (MiniLM 384-dim) | — | Production embedding endpoint |
| **Streaming** | SSE fast/deep streams on ECS | Unified `/api/alex/chat` SSE (P1) | Single stream contract |
| **Token/cost tracking** | `agent_observations` — tokens, cost per call | Per-query cost in `query_latency_metrics` (P15) + **P21 daily synthesis email** | Join tables for cost/query |
| **Context budget** | Ad-hoc in prompts | RAG engine 4000-token budget (P2) | Explicit token counting |
| **Smart guardrail skip** | `should_apply_guardrail()` — 3+ financial keywords | — | Document tradeoff |
| **Parallel inference** | Trading agents parallel (ThreadPool) | Deep sub-agents parallel (P15) | asyncio gather pattern |

**Next implementation (1 week):**
- Add `litellm` or direct Bedrock token counting in `latency_tracker.py`
- Model config in SSM: `/alex/models/{agent}` — hot-swappable without redeploy
- `/observe` panel: cost per route, tokens per agent

---

### Pillar 6 — Evaluation & Benchmarking Frameworks

| Component | Current (Alex) | Planned | Implement Next |
|-----------|----------------|---------|----------------|
| **RAGAS eval** | `scripts/tests/test_ragas.py` — relevancy, faithfulness, recall, hallucination | **P17** — Aurora persist, CI, observe panel | See [§ RAGAS Evaluation Framework (P17)](#ragas-evaluation-framework-p17) |
| **RAGAS storage** | `ragas_evaluations` table in Aurora (DDL ✅) | Per-run history + `passed` gate | P17 `backend/eval/db.py` |
| **CI weekly run** | — | `.github/workflows/ragas_eval.yml` | P17 Phase 3 |
| **Deploy gate** | — | `deploy_researcher.yml` blocks if `passed = false` | P17 Phase 3 |
| **Trading accuracy** | `agent_performance` table (empty) | RL evaluator (P8) | Daily outcome scoring |
| **Agent observability** | `/observe` — cost, latency, guardrails | +RAGAS scorecard (P17) + accuracy leaderboard (P8) | P17 + P11 |
| **Latency benchmarks** | CloudWatch `ResearchLatency` | `query_latency_metrics` (P15) | P50/P95 dashboard |
| **Regression suite** | `test_trading.sh`, `test_planner.py`, `test_multi_agent.py` | `scripts/eval_suite.sh` | P17 Phase 3 |

**Benchmark targets (P17):**
- Answer Relevancy > 0.87 (gate: 0.85)
- Faithfulness > 0.91 (gate: 0.88)
- Hallucination rate < 5% (gate: 8%)

**Unified harness (P17):**
```bash
# scripts/eval_suite.sh
python3 scripts/tests/test_ragas.py      # exits 1 if gate fails
python3 scripts/tests/test_planner.py
python3 scripts/tests/test_multi_agent.py
bash scripts/test_trading.sh
# → eval_report.json artifact for /observe + CI
```

---

### Pillar 7 — Distributed Systems & Production-Scale Architecture

| Component | Current (Alex) | Pattern | Scale path |
|-----------|----------------|---------|------------|
| **Compute** | Lambda (agents) + ECS (researcher) + SageMaker (embeddings) | Hybrid serverless + containers | Right tool per workload |
| **Messaging** | SQS (research, results, trading, frontend-results) | Async decoupling | Add DLQ, increase visibility timeout |
| **Scheduling** | EventBridge Scheduler (2h research, daily cost-agent 7AM, ops 30min) | Cron + rate triggers | Per-user schedules (P5) |
| **Database** | Aurora Serverless v2 + pgvector | RDS Data API (no connection pool) | Scales to zero, cold start handled |
| **Vector search** | pgvector in Aurora | Cosine similarity | IVFFlat indexes (P14) |
| **API layer** | API Gateway (ingest/search) + ALB (ECS) + Next.js API routes | Multi-entry | Unified behind single ALB |
| **Auth** | Clerk + API keys | Per-user isolation | user_id scoping on all vectors |
| **Observability** | CloudWatch logs + `agent_observations` + `/observe` UI | Custom metrics namespace `AlexAI/*` | Full distributed trace (P11) |
| **Multi-tenancy** | Per-user portfolio, digests, sessions | Row-level user_id | Ready for scale |

**Architecture diagram (production-scale path):**

```
Users → CloudFront/Vercel (Next.js)
          ↓
       ALB → ECS Researcher (streaming, MCP, router)
          ↓                    ↓
    API Gateway            SQS Queues
    (ingest/search)     (research, trading, results)
          ↓                    ↓
    Lambda Ingest         Lambda Agents (planner, tagger, reporter, debate)
          ↓                    ↓
    Aurora pgvector ←──── RDS Data API ────→ Aurora tables (24+)
          ↑
    SageMaker Embeddings
          ↑
    EventBridge Schedulers (research 2h, trading, cost, eval)
```

**Next implementation (2 weeks):**
- Add OpenTelemetry traces across router → sub-agent → synthesizer (optional: AWS X-Ray)
- SQS DLQ monitoring dashboard
- Load test: `scripts/load_test.sh` — 10 concurrent queries, measure P95

---

### New Phase Summary: Production Engineering

| Phase | Pillar | Effort | Priority |
|-------|--------|--------|----------|
| **P16** | Unified CI/CD pipeline + deploy gates | 3 days | High |
| **P17** | RAGAS eval framework — **see main [P17](#ragas-evaluation-framework-p17)** | 2–3 days | High |
| **P18** | SLOs + CloudWatch alarms + DLQ | 2 days | High |
| **P19** | OpenTelemetry / X-Ray tracing | 3 days | Medium |
| **P22** | LangSmith tracing + eval | 2–3 days | High |
| **P23** | LangGraph orchestration (selective) | 3–5 days | Medium |
| **P24** | Agentic RAG engine | 4–6 days | High |

These phases layer on top of P0–P17 without blocking MVP delivery. **P17 (RAGAS)** is the single source of truth for eval implementation; PE P16/P18 add infra around it.

---

## LangChain Family — LangChain, LangGraph, LangSmith

> **Feasibility:** ✅ **Yes — incremental adoption recommended.** Do **not** rewrite the full platform. Alex already runs **OpenAI Agents SDK** + **LiteLLM** + **direct Bedrock** on ECS/Lambda. LangChain family tools slot in as **RAG primitives**, **graph orchestration**, and **observability/eval** — not as a replacement for every agent path.

### Current State vs LangChain Family

| Alex today | Package | Role |
|------------|---------|------|
| Fast / deep research agents | `openai-agents==0.0.11` | Tool-use agents (`Agent`, `Runner`, `function_tool`) |
| Bedrock models | `litellm` + `boto3` | Nova Lite/Pro routing |
| Query router, planner, trading agents | Custom Python + Bedrock | Intent + orchestration |
| RAG / context | `context_service.py` (partial) | Manual SQL + pgvector — **P2 `rag_engine.py` planned** |
| Eval | `test_ragas.py` (P17) | Local RAGAS heuristics — no LangSmith yet |
| Async pipelines | SQS + Lambda | scheduler → planner → reporter; trading debate queue |
| Tracing | `query_latency_metrics`, `/observe` | Custom metrics — no distributed trace IDs |

**Resume alignment:** Archemy used **LangSmith + RAGAS** (+30% reliability). Alex P17 covers RAGAS; **P22 adds LangSmith** for production trace + human-review loops.

### Adoption Strategy (Recommended Order)

```
Phase 1 — LangSmith (P22)     ← lowest risk, highest ops value
Phase 2 — Agentic RAG (P24)   ← can use LangChain retrievers OR native Python
Phase 3 — LangGraph (P23)     ← formalize multi-step flows only where SQS is heavy
Phase 4 — LangChain LCEL      ← optional retriever/chain helpers inside rag_engine only
```

**Do NOT:** Replace `server.py` OpenAI Agents SDK paths with LangChain agents wholesale — two agent frameworks = debugging hell.

---

### P22 — LangSmith (Tracing + Eval + Human Review)

**Goal:** Production traces for every chat route, RAG retrieval, and tool call — complement `/observe` and P17 RAGAS.

| Task | File / change | Detail |
|------|---------------|--------|
| Add dependency | `backend/researcher/pyproject.toml` | `langsmith>=0.1.0` (ECS researcher only first) |
| Env vars | `.env`, ECS task definition (Terraform) | `LANGCHAIN_TRACING_V2=true`, `LANGCHAIN_API_KEY`, `LANGCHAIN_PROJECT=alex-production` |
| Trace router | `query_router.py` | `@traceable` on `classify_query()` — log route, intent, entities, confidence |
| Trace RAG | `rag_engine.py` (P2) | Trace `build_context()` — chunks retrieved, scores, token budget |
| Trace agents | `server.py` | Wrap `Runner.run()` spans; child spans per tool/MCP call |
| Trace ingest | `ingest_pgvector.py` | Span per vector write with `chunk_type`, `user_id` |
| Trace trading | `debate_engine.py`, `debater_handoff.py` | Parent span `debate_run`; child per agent vote |
| Feedback API | `frontend/app/api/alex/feedback/route.ts` *(new)* | Thumbs up/down → LangSmith `create_feedback()` |
| Low-confidence queue | `rag_engine.py` + dashboard | Faithfulness < 0.7 → `needs_review` flag (Archemy pattern) |
| `/observe` panel | `observe/page.tsx` | Link to LangSmith project; show 24h trace count + error rate |
| P17 bridge | `backend/eval/ragas_runner.py` | Attach RAGAS run ID to LangSmith experiment |

**Terraform:** Add `LANGCHAIN_API_KEY` to ECS researcher + optional eval Lambda via SSM Parameter Store (`terraform/4_researcher`).

**Effort:** 2–3 days · **Depends:** P1 ✅, P11 (observe panels helpful)

**User sees:** Every Alex answer traceable in LangSmith; team can flag bad retrieval; eval runs linked to traces.

---

### P23 — LangGraph (Selective Orchestration)

**Goal:** Replace ad-hoc multi-step Python/SQS glue with **explicit state graphs** where checkpointing and human-in-the-loop matter.

**Use LangGraph for:**

| Flow | Why graph | Replaces |
|------|-----------|----------|
| **Agentic RAG loop** (P24) | retrieve → grade → rewrite → web fallback → generate | Custom while-loop in `rag_engine.py` |
| **Edu fast search** (`Alex_chat_intelligence.md` C1) | vector hit → glossary → fast search → ingest | Linear `edu_fast_agent.py` |
| **Committee mini-debate** (C6.2) | Marcus ∥ Victoria → Executor synthesize | Ad-hoc asyncio |
| **Deep report + PDF** (C3) | deep → synthesize → render PDF → S3 | Sequential awaits in `report_agent.py` |
| **Human approval** (P1.5, RIA) | `pending → approved → publish` with interrupt | Custom state table only |

**Keep SQS + Lambda (do NOT LangGraph-ify):**

| Flow | Why keep SQS |
|------|--------------|
| Portfolio research pipeline | Already durable, 2h schedule, proven |
| Trading orchestrator → debate queue | High volume, Lambda burst, existing Terraform |
| Deep parallel planner → reporter | Map-reduce at scale; LangGraph on ECS for coordination only if needed |

**Deliverables:**

| File | Purpose |
|------|---------|
| `backend/researcher/graphs/agentic_rag_graph.py` | P24 graph definition |
| `backend/researcher/graphs/edu_fast_graph.py` | Education pipeline graph |
| `backend/researcher/graphs/committee_graph.py` | 2-debater + executor |
| `backend/researcher/graph_checkpoint.py` | Aurora or SQLite checkpointer for HITL resume |
| `backend/researcher/pyproject.toml` | `langgraph>=0.2.0`, `langchain-core>=0.3.0` |

**Bedrock integration:**

```python
from langchain_aws import ChatBedrockConverse

llm = ChatBedrockConverse(
    model="us.amazon.nova-lite-v1:0",
    region_name="us-east-1",
)
```

Use **Nova Lite** for graph routing/grading nodes; **Nova Pro** for final generation — same cost discipline as today.

**Effort:** 3–5 days · **Depends:** P2, P22 (traces on graph nodes)

---

### LangChain (Library — RAG Primitives Only)

**Goal:** Use LangChain as **retriever + document + chain utilities** inside `rag_engine.py` — not as the agent runtime.

| Component | LangChain class | Alex mapping |
|-----------|-----------------|--------------|
| Embeddings | `SageMakerEndpointEmbeddings` *(custom wrapper)* | Existing SageMaker `alex-embedding` |
| Vector store | `PGVector` or custom retriever over `research_vectors` | Aurora pgvector |
| Text splitter | `RecursiveCharacterTextSplitter` / `MarkdownHeaderTextSplitter` | `chunking.py` (P2) |
| Retriever | `EnsembleRetriever` (BM25 + vector) | Hybrid search in P2 |
| Reranker | `ContextualCompressionRetriever` + LLM filter | Nova Lite relevance scoring |
| LCEL chain | `retrieve \| compress \| prompt \| llm` | Fast path context injection only |

**Add to `pyproject.toml` (with P2 or P24):**

```
langchain-core>=0.3.0
langchain-aws>=0.2.0
langchain-community>=0.3.0   # PGVector, text splitters
langchain-text-splitters>=0.3.0
```

**Conflict avoidance:**

| Keep | Don't duplicate |
|------|-----------------|
| OpenAI Agents SDK for tool-heavy research (`server.py`) | LangChain `create_react_agent` for same paths |
| Custom `query_router.py` | LangChain routing middleware (optional later) |
| `function_tool` in `tools.py` | LangChain `@tool` duplicates |

**Effort:** 1–2 days (bundled with P2/P24) · **Optional** if native Python RAG is preferred

---

### LangChain Family — Architecture After Adoption

```
User → /api/alex/chat
         ↓
    query_router  ──trace──► LangSmith
         ↓
    ┌────┴────┬────────────┬──────────────┐
    │         │            │              │
  fast     edu_fast    debater      deep+parallel
 (Agents   (LangGraph   (handoff)    (Agents SDK
  SDK)      + RAG)                     + MCP)
    │         │            │              │
    └────┬────┴────────────┴──────────────┘
         ↓
   rag_engine (LangChain retrievers OR agentic graph P24)
         ↓
   pgvector / portfolio_digests / trading_floor_intelligence
         ↓
   synthesizer → ingest → LangSmith feedback
```

### LangChain Family — Decision Points

| # | Decision | Options | Recommendation |
|---|----------|---------|----------------|
| 1 | LangSmith scope | ECS only vs ECS + Lambdas | **ECS first**, add planner/reporter traces in Sprint 2 |
| 2 | LangGraph scope | Full platform vs 4 graphs | **4 graphs only** (P24, edu, committee, PDF) |
| 3 | LangChain depth | Full LCEL vs native Python RAG | **LangChain retrievers only**; keep agents on OpenAI SDK |
| 4 | Checkpoint store | Aurora vs SQLite vs Redis | **Aurora** (`graph_checkpoints` table) — already serverless |
| 5 | Eval stack | RAGAS only vs RAGAS + LangSmith experiments | **Both** — RAGAS gates deploy, LangSmith traces debug |

### LangChain Family — New Schema (P23 HITL checkpoints)

```sql
CREATE TABLE IF NOT EXISTS graph_checkpoints (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  thread_id VARCHAR(64) NOT NULL,
  graph_name VARCHAR(50) NOT NULL,
  checkpoint JSONB NOT NULL,
  user_id UUID REFERENCES users(id),
  created_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS gc_thread_idx ON graph_checkpoints (thread_id, created_at DESC);
```

### LangChain Family — Verification

```bash
# After P22
LANGCHAIN_TRACING_V2=true python3 scripts/tests/test_p1_router.py
# Confirm traces appear in LangSmith project "alex-production"

# After P23
python3 scripts/tests/test_agentic_rag_graph.py  # create with P24
```

---

## Agentic RAG

> **Feasibility:** ✅ **Yes — high value, aligns with P2 + `Alex_chat_intelligence.md` C1.**  
> **Definition:** RAG where an **agent decides** whether to retrieve, what to retrieve, whether results are good enough, and whether to rewrite the query or fall back to tools — not a single static `search → inject → generate` pass.

### Passive RAG (P2 baseline) vs Agentic RAG (P24)

| Step | Passive RAG (P2) | Agentic RAG (P24) |
|------|------------------|-------------------|
| Retrieve | One vector search (top-k) | Agent may multi-query, HyDE, or skip retrieval |
| Grade | None | LLM grades doc relevance per chunk |
| Fallback | None | Low grade → Playwright MCP / fast search / glossary |
| Rewrite | None | Agent rewrites query and re-retrieves (max 2 loops) |
| Generate | Single LLM call | Generate only after `context_sufficient = true` |
| Ingest | Post-hoc optional | Agent decides what to persist + `chunk_type` |
| Observability | Chunk list | Full decision trace on `/observe` + LangSmith |

### When Agentic RAG Applies on Alex

| Route | Agentic RAG? | Why |
|-------|--------------|-----|
| `edu_fast` | ✅ **Yes** | "What is a bond?" — check vector → glossary → web → ingest |
| `chat` follow-ups | ✅ **Yes** | "What about their risk?" needs session-aware re-retrieval |
| `fast` ticker | ⚠️ Partial | Live tools primary; RAG for prior research on ticker |
| `deep` SEC | ❌ No | MCP tools are the retrieval — agentic RAG adds latency |
| `debater` | ⚠️ Partial | Inject RAG context before handoff; no full loop |
| Portfolio digest reporter | ❌ No | Pipeline already has planner decomposition |

### Agentic RAG Graph (LangGraph — P24)

**File:** `backend/researcher/graphs/agentic_rag_graph.py`

```
                    ┌─────────────┐
                    │   START     │
                    │  (query)    │
                    └──────┬──────┘
                           ▼
                    ┌─────────────┐
              ┌────│ route_need  │──── skip_retrieval ──────────────┐
              │    │  _rag?      │                                  │
              │    └──────┬──────┘                                  │
              │           │ retrieve                               │
              │           ▼                                        │
              │    ┌─────────────┐                                  │
              │    │  retrieve   │  pgvector + portfolio_digests    │
              │    │  _vectors   │  + trading_floor_intelligence    │
              │    └──────┬──────┘                                  │
              │           ▼                                        │
              │    ┌─────────────┐     insufficient                 │
              │    │   grade     │──────────────────┐               │
              │    │  _documents │                  │               │
              │    └──────┬──────┘                  ▼               │
              │           │ sufficient      ┌─────────────┐        │
              │           │                 │  rewrite    │        │
              │           │                 │  _query     │──┐     │
              │           │                 └─────────────┘  │     │
              │           │                      ▲            │     │
              │           │                      └────────────┘     │
              │           │                 (max 2 loops)           │
              │           │                          │               │
              │           │                          ▼               │
              │           │                 ┌─────────────┐        │
              │           │                 │  tool       │        │
              │           │                 │  _fallback  │        │
              │           │                 │ (MCP/glossary)│       │
              │           │                 └──────┬──────┘        │
              │           │                        │               │
              │           ▼                        ▼               ▼
              │    ┌─────────────────────────────────────────────┐
              │    │              generate_answer                 │
              │    │         (Nova Lite/Pro + context bundle)     │
              │    └──────────────────────┬──────────────────────┘
              │                           ▼
              │    ┌─────────────┐   ┌─────────────┐
              │    │  self_check │──►│   ingest    │ (if novel)
              │    │  _quality   │   │  _decision  │
              │    └──────┬──────┘   └─────────────┘
              │           │ low confidence → needs_review (P22)
              │           ▼
              │         END
              └──────────────────────────────────────────────────►
```

### Agentic RAG — State Schema

```python
class AgenticRAGState(TypedDict):
    query:            str
    user_id:          str
    session_id:       str
    route:            str           # edu_fast | chat | fast
    rewritten_queries: list[str]
    retrieved_chunks: list[dict]     # {content, source, score, chunk_type}
    grade_scores:     list[float]
    context_bundle:   str
    answer:           str
    retrieval_loops:  int
    used_fallback:    bool
    ingest:           bool
    confidence:       float
    needs_review:     bool
```

### Agentic RAG — Node Implementations

| Node | Model | Logic |
|------|-------|-------|
| `route_need_rag` | Nova Lite | Edu/concept/follow-up → retrieve; live-price-only → skip |
| `retrieve_vectors` | — | Hybrid: pgvector cosine + `portfolio_digests` + `trading_floor_intelligence` (P14) |
| `grade_documents` | Nova Lite | Per-chunk relevant / irrelevant / ambiguous (CRAG-style) |
| `rewrite_query` | Nova Lite | HyDE or multi-query expansion; increment `retrieval_loops` |
| `tool_fallback` | Tools | Glossary seed → Playwright allowlist (edu) → yfinance (ticker) |
| `generate_answer` | Nova Lite/Pro | Inject `context_bundle` with attribution footnotes |
| `self_check_quality` | Nova Lite | Faithfulness self-grade; < 0.7 → `needs_review` |
| `ingest_decision` | Rule + LLM | Novel + high confidence → `ingest_pgvector` async |

### Agentic RAG — Techniques Mapped

| Technique | Alex use | Implementation |
|-----------|----------|----------------|
| **Adaptive RAG** | Router picks retrieve vs tools vs skip | `route_need_rag` node |
| **Corrective RAG (CRAG)** | Grade chunks; fallback if poor | `grade_documents` + `tool_fallback` |
| **Self-RAG** | Self-check before return | `self_check_quality` node |
| **HyDE** | Hypothetical doc for better embedding | `rewrite_query` option |
| **Multi-query** | 3 variant queries merged | `rewrite_query` option |
| **Parent-child chunks** | Long deep answers | P3 `chunking.py` parent_id column |
| **Reranking** | Top 20 → top 5 | Nova Lite listwise rank or Cohere (optional) |

### Agentic RAG — Deliverables (P24)

| File | Purpose |
|------|---------|
| `backend/researcher/agentic_rag.py` | Graph builder + `run_agentic_rag()` entry |
| `backend/researcher/graphs/agentic_rag_graph.py` | LangGraph state machine |
| `backend/researcher/rag_grader.py` | Chunk relevance scoring |
| `backend/researcher/rag_fallback.py` | Glossary + MCP + fast search fallbacks |
| `backend/researcher/rag_engine.py` | Shared retrieval (P2) — used by graph nodes |
| `scripts/tests/test_agentic_rag.py` | Loop limits, fallback triggers, ingest rules |
| `frontend/app/observe/page.tsx` | Agentic RAG panel: loops, fallback rate, grade distribution |

### Agentic RAG — API Integration

Wire into existing routes (no new user-facing endpoint):

| Entry | Change |
|-------|--------|
| `/research/conversation/stream` | `intent=education` → `run_agentic_rag(route='edu_fast')` |
| `/research/stream` (fast) | Prepend agentic RAG context for ticker prior research |
| `/api/alex/chat` | SSE events: `rag_step`, `chunks_retrieved`, `fallback_used`, `confidence` |

**New SSE events:**

```json
{ "type": "rag_step", "step": "grade_documents", "relevant": 3, "irrelevant": 2 }
{ "type": "rag_fallback", "source": "glossary", "query": "what is a bond" }
{ "type": "rag_done", "loops": 1, "confidence": 0.91, "ingested": true }
```

### Agentic RAG — Schema Extensions

```sql
-- Extend rag_attributions (P2) for agentic decisions
ALTER TABLE rag_attributions ADD COLUMN IF NOT EXISTS retrieval_loops INTEGER DEFAULT 0;
ALTER TABLE rag_attributions ADD COLUMN IF NOT EXISTS fallback_source VARCHAR(50);
ALTER TABLE rag_attributions ADD COLUMN IF NOT EXISTS grade_scores JSONB DEFAULT '[]';
ALTER TABLE rag_attributions ADD COLUMN IF NOT EXISTS agentic_graph VARCHAR(50) DEFAULT 'agentic_rag_v1';
```

### Agentic RAG — Without LangGraph (Fallback)

If P23 is deferred, implement the same loop in `agentic_rag.py` as a native async Python state machine:

```python
async def run_agentic_rag(state: AgenticRAGState) -> AgenticRAGState:
    for loop in range(MAX_RETRIEVAL_LOOPS):
        chunks = await retrieve_vectors(state)
        grades = await grade_documents(state, chunks)
        if grades.sufficient:
            break
        state = await rewrite_or_fallback(state, grades)
    state.answer = await generate_answer(state)
    return state
```

LangGraph adds **checkpointing, HITL interrupt, and visual debugging** — recommended but not blocking.

### Agentic RAG — Effort & Dependencies

| Item | Effort | Depends on |
|------|--------|------------|
| P2 `rag_engine.py` (passive retrieval) | 4–5 days | P0 ✅ |
| P24 agentic loop (native Python) | 3–4 days | P2 |
| P24 + LangGraph version | +1–2 days | P23 |
| LangSmith traces on RAG nodes | 0.5 day | P22 |
| P17 eval Path C (agentic RAG gate) | 1 day | P17, P24 |

**Total P24:** 4–6 days (with P2 prerequisite)

### Agentic RAG — P17 Eval Extension (Path C)

Add to `ragas_runner.py` after P24:

| Test query type | Assert |
|-----------------|--------|
| Education (cache miss) | `fallback_used` at least once OR `ingest=true` |
| Follow-up with session | `retrieval_loops >= 1`, context contains prior ticker |
| Live price query | `retrieval_skipped=true`, answer has live price |
| Adversarial (no data) | `needs_review=true` OR graceful decline — not hallucination |

**Gate:** Agentic RAG faithfulness ≥ 0.88 on education benchmark set.

### Agentic RAG — Recommended Sprint Placement

```
Sprint 2 (with P2):
  P2  rag_engine.py (passive hybrid retrieval)
  P24-lite  agentic loop for edu_fast only (Alex_chat_intelligence C1)

Sprint 3:
  P22  LangSmith traces
  P24  full agentic RAG on chat + fast paths

Sprint 4 (optional):
  P23  LangGraph refactor of P24 + committee + PDF graphs
```

---

## Document Index

| Document | Purpose |
|----------|---------|
| `scripts/TEST_PLAYBOOK.md` | **Test after every addition** — 3-layer protocol (automated → deploy → frontend checkpoints) |
| `Alex_AI_2.0.md` | Detailed AI plan — router, RAG, MCP, synthesis, guardrails |
| `Alex_chat_intelligence.md` | Chat routing upgrades — edu fast search, PDF reports, debater handoffs, earnings agent |
| `Alex_Trading_Floor_2.0.md` | Detailed trading plan — simulation, scout, RL, autonomy |
| `Alex_Master_Implementation_Plan.md` | **This file** — unified implementation order |
| `usecases.md` | Cross-industry agentic AI use cases, startup ideas, beginner setup guide |
| `Agentic_Usecase.md` | Agentic use cases on **current** Alex setup — finance-native, demos, matrix |
| `Alex_chat_intelligence.md` | Chat routing — edu fast search, PDF, debater handoffs; **P24 edu_fast target** |
| `RIA.md` | **RIA Copilot** — white-label Alex for advisors; architecture leverage + MVP roadmap |
| `Startup.md` | Business model, monetization, startup ideas, unit economics |
| `Ophelia.md` | Interview prep — Alex → Ophelia mapping, talking points, intro |

---

*All documents are PARKED. Reply with your decision checklist selections to begin implementation.*
