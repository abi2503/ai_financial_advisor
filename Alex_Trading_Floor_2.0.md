# Alex Trading Floor 2.0 — Architecture & Implementation Plan

> **Status:** PARKED — awaiting approval before implementation  
> **Created:** June 13, 2026  
> **Scope:** Autonomous paper-trading simulation, MCP intelligence, RL learning, user-configurable debates, full observability mapping  
> **Change log:** All shipped changes must also be recorded in `Alex_report.md` §33 (rationale, tech, verification)  
> **Infrastructure:** All AWS resource changes via Terraform only — see `Alex_Master_Implementation_Plan.md` Infrastructure Policy

---

## Table of Contents

1. [Executive Summary](#executive-summary)
2. [Current State Assessment](#current-state-assessment)
3. [Target Architecture](#target-architecture)
4. [Phase 0.6 — Full Fresh Start Toggle (New-User State)](#phase-06--full-fresh-start-toggle-new-user-state)
5. [Phase 1 — Paper Trading Simulation Engine](#phase-1--paper-trading-simulation-engine)
6. [Phase 1.5 — Dashboard Recommendation Approval (Human-in-the-Loop)](#phase-15--dashboard-recommendation-approval-human-in-the-loop)
7. [Phase 2 — User-Configurable Autonomous Debates](#phase-2--user-configurable-autonomous-debates)
8. [Phase 3 — Agentic Add-ons](#phase-3--agentic-add-ons)
9. [Phase 4 — MCP Capabilities](#phase-4--mcp-capabilities)
10. [Phase 5 — RL Learning Loop](#phase-5--rl-learning-loop)
11. [Phase 6 — Observability Page Mapping](#phase-6--observability-page-mapping)
12. [Phase 7 — Frontend Changes](#phase-7--frontend-changes)
13. [Phase 8 — Infrastructure & Deploy](#phase-8--infrastructure--deploy)
14. [Implementation Phases & Estimates](#implementation-phases--estimates)
15. [MVP Recommendation](#mvp-recommendation)
16. [Risks & Guardrails](#risks--guardrails)
17. [Decision Points for Approval](#decision-points-for-approval)
18. [Key File Index](#key-file-index)
19. [Data Source & MCP Registry](#data-source--mcp-registry)
20. [Tools-Only Agent Action Model](#tools-only-agent-action-model)
21. [Tagger Agent & Tagged Observability](#tagger-agent--tagged-observability)

---

## Executive Summary

Alex already has a strong **analysis + paper-log** foundation: 6-agent debate, SQS/Lambda pipeline, trade history UI, and cost observability. What is missing is a **closed-loop simulation** (trades actually move paper positions), **autonomous scheduling**, **MCP-enriched intelligence**, **scouting beyond portfolio holdings**, and an **RL feedback loop** that improves agent weights over time.

This plan extends existing infrastructure rather than replacing it. All subsystems must be visible on the `/observe` observability page.

**Core user experience goal:** Agents autonomously trade against a virtual account seeded from the user's real portfolio value, with full transparency — the user watches a simulation replay of how agents debate, decide, and execute paper trades.

**Human-in-the-loop goal:** Debate outcomes surface on the **dashboard** as actionable recommendations for the user's **real** portfolio. Nothing is applied automatically — the user reviews rationale grounded in debate context and current holdings, then explicitly approves or dismisses. Approved actions update `portfolios` and are tagged **`trading_floor_recommendation`**.

**Testing goal:** Two reset controls — **Reset Debate Context** (trading sim only, ✅ implemented) and **Fresh Start** (all user Aurora data, P0.6) — so developers and users can return to a clean slate without dropping DDL or affecting other tenants.

**Observability goal:** Every data fetch, MCP call, tool invocation, and portfolio mutation is tagged by the **Tagger Agent** and visible on `/observe` with filterable tag pills — full traceability from debate → tool → portfolio change.

---

## Current State Assessment

### What Works Today

| Layer | Status | Key Files |
|-------|--------|-----------|
| 6 agents (Marcus, Victoria, Zara, Reid, Elena + Executor) | ✅ Working | `backend/agents/trading/agents/*.py` |
| Debate engine + SQS pipeline | ✅ Working | `backend/agents/trading/core/debate_engine.py` |
| Manual "Run Analysis" from `/trading` | ✅ Working | `frontend/app/api/trading/run/route.ts` |
| Trade log with full debate transparency | ✅ Working | `frontend/app/trading/page.tsx` |
| Portfolio → orchestrator ticker selection | ✅ Working | `backend/agents/trading/core/orchestrator.py` |
| Observability (`/observe`) — cost, latency, guardrails | ✅ Working | `frontend/app/observe/page.tsx` |
| Global ON/OFF toggle (SSM) | ✅ Working | `frontend/app/api/trading/toggle/route.ts` |
| Reset debate context (trading tables only) | ✅ Working | `frontend/app/api/trading/reset/route.ts`, `frontend/lib/tradingDb.ts` |
| Full fresh start (all user Aurora data) | 🔲 Planned | Phase 0.6 — `POST /api/account/fresh-start` |
| Tool-only agent actions (no direct SQL in agents) | 🔲 Planned | Tools-Only Action Model — refactor orchestrator/debate_engine |
| Tagger agent for observe / event labels | 🔲 Planned | Tagger Agent — Nova Lite post-action labeling |
| Market data (yfinance, CNN Fear & Greed, Polygon, Alpha Vantage) | ✅ Working | `backend/agents/trading/tools/market_data.py` |
| Portfolio research digests (every 2h) | ✅ Working | `portfolio_digests` table, dashboard cards |

### Critical Gaps

| Gap | Impact |
|-----|--------|
| Trades are **advisory only** — `agent_positions` never updated after BUY/SELL | No real simulation |
| No EventBridge schedule for trading debates | Not autonomous |
| `user_trading_config` table exists but is **unused** (orchestrator reads SSM instead) | No per-user settings |
| `agent_performance` table exists but has **zero writes** | No learning |
| `trading_daily_pnl` table exists but has **no INSERT/UPDATE** | No P&L rollup |
| Trading MCP stub is **empty** (`backend/agents/trading/mcp/__init__.py`) | No live web/SEC context in debates |
| Portfolio research digests **not fed** into agent debate prompts | Missed intelligence |
| Debate results **not surfaced** on dashboard for user approval | Simulation disconnected from real portfolio |
| No human-in-the-loop path from `simulated_trades` → `portfolios` | Users cannot adopt agent decisions safely |
| Observer Lambda exists but is **not deployed** | No daily digest email |
| `/observe` missing simulation, RL, P&L, scout panels | Incomplete observability |
| `simulated_trades.pnl` never populated | No outcome tracking |
| `trading_simulations.win_count/loss_count` never incremented | Win rate UI is stale |
| Orchestrator sends `MessageGroupId` to **standard** SQS queue | Potential send failures |
| `agent_observations` DDL missing from `aurora_warmup.py` | Observability may fail on fresh DB |
| `simulated_trades` schema missing `target_price`, `stop_loss` columns | Possible SQL errors on fresh DB |

### Current Agent Roster

| Agent | Role | Model Default | File |
|-------|------|---------------|------|
| Marcus Chen | Bull analyst | Nova Pro | `agents/marcus.py` |
| Victoria Sterling | Bear analyst | Nova Pro | `agents/victoria.py` |
| Zara Patel | Quant strategist | Nova Pro | `agents/zara.py` |
| Reid Morrison | Macro strategist | Nova Pro | `agents/reid.py` |
| Elena Vasquez | Risk manager | Nova Lite | `agents/elena.py` |
| Executor (Alex) | PM synthesis | Nova Pro | `core/debate_engine.py` → `run_executor()` |
| **Tagger (Nova)** (planned) | Metadata & observability labels | Nova Lite | `agents/tagger.py` — assigns tags to tool calls, events, recs |

### Current Trigger Flow

```
Manual:  Trading UI → POST /api/trading/run → alex-trading-orchestrator
                              ↓
                    SQS alex-trading-queue (one msg/ticker)
                              ↓
                    alex-debate-agent → run_debate() → simulated_trades

Fallback: orchestrator.run_direct_analysis() if TRADING_QUEUE_URL empty

Autonomous (planned): EventBridge → orchestrator (permission exists in Terraform, schedule missing)
Global gate: SSM /alex/trading/enabled (bypassed with force:true on manual run)
```

### Existing Aurora Tables (Trading)

| Table | Purpose | Usage Status |
|-------|---------|--------------|
| `trading_simulations` | Per-user paper account | Created/updated in orchestrator; `current_value` only |
| `simulated_trades` | Trade log with debate JSON | Written by debate_engine; read by `/api/trading` |
| `agent_positions` | Simulated holdings mirror | Synced from real `portfolios` on run; **not updated after trades** |
| `trading_daily_pnl` | Daily P&L rollup + digest | **Table exists; no writes** |
| `user_trading_config` | Per-user mode, autonomous, models, risk limits | **Table exists; orchestrator uses SSM instead** |
| `agent_observations` | Per-call tokens, cost, latency, guardrails | Written by `base_agent.store_observation()` |
| `agent_performance` | Weekly agent accuracy/outcome tracking | **Table exists; no writes** |
| `portfolio_digests` | Per-stock research cards (from portfolio research pipeline) | ✅ Active — not yet fed to trading agents |
| `trading_recommendations` (planned P1.5) | Pending dashboard recs from debate → user approve → real portfolio | **Not built** |

---

## Target Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                           USER LAYER                                     │
│  /trading (Simulation + Settings)  /observe (Full Observability)        │
│  /portfolio (holdings + rec badges)  /dashboard (pending recs + approve) │
└──────────────────────────────┬──────────────────────────────────────────┘
                               │
┌──────────────────────────────▼──────────────────────────────────────────┐
│                        SCHEDULING LAYER                                  │
│  EventBridge per-user schedule (2h/3h configurable)                    │
│  Manual "Run Analysis" trigger                                          │
│  Sentinel hourly position monitor (new)                                   │
└──────────────────────────────┬──────────────────────────────────────────┘
                               │
┌──────────────────────────────▼──────────────────────────────────────────┐
│                      ORCHESTRATION LAYER                                 │
│  alex-trading-orchestrator                                               │
│    ├── Scout Agent (new) — find attractive stocks outside portfolio      │
│    ├── Context Builder (new) — digests + market data + trade history     │
│    └── Queue debate tasks per ticker                                     │
└──────────────────────────────┬──────────────────────────────────────────┘
                               │
┌──────────────────────────────▼──────────────────────────────────────────┐
│                      INTELLIGENCE LAYER                                  │
│  5-Agent Parallel Debate (Marcus/Victoria/Zara/Reid/Elena)              │
│  Executor PM Synthesis                                                   │
│  MCP Tool Layer (Playwright, News, Market, Portfolio)                   │
│  Portfolio Research Digests (portfolio_digests)                          │
│  Market Data Providers (yfinance, Polygon, Alpha Vantage)                │
└──────────────────────────────┬──────────────────────────────────────────┘
                               │
┌──────────────────────────────▼──────────────────────────────────────────┐
│                      EXECUTION LAYER (new)                               │
│  Paper Trade Executor — BUY/SELL/TRIM/HOLD against virtual account       │
│  Position Manager — update agent_positions, cash_balance                 │
│  Cash Ledger — enforce position limits, stop-loss, daily trade caps       │
└──────────────────────────────┬──────────────────────────────────────────┘
                               │
┌──────────────────────────────▼──────────────────────────────────────────┐
│                      LEARNING LAYER (new)                                │
│  Trade Outcome Evaluator (daily batch)                                   │
│  RL Weight Updater — adaptive agent trust scores in Aurora               │
│  agent_performance table                                                 │
└──────────────────────────────┬──────────────────────────────────────────┘
                               │
┌──────────────────────────────▼──────────────────────────────────────────┐
│                      AURORA (alex_db)                                    │
│  trading_simulations | agent_positions | simulated_trades                │
│  user_trading_config | portfolio_digests | agent_observations            │
│  trading_daily_pnl | agent_performance | rl_weights (new)                │
│  scout_candidates (new) | trading_events (new)                           │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## Phase 0.6 — Full Fresh Start Toggle (New-User State)

**Goal:** Provide a **single toggle/button** that wipes **all user-scoped rows** in Aurora for the logged-in user, returning the platform to the same empty state as a **brand-new login** — clean portfolio, no chat history, no research memory, no simulation, no pending recommendations. Intended for **testing**, demos, and recovering from bad state without manual SQL.

> **Not the same as Reset Debate Context** (✅ implemented) — that only clears trading simulation tables and re-seeds from the existing portfolio. Fresh Start clears **everything** user-owned.

### Reset tiers (comparison)

| Control | Location | Scope | Portfolio | Chat / RAG | Trading sim | Re-seed after |
|---------|----------|-------|-----------|------------|-------------|---------------|
| **Reset Debate Context** | `/trading` | 8 trading tables | **Kept** | **Kept** | Cleared → re-seeded from portfolio | Yes — mirror current holdings |
| **Fresh Start** | `/trading` + `/dashboard` | All user-scoped tables (see below) | **Cleared** | **Cleared** | Cleared | **No** — empty like new user |
| **Fresh context on enable** | `/trading` checkbox | Trading tables only when turning ON | Kept | Kept | Cleared → re-seeded | Yes — on enable |

### What gets cleared (per-user `DELETE`)

Executed in **FK-safe order** via `frontend/lib/freshStart.ts` (or `backend/agents/trading/core/fresh_start.py` for Lambda reuse):

```
Tier 1 — Trading & recommendations
  trading_floor_intelligence
  trading_recommendations        (P1.5)
  simulated_trades
  agent_positions
  trading_daily_pnl
  trading_events
  scout_candidates
  rl_weights
  trading_simulations

Tier 2 — Portfolio & research
  portfolio_digests
  portfolios
  research_vectors               (user_id scoped)
  research_snapshots
  portfolio research queue refs  (if any per-user rows)

Tier 3 — Chat & session memory
  rag_attributions
  session_metadata
  chat_sessions
  query_latency_metrics          (user_id scoped)

Tier 4 — User preferences (optional — confirm in UI)
  user_trading_config
  preferences
```

### What is NEVER cleared

| Scope | Tables / data | Reason |
|-------|---------------|--------|
| **Global platform** | `ops_snapshots`, `cost_snapshots`, `cost_alerts`, `ragas_evaluations`, `knowledge_graph_*` | Shared infra / eval data |
| **User identity** | `users` row (Clerk `clerk_id` mapping) | User stays logged in |
| **Global agent metrics** | `agent_performance` (no `user_id`), `agent_observations` (optional retain for ops) | Platform observability |
| **Other users** | All rows where `user_id ≠ current user` | Multi-tenant safety |

> **DDL is not dropped.** `scripts/aurora_warmup.py` only ensures tables exist (`CREATE IF NOT EXISTS`). Fresh Start runs **`DELETE … WHERE user_id = …`** — schema stays intact for the next session.

### End-to-end flow

```
User taps "Fresh Start" on /trading or /dashboard
        │
        ▼
Confirmation modal (two-step):
  ① Checkbox: "I understand this deletes portfolio, chat, and simulation data"
  ② Type FRESH START to confirm
        │
        ▼
POST /api/account/fresh-start  { confirm: true, phrase: "FRESH START" }
        │
        ▼
fresh_start_wipe_user(clerk_id)
  → DELETE all tiers in FK order (single transaction where Aurora supports)
  → INSERT trading_events: event_type = 'fresh_start_completed'
        │
        ▼
Frontend clears local state:
  • Redirect to /dashboard (empty widgets)
  • Alex chat session cleared (new session_id)
  • Trading page shows zero trades / positions
  • Portfolio page empty — "Add your first holding"
```

### UI specification

**`/trading` header** (alongside existing Reset Context):

```
┌──────────────────────────────────────────────────────────────────┐
│ Trading ON/OFF  ☐ Fresh context on enable  ↺ Reset Context       │
│                                                                  │
│ [ ⚠ Fresh Start ]  ← destructive, amber/red outline button      │
└──────────────────────────────────────────────────────────────────┘
```

**`/dashboard` settings strip** (collapsible "Developer / Testing"):

```
┌──────────────────────────────────────────────────────────────────┐
│ Testing                                                          │
│ Reset debate context only     [↺ Reset Context →]                │
│ Wipe all my data (new user)   [⚠ Fresh Start →]                  │
└──────────────────────────────────────────────────────────────────┘
```

| UI rule | Implementation |
|---------|----------------|
| Destructive styling | Amber/red button, never primary indigo |
| Two-step confirm | Modal + type `FRESH START` |
| Post-wipe UX | Toast: "Account reset — add holdings to begin" |
| Disable during wipe | Button shows spinner; block double-submit |
| Clerk session | User remains authenticated; only Aurora data wiped |

### API

| Route | Method | Body | Response |
|-------|--------|------|----------|
| `/api/account/fresh-start` | POST | `{ confirm: true, phrase: "FRESH START" }` | `{ success, tables_cleared: string[], rows_deleted: number }` |
| `/api/account/fresh-start` | GET | — | `{ available: true, warning: string }` (optional pre-flight copy) |

Auth: Clerk `userId` required. No global/admin wipe from this endpoint (separate `scripts/admin_fresh_start.sh` for dev-only full DB if ever needed).

### Backend module

**File:** `frontend/lib/freshStart.ts` (Next.js API) + optional mirror `backend/agents/trading/core/fresh_start.py`

```python
USER_SCOPED_TABLES = [
    # order matters — children before parents
    "trading_floor_intelligence", "trading_recommendations",
    "simulated_trades", "agent_positions", "trading_daily_pnl",
    "trading_events", "scout_candidates", "rl_weights",
    "trading_simulations",
    "portfolio_digests", "portfolios",
    "research_vectors", "research_snapshots",
    "rag_attributions", "session_metadata", "chat_sessions",
    "query_latency_metrics",
    "user_trading_config", "preferences",
]

def wipe_user_data(clerk_id: str) -> dict:
    uid_subquery = "(SELECT id FROM users WHERE clerk_id = :uid)"
    for table in USER_SCOPED_TABLES:
        execute(f"DELETE FROM {table} WHERE user_id = {uid_subquery}")
    return {"tables_cleared": USER_SCOPED_TABLES, ...}
```

**Extend** existing `resetTradingDebateContext()` in `frontend/lib/tradingDb.ts` to call shared tier-1 list only — avoid duplicating table names (single `TRADING_CONTEXT_TABLES` constant).

### Observability

Log to `trading_events`:

```json
{
  "event_type": "fresh_start_completed",
  "payload": {
    "tables_cleared": 18,
    "rows_deleted": 142,
    "trigger": "dashboard" | "trading"
  }
}
```

`/observe` panel (optional P7): fresh starts per week (should be rare in production).

### Guardrails

| Risk | Mitigation |
|------|------------|
| Accidental wipe | Type-to-confirm `FRESH START`; checkbox acknowledgment |
| Cross-user data leak | Every `DELETE` uses `user_id = (SELECT id FROM users WHERE clerk_id = :uid)` |
| Partial wipe / FK error | Fixed delete order; wrap in try/except per table with rollback log |
| User thinks portfolio is real money | Modal copy: "Removes tracked holdings — not brokerage accounts" |
| Production abuse | Rate limit: max 3 fresh starts per user per day (SSM or `trading_events` count) |

### Deliverables (P0.6)

- `frontend/lib/freshStart.ts` — `wipeUserData(clerkId)`
- `frontend/app/api/account/fresh-start/route.ts`
- `frontend/components/FreshStartModal.tsx` — shared confirm UI
- Wire button on `/trading/page.tsx` and `/dashboard/page.tsx`
- Refactor `frontend/lib/tradingDb.ts` — export shared `TRADING_CONTEXT_TABLES`
- `scripts/tests/test_fresh_start.py` — unit test table order + mock SQL
- Document in `scripts/TEST_PLAYBOOK.md`

**Effort:** 1–2 days  
**Depends on:** P0 schema (tables exist); can ship alongside ✅ debate context reset

---

## Phase 1 — Paper Trading Simulation Engine

**Goal:** Agents trade against a virtual account seeded from the user's real portfolio value. The UI shows a live simulation the user can watch and replay.

### 1.1 Virtual Account Model

On first autonomous run per user:

```
initial_value = SUM(portfolio shares × live price) + cash_buffer
cash_balance  = initial_value - current_holdings_value
```

Stored in existing `trading_simulations` table (columns already exist: `initial_value`, `current_value`, `cash_balance`).

### 1.2 Paper Trade Executor (new module)

**File:** `backend/agents/trading/core/trade_executor.py`

After each debate produces `BUY | SELL | TRIM | HOLD`:

| Action | Simulation Behavior |
|--------|---------------------|
| **BUY** | Deduct cash at market price, add/increase `agent_positions`, log `simulated_trades` |
| **SELL** | Liquidate full position, add proceeds to cash, realize P&L on trade record |
| **TRIM** | Sell 25% of shares, partial P&L realization |
| **HOLD** | Log debate outcome only, no position change |

**Enforcement rules:**
- Max position % from `user_trading_config.max_position_pct` (default 25%)
- Stop-loss from `user_trading_config.stop_loss_pct` (default 8%)
- Max daily trades from `user_trading_config.max_daily_trades` (default 10)
- Minimum cash reserve (e.g. 10% of portfolio always kept liquid)
- Block BUY if insufficient cash
- Block SELL/TRIM if no position exists

**Post-execution updates:**
- `agent_positions` — shares, avg_cost, current_price, pnl, pnl_pct, last_action
- `trading_simulations` — current_value, cash_balance, total_trades, win_count, loss_count
- `simulated_trades` — realized_pnl, outcome (populated later by evaluator)

### 1.3 Frontend Simulation View (extend `/trading`)

New **"Simulation"** tab alongside existing Trades and Positions tabs:

| Panel | Data Source |
|-------|-------------|
| Virtual portfolio value vs initial | `trading_simulations.current_value` vs `initial_value` |
| Return % since simulation start | computed |
| Cash available | `trading_simulations.cash_balance` |
| Simulated holdings table | `agent_positions` |
| Trade timeline | `simulated_trades` ordered by `executed_at` |
| Per-trade P&L attribution | `simulated_trades.pnl` |
| Win rate / total trades | `trading_simulations.win_count / total_trades` |

**Replay mode:** Step through trades chronologically with animation:
> *"At 2:00 PM — Marcus voted BUY NVDA (82% confidence), Victoria dissented SELL. Executor approved BUY. Simulation purchased 5 shares @ $142.30. Cash remaining: $12,450."*

### 1.4 Aurora Schema Fixes (P0)

Add to `scripts/aurora_warmup.py`:

```sql
-- Fix simulated_trades schema
ALTER TABLE simulated_trades ADD COLUMN IF NOT EXISTS target_price NUMERIC(10,2);
ALTER TABLE simulated_trades ADD COLUMN IF NOT EXISTS stop_loss NUMERIC(10,2);
ALTER TABLE simulated_trades ADD COLUMN IF NOT EXISTS realized_pnl NUMERIC(12,2) DEFAULT 0;
ALTER TABLE simulated_trades ADD COLUMN IF NOT EXISTS outcome VARCHAR(20);
ALTER TABLE simulated_trades ADD COLUMN IF NOT EXISTS trigger VARCHAR(20) DEFAULT 'debate';

-- Ensure agent_observations exists
CREATE TABLE IF NOT EXISTS agent_observations (
  id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  user_id UUID REFERENCES users(id),
  agent_name VARCHAR(50),
  ticker VARCHAR(10),
  action VARCHAR(10),
  confidence NUMERIC(5,2),
  input_tokens INTEGER DEFAULT 0,
  output_tokens INTEGER DEFAULT 0,
  total_cost NUMERIC(10,6) DEFAULT 0,
  latency_ms INTEGER DEFAULT 0,
  guardrail_triggered BOOLEAN DEFAULT false,
  guardrail_reason TEXT,
  success BOOLEAN DEFAULT true,
  data_used JSONB DEFAULT '[]',
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- New tables
CREATE TABLE IF NOT EXISTS scout_candidates (
  id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  user_id UUID REFERENCES users(id),
  ticker VARCHAR(10) NOT NULL,
  score NUMERIC(5,2) DEFAULT 0,
  rationale TEXT,
  sector VARCHAR(50),
  discovered_at TIMESTAMPTZ DEFAULT NOW(),
  debated BOOLEAN DEFAULT false,
  traded BOOLEAN DEFAULT false
);

CREATE TABLE IF NOT EXISTS rl_weights (
  id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  user_id UUID REFERENCES users(id),
  agent_name VARCHAR(50) NOT NULL,
  weight NUMERIC(5,3) DEFAULT 1.0,
  accuracy_30d NUMERIC(5,3) DEFAULT 0,
  total_votes INTEGER DEFAULT 0,
  correct_votes INTEGER DEFAULT 0,
  updated_at TIMESTAMPTZ DEFAULT NOW(),
  UNIQUE(user_id, agent_name)
);

CREATE TABLE IF NOT EXISTS trading_events (
  id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  user_id UUID REFERENCES users(id),
  event_type VARCHAR(30) NOT NULL,
  ticker VARCHAR(10),
  agent VARCHAR(50),
  payload JSONB DEFAULT '{}',
  created_at TIMESTAMPTZ DEFAULT NOW()
);
```

**Bug fix:** Remove `MessageGroupId` from orchestrator SQS send (standard queue, not FIFO).

---

## Phase 1.5 — Dashboard Recommendation Approval (Human-in-the-Loop)

**Goal:** After each debate cycle, surface **actionable recommendations** on the user's dashboard for holdings in their real portfolio. The user reviews a **rationale built from debate context** (agent votes, executor synthesis, portfolio snapshot, digests) and explicitly **approves or dismisses**. Only on approval does Alex update the real `portfolios` table — tagged as a **Trading Floor recommendation**, never silent auto-trades.

### Design principle

| Layer | What changes | User control |
|-------|----------------|--------------|
| **Paper simulation** (`agent_positions`, `simulated_trades`) | Updates immediately per Phase 1 executor | Watch-only; "PAPER TRADING SIMULATION" |
| **Real portfolio** (`portfolios`) | **Only** after user taps **Approve** | Required explicit acceptance |

HOLD debates do not create dashboard recommendations. BUY, SELL, and TRIM do.

### End-to-end flow

```
debate_engine.run_debate(ticker)
        │
        ├── trade_executor → simulated_trades + agent_positions (paper)
        │
        └── recommendation_builder.create_pending()
                │
                ▼
        trading_recommendations (status = pending)
                │
        ┌───────┴────────┐
        ▼                ▼
   /dashboard      GET /api/trading/recommendations
   "Trading Floor   (pending cards with rationale)
    Recommendations"
        │
   User reviews:
   • ticker + action + confidence
   • holding context (shares, cost basis, weight %)
   • executor rationale + agent vote summary
   • link to full debate on /trading
        │
   ┌────┴────┐
   ▼         ▼
 Approve   Dismiss
   │         │
   ▼         └── status = dismissed
portfolio_applier.apply()
   │
   ├── UPSERT portfolios (shares, purchase_price)
   ├── SET source = 'trading_floor_recommendation'
   ├── SET notes = "Approved YYYY-MM-DD · {action} · conf {n}%"
   └── INSERT trading_events event_type = 'recommendation_approved'
```

### Rationale composition

**File:** `backend/agents/trading/core/recommendation_builder.py`

Each pending recommendation stores a structured rationale derived from debate context and the user's **current real holding** (not simulation):

```python
def build_recommendation_rationale(
    ticker: str,
    action: str,
    confidence: float,
    holding: dict,           # from portfolios — shares, purchase_price, weight
    agent_debate: list,      # from simulated_trades.agent_debate
    executor_rationale: str,
    portfolio_summary: dict, # total value, position count
    digest_snippet: str | None = None,  # from portfolio_digests
) -> dict:
    return {
        "headline": f"{action} {ticker} — {confidence:.0f}% confidence",
        "executor_summary": executor_rationale,
        "holding_context": {
            "shares": holding.get("shares"),
            "avg_cost": holding.get("purchase_price"),
            "weight_pct": holding.get("weight_pct"),
            "current_value": holding.get("market_value"),
        },
        "portfolio_context": {
            "total_positions": portfolio_summary.get("position_count"),
            "total_market_value": portfolio_summary.get("total_market_value"),
        },
        "agent_consensus": [
            {"agent": v["agent"], "action": v["action"], "confidence": v["confidence"],
             "opening": v.get("opening_statement", "")[:120]}
            for v in agent_debate
        ],
        "research_snippet": digest_snippet,
        "disclaimer": "Paper simulation result — not financial advice. Approve to reflect in your tracked portfolio.",
    }
```

Displayed on dashboard as a readable card; full `agent_debate` JSON linked to `/trading` trade detail.

### Aurora schema (new)

Add to `scripts/aurora_warmup.py`:

```sql
CREATE TABLE IF NOT EXISTS trading_recommendations (
  id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  user_id UUID REFERENCES users(id) NOT NULL,
  simulation_id UUID REFERENCES trading_simulations(id),
  simulated_trade_id UUID REFERENCES simulated_trades(id),
  ticker VARCHAR(10) NOT NULL,
  action VARCHAR(10) NOT NULL,           -- BUY | SELL | TRIM (not HOLD)
  shares INTEGER DEFAULT 0,
  price NUMERIC(10,2) DEFAULT 0,
  total_value NUMERIC(12,2) DEFAULT 0,
  confidence NUMERIC(5,2) DEFAULT 0,
  status VARCHAR(20) DEFAULT 'pending', -- pending | approved | dismissed | expired
  rationale JSONB NOT NULL DEFAULT '{}',
  agent_debate JSONB DEFAULT '[]',
  portfolio_snapshot JSONB DEFAULT '{}', -- holding state at recommendation time
  created_at TIMESTAMPTZ DEFAULT NOW(),
  resolved_at TIMESTAMPTZ,
  expires_at TIMESTAMPTZ                  -- optional: auto-expire after 7 days
);

CREATE INDEX IF NOT EXISTS tr_user_status_idx
  ON trading_recommendations (user_id, status, created_at DESC);

-- Tag real portfolio rows applied from Trading Floor
ALTER TABLE portfolios ADD COLUMN IF NOT EXISTS source VARCHAR(30) DEFAULT 'user';
ALTER TABLE portfolios ADD COLUMN IF NOT EXISTS recommendation_id UUID REFERENCES trading_recommendations(id);
```

| Column | Purpose |
|--------|---------|
| `trading_recommendations.status` | Workflow state; dashboard queries `pending` only |
| `simulated_trade_id` | Audit link back to paper trade + debate JSON |
| `portfolio_snapshot` | Frozen holding at recommendation time for rationale display |
| `portfolios.source` | `'user'` (manual entry) vs `'trading_floor_recommendation'` (approved) |
| `portfolios.recommendation_id` | Traceability to the approved recommendation |

**Reset debate context** (`POST /api/trading/reset`) should set related pending recommendations to `expired` (not delete — preserves audit trail).

### Portfolio apply rules (on approve)

**File:** `backend/agents/trading/core/portfolio_applier.py`

| Action | Real `portfolios` update |
|--------|-------------------------|
| **BUY** | Upsert ticker: increase `shares`, weighted-average `purchase_price`, `source = trading_floor_recommendation` |
| **SELL** | Reduce shares to 0 (or remove row if fully liquidated) |
| **TRIM** | Reduce shares by recommendation amount (25% of simulated trim) |

Never apply if:
- User has no Clerk session / wrong `user_id`
- Recommendation already `approved` or `dismissed`
- Ticker not in portfolio and action is SELL/TRIM (guard: block or require scout flow in v2)

Emit `trading_events` row: `event_type = 'recommendation_approved' | 'recommendation_dismissed'`.

### Dashboard UI

**Location:** `frontend/app/dashboard/page.tsx` — new section **"Trading Floor Recommendations"** (below Quick Actions or above Portfolio Research).

```
┌─────────────────────────────────────────────────────────────────────┐
│  Trading Floor Recommendations                    [View all → /trading] │
├─────────────────────────────────────────────────────────────────────┤
│  NVDA · BUY · 82% confidence                          2h ago          │
│  You hold 12 shares @ $118.40 (18.2% of portfolio)                  │
│  Executor: "5-agent consensus BUY — Marcus/Zara bullish, Elena       │
│  approves size. Target $145, stop $108."                             │
│  Marcus BUY 85% · Victoria SELL 40% · Zara BUY 78% · …              │
│                                                                     │
│  [Dismiss]                              [Approve → Update Portfolio]  │
└─────────────────────────────────────────────────────────────────────┘
```

| UI element | Behavior |
|------------|----------|
| Pending count badge | Dashboard greeting or quick-action tile: "3 recommendations" |
| Approve button | `POST /api/trading/recommendations/{id}/approve` → refresh portfolio + mark approved |
| Dismiss button | `POST /api/trading/recommendations/{id}/dismiss` → no portfolio change |
| Portfolio tag | Approved holdings show badge **Trading Floor** on `/portfolio` |
| Empty state | "No pending recommendations — Run Analysis on Trading Floor" |

### API routes (new)

| Route | Method | Purpose |
|-------|--------|---------|
| `/api/trading/recommendations` | GET | List pending (+ optional `?status=approved` history) for dashboard |
| `/api/trading/recommendations/[id]/approve` | POST | Apply to `portfolios`, tag source, set `resolved_at` |
| `/api/trading/recommendations/[id]/dismiss` | POST | Mark dismissed, no portfolio write |

Extend `GET /api/trading` to include `pending_recommendations_count` for dashboard polling.

### Integration with existing phases

| Phase | Relationship |
|-------|----------------|
| **P1 Paper executor** | Creates `simulated_trades` that `recommendation_builder` reads |
| **P3 Context bridge** | `portfolio_digests` + `research_vectors` enrich rationale JSON |
| **P6 RL** | Approved recommendations can later feed outcome evaluator ("did user adopt winning trades?") |
| **P7 Observability** | Panel: recommendations pending vs approved rate, time-to-approve |

### Guardrails

| Rule | Implementation |
|------|----------------|
| No auto-apply to real portfolio | `portfolio_applier` only called from approve API |
| Clear simulation vs real distinction | Dashboard card disclaimer + portfolio `source` badge |
| Idempotent approve | Second approve on same `id` returns 409 |
| Audit trail | `trading_recommendations` + `trading_events` + `recommendation_id` on portfolio row |
| Expiry | Optional `expires_at`; cron or dashboard hides stale pending recs |

### Deliverables (P1.5)

- `backend/agents/trading/core/recommendation_builder.py`
- `backend/agents/trading/core/portfolio_applier.py`
- Wire into `debate_engine.py` after `store_trade()` for non-HOLD actions
- `frontend/app/api/trading/recommendations/route.ts`
- `frontend/app/api/trading/recommendations/[id]/approve/route.ts`
- `frontend/app/api/trading/recommendations/[id]/dismiss/route.ts`
- `frontend/components/TradingRecommendations.tsx` (dashboard widget)
- `scripts/aurora_warmup.py` — `trading_recommendations` + `portfolios.source` columns

**Effort:** 2–3 days  
**Depends on:** P1 (paper executor + `simulated_trades` with debate JSON)

---

## Phase 2 — User-Configurable Autonomous Debates

**Goal:** User sets debate frequency (2h / 3h / manual only) and trading parameters from the frontend. Agents run autonomously on schedule.

### 2.1 Per-User Config (wire `user_trading_config`)

| Field | UI Control | Default | Description |
|-------|-----------|---------|-------------|
| `autonomous` | ON/OFF toggle | `true` | Enable scheduled debates |
| `debate_interval_hours` | Dropdown: 2h / 3h / 4h / manual | `2` | How often agents debate |
| `trading_mode` | aggressive / neutral / safe | `neutral` | Agent vote weighting |
| `scout_enabled` | Toggle | `false` | Allow buying non-portfolio stocks |
| `max_position_pct` | Slider 5–50% | `25` | Max % of portfolio per position |
| `stop_loss_pct` | Slider 3–15% | `8` | Auto-sell trigger |
| `max_daily_trades` | Number input | `10` | Daily trade cap |
| `model_marcus` etc. | Advanced panel | Nova Pro | Per-agent model override |

**Frontend:** "Agent Settings" panel on `/trading`  
**API:** `GET/POST /api/trading/config` → reads/writes `user_trading_config` via RDS Data API

### 2.2 Scheduling Options

**Option A — Per-user EventBridge schedules (full autonomy):**
```
alex-trading-{user_hash}  →  rate(2 hours)  →  alex-trading-orchestrator
Payload: { user_id, trigger: 'scheduled' }
```
- Created/updated when user saves config
- Deleted when `autonomous=false`

**Option B — Single schedule, orchestrator loops users (simpler MVP):**
```
alex-trading-auto  →  rate(2 hours)  →  orchestrator
Orchestrator: SELECT users WHERE autonomous=true AND debate_interval_hours matches current slot
```

**Recommended for MVP:** Option B. Upgrade to Option A in v2.

**Gates applied before each run:**
1. Global SSM `/alex/trading/enabled` (master kill switch)
2. `user_trading_config.autonomous = true`
3. `debate_interval_hours` matches current 2-hour slot
4. Optional: market hours only (9:30 AM – 4:00 PM ET weekdays)
5. Daily trade count < `max_daily_trades`

### 2.3 Debate Scope Per Cycle

Each scheduled run debates:

1. **All portfolio holdings** — always
2. **Scout candidates** (if `scout_enabled=true`) — top 3 by score, not yet debated
3. **Stale positions** — holdings with no debate in >24 hours

---

## Phase 3 — Agentic Add-ons

### 3.1 New Agents

| Agent | Role | When It Runs | File |
|-------|------|--------------|------|
| **Scout** | Scans market for attractive stocks outside portfolio | Before each debate cycle (if scout_enabled) | `agents/scout.py` (new) |
| **Sentinel** | Monitors open positions for stop-loss / take-profit | Hourly between debate cycles | `agents/sentinel.py` (new) |
| **Historian** | Summarizes past trade outcomes for agent context | Before each debate | `agents/historian.py` (new) |
| **Research Bridge** | Pulls portfolio_digests into debate prompts | Context build step | `core/context_builder.py` (new) |

### 3.2 Scout Agent — "Buy Attractive Stocks"

```
Scout Agent
  ├── Input: user mode, sector preferences, cash available, existing holdings
  ├── Tools: MCP news scanner, sector movers, momentum screeners, yfinance
  ├── Process:
  │     1. Screen top gainers / unusual volume in user's preferred sectors
  │     2. Cross-reference with portfolio research digests
  │     3. Score candidates 0-100 with rationale
  │     4. Return top 3-5 candidates
  └── Output: scout_candidates table
```

Full 6-agent debate then runs on each scout candidate. Executor can approve BUY into simulation.

**Guardrails:**
- Only runs when `scout_enabled=true` AND cash > 20% of portfolio value
- Max 2 new positions per week
- Block tickers already in portfolio
- Block highly correlated tickers (same sector ETF overlap)
- Elena (risk manager) has veto power on scout candidates

### 3.3 Sentinel Agent — Between-Cycle Monitoring

Lightweight check (hourly Lambda or orchestrator sub-task):

- Read `agent_positions` with `target_price` / `stop_loss` from last trade
- If current price breaches stop-loss → auto SELL in simulation
- If current price hits target → auto TRIM 50% in simulation
- Log to `simulated_trades` with `trigger='sentinel'`
- Write `trading_events` row
- Emit CloudWatch metric `SentinelTrigger`

### 3.4 Historian Agent — Memory for Debates

Before each debate, inject into all agent prompts:

```
=== TRADE HISTORY FOR NVDA ===
Past 10 simulated trades:
  3/15 BUY @ $142 → +8.2% after 5 days (Marcus correct ✓, Victoria wrong ✗)
  3/18 HOLD → -2.1% (Zara correct ✓)
  3/22 TRIM @ $155 → +4.5% (Elena correct ✓)

Agent accuracy (30-day): Marcus 72% | Victoria 45% | Zara 68% | Reid 61% | Elena 74%
Current RL weights: Marcus 1.15x | Victoria 0.82x | ...
```

Data sourced from `agent_performance` + `simulated_trades` + `rl_weights`.

### 3.5 Research Bridge — Portfolio Intelligence → Trading

Connects the portfolio research pipeline (built in prior session) to trading decisions:

```
portfolio_digests (updated every 2h by portfolio research scheduler)
  → Research Bridge reads latest digest per ticker
  → Injected as "Alex's Latest Research on {ticker}" in all debate prompts
  → Includes: headline, sentiment, key_news bullets, dimension summaries
```

**File:** `backend/agents/trading/core/context_builder.py`

```python
def build_debate_context(user_id, ticker) -> str:
    # 1. portfolio_digests for ticker
    # 2. agent_positions current state
    # 3. last 5 simulated_trades for ticker
    # 4. agent_performance summary
    # 5. live market data (price, volume, fear/greed)
    # 6. rl_weights for vote context
    return formatted_context_string
```

---

## Phase 4 — MCP Capabilities

**Goal:** Give trading agents live-web intelligence similar to the researcher service.

### 4.1 MCP Tool Layer

**Directory:** `backend/agents/trading/mcp/` (currently empty stub)

| MCP Server | Tools | Used By |
|------------|-------|---------|
| **Playwright** (reuse from `backend/researcher/mcp_servers.py`) | Browse news sites, analyst pages, SEC EDGAR | Scout, Marcus, Victoria |
| **Market MCP** (new thin wrapper) | `get_stock_data`, `get_options_chain`, `get_sector_etf` | Zara, Reid |
| **News MCP** (new) | `search_financial_news`, `get_earnings_calendar` | All agents |
| **Portfolio MCP** (new) | `get_user_portfolio`, `get_past_trades`, `get_research_digest` | Executor, Historian |

### 4.2 Integration Pattern

```
debate_engine.run_debate(ticker, user_id)
  │
  ├── context_builder.build(user_id, ticker)    # Aurora + market data + digests
  │
  ├── [Scout only] mcp_gateway.get_tools('playwright')
  │     └── Scout browses live news before candidate scoring
  │
  ├── agents run (5 parallel, ThreadPoolExecutor)
  │     └── Each receives rich context (no per-agent MCP in MVP)
  │
  └── executor.synthesize(votes, context)
```

### 4.3 Pragmatic Rollout

| Stage | Scope |
|-------|-------|
| **MVP** | Context builder pre-fetches everything from Aurora + yfinance. No MCP in debate agents. |
| **v2** | Scout gets Playwright MCP for live web scanning |
| **v3** | Marcus/Victoria get News MCP for real-time headline verification |
| **v4** | Full MCP-per-agent with observability of tool calls |

### 4.4 MCP Observability

Every MCP tool call logged to `agent_observations.data_used`:
```json
{ "tool": "playwright_browse", "url": "...", "latency_ms": 3200, "success": true }
```

Visible on `/observe` in new "MCP Tool Usage" panel.

---

## Phase 5 — RL Learning Loop

**Goal:** Agents improve vote weights based on past trade outcomes. Lightweight reward system in Aurora — no heavy ML infrastructure.

### 5.1 Outcome Evaluator (daily batch Lambda)

**New Lambda:** `alex-trade-evaluator`  
**Schedule:** Daily at 5:00 PM ET (after market close)  
**File:** `backend/agents/trading/learning/trade_evaluator.py`

For each `simulated_trades` row older than 1 day where `outcome IS NULL`:

```
1. Fetch price at trade time (stored) vs price 1d / 5d / 30d later (yfinance)
2. Score each action:
   BUY  + price up over 5d   → correct (+1)
   BUY  + price down over 5d → incorrect (-1)
   SELL + price down over 5d → correct (+1)
   SELL + price up over 5d   → incorrect (-1)
   HOLD + abs(return) < 2%   → neutral (0)
   TRIM + subsequent rise     → partial correct (+0.5)
3. Attribute score to each agent's vote (weighted by their confidence)
4. Write per-agent outcome to agent_performance table
5. Update simulated_trades.outcome + realized_pnl
6. Emit trading_events row: event_type='outcome_evaluated'
```

### 5.2 RL Weight Updater

**File:** `backend/agents/trading/learning/weight_updater.py`  
**Runs:** After evaluator, same daily schedule

```python
# For each agent, over rolling 30-day window:
accuracy = correct_votes / total_votes  # range 0.0 to 1.0

# Minimum 10 votes before weight changes
if total_votes < 10:
    new_weight = 1.0  # default
else:
    new_weight = clamp(0.5 + accuracy, 0.5, 1.5)

# Store in rl_weights table (per user, per agent)
```

### 5.3 Dynamic Vote Weights in Debate Engine

**Current (static):**
```python
MODE_WEIGHTS = {
    'aggressive': { 'marcus': 1.3, 'victoria': 0.7, 'zara': 1.1, ... },
    'neutral':    { 'marcus': 1.0, 'victoria': 1.0, 'zara': 1.0, ... },
    'safe':       { 'marcus': 0.7, 'victoria': 1.3, 'zara': 0.9, ... },
}
```

**Proposed (learned):**
```python
effective_weight = MODE_WEIGHTS[mode][agent] × rl_weights[user_id][agent]
```

Poor-performing agents get downweighted over time. Consistently accurate agents gain influence.

### 5.4 What This Is NOT

- Not training custom neural networks (too heavy for Lambda/Aurora)
- Not real-money execution
- Not guaranteed alpha — it is **adaptive agent trust scoring**
- Not immutable — weights reset if user changes trading mode

### 5.5 Future Upgrade Path

If outcomes are positive:
- Contextual bandits per ticker/sector
- SageMaker endpoint for policy model
- Multi-armed bandit for scout candidate selection
- For now: **tabular RL in Aurora is the right MVP**

---

## Phase 6 — Observability Page Mapping

**Goal:** Every subsystem reports to `/observe`. Nothing happens in the dark.

### 6.1 New Observability Panels

| Panel | Data Shown | Aurora Source | Tags (via Tagger) |
|-------|-----------|---------------|-------------------|
| **Simulation Health** | Active simulations, total virtual AUM, avg return % | `trading_simulations` | `domain:trading`, `layer:simulation` |
| **Daily P&L Chart** | 7-day simulated P&L trend line | `trading_daily_pnl` | `domain:trading`, `layer:data` |
| **Agent Accuracy Leaderboard** | Per-agent win rate, avg P&L attribution, trend arrow | `agent_performance` | `domain:trading`, `layer:agent` |
| **RL Weights Chart** | How agent trust weights evolved over 30 days | `rl_weights` | `domain:trading`, `layer:learning` |
| **Scout Activity** | Candidates discovered, debated, traded conversion rate | `scout_candidates` + `simulated_trades` | `domain:trading`, `agent:scout` |
| **Debate Schedule** | Last run time, next scheduled run, interval per user | `user_trading_config` + EventBridge | `domain:trading`, `layer:schedule` |
| **MCP Tool Usage** | Tools called, avg latency, error rate | `agent_observations.data_used` | `layer:mcp`, `source:{server}` |
| **Data Source Health** | Per-API pass/fail, latency, tier | `query_latency_metrics.data_sources` | `layer:data`, `tier:{1\|2\|3}`, `source:{api}` |
| **System Action Log** | Portfolio updates, rec approvals, fresh starts | `trading_events` + `tool_invocations` | `layer:action`, `action:{name}` |
| **Tag Explorer** | Filter all events by tag prefix / agent / source | `event_tags` + `tool_invocations` | All tag dimensions |
| **Sentinel Triggers** | Auto stop-loss / take-profit events today | `simulated_trades WHERE trigger='sentinel'` | `agent:sentinel`, `action:trim\|sell` |
| **Trade Replay Feed** | Live stream of latest 20 simulation trades | `simulated_trades ORDER BY executed_at DESC` | `domain:trading`, `layer:execution` |
| **Recommendation Queue** | Pending / approved / dismissed recs | `trading_recommendations` | `layer:action`, `action:recommendation` |
| **Cost per Trade** | Bedrock $/trade, tokens/trade | `agent_observations` aggregated | `layer:agent`, `domain:trading` |
| **Guardrail Log** | (existing) Last 10 guardrail hits | `agent_observations` | `layer:guardrail` |
| **Platform Cost** | (existing) 7-day total cost, tokens, calls | `agent_observations` | `domain:platform` |
| **Per-Agent Stats** | (existing) Cost, latency, action distribution | `agent_observations` | `agent:{name}` |

### 6.2 Unified Event Timeline

New `trading_events` table powers a chronological audit log on `/observe`:

```
10:00 AM  debate_start     NVDA   orchestrator   {"agents": 5, "mode": "neutral"}
10:02 AM  agent_vote       NVDA   marcus         {"action": "BUY", "confidence": 82}
10:02 AM  agent_vote       NVDA   victoria       {"action": "SELL", "confidence": 71}
10:03 AM  trade_execute    NVDA   executor       {"action": "BUY", "shares": 5, "price": 142.30}
10:03 AM  scout_find       TSM    scout          {"score": 87, "rationale": "AI capex tailwind"}
02:00 PM  sentinel_trigger NVDA   sentinel       {"action": "TRIM", "reason": "target_price hit"}
05:00 PM  outcome_evaluated NVDA  evaluator      {"outcome": "correct", "pnl": +8.2%}
05:01 PM  rl_update        —      weight_updater {"marcus": 1.15, "victoria": 0.82}
```

### 6.3 Observer Lambda Deployment

Deploy existing `backend/agents/trading/observer/observer_agent.py`:

- Aggregates day's trading activity
- Generates Nova Lite digest
- Writes to `trading_daily_pnl.digest`
- Sends SES email to user
- Schedule: 4:30 PM ET weekdays
- Add to `terraform/9_trading_floor/main.tf`
- Add to `scripts/deploy_trading.sh`

### 6.4 API Extensions

Extend `frontend/app/api/observe/route.ts` to return:

```typescript
{
  platform: { ... },          // existing
  agents: [ ... ],          // existing
  guardrails: [ ... ],      // existing
  simulation: {              // new
    active_users, total_aum, avg_return
  },
  daily_pnl: [ ... ],       // new — 7-day trend
  agent_accuracy: [ ... ],    // new — from agent_performance
  rl_weights: [ ... ],        // new
  scout_activity: { ... },    // new
  recent_trades: [ ... ],     // new — last 20
  trading_events: [ ... ],    // new — timeline
}
```

---

## Phase 7 — Frontend Changes

### Page-by-Page Summary

| Page | Changes |
|------|---------|
| **`/trading`** | Simulation tab; Agent Settings; Scout panel; RL badge; **Reset Debate Context** (✅); **Fresh Start** toggle (P0.6); "PAPER TRADING SIMULATION" banner |
| **`/observe`** | All Phase 6 panels; **Tag Explorer**, **Data Source Map**, **Tool Invocation Log**; tag filter bar (P5.5) |
| **`/portfolio`** | Link to Trading Floor; agent badge; `trading_floor_recommendation` source tag |
| **`/dashboard`** | Trading Floor Recommendations widget (P1.5); simulation summary; **Testing strip** with Fresh Start + Reset Context |
| **`Navbar`** | Add Trading Floor + Observability links |

### New API Routes

| Route | Method | Purpose |
|-------|--------|---------|
| `/api/trading/reset` | POST | Reset debate context only (✅ implemented) |
| `/api/account/fresh-start` | POST | Wipe all user-scoped Aurora rows — new-user state (P0.6) |
| `/api/trading/recommendations` | GET | Pending + history recommendations for dashboard |
| `/api/trading/recommendations/[id]/approve` | POST | User accepts → apply to `portfolios` with `trading_floor_recommendation` tag |
| `/api/trading/recommendations/[id]/dismiss` | POST | User rejects → no portfolio change |
| `/api/trading/config` | GET, POST | Per-user trading settings (user_trading_config) |
| `/api/trading/simulation` | GET | Virtual portfolio state, holdings, cash, replay data |
| `/api/trading/scout` | GET | Scout candidates for user |
| `/api/trading/performance` | GET | Agent accuracy + RL weights |
| `/observe` | GET (extend) | All simulation, P&L, RL, scout, events, **tag explorer**, data source map |

### Agent Settings UI Mockup

```
┌─────────────────────────────────────────────────┐
│  Agent Settings                          [Save]  │
├─────────────────────────────────────────────────┤
│  Autonomous Trading        [ON ●━━━━━━━ OFF]    │
│  Debate Interval           [Every 2 hours ▼]     │
│  Trading Mode              [Neutral ▼]           │
│  Scout New Stocks          [OFF]                 │
│                                                 │
│  Risk Limits                                    │
│  Max Position    [━━━━━━●━━] 25%                │
│  Stop Loss       [━━●━━━━━━] 8%                 │
│  Max Daily Trades [10]                          │
│                                                 │
│  Agent Weights (learned)                        │
│  Marcus  ●━━━━━━━━ 1.15x  (72% accuracy)       │
│  Victoria ●━━━━━━━ 0.82x  (45% accuracy)       │
│  Zara     ●━━━━━━━━ 1.08x  (68% accuracy)       │
│  Reid     ●━━━━━━━ 0.95x  (61% accuracy)       │
│  Elena    ●━━━━━━━━ 1.12x  (74% accuracy)       │
└─────────────────────────────────────────────────┘
```

---

## Phase 8 — Infrastructure & Deploy

### Terraform Changes (`terraform/9_trading_floor/main.tf`)

| Resource | Action |
|----------|--------|
| `aws_scheduler_schedule.trading_auto` | **Add** — `rate(2 hours)` → orchestrator |
| `aws_scheduler_schedule.trade_evaluator` | **Add** — `cron(0 22 * * ? *)` (5PM ET) → evaluator Lambda |
| `aws_scheduler_schedule.trading_observer` | **Add** — `cron(30 21 * * ? *)` (4:30PM ET) → observer Lambda |
| `aws_scheduler_schedule.sentinel` | **Add** — `rate(1 hour)` → sentinel Lambda |
| `aws_lambda_function.trade_evaluator` | **Add** |
| `aws_lambda_function.trading_observer` | **Add** |
| `aws_lambda_function.sentinel` | **Add** |
| `aws_sqs_queue.trading_dlq` | **Add** — dead letter queue |
| Fix orchestrator SQS | Remove `MessageGroupId` from send call |

### Deploy Script Changes (`scripts/deploy_trading.sh`)

Package and deploy:
- `trade_executor.py`
- `context_builder.py`
- `agents/scout.py`
- `agents/sentinel.py`
- `agents/historian.py`
- `learning/trade_evaluator.py`
- `learning/weight_updater.py`
- `mcp/` (when ready)

### SSM Parameters (new)

| Parameter | Default | Purpose |
|-----------|---------|---------|
| `/alex/trading/scout_enabled` | `false` | Global scout master switch |
| `/alex/trading/mcp_enabled` | `false` | Global MCP master switch |
| `/alex/trading/market_hours_only` | `true` | Only debate during market hours |

### `scripts/aurora_warmup.py`

Add all new tables and schema fixes from Phase 1.4.

### `scripts/start_session.sh`

- Enable trading EventBridge schedule on session start
- Deploy observer + evaluator if not running
- Update orchestrator/reporter Lambda env with ECS_URL

---

## Implementation Phases & Estimates

| Phase | Scope | Effort | Depends On |
|-------|-------|--------|------------|
| **P0 — Fixes** | Schema fixes, FIFO bug, `agent_observations` warmup, `simulated_trades` columns | 2–3 days | — |
| **P0.6 — Fresh Start** | Full user wipe toggle, type-to-confirm, dashboard + trading UI | 1–2 days | P0 |
| **P1 — Simulation** | Paper trade executor, position manager, simulation UI, P&L tracking | 3–4 days | P0 |
| **P1.5 — Recommendations** | Dashboard pending recs, approve/dismiss, `portfolios` apply + source tag | 2–3 days | P1 |
| **P2 — Autonomy** | `user_trading_config` UI + API, EventBridge schedule, debate interval config | 2–3 days | P1 |
| **P3 — Intelligence** | Research bridge, Historian context, `context_builder.py` | 2–3 days | P1 |
| **P4 — Scout** | Scout agent, `scout_candidates`, scout UI panel | 3–4 days | P2, P3 |
| **P5 — MCP** | Playwright for Scout, News MCP, tool observability, **tools-only refactor** | 4–5 days | P4 |
| **P5.5 — Tagger** | Tagger agent, `event_tags` table, observe tag panels | 2 days | P5, P6 |
| **P6 — RL Loop** | Trade evaluator Lambda, weight updater, accuracy leaderboard | 3–4 days | P1 |
| **P7 — Observability** | Full `/observe` expansion, `trading_events`, observer deploy | 3–4 days | P1–P6 |
| **P8 — Sentinel** | Hourly stop-loss monitor, auto TRIM/SELL | 2 days | P1, P2 |

**Total estimate:** ~4–5 weeks for the full plan.  
**MVP estimate:** ~2 weeks (P0 + P1 + **P1.5** + P2 + minimal P7).

---

## MVP Recommendation

Fastest path to *"agents autonomously trading a simulation the user can watch, with optional adoption into their tracked portfolio"*:

### MVP = P0 + P1 + P1.5 + P2 + minimal P7

**Delivers:**
- ✅ Virtual account seeded from real portfolio value
- ✅ Agents actually BUY/SELL/TRIM in simulation (positions update)
- ✅ **Dashboard recommendations with debate rationale — user approves before real portfolio changes**
- ✅ Approved holdings tagged **`trading_floor_recommendation`** on `/portfolio`
- ✅ User configures 2h / 3h debate interval from frontend
- ✅ Simulation replay on `/trading`; **Reset Debate Context** for testing (✅ implemented)
- ✅ Basic P&L + trade count on `/observe`
- ✅ Schema fixes and FIFO bug resolved
- ✅ **Reset Debate Context** for trading-only test runs (implemented)
- 🔲 **Fresh Start** toggle for full new-user state (P0.6)

**Defers to v2:**
- Scout agent (buying non-portfolio stocks)
- Full MCP per agent
- RL weight learning
- Sentinel auto stop-loss
- Observer daily email
- Research bridge context injection

---

## Risks & Guardrails

| Risk | Mitigation |
|------|-----------|
| ECS/Bedrock cost from frequent debates | Per-user daily trade cap; cost-per-trade metric on `/observe`; alert if daily cost > $5 |
| Scout buys bad stocks | Score threshold ≥70; Elena veto; max 2 new positions/week; user opt-in only |
| MCP latency blows Lambda timeout | Pre-fetch context in `context_builder`; MCP only on Scout (not all 5 debate agents) |
| RL overfits to recent noise | 30-day rolling window; minimum 10 votes before weight changes; max weight swing ±50% |
| User confuses simulation with real money | Persistent "PAPER TRADING SIMULATION" banner on `/trading` and `/observe`; dashboard approve step before any real `portfolios` write |
| User approves recommendation without reading rationale | Require explicit Approve tap; show holding context + agent summary; disclaimer on every card |
| Stale pending recommendations after reset | `POST /api/trading/reset` expires open `trading_recommendations` for that user |
| Accidental full data wipe | Fresh Start requires type `FRESH START` + checkbox; rate limit 3/day per user |
| Fresh Start during active debate | Disable button while `running` analysis; queue drain optional |
| Aurora cold starts delay trades | Keep existing warmup pattern in orchestrator + debate_agent |
| Runaway autonomous trading | `max_daily_trades` cap; global SSM kill switch; per-user autonomous toggle |
| Stale market data | yfinance with fallback; data_quality score in debate result; HOLD if data_quality < 0.5 |
| Untagged observe events | Hard to filter/debug on `/observe` | Tagger agent (P5.5) labels all tool/MCP/action events into `event_tags` |
| Direct SQL bypasses audit | Tools-only model (P5); `tool_invocations` required for mutations |

---

## Decision Points for Approval

Before implementation begins, confirm:

| # | Decision | Options | Recommendation |
|---|----------|---------|----------------|
| 1 | **Scope** | MVP only (P0–P2) vs full plan (P0–P8) | Start MVP, iterate |
| 2 | **Scout autonomy** | Allow agents to buy stocks NOT in portfolio? | Default: OFF, user opt-in |
| 3 | **Debate interval default** | 2h / 3h / 4h | 2h default, user picks 2/3/4/manual |
| 4 | **Market hours gate** | Debates only 9:30 AM–4 PM ET, or 24/7? | Market hours only (configurable) |
| 5 | **RL approach** | Lightweight Aurora weights vs SageMaker ML | Lightweight Aurora for MVP |
| 6 | **MCP scope** | Scout-only first vs all agents get tools | Scout-only in v2, context builder in MVP |
| 7 | **Observer email** | Daily simulation digest to user email? | Yes, deploy in P7 |
| 8 | **Scheduling model** | Single schedule looping users vs per-user EventBridge | Single schedule for MVP |
| 9 | **Simulation seed** | Mirror real portfolio exactly vs fixed virtual budget (e.g. $100k) | Mirror real portfolio value |
| 10 | **Navbar links** | Add Trading + Observe to main nav? | Yes |
| 11 | **Recommendation adoption** | Auto-apply debate results to real portfolio vs user approve on dashboard? | **Dashboard approve only** (P1.5); simulation never writes `portfolios` directly |
| 12 | **Recommendation expiry** | Pending recs expire after N days vs stay until dismissed? | 7-day expiry default |
| 13 | **Fresh Start scope** | Trading tables only vs all user Aurora data? | **All user-scoped tables** (P0.6); never global/platform rows |
| 14 | **Fresh Start in production** | Dev-only vs available to all users? | Available with strong confirm; rate-limited |
| 15 | **Tools-only actions** | Gradual refactor vs big-bang before P1? | New code tools-only; refactor orchestrator in P5 |
| 16 | **Tagger placement** | Inline per event vs async batch? | Async after tool call (Nova Lite); batch for observe rollup |

---

## Key File Index

### Existing (to extend)

```
frontend/app/trading/page.tsx
frontend/app/observe/page.tsx
frontend/app/api/trading/route.ts
frontend/app/api/trading/run/route.ts
frontend/app/api/trading/toggle/route.ts
frontend/app/api/trading/reset/route.ts          # ✅ debate context reset (testing)
frontend/app/api/account/fresh-start/route.ts    # P0.6 — full user wipe
frontend/app/api/observe/route.ts
frontend/app/api/portfolio/route.ts

backend/agents/trading/core/orchestrator.py
backend/agents/trading/core/debate_engine.py
backend/agents/trading/core/debate_agent.py
backend/agents/trading/observer/observer_agent.py
backend/agents/trading/agents/base_agent.py
backend/agents/trading/tools/market_data.py
backend/agents/trading/models/__init__.py
backend/agents/trading/mcp/__init__.py  (empty stub)

terraform/9_trading_floor/main.tf
scripts/deploy_trading.sh
scripts/test_trading.sh
scripts/aurora_warmup.py
scripts/start_session.sh
```

### New (to create)

```
backend/agents/trading/core/trade_executor.py       # Paper trade execution
backend/agents/trading/core/recommendation_builder.py  # P1.5 — pending dashboard recs
backend/agents/trading/core/portfolio_applier.py      # P1.5 — apply approved rec to portfolios
backend/agents/trading/core/context_builder.py      # Rich debate context
backend/agents/trading/agents/scout.py              # Market scout agent
backend/agents/trading/agents/sentinel.py           # Stop-loss monitor
backend/agents/trading/agents/historian.py          # Trade history context
backend/agents/trading/learning/trade_evaluator.py  # Daily outcome scoring
backend/agents/trading/learning/weight_updater.py   # RL weight updates
backend/agents/trading/mcp/market_mcp.py            # Market data MCP wrapper
backend/agents/trading/mcp/news_mcp.py              # News search MCP
backend/agents/trading/mcp/portfolio_mcp.py         # Portfolio context MCP
backend/agents/trading/mcp/tool_gateway.py          # P5 — tools-only gateway
backend/agents/trading/agents/tagger.py             # P5.5 — observability tagger
backend/agents/trading/core/tagger_pipeline.py      # P5.5 — post-tool labeling
backend/researcher/mcp/mcp_gateway.py               # Research MCP router
backend/researcher/mcp/quant/quant_gateway.py       # P13 quant router

frontend/app/api/trading/config/route.ts
frontend/app/api/trading/recommendations/route.ts
frontend/app/api/trading/recommendations/[id]/approve/route.ts
frontend/app/api/trading/recommendations/[id]/dismiss/route.ts
frontend/app/api/trading/simulation/route.ts
frontend/components/TradingRecommendations.tsx    # Dashboard widget (P1.5)
frontend/components/FreshStartModal.tsx           # P0.6 — type-to-confirm wipe
frontend/lib/tradingDb.ts                         # ✅ reset debate context helper
frontend/lib/freshStart.ts                        # P0.6 — wipe all user-scoped tables
frontend/components/ObserveTagPills.tsx           # P5.5 — observe filter pills
frontend/app/api/trading/scout/route.ts
frontend/app/api/trading/performance/route.ts
```

---

## Data Source & MCP Registry

**Goal:** Single canonical map of **every external API**, **MCP server**, and **internal data store** used across Alex Research, Trading Floor, and the Quant layer — who consumes what, cost tier, and observability tag prefix.

### Registry overview

```
                    ┌─────────────────────────────────────┐
                    │         DATA & MCP GATEWAY          │
                    │  mcp_gateway / quant_gateway        │
                    │  trading/mcp/tool_gateway.py        │
                    └──────────────┬──────────────────────┘
           ┌───────────────────────┼───────────────────────┐
           ▼                       ▼                       ▼
    Tier 1 APIs (free)      Tier 2 APIs (paid)      Internal stores
    yfinance, FRED,         Polygon, Finnhub,       Aurora, SageMaker
    Fear&Greed, EDGAR       Alpha Vantage,          embeddings, S3
                            Unusual Whales
           │                       │                       │
           └───────────────────────┴───────────────────────┘
                                   │
              ┌────────────────────┼────────────────────┐
              ▼                    ▼                    ▼
        Alex Researcher      Trading Floor 6       Portfolio Reporter
        (fast/deep/chat)     (debate agents)       (2h digests)
```

### Tier 1 — Live today (free / low cost)

| Data Source | Access | Wrapper today | MCP (target) | Key tools | Consumers | Observe tag |
|-------------|--------|---------------|--------------|-----------|-----------|-------------|
| **Yahoo Finance** | `yfinance` | `tools.py`, `market_data.py` | `market_price_mcp` | `get_quote`, `get_ohlcv`, `get_fundamentals` | Marcus, Zara, Fast Alex, Scout | `data:yfinance`, `tier:1` |
| **Yahoo Finance RSS** | HTTP | `tools.py` | `financial_news_mcp` | `get_headlines` | Deep Alex, Marcus | `data:yahoo_rss`, `tier:1` |
| **CNN Fear & Greed** | HTTP scrape | `market_data.fetch_fear_greed` | `sentiment_mcp` | `get_fear_greed_index` | Reid, Elena | `data:fear_greed`, `tier:1` |
| **SEC EDGAR** | `edgartools` | `tools.py` | `sec_edgar_mcp` | `get_filings`, `get_insider_trades` | Deep Alex, Victoria | `data:sec_edgar`, `mcp:sec`, `tier:1` |
| **Playwright MCP** | `@playwright/mcp` | `mcp_servers.py` | `playwright_mcp` | `browse`, `snapshot` | Deep Alex, Scout (planned) | `mcp:playwright`, `tier:1` |
| **pandas-ta / numpy** | Local compute | `market_data.py` (partial) | `technical_mcp` | `calc_rsi`, `calc_macd`, `detect_support_resistance` | Zara | `data:computed`, `tier:1` |
| **Aurora PostgreSQL** | RDS Data API | `context_service`, orchestrator | `aurora_tool.*` | `read_portfolio`, `read_digests`, `search_vectors` | All agents | `data:aurora`, `tier:1` |
| **SageMaker Embeddings** | `alex-embedding` | `context_service.embed_text` | `embedding_tool` | `embed`, `batch_embed` | RAG, P14 ingest | `data:sagemaker`, `tier:1` |
| **Amazon Bedrock** | `bedrock-runtime` | All `invoke()` | — | `invoke_model` | All LLM agents | `model:bedrock` |

### Tier 2 — Configured / planned (paid)

| Data Source | Wrapper today | MCP (target) | Consumers | Observe tag |
|-------------|---------------|--------------|-----------|-------------|
| **Polygon.io** | `market_data.fetch_polygon` | `polygon_mcp` | Zara, Scout | `data:polygon`, `tier:2` |
| **Alpha Vantage** | `market_data.fetch_alpha_vantage` | `alpha_vantage_mcp` | Zara, Reid | `data:alpha_vantage`, `tier:2` |
| **Finnhub** | — | `finnhub_mcp` | Marcus, Fast Alex | `data:finnhub`, `tier:2` |
| **FRED** | — | `macro_mcp` / `fred_mcp` | Reid, Elena | `data:fred`, `tier:2` |
| **NewsAPI / Benzinga** | — | `financial_news_mcp` | Marcus, Victoria | `data:newsapi`, `tier:2` |

### Tier 3 — Differentiation

| Data Source | MCP (target) | Consumers | Observe tag |
|-------------|--------------|-----------|-------------|
| **Unusual Whales** | `options_flow_mcp` | Zara, Scout | `data:unusual_whales`, `tier:3` |
| **CBOE / VIX** | `volatility_mcp` | Elena, Zara | `data:cboe`, `tier:3` |
| **Chart render → S3** | `chart_mcp` | Alex UI, Zara | `mcp:chart`, `tier:3` |
| **Sector ETFs** | `sector_mcp` | Reid, Scout | `data:sector`, `tier:3` |

### MCP server catalog

| MCP Server | Path | Status | Primary agents |
|------------|------|--------|----------------|
| `playwright_mcp` | `backend/researcher/mcp_servers.py` | ✅ Live | Deep Alex, Scout |
| `sec_edgar_mcp` | `backend/researcher/mcp/sec_edgar_mcp.py` | 🔲 Planned | Victoria, Deep Alex |
| `financial_news_mcp` | `backend/researcher/mcp/financial_news_mcp.py` | 🔲 Planned | Marcus, Victoria |
| `market_price_mcp` | `backend/researcher/mcp/quant/market_price_mcp.py` | 🔲 P13 | Zara, Scout |
| `technical_mcp` | `backend/researcher/mcp/quant/technical_mcp.py` | 🔲 P13 | Zara |
| `macro_mcp` | `backend/researcher/mcp/quant/macro_mcp.py` | 🔲 P13 | Reid, Elena |
| `options_flow_mcp` | `backend/researcher/mcp/quant/options_flow_mcp.py` | 🔲 P13 | Zara |
| `portfolio_mcp` | `backend/agents/trading/mcp/portfolio_mcp.py` | 🔲 P4 | Executor, Historian |
| `market_mcp` | `backend/agents/trading/mcp/market_mcp.py` | 🔲 P4 | Zara, Reid |
| `simulation_mcp` | `backend/agents/trading/mcp/simulation_mcp.py` | 🔲 P5 | Executor, Sentinel |
| `action_mcp` | `backend/agents/trading/mcp/action_mcp.py` | 🔲 P5 | Executor, API bridge |

### Internal data stores

| Store | Written by | Read by | Tag |
|-------|-----------|---------|-----|
| `portfolios` | User UI, `portfolio_tool.apply` | Orchestrator, RAG | `store:portfolios` |
| `portfolio_digests` | Reporter Lambda | Dashboard, context_builder | `store:digests` |
| `research_vectors` | Chat/deep ingest | `context_service` | `store:research_vectors` |
| `trading_floor_intelligence` | debate_ingest (P14) | Historian | `store:tfi` |
| `quant_snapshots` | quant_gateway (P13) | Zara | `store:quant_snapshots` |
| `simulated_trades` | `simulation_tool` | Trading UI, recs | `store:simulated_trades` |
| `trading_recommendations` | `recommendation_tool` | Dashboard | `store:recommendations` |
| `tool_invocations` | All action tools | `/observe` | `store:tool_log` |
| `event_tags` | Tagger agent | Tag Explorer | `store:tags` |

---

## Tools-Only Agent Action Model

**Goal:** **No agent or API handler may mutate system state directly.** All portfolio updates, simulation trades, recommendations, config changes, and account wipes go through **registered tools** with schema validation, idempotency keys, audit logging, and Tagger labels.

### Principle

| ❌ Forbidden | ✅ Required |
|-------------|------------|
| `rds.execute_statement(INSERT…)` inside `marcus.py` | `tool_gateway.call("simulation_tool.log_trade", …)` |
| Direct `portfolios` UPDATE in API route | `portfolio_tool.upsert_holding` |
| Orchestrator inline SQL | `schedule_tool.enqueue_debate` + read tools |

### Tool catalog — read

| Tool | Consumers |
|------|-----------|
| `market_tool.get_snapshot` | All debate agents |
| `digest_tool.get_for_ticker` | context_builder |
| `vector_tool.search_research` | Historian, Alex |
| `quant_tool.get_snapshot` | Zara (P13) |
| `portfolio_tool.get_holdings` | Executor, Orchestrator |
| `simulation_tool.get_positions` | Executor, Sentinel |

### Tool catalog — action (mutations)

| Tool | Trigger | Observe tag |
|------|---------|-------------|
| `simulation_tool.execute_trade` | Post-debate paper trade | `action:simulation:execute` |
| `simulation_tool.log_trade` | Debate stores trade JSON | `action:simulation:log` |
| `simulation_tool.reset_context` | Reset Context button | `action:simulation:reset` |
| `recommendation_tool.create_pending` | Non-HOLD debate | `action:recommendation:create` |
| `recommendation_tool.approve` | Dashboard approve | `action:recommendation:approve` |
| `recommendation_tool.dismiss` | Dashboard dismiss | `action:recommendation:dismiss` |
| `portfolio_tool.upsert_holding` | Approve BUY/TRIM | `action:portfolio:upsert` |
| `portfolio_tool.remove_holding` | Approve SELL | `action:portfolio:remove` |
| `account_tool.fresh_start` | Fresh Start toggle | `action:account:fresh_start` |
| `config_tool.update_trading` | Settings save | `action:config:update` |
| `schedule_tool.enqueue_debate` | Orchestrator | `action:schedule:enqueue` |

### `tool_invocations` table

```sql
CREATE TABLE IF NOT EXISTS tool_invocations (
  id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  correlation_id VARCHAR(36),
  user_id UUID REFERENCES users(id),
  agent_name VARCHAR(50),
  tool_name VARCHAR(100) NOT NULL,
  idempotency_key VARCHAR(36),
  payload JSONB DEFAULT '{}',
  result JSONB DEFAULT '{}',
  success BOOLEAN DEFAULT true,
  latency_ms INTEGER DEFAULT 0,
  tags JSONB DEFAULT '[]',
  created_at TIMESTAMPTZ DEFAULT NOW()
);
```

**Migration:** P1 uses tools for new executor code; P5 refactors orchestrator + debate_engine; P0.6/P1.5 API routes wrap existing logic in tool modules.

---

## Tagger Agent & Tagged Observability

**Goal:** A dedicated **Tagger Agent** (Nova Lite) assigns **all** observability and UI classification tags. Hardcoded tags in frontend are display-only; source of truth is `event_tags` written by Tagger.

### Tagger Agent

| Property | Value |
|----------|-------|
| File | `backend/agents/trading/agents/tagger.py` |
| Model | Nova Lite |
| Triggers | Post `tool_invocations`; post debate; hourly observe rollup |
| Does NOT | Trade, recommend, or mutate portfolio |

### Tag schema

```typescript
interface EventTag {
  event_id: string
  event_type: 'tool' | 'debate' | 'recommendation' | 'query' | 'guardrail' | 'data_fetch'
  tags: string[]           // e.g. ["domain:trading", "action:portfolio:upsert", "tier:1"]
  dimensions: {
    domain?:  'trading' | 'research' | 'portfolio' | 'platform' | 'system'
    layer?:   'data' | 'mcp' | 'tool' | 'agent' | 'action' | 'simulation' | 'guardrail'
    source?:  string       // yfinance, polygon, playwright
    agent?:   string
    action?:  string
    tier?:    '1' | '2' | '3'
    ticker?:  string
    status?:  'success' | 'error'
  }
}
```

```sql
CREATE TABLE IF NOT EXISTS event_tags (
  id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  event_id VARCHAR(36) NOT NULL,
  event_type VARCHAR(30) NOT NULL,
  user_id UUID REFERENCES users(id),
  tags JSONB DEFAULT '[]',
  dimensions JSONB DEFAULT '{}',
  created_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS et_tags_gin ON event_tags USING gin (tags);
```

### `/observe` tag UX (full observability)

| Panel | Tags shown |
|-------|------------|
| **Tag filter bar** | Multi-select: `domain:*`, `layer:*`, `action:*`, `source:*` |
| **Data Source Map** | Live registry § tier health + `tier:1/2/3` pills |
| **Tool Invocation Log** | Every mutation/read tool with tag pills + latency |
| **Research queries** | Route + MCP + data source tags per row |
| **Trading events** | Debate, execute, recommendation, approve tags |
| **Tag Explorer** | Search `event_tags`; click tag → filter all panels |

**Pill colors** (extend `TagPills.tsx` / `ObserveTagPills.tsx`):

| Prefix | Color |
|--------|-------|
| `layer:data` | gray |
| `layer:mcp` | cyan |
| `layer:action` / `layer:tool` | amber |
| `domain:trading` | purple |
| `rec:*` | green |
| `action:portfolio:*` | blue |
| `tier:3` | gold outline |

### API

`GET /api/observe?tags=domain:trading,action:portfolio:*` returns `toolInvocations`, `eventTags`, `dataSourceHealth`, `tagSummary`.

**Deliverables (P5.5):** `tagger.py`, `tagger_pipeline.py`, `event_tags` DDL, `ObserveTagPills.tsx`, observe panel wiring.

---

## Relationship to Portfolio Research Pipeline

The portfolio research pipeline (implemented prior to this plan) feeds directly into Trading Floor 2.0:

```
EventBridge (every 2h)
  → scheduler reads portfolios
  → planner queues dimension tasks per stock
  → ECS fast/deep research agents
  → portfolio_digests table
  → dashboard "Your Portfolio Research" cards

Trading Floor 2.0 adds:
  → Research Bridge reads portfolio_digests
  → Injects into debate agent prompts
  → Scout uses digests to score candidates
  → Historian + RL weights inform agent trust
  → Recommendation Bridge (P1.5) surfaces debate outcomes on /dashboard
  → User approves → real portfolios updated (tag: trading_floor_recommendation)
  → All mutations via tools-only gateway → Tagger labels → /observe
```

Both pipelines share:
- Aurora `portfolios` table (source of truth for holdings)
- `user_trading_config` (trading settings)
- `/observe` (unified observability)
- EventBridge scheduling infrastructure

---

*This document is the single source of truth for Alex Trading Floor 2.0. Update status here as phases are approved and implemented.*

---

## Related Documents

| Document | Purpose |
|----------|---------|
| `Alex_AI_2.0.md` | Conversational AI — query routing, session RAG, MCP, synthesis, guardrails |
| `Alex_Master_Implementation_Plan.md` | **Unified implementation order** combining this doc + Alex AI 2.0 |

### Integration Points with Alex AI 2.0

- **Research Bridge** (Phase 3) reads `portfolio_digests` produced by the portfolio research pipeline
- **Context Builder** (Phase 3) reads `research_vectors` from Alex AI chat sessions
- **Historian agent** uses Alex AI session memory in debate prompts
- **AI Synthesizer** proactively compares simulation P&L vs real portfolio
- **RL weights** visible on `/observe` alongside RAG performance metrics
- See `Alex_Master_Implementation_Plan.md` for unified sprint plan
