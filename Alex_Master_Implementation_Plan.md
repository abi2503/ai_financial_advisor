# Alex Master Implementation Plan

> **Status:** PARKED — awaiting approval  
> **Created:** June 13, 2026  
> **Source documents:**
> - `Alex_Trading_Floor_2.0.md` — Autonomous paper-trading simulation, scout agents, RL learning
> - `Alex_AI_2.0.md` — Intelligent conversational AI, query routing, session RAG, MCP, synthesis
> - `Startup.md` — Business model, monetization, startup ideas, unit economics

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
11. [Aurora Schema Master List](#aurora-schema-master-list)
12. [API Master List](#api-master-list)
13. [Frontend Master List](#frontend-master-list)
14. [Infrastructure Master List](#infrastructure-master-list)
15. [Observability Master Map](#observability-master-map)
16. [Effort Estimates](#effort-estimates)
17. [Recommended Implementation Order](#recommended-implementation-order)
18. [Decision Checklist for Approval](#decision-checklist-for-approval)
19. [Production Engineering Pillars](#production-engineering-pillars-implementable-from-current-setup)
20. [Test After Every Phase](#test-after-every-phase)
21. [Document Index](#document-index)

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

### All tables in `aurora_warmup.py` after implementation: **25 tables**

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

### Extended APIs

| Route | Changes | Phase |
|-------|---------|-------|
| `GET /api/observe` | +simulation, P&L, RL, scout, events, RAG, routing, **RAGAS** | P11, P17 |
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
| `/observe` | 10+ new panels + **RAGAS quality scorecard** (see observability map) | P11, P17 |
| `/portfolio` | Agent recommendation badge per holding, link to trading | P6 |
| `/dashboard` | Simulation summary card, contextual Alex suggestions | P3, P4 |
| `Navbar` | Add Trading + Observe links | P4 |

---

## Infrastructure Master List

| Resource | Action | Phase |
|----------|--------|-------|
| `alex-trading-orchestrator` Lambda | Update: context_builder, trade_executor | P4, P6 |
| `alex-debate-agent` Lambda | Update: dynamic RL weights, richer context | P6, P8 |
| `alex-trade-evaluator` Lambda | **New** — daily outcome scoring | P8 |
| `alex-trading-observer` Lambda | **New** — daily digest | P12 |
| `alex-sentinel` Lambda | **New** — hourly stop-loss check | P9 |
| ECS researcher service | Update: router, synthesizer, RAG, MCP, quant MCP, deep orchestrator | P1–P3, P7, P13, P15 |
| `alex-ingest` Lambda | Update: user-scoped vectors | P3 |
| `alex-debate-ingest` (in debate Lambda) | **New** — trading_floor_intelligence writer | P14 |
| EventBridge: `alex-trading-auto` | **Add** — debate schedule | P5 |
| EventBridge: `alex-trade-evaluator` | **Add** — daily 5PM ET | P8 |
| EventBridge: `alex-trading-observer` | **Add** — daily 4:30PM ET | P12 |
| EventBridge: `alex-sentinel` | **Add** — hourly | P9 |
| EventBridge: `alex-ragas-weekly` | **Add** — Sunday 6 AM ET (optional) | P17 |
| `alex-ragas-eval` Lambda | **New** — scheduled RAGAS runner (optional) | P17 |
| SQS DLQ for trading queue | **Add** | P4 |
| Reporter timeout 900s | ✅ Already done (portfolio research) | — |

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
```

**Milestone:** Alex remembers conversations. Trading simulation actually executes trades. User sees replay.

### Sprint 3 (Week 3): Autonomy + Bridge

```
P5  User trading config + autonomous schedule
P6  Context bridge (AI ↔ Trading)
P11 Observability (core panels: simulation, RAG, routing)
P17 RAGAS eval — Path A (search API smoke) + `/observe` scorecard
```

**Milestone:** Agents debate every 2h autonomously using Alex's research. AI answers trading questions. Observe shows simulation + RAG + **RAG quality scores**.

### Sprint 4 (Week 4): Intelligence Upgrade

```
P7  MCP expansion (SEC, News)
P15 Async deep research sub-agents + latency observability
P8  RL learning loop
P17 RAGAS Path B — eval full `/api/alex/chat` RAG path (after P2 live)
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
| **IaC** | 9 Terraform modules (VPC → guardrails) | Manual `start_session.sh` for env sync | Terraform outputs → GitHub env vars |
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
| **Token/cost tracking** | `agent_observations` — tokens, cost per call | Per-query cost in `query_latency_metrics` (P15) | Join tables for cost/query |
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
| **Scheduling** | EventBridge Scheduler (2h research, daily cost) | Cron + rate triggers | Per-user schedules (P5) |
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
| **P20** | Load testing + capacity planning | 2 days | Medium |

These phases layer on top of P0–P17 without blocking MVP delivery. **P17 (RAGAS)** is the single source of truth for eval implementation; PE P16/P18 add infra around it.

---

## Document Index

| Document | Purpose |
|----------|---------|
| `scripts/TEST_PLAYBOOK.md` | **Test after every addition** — 3-layer protocol (automated → deploy → frontend checkpoints) |
| `Alex_AI_2.0.md` | Detailed AI plan — router, RAG, MCP, synthesis, guardrails |
| `Alex_Trading_Floor_2.0.md` | Detailed trading plan — simulation, scout, RL, autonomy |
| `Alex_Master_Implementation_Plan.md` | **This file** — unified implementation order |
| `Startup.md` | Business model, monetization, startup ideas, unit economics |
| `Ophelia.md` | Interview prep — Alex → Ophelia mapping, talking points, intro |

---

*All documents are PARKED. Reply with your decision checklist selections to begin implementation.*
