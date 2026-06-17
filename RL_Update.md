# Alex RL Learning Loop + Model/Mode Selectors + Observability

**Document:** `RL_Update.md`  
**Date:** June 16, 2026  
**Status:** Plan — awaiting approval before execution  
**Companion specs:** `Alex_Trading_Floor_2.0.md` Phase 5, `Alex_Master_Implementation_Plan.md` P8/P9/P11, `Alex_report.md` §34

**Contents:** §1–11 implementation plan · **§12 debater RL use cases & full upgrade requirements** · **§13 model fine-tuning + debate data plane**

---

## Executive summary

Today Alex’s trading floor is a **fixed-weight committee**: 5 agents vote, `MODE_WEIGHTS` in `debate_engine.py` decides the outcome, trades are logged, but **nothing learns from results**. The `rl_weights` and `agent_performance` tables are **schema-only**.

We will add a **lightweight tabular RL loop** (not neural-net training): score past paper trades → update per-agent trust weights → use those weights in the next debate → show everything on `/observe` and let users pick **mode + models** on `/trading`.

**End state (§13):** Tabular RL tells Alex **which agent to trust**; **richer data feeds** give agents the facts to argue with; **per-persona fine-tuning** teaches Marcus/Victoria/Zara/Reid/Elena to debate like specialists — citing numbers, counter-arguing, and staying in voice. See **§13** for the full data-source matrix and fine-tuning path.

This matches **P8** in `Alex_Master_Implementation_Plan.md` and **Phase 5** in `Alex_Trading_Floor_2.0.md`.

---

## 1. Current setup vs. target (what changes)

### Today (as-is)

```
User → /trading Run Analysis
     → alex-trading-orchestrator (Lambda)
     → SQS → alex-debate-agent
     → debate_engine.run_debate()
           • 5 agents (Marcus…Elena) — models from SSM defaults
           • calculate_decision(votes, mode) uses STATIC MODE_WEIGHTS only
           • INSERT simulated_trades (outcome/realized_pnl usually NULL)
     → /observe shows chat/research metrics only
```

| Piece | Status today |
|-------|----------------|
| `MODE_WEIGHTS` | Hardcoded in `debate_engine.py` |
| `rl_weights` table | Created in `aurora_warmup.py`, **never written** |
| `agent_performance` table | **never written** |
| `user_trading_config` | Has `trading_mode` + `model_*` columns, **no UI/API** |
| `/alex/trading/mode` SSM | Terraform default `neutral`, **not user-editable from UI** |
| Per-agent models | Orchestrator reads SSM (`models/marcus`, etc.) — **partially wired** |
| Outcome evaluator | **Does not exist** |
| `/observe` RL panels | **Missing** |

### Target (after implementation)

```
Daily (5 PM ET) alex-trade-evaluator Lambda
     → score simulated_trades (1d/5d/30d price vs action)
     → write agent_performance
     → alex-rl-updater → rl_weights (per user, per agent)

Next debate:
     effective_weight = MODE_WEIGHTS[mode][agent] × rl_weights[user][agent]

Frontend /trading:
     Mode selector (aggressive | neutral | safe)
     Model selector (per agent + executor)

/observe:
     RL weights chart, agent accuracy leaderboard, model-wise performance
```

---

## 2. Architecture (end-to-end)

```mermaid
flowchart TB
    subgraph ui [Frontend]
        TR[/trading — mode + model selectors]
        OBS[/observe — RL + model perf]
    end

    subgraph debate [Trading Floor — unchanged trigger]
        ORCH[orchestrator]
        DEB[debate_engine]
        ORCH --> DEB
    end

    subgraph learn [New — daily learning]
        EVAL[alex-trade-evaluator]
        RL[alex-rl-updater]
        EVAL --> RL
    end

    subgraph db [Aurora]
        ST[(simulated_trades)]
        AP[(agent_performance)]
        RW[(rl_weights)]
        UTC[(user_trading_config)]
        AO[(agent_observations)]
        QLM[(query_latency_metrics)]
    end

    TR -->|PUT /api/trading/config| UTC
    TR --> ORCH
    DEB -->|read rl_weights| RW
    DEB -->|read config| UTC
    DEB --> ST
    DEB --> AO
    EVAL --> ST
    EVAL --> AP
    RL --> RW
    OBS --> AP
    OBS --> RW
    OBS --> QLM
    OBS --> AO
```

---

## 3. Phased implementation (recommended order)

| Phase | Scope | Est. | Depends on |
|-------|--------|------|------------|
| **P8a — Outcome foundation** | Trade evaluator + populate `outcome`, `realized_pnl` | 2 days | None |
| **P8b — RL updater** | `weight_updater.py` + `rl_weights` writes | 1 day | P8a |
| **P8c — Debate integration** | `effective_weight` in `calculate_decision` | 0.5 day | P8b |
| **P8d — Observe UI** | RL + accuracy + model panels | 2 days | P8b |
| **P9a — Trading config API** | GET/PUT mode + models → `user_trading_config` | 1 day | None (parallel) |
| **P9b — Trading UI selectors** | Mode + model dropdowns on `/trading` | 1 day | P9a |
| **P9c — AWS model enablement** | Bedrock access + SSM model registry | 0.5 day | User approval |
| **P9d — Model performance** | Aggregate by `model_id` on observe + trading | 1 day | P8d |

**Total:** ~8–9 focused days, split into **3 PRs** (learning backend → observe → frontend config).

---

## 4. Step-by-step: what we build and what logic changes

### Step 1 — Outcome evaluator (new Lambda)

**New files:**

- `backend/agents/trading/learning/trade_evaluator.py`
- `terraform/9_trading_floor` — `alex-trade-evaluator` + EventBridge `cron(0 22 ? * MON-FRI *)` (5 PM ET)

**Logic:**

For each `simulated_trades` row where `outcome IS NULL` and trade is ≥1 day old:

1. Fetch entry price (stored) vs yfinance price at +1d, +5d, +30d
2. Score action correctness (from spec in `Alex_Trading_Floor_2.0.md` §5.1)
3. Attribute fractional credit to each agent vote (by confidence)
4. `INSERT` into `agent_performance`
5. `UPDATE simulated_trades SET outcome, realized_pnl`
6. `INSERT trading_events` (`event_type='outcome_evaluated'`)

**What changes from current:** trades stop being “fire and forget”; they become **labeled training data**.

**Scoring rules (from `Alex_Trading_Floor_2.0.md`):**

| Action | Condition (5d horizon) | Score |
|--------|------------------------|-------|
| BUY | Price up | +1 (correct) |
| BUY | Price down | -1 (incorrect) |
| SELL | Price down | +1 |
| SELL | Price up | -1 |
| HOLD | \|return\| < 2% | 0 (neutral) |
| TRIM | Subsequent rise | +0.5 (partial) |

---

### Step 2 — RL weight updater

**New file:** `backend/agents/trading/learning/weight_updater.py`  
**Runs:** chained after evaluator (same Lambda or separate)

**Formula (MVP — from spec):**

```python
# Rolling 30-day window per (user_id, agent_name)
accuracy = correct_votes / total_votes   # 0.0 – 1.0

if total_votes < 10:
    weight = 1.0                         # cold start — no learning yet
else:
    weight = clamp(0.5 + accuracy, 0.5, 1.5)

UPSERT rl_weights (user_id, agent_name, weight, accuracy_30d, ...)
```

**Safeguards:**

- Min 10 votes before weight moves off 1.0
- Max swing per update: ±0.1 (optional smoothing)
- Max total range: 0.5 – 1.5
- Emit `trading_events` `event_type='rl_weight_updated'`

**What this is NOT:**

- Not training custom neural networks
- Not real-money execution
- Not guaranteed alpha — **adaptive agent trust scoring**
- Weights can reset when user changes trading mode (optional policy)

---

### Step 3 — Wire RL into debate engine (core behavior change)

**File:** `backend/agents/trading/core/debate_engine.py`

**Today:**

```python
def calculate_decision(votes: list, mode: str) -> tuple:
    weights = MODE_WEIGHTS.get(mode, MODE_WEIGHTS["neutral"])
    ...
        w = weights.get(vote.agent.lower(), 1.0)
```

**After:**

```python
def calculate_decision(votes, mode, rl_weights: dict[str, float] | None = None):
    base = MODE_WEIGHTS.get(mode, MODE_WEIGHTS["neutral"])
    rl   = rl_weights or {}
    for vote in votes:
        agent = vote.agent.lower()
        w = base.get(agent, 1.0) * rl.get(agent, 1.0)
        ...
```

**New helper:** `load_rl_weights(user_id) → dict` from Aurora.

**Orchestrator change:** pass `user_id` into `run_debate`, load weights before `calculate_decision`.

**Observable in debate output:** store `effective_weights` in `simulated_trades.agent_votes` JSON or new column `weight_snapshot JSONB`.

**Current static mode weights (reference):**

```python
MODE_WEIGHTS = {
    "aggressive": {"marcus": 2.0, "zara": 1.5, "reid": 1.0, "victoria": 0.5, "elena": 0.5},
    "neutral":    {"marcus": 1.0, "zara": 1.0, "reid": 1.0, "victoria": 1.0, "elena": 1.0},
    "safe":       {"marcus": 0.5, "zara": 0.5, "reid": 1.0, "victoria": 1.5, "elena": 2.0},
}
```

**Proposed effective weight:**

```python
effective_weight = MODE_WEIGHTS[mode][agent] × rl_weights[user_id][agent]
```

---

### Step 4 — Observe page extensions

**Files:**

- `frontend/app/api/observe/route.ts` — new SQL sections
- `frontend/app/observe/page.tsx` — new panels

**New API sections:**

| Panel | Data source | What user sees |
|-------|-------------|----------------|
| **RL Weights Evolution** | `rl_weights` history (add `rl_weight_history` table OR use `trading_events`) | Line chart: Marcus 1.0 → 1.2 over 30d |
| **Agent Accuracy Leaderboard** | `agent_performance` | Win rate, avg P&L attribution, trend ▲▼ |
| **Learning Events** | `trading_events` where type ∈ `outcome_evaluated`, `rl_weight_updated` | Audit trail |
| **Model Performance** | `agent_observations` + `query_latency_metrics` grouped by `model_id` | Cost, latency, success rate per model |
| **Simulation P&L** (optional P8+) | `simulated_trades`, `trading_daily_pnl` | Paper portfolio curve |

**Tag convention (future P5.5):** `domain:trading`, `layer:learning` on events.

---

### Step 5 — Frontend mode + model selectors

**New API:** `GET/PUT /api/trading/config`

Reads/writes `user_trading_config`:

- `trading_mode`: `aggressive` | `neutral` | `safe`
- `model_marcus`, `model_victoria`, … `model_executor`

**UI on `/trading`:** settings card above “Run Analysis”

| Control | Maps to | Effect |
|---------|---------|--------|
| **Mode selector** | `user_trading_config.trading_mode` + passed to orchestrator | Changes `MODE_WEIGHTS` base |
| **Model selector (per agent)** | `model_*` columns | Each agent uses chosen Bedrock model |
| **Preset buttons** | “Cost optimized”, “Quality”, “Balanced” | One-click model bundle |

**Orchestrator already supports per-agent models** via `config.get("models", {})` in `run_debate` — we mainly need **persist + load user config**.

**Existing schema (`aurora_warmup.py`):**

```sql
user_trading_config (
  trading_mode VARCHAR(20) DEFAULT 'neutral',
  model_marcus, model_victoria, model_zara, model_reid, model_elena, model_executor
  -- defaults: Pro for analysts, Lite for Elena
)
```

---

### Step 6 — AWS model configuration (for approval)

Currently **Amazon Nova** is used everywhere. `base_agent.py` and `bedrock_cost.py` also list **Claude Haiku/Sonnet**. Before execution, enable chosen models in Bedrock (us-east-1).

### Suggested model tiers

| Tier | Marcus / Victoria / Zara / Reid | Elena (risk) | Executor | Est. cost/debate | Quality |
|------|----------------------------------|--------------|----------|------------------|---------|
| **A — Current (default)** | Nova Pro | Nova Lite | Nova Pro | ~$0.08–0.12 | Baseline |
| **B — Cost optimized** ⭐ | Nova Lite | Nova Micro | Nova Lite | ~$0.01–0.02 | Good for paper sim |
| **C — Balanced** | Nova Pro | Nova Lite | Nova Pro | ~$0.06–0.10 | Recommended MVP |
| **D — Quality** | Claude 3.5 Sonnet | Claude 3.5 Haiku | Sonnet | ~$0.25–0.40 | Best reasoning, expensive |
| **E — A/B test** | Mixed per agent via UI | User picks | User picks | Variable | Enables model-wise RL comparison |

**Recommendation for MVP:** **Tier C (Balanced)** with **Tier B** available as a user preset — keeps cost predictable while RL collects data.

**AWS steps (after tier approval):**

1. Bedrock console → Model access → enable chosen models
2. Terraform SSM parameters under `/alex/trading/models/*` (defaults)
3. IAM: debate Lambdas already have Bedrock — verify Claude if Tier D/E
4. No new SageMaker for RL (tabular Aurora only)

**Model IDs already in codebase:**

| Model | ID | Used in |
|-------|-----|---------|
| Nova Pro | `us.amazon.nova-pro-v1:0` | Debate agents, deep research |
| Nova Lite | `us.amazon.nova-lite-v1:0` | Elena, router, chat |
| Nova Micro | `us.amazon.nova-micro-v1:0` | Cost tier option |
| Claude 3.5 Sonnet | `anthropic.claude-3-5-sonnet-20241022-v2:0` | Quality tier |
| Claude 3 Haiku | `anthropic.claude-3-haiku-20240307-v1:0` | Fast/cheap tier |

---

### Step 7 — Model-wise performance tracking

**Research/chat (already partial):**

- `query_latency_metrics.model`, `input_tokens`, `output_tokens`, `cost_usd` — FIX-007
- `/observe` adds **“Performance by Model”** table: route × model × avg cost × p95 latency

**Trading floor (new):**

- `agent_observations` already logs tokens/cost per agent — ensure `model_id` always populated
- Nightly rollup (ops agent or evaluator) or query-on-the-fly:

```sql
SELECT model_id,
       COUNT(*) AS calls,
       AVG(latency_ms), SUM(cost_usd),
       SUM(CASE WHEN correct THEN 1 ELSE 0 END)::float / COUNT(*) AS accuracy
FROM agent_performance ap
JOIN agent_observations ao ON ...
GROUP BY model_id
```

**Question this answers:** *“Is Nova Pro worth 10× Lite for Marcus’s vote accuracy?”*

---

## 5. How this improves performance (realistic expectations)

| Dimension | Without RL | With RL |
|-----------|------------|---------|
| **Vote weighting** | Static — Victoria always 0.5× in aggressive mode | Agents that **predict 5d direction** better get more influence |
| **User-specific** | Same weights for everyone | Per-user `rl_weights` from **their** paper trades |
| **Mode + learning** | Mode only | `mode × learned trust` — aggressive still favors Marcus, but **learned** Marcus boost/penalty applies |
| **Model selection** | Fixed Nova Pro for all | Cheaper models where accuracy is similar; Pro where it matters |
| **Observability** | “Black box committee” | See **who** is helping/hurting P&L |

**What it does NOT do:**

- Not guaranteed alpha or market beating
- Not training custom LLMs
- Needs **≥10 evaluated trades per agent** before weights move meaningfully
- Cold start: first ~2 weeks behaves like today (weight = 1.0)

**Expected improvement (MVP — to measure on `/observe`):**

- **Decision quality:** 5–15% better directional accuracy on paper trades over 30–60 days (hypothesis)
- **Cost:** Tier B/C can cut debate cost **50–80%** vs all-Pro
- **Trust:** Users see *why* Marcus was downweighted — transparency USP

---

## 6. Schema additions (minimal)

| Change | Purpose |
|--------|---------|
| Optional `rl_weight_history` | Time-series for chart (or reuse `trading_events.payload`) |
| Optional `model_id` on `agent_performance` | Tie accuracy to model choice |
| Index on `simulated_trades(outcome)` WHERE NULL | Fast evaluator queries |

**Existing `rl_weights` schema (sufficient for MVP):**

```sql
CREATE TABLE IF NOT EXISTS rl_weights (
  id UUID PRIMARY KEY,
  user_id UUID REFERENCES users(id),
  agent_name VARCHAR(50) NOT NULL,
  weight NUMERIC(5,3) DEFAULT 1.0,
  accuracy_30d NUMERIC(5,3) DEFAULT 0,
  total_votes INTEGER DEFAULT 0,
  correct_votes INTEGER DEFAULT 0,
  updated_at TIMESTAMPTZ DEFAULT NOW(),
  UNIQUE(user_id, agent_name)
);
```

---

## 7. Testing plan

| Test | Type |
|------|------|
| `test_rl_weight_updater.py` | Unit — formula, clamps, cold start |
| `test_trade_evaluator.py` | Unit — mock yfinance, BUY+up = correct |
| `test_debate_engine_rl.py` | Unit — effective_weight math |
| `test_p1_router.py` | Unchanged |
| Manual | Run 3 debates → force evaluator → verify `/observe` RL panel |

---

## 8. Execution PR breakdown (after approval)

### PR1 — Learning backend (P8a–c)

- Evaluator Lambda
- Weight updater
- `debate_engine` integration
- Terraform schedule

### PR2 — Observe (P8d + P9d)

- API + UI panels for RL, accuracy, model performance

### PR3 — Frontend config (P9a–b + AWS models)

- `/api/trading/config`
- Mode/model selectors on `/trading`
- Bedrock model enablement

---

## 9. Decisions needed before execution

| # | Decision | Recommendation |
|---|----------|----------------|
| 1 | **Model tier** A / B / C / D / E | **C** with **B** preset |
| 2 | **RL scope** per-user vs global | **Per-user** |
| 3 | **Evaluator schedule** | Daily **5 PM ET** (Mon–Fri) |
| 4 | **History storage** | `trading_events` + daily snapshot (no new table for MVP) |
| 5 | **Chat model selector** | **Trading first**; `/research` in follow-up |
| 6 | **P4 paper executor** | **Don’t block** RL MVP on position updates |

---

## 10. File reference (planned changes)

| File | Change |
|------|--------|
| `backend/agents/trading/learning/trade_evaluator.py` | **New** — outcome scoring |
| `backend/agents/trading/learning/weight_updater.py` | **New** — RL weight UPSERT |
| `backend/agents/trading/core/debate_engine.py` | `calculate_decision` + `load_rl_weights` |
| `backend/agents/trading/core/orchestrator.py` | Load user config + RL weights |
| `terraform/9_trading_floor/main.tf` | Evaluator Lambda + EventBridge |
| `frontend/app/api/trading/config/route.ts` | **New** — GET/PUT config |
| `frontend/app/api/observe/route.ts` | RL + model perf queries |
| `frontend/app/observe/page.tsx` | New panels |
| `frontend/app/trading/page.tsx` | Mode + model selectors |
| `scripts/tests/test_rl_*.py` | Unit tests |

---

## 11. Future upgrade path

If paper-trade outcomes are positive:

- Contextual bandits per ticker/sector
- SageMaker endpoint for policy model
- Multi-armed bandit for scout candidate selection
- For MVP: **tabular RL in Aurora is the right choice** (`Alex_Trading_Floor_2.0.md` §5.5)

---

## 12. Debater agent RL — use cases, viability, and full upgrade requirements

> **Scope:** Alex has two “debater” surfaces that share the **same five personas** (Marcus, Victoria, Zara, Reid, Elena):
>
> 1. **Trading Floor committee** — all 5 vote in parallel; weights combine votes into BUY/SELL/HOLD (`debate_engine.py`). **RL MVP targets this first** — measurable outcomes via paper trades.
> 2. **Chat debater handoffs** — router sends one specialist (`debater_registry.py` → `debater_handoff.py`). **Phase 2 RL** — routing trust + optional multi-debater synthesis weights.
>
> This section explains **where tweaking agent weights improves Alex**, **why it is viable without heavy ML**, and **everything required to upgrade the current setup**.

### 12.1 The problem with static weights today

Alex’s debater agents are **persona-rich but statistically equal** (modulo mode):

| Mode | Marcus | Victoria | Zara | Reid | Elena |
|------|--------|----------|------|------|-------|
| aggressive | 2.0× | 0.5× | 1.5× | 1.0× | 0.5× |
| neutral | 1.0× | 1.0× | 1.0× | 1.0× | 1.0× |
| safe | 0.5× | 1.5× | 0.5× | 1.0× | 2.0× |

These weights encode **design intent** (“aggressive favors growth”), not **empirical performance**. In practice:

- Zara may nail short-term direction on tech names while Marcus lags — but Marcus still gets 2.0× in aggressive mode.
- Victoria’s bear calls may save the portfolio in drawdowns — but she is permanently downweighted in aggressive mode even when she is right.
- The same weights apply to **every user**, **every ticker**, and **every model** — no adaptation.

**RL fixes this** by multiplying static mode weights with **learned trust scores** from labeled outcomes:

```text
effective_weight(agent) = MODE_WEIGHTS[mode][agent] × rl_weights[user][agent]
```

---

### 12.2 Use cases — where RL weight tweaking improves performance

#### Use case 1 — Tech growth portfolio (Marcus vs Zara)

**Scenario:** User holds NVDA, AMD, MU. Mode = `aggressive`.

| Without RL | With RL (after 30d) |
|------------|---------------------|
| Marcus always 2.0× — dominates votes even when momentum (Zara) was correct on 5d horizon | Zara `rl_weight` → 1.35, Marcus → 0.85 — committee tilts toward **signals that actually worked** on user’s names |
| Repeated late BUYs after run-up | Fewer whipsaw BUYs; TRIM/HOLD weighted when Zara + Elena were historically right |

**Measurable gain:** Higher % of paper trades where committee action matched 5d price direction (+8–12% hypothesis).

---

#### Use case 2 — Defensive / drawdown period (Victoria + Elena)

**Scenario:** Market correction; user mode = `neutral` but VIX elevated.

| Without RL | With RL |
|------------|---------|
| Victoria 1.0× — same as Marcus | Victoria `rl_weight` → 1.4 after correct SELL/TRIM calls; Marcus → 0.75 |
| Committee still leans BUY on “quality” narratives | Risk-off votes gain influence **when they earned it** |

**Alex performance impact:** Better **downside protection** on paper P&L — often more valuable than upside capture for retention.

---

#### Use case 3 — Macro-driven holdings (Reid)

**Scenario:** User asks trading floor to analyze rate-sensitive names (banks, REITs). Fed cycle turning.

| Without RL | With RL |
|------------|---------|
| Reid 1.0× in all modes | Reid `rl_weight` → 1.25 when macro calls correlated with 5d returns on user’s book |
| Growth agents override macro caution | Synthesis respects **who was right in this user’s history** for macro-sensitive tickers |

**Future (Phase 2):** Contextual bandit: `rl_weight(user, agent, sector=financials)`.

---

#### Use case 4 — Position sizing questions (Elena + chat handoff)

**Scenario:** Chat routes *“how much NVDA should I hold?”* to **Elena** (`debater_registry.py`). Trading floor later debates NVDA.

| Without RL | With RL |
|------------|---------|
| Chat Elena advice unrelated to floor vote weights | Shared `rl_weights` — if Elena’s risk votes correlate with good outcomes, **both** chat trust and floor weight rise |
| User sees inconsistent “bull” chat vs cautious floor | Persona consistency; `/observe` shows Elena accuracy |

**Phase 2:** Extend evaluator to score **chat debater** outcomes via user thumbs-up / follow-up research quality ( softer signal than trades).

---

#### Use case 5 — Model A/B per agent (Nova Lite vs Pro)

**Scenario:** User sets Marcus = Nova Lite, Victoria = Nova Pro (Tier E).

| Without RL | With RL + model perf panel |
|------------|---------------------------|
| No feedback on whether Pro is worth 10× cost for Victoria | `agent_performance.model_id` + accuracy → auto-suggest preset: *“Switch Marcus to Lite — same accuracy, −70% cost”* |
| Fixed spend per debate | **Cost-adjusted performance** — significant platform economics improvement |

---

#### Use case 6 — Multi-user SaaS (per-user learning)

**Scenario:** User A (day-trader, aggressive) vs User B (retiree, safe).

| Without RL | With RL |
|------------|---------|
| Identical committee behavior | Separate `rl_weights` rows — Alex **personalizes** without fine-tuning LLMs |
| One-size-fits-all “AI committee” | Core USP vs generic ChatGPT — **your** agents learn **your** paper track record |

---

### 12.3 Why this is viable (and not over-engineering)

| Concern | Answer |
|---------|--------|
| **Do we need SageMaker / custom models?** | No. MVP = **tabular multiplicative weights** in Aurora. Cheap, auditable, reversible. |
| **Enough signal?** | Each debate produces 5 labeled votes + 1 outcome after T+5d. ~10 debates/week/user → cold start ~2 weeks, meaningful weights ~4–6 weeks. |
| **Reward hacking?** | We score **action vs market**, not LLM eloquence. Guardrails unchanged. Weights clamped [0.5, 1.5]. |
| **Latency impact?** | One Aurora read (`rl_weights`) per debate — &lt;20ms. No extra LLM calls. |
| **Regulatory** | Paper simulation only; weights are **trust scores**, not auto-execution. |
| **Same agents in chat + floor** | Same persona prompts in `agents/*.py` and `debater_handoff.py` — shared learning story. |

**Comparison to alternatives:**

| Approach | Cost | Time | Fits Alex? |
|----------|------|------|------------|
| Fine-tune LLMs per agent | $$$ | Weeks–months | **Phase 3 — §13** (after data plane + corpus) |
| SageMaker RL (PPO) | $$ | Days infra | Phase 4+ |
| **Tabular weight updater** | ~$0/mo | 3–4 dev days | **Yes — MVP (§12)** |
| Manual weight tuning | $0 | Never scales | No |

---

### 12.4 Expected performance improvement (significance)

We separate **user-visible quality**, **simulation metrics**, and **platform economics**:

#### A. Decision quality (Trading Floor)

| Metric | Baseline (static) | Target @ 60d RL | How measured |
|--------|-------------------|-----------------|--------------|
| Directional accuracy (5d) | ~50–55% (hypothesis) | **58–65%** | `agent_performance.correct` / trades |
| Paper P&L vs buy-and-hold | Unmeasured | **+2–5% relative** | `simulated_trades.realized_pnl` aggregate |
| Bad BUY rate (BUY then −5d) | Unmeasured | **−10–20%** | Evaluator labels |
| Committee confidence calibration | Overconfident | Closer to 70% when conf=70% | Confidence vs outcome |

**Why “significant” for Alex:** Research chat is already strong; **trading floor is the weak closed loop**. RL turns the floor from a demo into a **learning simulation** — the main product differentiator in `Alex_Trading_Floor_2.0.md`.

#### B. Chat / debater handoffs (Phase 2)

| Metric | Improvement |
|--------|-------------|
| Router sends query to **best** specialist | +RL on `match_debater` scores from outcome proxy |
| User trust | `/observe` shows *why* Zara handled RSI queries well |

#### C. Cost efficiency (model tier + RL)

| Metric | Baseline | With model selector + RL |
|--------|----------|--------------------------|
| Cost per debate (5 agents) | ~$0.08–0.12 (all Pro) | **$0.02–0.06** (Tier B/C) |
| Cost per correct trade signal | High | **−30–50%** after model perf feedback |

#### D. Observability & retention

- Users who see **RL Weights Evolution** on `/observe` understand Alex **improves** — reduces churn vs static bots.
- B2B / RIA story (`RIA.md`): *“Auditable agent trust scores”* — enterprise-ready narrative.

---

### 12.5 Complete upgrade requirements

Everything needed to move from **current setup** → **RL-enabled debater system**.

#### 12.5.1 Infrastructure (AWS / Terraform)

| Component | Current | Required upgrade | Terraform module |
|-----------|---------|------------------|------------------|
| **alex-debate-agent** | ✅ Live | Pass `user_id`; load RL weights | `9_trading_floor` |
| **alex-trading-orchestrator** | ✅ Live | Load `user_trading_config`; pass models + mode | `9_trading_floor` |
| **alex-trade-evaluator** | ❌ Missing | **New Lambda** — daily outcome scoring | `9_trading_floor` |
| **alex-rl-updater** | ❌ Missing | **New Lambda** (or combined with evaluator) | `9_trading_floor` |
| **EventBridge** | Trading optional | `cron(0 22 ? * MON-FRI *)` evaluator | `9_trading_floor` |
| **Aurora PostgreSQL** | ✅ Live | No new cluster — use existing tables + indexes | `5_database` |
| **Bedrock** | ✅ Nova | Enable approved models (Tier C/D) | Console + IAM |
| **SSM parameters** | Partial | `/alex/trading/models/{marcus,victoria,...}` defaults | `9_trading_floor` |
| **ECS researcher** | Session-based | Unchanged for RL MVP | `4_researcher` |
| **SQS alex-trading-queue** | ✅ Live | Unchanged | `9_trading_floor` |
| **CloudWatch** | ✅ Live | Alarms: evaluator failures, 0 trades evaluated | `6_agents` |
| **IAM** | ✅ agent-role | Add yfinance/network for evaluator if VPC-bound | `1_permissions` |

**Estimated incremental AWS cost (RL MVP):**

| Resource | Monthly est. |
|----------|--------------|
| Evaluator Lambda (1×/day, ~2 min) | &lt; $1 |
| RL updater Lambda | &lt; $1 |
| Aurora storage (rl_weights + events) | &lt; $0.50 |
| Extra Bedrock (evaluator none) | $0 |
| **Total** | **~$2–3/mo** |

---

#### 12.5.2 Data layer (Aurora)

| Table | Current | Action |
|-------|---------|--------|
| `rl_weights` | Schema only | **Write path** via weight_updater |
| `agent_performance` | Schema only | **Write path** via trade_evaluator |
| `simulated_trades` | `outcome`, `realized_pnl` columns exist | **Populate** on evaluation |
| `trading_events` | Schema only | Log `outcome_evaluated`, `rl_weight_updated` |
| `user_trading_config` | Schema only | **Read/write** via API |
| `agent_observations` | Partial writes | Ensure `model_id` on every debater call |

**New indexes (recommended):**

```sql
CREATE INDEX IF NOT EXISTS idx_simulated_trades_outcome_null
  ON simulated_trades (executed_at) WHERE outcome IS NULL;

CREATE INDEX IF NOT EXISTS idx_agent_performance_user_agent_week
  ON agent_performance (week_of, agent_name);

CREATE INDEX IF NOT EXISTS idx_trading_events_learning
  ON trading_events (event_type, created_at)
  WHERE event_type IN ('outcome_evaluated', 'rl_weight_updated');
```

**Optional Phase 2:**

```sql
-- Time-series for /observe chart (alternative: trading_events JSONB)
CREATE TABLE rl_weight_history (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID REFERENCES users(id),
  agent_name VARCHAR(50),
  weight NUMERIC(5,3),
  accuracy_30d NUMERIC(5,3),
  snapshot_date DATE DEFAULT CURRENT_DATE
);
```

---

#### 12.5.3 Models (Bedrock)

| Role | Current default | Recommended MVP (Tier C) | RL tie-in |
|------|-----------------|--------------------------|-----------|
| Marcus (growth) | Nova Pro | Nova Pro | Weight ↑ when growth calls correct |
| Victoria (bear) | Nova Pro | Nova Pro | Weight ↑ in drawdowns when SELL/TRIM right |
| Zara (quant) | Nova Pro | Nova Pro | Weight ↑ when technical signals match 5d move |
| Reid (macro) | Nova Pro | Nova Pro | Weight ↑ for rate-sensitive names |
| Elena (risk) | Nova Lite | Nova Lite | Weight ↑ when sizing/risk votes prevent loss |
| Executor synthesis | Nova Pro | Nova Pro | Optional separate model perf tracking |

**Bedrock console actions (one-time):**

1. Model access → enable **Amazon Nova Pro, Lite, Micro**
2. (If Tier D) enable **Anthropic Claude 3.5 Sonnet / Haiku**
3. Verify quotas in us-east-1 (debate = 6 invokes × N tickers)

**SSM defaults to add (Terraform):**

```hcl
resource "aws_ssm_parameter" "model_marcus" {
  name  = "/alex/trading/models/marcus"
  type  = "String"
  value = "us.amazon.nova-pro-v1:0"
}
# ... victoria, zara, reid, elena (lite), executor (pro)
```

**IAM:** `alex-agent-role` already has Bedrock; add Claude ARNs if Tier D.

---

#### 12.5.4 Backend (Python)

| Module | File | Change |
|--------|------|--------|
| Outcome scoring | `backend/agents/trading/learning/trade_evaluator.py` | **New** |
| Weight update | `backend/agents/trading/learning/weight_updater.py` | **New** |
| Vote synthesis | `backend/agents/trading/core/debate_engine.py` | `load_rl_weights()`, `calculate_decision(..., rl_weights)` |
| Orchestration | `backend/agents/trading/core/orchestrator.py` | Load config + RL; pass to `run_debate` |
| Observations | `backend/agents/trading/agents/base_agent.py` | Persist `model_id` on every vote |
| Chat debaters | `backend/researcher/debater_handoff.py` | Phase 2: read RL badge in prompt context |
| Router | `backend/researcher/debater_registry.py` | Phase 2: boost match score by `rl_weights` |
| Ops | `backend/agents/ops_agent.py` | Optional: daily RL summary metric |

**Lambda packaging:**

```text
backend/agents/trading/
  learning/
    trade_evaluator.py    → alex-trade-evaluator
    weight_updater.py     → bundled or alex-rl-updater
  core/debate_agent.py    → existing handler (updated)
```

**Environment variables (evaluator Lambda):**

```bash
DB_CLUSTER_ARN, DB_SECRET_ARN, DB_NAME
AWS_REGION_NAME=us-east-1
EVAL_HORIZON_DAYS=5          # primary reward horizon
MIN_VOTES_FOR_RL=10
WEIGHT_MIN=0.5
WEIGHT_MAX=1.5
```

---

#### 12.5.5 Frontend (Next.js)

| Surface | File | Change |
|---------|------|--------|
| Trading config API | `frontend/app/api/trading/config/route.ts` | **New** GET/PUT |
| Trading UI | `frontend/app/trading/page.tsx` | Mode selector + per-agent model dropdowns + presets |
| Observe API | `frontend/app/api/observe/route.ts` | `rl_weights`, `agent_accuracy`, `model_performance`, `learning_events` |
| Observe UI | `frontend/app/observe/page.tsx` | RL Weights chart, leaderboard, model table |
| Types | `frontend/lib/tradingDb.ts` | Helpers for config + RL queries |

**UX requirements:**

- Show **effective weight** on each agent vote in trade history (e.g. “Marcus BUY — weight 1.7× (mode 2.0 × RL 0.85)”)
- Badge on `/trading`: *“Learning active — 23 trades evaluated”*
- Model preset chips: Balanced | Cost optimized | Quality

---

#### 12.5.6 Observability & audit

| Signal | Where | Purpose |
|--------|-------|---------|
| `trading_events` | Aurora | Audit every weight change |
| `/observe` RL panel | Frontend | User-visible learning |
| CloudWatch metric `AlexAI/RLWeightUpdates` | Custom | Ops alert if updater fails |
| CloudWatch metric `AlexAI/TradesEvaluated` | Custom | Data pipeline health |
| `Alex_Fixes.md` + `RL_Update.md` | Docs | FIX-014+ when shipped |

**Sample `/observe` API extension:**

```json
{
  "rl_weights": [
    { "agent": "marcus", "weight": 1.12, "accuracy_30d": 0.62, "total_votes": 18 }
  ],
  "agent_accuracy": [
    { "agent": "zara", "win_rate": 0.68, "avg_pnl_attribution": 0.004, "trend": "up" }
  ],
  "model_performance": [
    { "model_id": "us.amazon.nova-pro-v1:0", "calls": 120, "cost_usd": 2.4, "accuracy": 0.61 }
  ],
  "learning_events": [
    { "type": "rl_weight_updated", "agent": "victoria", "old": 1.0, "new": 1.15, "at": "..." }
  ]
}
```

---

#### 12.5.7 Testing & CI

| Test | Path |
|------|------|
| Weight formula + clamps | `scripts/tests/test_rl_weight_updater.py` |
| Outcome labeling | `scripts/tests/test_trade_evaluator.py` |
| Effective weight math | `scripts/tests/test_debate_engine_rl.py` |
| Config API | `scripts/tests/test_trading_config_api.py` (optional) |
| P0 schema | Existing `aurora_warmup.py` — verify indexes |

**Manual acceptance:**

1. Run 5+ debates on 2 tickers  
2. Trigger evaluator manually (or wait T+1)  
3. Confirm `rl_weights` ≠ 1.0 for at least one agent  
4. Run debate — confirm vote math uses new weights  
5. `/observe` shows chart + events  

---

#### 12.5.8 Deployment sequence

```text
1. Aurora indexes + aurora_warmup.py
2. Terraform: evaluator + EventBridge + SSM model params
3. Deploy debate_engine + orchestrator (read RL weights; backward compatible if empty)
4. Deploy evaluator/updater Lambdas
5. Frontend: /api/trading/config + /observe panels
6. Enable Bedrock models (Tier approval)
7. Backfill: optional manual evaluator run on historical simulated_trades
8. Document FIX-014 in Alex_Fixes.md
```

**Rollback:** Set all `rl_weights.weight = 1.0` or feature-flag `RL_ENABLED=false` in SSM — debates revert to static mode weights.

---

#### 12.5.9 Phase 2 — Chat debater RL (extension)

| Item | Description |
|------|-------------|
| **Signal** | User feedback, follow-up sentiment, or proxy from research RAG quality |
| **Mechanism** | Same `rl_weights` table, scope=`chat` or shared with floor |
| **Router** | `match_debater()` adds `+ log(rl_weight)` to pattern scores |
| **UI** | `/research` shows specialist badge with accuracy |

Not required for MVP but **uses same infra** — low incremental cost.

---

### 12.6 Summary — why Alex performance improves significantly

```text
┌─────────────────────────────────────────────────────────────────┐
│  TODAY: Smart agents + dumb committee math (static MODE_WEIGHTS) │
│  AFTER:  Smart agents + learning committee (mode × RL weights)   │
│                                                                 │
│  • Personalized per user — not one global committee              │
│  • Outcome-labeled — not vibe-based                              │
│  • Observable — /observe proves improvement                      │
│  • Cost-optimizable — model tier + accuracy feedback             │
│  • Flywheel — more debates → better weights → better debates     │
└─────────────────────────────────────────────────────────────────┘
```

**Bottom line:** RL does not make LLMs smarter overnight. It makes **Alex’s use of its debater agents smarter over time** — which is exactly what a multi-agent financial platform should do, at **~$2/mo infra** and **~9 dev-days**, using tables and Lambdas you already planned in `Alex_Trading_Floor_2.0.md`.

---

### 12.7 Approval checklist (extends §9)

| # | Item | Status |
|---|------|--------|
| 1 | Model tier (A–E) | ☐ Pending |
| 2 | Per-user RL scope confirmed | ☐ Recommended |
| 3 | Evaluator schedule 5 PM ET | ☐ Recommended |
| 4 | Phase 2 chat debater RL | ☐ Optional later |
| 5 | `rl_weight_history` table vs events-only | ☐ Decide at PR2 |
| 6 | Bedrock model access enabled in console | ☐ After tier pick |
| 7 | ECS session running for chat/research (separate from RL Lambdas) | ☐ Ops |

---

---

## 13. Model fine-tuning for financially rich debates + required data plane

> **Scope:** §12 covers **who to trust** (tabular RL weights). This section covers **what agents know** (data sources) and **how they argue** (fine-tuned models). All three layers stack — none replaces the others.

### 13.1 Three-layer learning stack

```text
┌─────────────────────────────────────────────────────────────────────────┐
│  LAYER 3 — MODEL FINE-TUNING (§13)                                      │
│  Persona voice, debate structure, cite-metrics habit, counter-arguments │
│  Bedrock Custom Model / SageMaker LoRA per agent                        │
└───────────────────────────────┬─────────────────────────────────────────┘
                                │ trained on labeled debate corpus
┌───────────────────────────────▼─────────────────────────────────────────┐
│  LAYER 2 — DATA PLANE (§13.6)                                           │
│  SEC filings, macro, options flow, portfolio context, debate memory       │
│  MCP gateway → build_data_context() enrichment                          │
└───────────────────────────────┬─────────────────────────────────────────┘
                                │ feeds prompts at inference time
┌───────────────────────────────▼─────────────────────────────────────────┐
│  LAYER 1 — TABULAR RL (§12)                                             │
│  effective_weight = MODE_WEIGHTS × rl_weights                           │
│  Learns which specialist was right for this user                        │
└─────────────────────────────────────────────────────────────────────────┘
```

| Layer | Question answered | Changes LLM weights? | When |
|-------|-------------------|----------------------|------|
| **1 — Tabular RL** | *Who should the committee listen to?* | No | MVP — weeks |
| **2 — Data plane** | *What facts can agents cite?* | No | Parallel — weeks |
| **3 — Fine-tuning** | *How persuasively does each persona argue?* | Yes | Phase 3 — months |

**Today’s gap:** Debates receive a **single yfinance snapshot** (`market_data.py` → `build_data_context()` in `debate_engine.py`). Reid has almost no macro series; Victoria has no EDGAR; Zara has computed RSI but no real options flow unless Polygon is enabled. Agents share the **same base model** (Nova Pro/Lite via SSM) with persona prompts only — debates read as **five similar JSON blobs**, not a Bloomberg-style committee.

---

### 13.2 Why fine-tune (beyond RL weights and prompts)

| Limitation today | What fine-tuning fixes |
|------------------|------------------------|
| Generic LLM tone — Marcus and Victoria sound alike | Distinct **reasoning patterns** per persona (growth narrative vs forensic skepticism) |
| Shallow `detailed_reasoning` — 3 generic sentences | Habit of **anchoring every claim to a metric** from `data_used` |
| Weak `counter_argument` — filler opposition | Trained on **paired bull/bear** examples from same ticker context |
| Inconsistent JSON quality across models | **Schema-stable** outputs on smaller/cheaper fine-tuned adapters |
| No cross-agent rebuttal in trading floor (parallel votes only) | Fine-tune for **synthesis-ready** statements Historian/RAG can retrieve |

Fine-tuning does **not** replace live data. Per `prompts.py` / agent prompts: agents must **never** invent prices. Fine-tuning teaches **argumentation over provided context**, not memorized tickers.

---

### 13.3 Per-agent fine-tuning targets

| Agent | Persona skill to reinforce | Training emphasis | Base model candidate |
|-------|---------------------------|-------------------|----------------------|
| **Marcus** | Growth / TAM / moat bull case | Revenue acceleration, margin expansion, peer comps, management beats | Nova Pro or Claude Haiku adapter |
| **Victoria** | Forensic short / risk | P/E vs history, FCF quality, insider selling, crowded longs, accounting flags | Same family — separate adapter |
| **Zara** | Quant / technical | RSI/MACD interpretation, volume anomalies, put/call, signal → action mapping | Nova Lite (fast, structured) |
| **Reid** | Macro linkage | Rate cycle, sector ETF relative strength, yield curve, Fear & Greed regime | Nova Pro |
| **Elena** | Portfolio risk | Concentration, correlation, stop sizing, drawdown scenarios | Nova Lite |

**Strategy:** One **shared financial base** (instruction-tuned on mixed debate JSON) + **five LoRA adapters** (or five Bedrock custom model IDs) — cheaper than five full fine-tunes.

---

### 13.4 Training data corpus

#### 13.4.1 Internal sources (Alex-generated — highest value)

| Source | Table / path | Label | Use |
|--------|--------------|-------|-----|
| Debate transcripts | `simulated_trades.agent_debate`, `agent_votes` JSONB | T+5d outcome from §4 evaluator | SFT on **winning** agent responses; DPO preferred vs losing vote |
| Full debate context | Reconstruct from `market_data` snapshot + portfolio at `executed_at` | Same | Input half of training pair |
| Research RAG chunks | `research_vectors` (SEC, news ingest) | Manual / retrieval score | Victoria + Marcus grounding examples |
| Chat debater handoffs | `debater_handoff` logs (Phase 2) | User follow-up / thumbs | Router + single-agent quality |
| Collective memory | `trading_floor_intelligence` (P14) | Retrieval relevance | Historian-conditioned debate examples |

#### 13.4.2 External / synthetic sources (bootstrap before enough internal data)

| Dataset | Purpose |
|---------|---------|
| **FinQA / TAT-QA** | Numeric reasoning over tables — Zara, Marcus |
| **FiNER / financial NER** | Ticker and metric extraction — all agents |
| **Earnings call transcripts** (public) | Marcus growth framing, Victoria guidance skepticism |
| **SEC 10-K risk factors** (EDGAR bulk) | Victoria bear cases |
| **Teacher distillation** | Claude/GPT generates `(context, persona) → gold JSON` from live `get_market_data()` snapshots — human spot-check 5% |

#### 13.4.3 Minimum corpus size (rule of thumb)

| Stage | Examples per agent | Expected lift |
|-------|-------------------|---------------|
| Bootstrap (synthetic + public) | 500–1,000 | Richer prose; modest accuracy |
| Internal @ 8 weeks RL | 2,000–5,000 labeled | Persona differentiation visible |
| Mature @ 6 months | 10,000+ | Stable adapter; A/B vs base |

**Label definition:** Agent vote `action` + `confidence` where T+5d price move **agrees** with action (same rules as §4 `trade_evaluator`).

---

### 13.5 Fine-tuning approaches on AWS

| Approach | Pros | Cons | Alex fit |
|----------|------|------|----------|
| **Amazon Bedrock Model Customization** (Nova fine-tuning) | Native invoke path; SSM model IDs already used | Model availability / region; cost per job | **Primary** if Nova customize enabled in `us-east-1` |
| **SageMaker JumpStart + LoRA** | Per-agent adapters; full control | Extra endpoint or adapter merge step | **Fallback** — reuse existing SageMaker stack (`terraform/2_sagemaker`) |
| **Bedrock Knowledge Bases only** | No weight change; fast | Does not fix argument style | Layer 2 — not substitute for §13 |
| **Full RLHF / PPO on policy** | Theoretical optimum | Lambda/Aurora too heavy | Phase 4+ — after tabular RL proves signal |

#### 13.5.1 Recommended pipeline

```text
1. Export training JSONL from Aurora (debates + outcomes + context snapshot)
2. Upload to s3://alex-ml-training/debates/{agent}/{date}/
3. SageMaker Processing OR Bedrock CreateModelCustomizationJob
4. Evaluate on held-out tickers (§13.10 harness)
5. Register model ID → SSM /alex/trading/models/{agent}_ft
6. debate_engine.invoke() reads fine-tuned ID when user_trading_config.use_finetuned=true
7. A/B: 50% base / 50% FT — log to agent_performance.model_id
```

#### 13.5.2 Training record format (JSONL)

```json
{
  "system": "You are Marcus Chen…",
  "user": "<data_ctx from build_data_context + portfolio>",
  "assistant": "{ \"action\": \"BUY\", \"confidence\": 82, … }",
  "metadata": {
    "ticker": "NVDA",
    "agent": "marcus",
    "outcome_label": "correct",
    "data_sources": ["yfinance", "polygon", "sec_edgar"],
    "debate_id": "uuid"
  }
}
```

For **DPO**, add `rejected`: losing agent’s JSON from same debate context.

---

### 13.6 Required data sources for financially rich debates

Debates are only as good as `data_ctx`. Below: **Required** = agent cannot fulfill persona without it; **Recommended** = materially richer arguments; **Optional** = differentiation / Tier 3.

#### 13.6.1 Per-agent data source matrix

| Data source | MCP / wrapper | Marcus | Victoria | Zara | Reid | Elena | Tier | Status today |
|-------------|---------------|--------|----------|------|------|-------|------|--------------|
| **Price / OHLCV** | `yfinance`, `market_price_mcp` | ✅ Req | ✅ Req | ✅ Req | ✅ Req | ✅ Req | 1 | ✅ Live |
| **Fundamentals** (P/E, growth, margins, FCF) | `yfinance`, `alpha_vantage_mcp` | ✅ Req | ✅ Req | ○ Rec | ○ Rec | ✅ Req | 1–2 | ✅ Partial (yfinance) |
| **Analyst ratings / PT** | `yfinance` | ✅ Req | ✅ Req | ○ Rec | — | ○ Rec | 1 | ✅ Live |
| **News headlines** | `yahoo_rss`, `financial_news_mcp` | ✅ Req | ✅ Req | ○ Rec | ○ Rec | — | 1–2 | ✅ Partial (yfinance news) |
| **RSI / MA / volume** | `market_data.py`, `technical_mcp` | ○ Rec | — | ✅ Req | — | ○ Rec | 1 | ✅ Partial (RSI only) |
| **MACD / BB / support-resistance** | `technical_mcp`, `pandas-ta` | — | — | ✅ Req | — | — | 1 | 🔲 Not in debate ctx |
| **Options flow / put-call** | `polygon`, `options_flow_mcp`, Unusual Whales | ○ Rec | ○ Rec | ✅ Req | — | ○ Rec | 2–3 | 🔲 Polygon optional |
| **Short interest** | `yfinance`, Finnhub | — | ✅ Req | ○ Rec | — | ○ Rec | 1–2 | 🔲 Often missing |
| **Insider trades / Form 4** | `sec_edgar_mcp`, `edgartools` | ○ Rec | ✅ Req | — | — | ○ Rec | 1 | 🔲 Research only — not floor |
| **10-K / 10-Q excerpts** (risk, MD&A) | `sec_edgar_mcp`, `research_vectors` | ○ Rec | ✅ Req | — | — | — | 1 | 🔲 Research RAG only |
| **Fear & Greed index** | `fetch_fear_greed`, `sentiment_mcp` | ○ Rec | — | ○ Rec | ✅ Req | ✅ Req | 1 | ✅ Live |
| **FRED macro** (rates, CPI, unemployment) | `macro_mcp`, `fred_mcp` | — | — | — | ✅ Req | ○ Rec | 2 | 🔲 Not wired to floor |
| **Yield curve / Fed funds** | `macro_mcp` | — | ○ Rec | — | ✅ Req | ○ Rec | 2 | 🔲 Planned |
| **Sector ETF relative strength** | `sector_mcp` | ○ Rec | — | ○ Rec | ✅ Req | ○ Rec | 3 | 🔲 Planned |
| **VIX / vol regime** | `volatility_mcp`, CBOE | — | ○ Rec | ✅ Req | ○ Rec | ✅ Req | 3 | 🔲 Not wired |
| **User portfolio / holdings** | `aurora`, `portfolio_mcp` | ○ Rec | ○ Rec | — | ○ Rec | ✅ Req | 1 | ✅ Partial (holding in prompt) |
| **Portfolio concentration / correlation** | `portfolio_mcp`, computed | — | — | — | — | ✅ Req | 1 | 🔲 Not computed |
| **Prior debates on ticker** | `trading_floor_intelligence` | ○ Rec | ○ Rec | ○ Rec | ○ Rec | ○ Rec | 1 | 🔲 P14 empty |
| **Research vectors** (user uploads) | `context_service`, `vector_tool` | ○ Rec | ✅ Req | — | ○ Rec | — | 1 | ✅ Chat — not floor |
| **Quant snapshots** | `quant_snapshots`, `quant_tool` | — | — | ✅ Req | — | — | 1 | 🔲 P13 scaffold |

**Legend:** ✅ Req = required for persona-credible debate · ○ Rec = recommended · — = low value for persona

#### 13.6.2 Debate-type data bundles

| Debate type | Trigger | Minimum bundle (must fetch before `run_debate`) | Rich bundle (target) |
|-------------|---------|--------------------------------------------------|----------------------|
| **Holding review** | User owns ticker | price, fundamentals, holding P&L, Elena portfolio slice | + prior TFI, sector exposure, stop vs 52w |
| **New idea / scout** | Scout candidate or manual ticker | price, fundamentals, news, analyst | + SEC recent filings, options flow, macro regime |
| **Earnings week** | Calendar / user query | price, estimates, last quarter growth, news | + 8-K, guidance text, Victoria forensic flags |
| **Macro shock** | VIX spike / Fed day | Fear & Greed, index move, sector ETFs | + FRED series, Reid cycle note, Elena book beta |
| **Deep forensic** | Victoria-weighted mode | price, P/E vs sector, short interest | + 10-Q cash flow, insider Form 4, peer comp table |

#### 13.6.3 Data quality gate (block or warn)

Extend `MarketData.data_quality` (today 0–1 score in `get_market_data()`) before invoking agents:

| `data_quality` | Behavior |
|----------------|----------|
| **≥ 0.6** | Run full 5-agent debate |
| **0.4 – 0.59** | Run debate; flag `data_sparse: true` in UI; Elena auto-downgrade confidence cap 60% |
| **< 0.4** | Block debate; return *“Enable Polygon / SEC / FRED for {ticker}”* with missing source list |

Per-agent **minimum fields** (else agent abstains with `HOLD` + `"insufficient_data"`):

| Agent | Hard minimum in `data_ctx` |
|-------|---------------------------|
| Marcus | `revenue_growth` OR `earnings_growth`, `price`, `analyst_rating` |
| Victoria | `pe_ratio`, `price`; ideally `short_interest` OR SEC snippet |
| Zara | `rsi`, `price`, `volume`; ideally `put_call_ratio` |
| Reid | `fear_greed_score`; ideally 1+ macro series |
| Elena | `holding` block + `market_cap`; ideally portfolio concentration |

---

### 13.7 Data ingestion architecture for debates

```text
run_debate(ticker)
    │
    ▼
context_builder.build_debate_context(ticker, user_id, debate_type)
    │
    ├── market_tool.get_snapshot()          ← yfinance + enabled providers
    ├── sec_tool.get_recent_filings()       ← Victoria, Marcus (NEW)
    ├── macro_tool.get_regime_snapshot()    ← Reid (NEW)
    ├── quant_tool.get_snapshot()           ← Zara (P13)
    ├── portfolio_tool.get_risk_slice()     ← Elena (NEW)
    ├── vector_tool.search_tfi(ticker)      ← all agents (P14)
    └── digest_tool.get_for_ticker()        ← optional narrative
    │
    ▼
build_data_context(enriched_market_data, holding, portfolio, debate_memory)
    │
    ▼
5 × invoke(agent, data_ctx)  →  optional fine-tuned model per agent
```

**Implementation hooks:**

| Component | File / action |
|-----------|---------------|
| Unified fetch | New `backend/agents/trading/tools/context_builder.py` |
| MCP routing | `backend/agents/trading/mcp/tool_gateway.py` (P4) |
| SSM toggles | `/alex/trading/data_sources/{source}/enabled` (exists) |
| Observe tags | `data:*`, `tier:*` per `Alex_Trading_Floor_2.0.md` §19 |
| Fine-tune export | New Lambda `alex-debate-training-export` (weekly) |

**Chat debater parity:** Same `context_builder` shared with `debater_handoff.py` so chat specialists and trading floor see **identical facts**.

---

### 13.8 Infrastructure & cost — fine-tuning path

| Resource | Purpose | Est. cost |
|----------|---------|-----------|
| **S3** `alex-ml-training` | JSONL corpus, checkpoints | ~$5/mo |
| **Bedrock customization job** | 5 adapter jobs / quarter | ~$200–800/job (model-dependent) |
| **SageMaker `ml.g5.xlarge`** (alt) | LoRA training 2–4 hrs × 5 agents | ~$50–150/run |
| **SageMaker endpoint** (optional) | Host adapters if not Bedrock-native | ~$100–300/mo if always-on — prefer Bedrock invoke |
| **Aurora export Lambda** | Weekly JSONL dump | ~$0 (existing cluster) |
| **Evaluation Lambda** | Held-out ticker harness | ~$1/mo |

**SSM parameters (new):**

```text
/alex/trading/models/{agent}_ft          → fine-tuned model ID
/alex/trading/finetune/enabled           → true|false
/alex/trading/finetune/ab_pct            → 0.5
/alex/trading/data_sources/*/enabled     → per-source (existing pattern)
```

**Terraform:** Extend `terraform/9_trading_floor` with S3 bucket + IAM for Bedrock customization; no change to debate Lambda until FT IDs registered.

---

### 13.9 Phased roadmap — data → RL → corpus → fine-tune

| Phase | Deliverable | Depends on | Dev effort |
|-------|-------------|------------|------------|
| **13.A — Data MVP** | Wire SEC + FRED + portfolio risk into `build_data_context` | API keys in SSM | 3–5 days |
| **13.B — MCP gateway** | `tool_gateway` for floor agents (P4) | 13.A | 4–6 days |
| **13.C — Tabular RL** | §12 MVP | simulated_trades labels | 9 days (§8) |
| **13.D — TFI ingest** | P14 `trading_floor_intelligence` populated | debate Lambda | 2–3 days |
| **13.E — Corpus export** | JSONL pipeline + 500 synthetic bootstrap | 13.C + 13.D | 2 days |
| **13.F — Pilot fine-tune** | Marcus + Victoria adapters | 13.E corpus | 1 week + eval |
| **13.G — Full five adapters** | All agents + A/B in production | 13.F success | 1 week |
| **13.H — DPO refresh** | Quarterly retrain from labeled debates | Ongoing | Automated |

**Do not fine-tune before Layer 2:** Training on thin yfinance-only context teaches models to **hallucinate macro and forensic detail**. Ship **13.A–13.D** first.

---

### 13.10 Evaluation metrics (fine-tuning vs base)

| Metric | How measured | Target vs base Nova |
|--------|--------------|---------------------|
| **Citation accuracy** | % of `key_evidence` fields match numbers in `data_ctx` | +15–25% |
| **Persona classifier score** | Blind human or LLM-judge: “which agent wrote this?” | >80% accuracy |
| **Directional accuracy (T+5d)** | Same as §12.4 — per agent | +3–8% absolute |
| **JSON schema validity** | Parse success rate | >99% |
| **Counter-argument relevance** | Judge rates 1–5 | +0.5 avg |
| **Debate richness** | Unique metrics cited per debate | +30% count |

Run evaluation **before** promoting FT model ID to SSM production slot.

---

### 13.11 Summary — financially rich debates need both data and fine-tuning

```text
┌─────────────────────────────────────────────────────────────────────────┐
│  RICH DEBATE = rich context × specialist reasoning × learned trust      │
│                                                                         │
│  • Data plane (§13.6) — SEC, macro, options, portfolio risk, TFI        │
│  • Fine-tuning (§13.3–5) — persona-specific argumentation             │
│  • Tabular RL (§12) — weight the votes that were actually right         │
│                                                                         │
│  Without data: fine-tuned models confabulate.                           │
│  Without fine-tuning: rich data still sounds generic.                   │
│  Without RL: committee ignores who earned trust.                        │
└─────────────────────────────────────────────────────────────────────────┘
```

---

### 13.12 Approval checklist (extends §12.7)

| # | Item | Status |
|---|------|--------|
| 8 | Tier 2 API keys (Polygon, Alpha Vantage, FRED) in SSM | ☐ |
| 9 | SEC EDGAR wired to trading floor (not research-only) | ☐ |
| 10 | `context_builder.py` spec approved | ☐ |
| 11 | Fine-tune platform: Bedrock customize vs SageMaker LoRA | ☐ |
| 12 | Bootstrap corpus: synthetic OK for pilot? | ☐ Recommended |
| 13 | Pilot agents: Marcus + Victoria first | ☐ Recommended |
| 14 | A/B percentage for fine-tuned vs base | ☐ Default 50% |
| 15 | P14 TFI ingest before FT export | ☐ Required |

---

*Plan authored June 16, 2026. §12 — debater RL. §13 — model fine-tuning + debate data plane. Execute §12 MVP first; parallel §13.A data MVP; fine-tuning (§13.F+) only after corpus + enriched context exist.*

