# Alex Chat Intelligence — Conversation Routing & Agentic Upgrades

> **Status:** PARKED — awaiting approval before implementation  
> **Created:** June 14, 2026  
> **Purpose:** Make Alex understand questions efficiently — route education, SEC, deep research, debater specialists, and proactive earnings intelligence through one chat surface  
> **Companion docs:** `Alex_AI_2.0.md`, `Alex_Trading_Floor_2.0.md`, `Alex_Master_Implementation_Plan.md` (P2, P6, P15)  
> **Infrastructure:** Terraform-only for AWS resources

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [Current State](#2-current-state)
3. [Target Query Taxonomy](#3-target-query-taxonomy)
4. [Architecture Overview](#4-architecture-overview)
5. [Phase C1 — Education Fast Search + Vector Memory](#phase-c1--education-fast-search--vector-memory)
6. [Phase C2 — SEC Filing Path (Keep Current)](#phase-c2--sec-filing-path-keep-current)
7. [Phase C3 — Deep Research Report + PDF Delivery](#phase-c3--deep-research-report--pdf-delivery)
8. [Phase C4 — Debater Handoff Intelligence](#phase-c4--debater-handoff-intelligence)
9. [Phase C5 — Earnings Calendar Agent](#phase-c5--earnings-calendar-agent)
10. [Phase C6 — Additional Agentic Add-ons](#phase-c6--additional-agentic-add-ons)
11. [Router Changes](#router-changes)
12. [Schema Extensions](#schema-extensions)
13. [API, SSE & Frontend](#api-sse--frontend)
14. [Implementation Order & Estimates](#implementation-order--estimates)
15. [Decision Points](#decision-points)
16. [Related Documents](#related-documents)

---

## 1. Executive Summary

Alex chat today routes to **fast / deep / chat / debater**, but **financial education** (`what is a bond?`, `explain put?`, `steps to invest in a bond?`) still hits **Nova Lite only** — no vector lookup first, no fast search, no post-answer ingest. Deep research streams text but cannot **deliver a PDF**. Debater handoffs exist but miss many natural questions. There is no **proactive earnings intelligence**.

**This plan adds five intelligence lanes:**

| Lane | Example questions | Handler |
|------|-------------------|---------|
| **Education Fast Search** | What is a bond? What is short selling? Steps to invest in a bond? What is stop loss? Explain put? | Vector hit → else fast search → answer → ingest if new |
| **SEC / Filings** | NVDA 10-K risks, 8-K material events, 10-Q revenue | **Current** deep + Playwright MCP + `get_sec_filings` |
| **Deep Research + PDF** | Full investment memo, compare 3 tickers with citations | Deep report as today + **Report Agent** → PDF via MCP → user download |
| **Debater Handoff** | NVDA RSI outlook, bear case on TSLA, Fed impact on tech | Route to Marcus / Victoria / Zara / Reid / Elena → specialist card in chat |
| **Earnings Calendar Agent** | (Proactive) + "when does ASML report?" | Autonomous scan → trend signals → dashboard + chat context |

**Core principle:** *Check memory before compute.* Education and repeat questions should be sub-second when already in `research_vectors`.

---

## 2. Current State

### What Works

| Component | File | Status |
|-----------|------|--------|
| Query router | `backend/researcher/query_router.py` | ✅ fast / deep / chat / debater |
| Unified chat SSE | `frontend/app/api/alex/chat/route.ts` | ✅ Routes to ECS paths |
| Education → chat | `server.py` → `/research/conversation/stream` | ✅ Nova Lite, 2–3 paragraphs |
| Debater registry | `backend/researcher/debater_registry.py` | ✅ 5 specialists + pattern match |
| Debater handoff | `backend/researcher/debater_handoff.py` | ✅ Single-agent stream |
| Deep SEC path | `/research/deep/stream` + Playwright MCP | ✅ 10-K, EDGAR |
| Vector ingest | `backend/ingest/ingest_pgvector.py` | ✅ `research_vectors` with `user_id`, `session_id` |
| Vector search | `handle_search_pgvector` | ✅ Semantic search API |
| Policy guardrails | `query_router.py` `POLICY_FLAG_PATTERNS` | ✅ Blocks actionable shorting advice |

### Gaps (This Plan Closes)

| Gap | Impact |
|-----|--------|
| Education skips vector lookup | "What is a bond?" re-generates every time — slow, inconsistent |
| Education answers **not ingested** after chat | No learning loop; RAG never warms up on concepts |
| No `chunk_type=education` taxonomy | Can't filter glossary vs research vs debate |
| Deep research has no **PDF artifact** | Users can't save/share memos |
| Debater patterns too narrow | "Explain put on NVDA" may miss Zara; "stop loss on my portfolio" may miss Elena |
| No earnings calendar agent | Missed proactive value; "when does X report?" hits generic fast path |
| Education vs debater boundary fuzzy | Concept vs actionable advice not always separated |
| Conversation path skips DB context for education | `intent=education` explicitly skips `get_conversation_context` today |

---

## 3. Target Query Taxonomy

### Routing Decision Tree (Priority Order)

```
1. Policy guardrail?        → chat + policy_flag (canned)
2. Off-topic?               → chat + off_topic
3. Greeting / social?       → chat + greeting
4. SEC / filing signals?    → deep + mcp (UNCHANGED)
5. Deep parallel (2+ tickers compare)? → deep + parallel (UNCHANGED)
6. Deep report + PDF intent?→ deep + report + pdf_delivery
7. Education / concept?     → edu_fast (NEW)
8. Debater specialist match?→ debater + agent_id
9. Live ticker research?    → fast
10. Default                 → chat + conversation
```

### Example Routing Table

| User question | Route | Why |
|---------------|-------|-----|
| What is a bond? | `edu_fast` | Pure concept — vector or fast search, then ingest |
| What is short selling? | `edu_fast` | Conceptual (policy allows; not actionable short advice) |
| Steps to invest in a bond? | `edu_fast` | Procedural education — numbered steps |
| What is stop loss? | `edu_fast` | Concept |
| Explain put? / Explain a put option? | `edu_fast` | Concept (no ticker) |
| Explain NVDA put options | `debater` → Zara | Ticker + options domain |
| NVDA 10-K risk factors | `deep` + `mcp` | SEC — current setup |
| AAPL latest 8-K | `deep` + `mcp` | Material events — current setup |
| Compare NVDA vs AMD Q3 outlook | `deep` + `parallel` | Multi-ticker — current setup |
| Send me a full NVDA research report as PDF | `deep` + `report` | Deep synthesis + PDF agent |
| What's NVDA's RSI and MACD? | `debater` → Zara | Quant specialist |
| Bear case on TSLA | `debater` → Victoria | Short-side specialist |
| How will Fed rate cuts affect my tech holdings? | `debater` → Reid | Macro (portfolio-aware) |
| What stop loss should I set on NVDA? | `debater` → Elena | Risk / position sizing (not pure concept) |
| NVDA price today | `fast` | Live data |
| When does NVDA report earnings? | `fast` + earnings context | Calendar lookup; enriched by C5 agent data |

### Education vs Debater Boundary

| Signal | Route |
|--------|-------|
| `what is / explain / define / how does` + **no ticker** | `edu_fast` |
| `what is / explain` + ticker but **pure concept** ("what is a put option") | `edu_fast` |
| Ticker + **specialist domain** (RSI, bear case, Fed, stop loss sizing) | `debater` |
| `how much should I / should I buy / should I sell` | `fast` or policy_flag — **not** debater auto-trade advice |

---

## 4. Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  USER — AlexChat (/research)                                                 │
│  POST /api/alex/chat                                                         │
└───────────────────────────────┬─────────────────────────────────────────────┘
                                ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  QUERY ROUTER (query_router.py) — extended intents                           │
│  + edu_fast | deep+report | debater | fast | deep+mcp | chat                   │
└───┬─────────┬─────────┬──────────────┬────────────────┬─────────────────────┘
    │         │         │              │                │
    ▼         ▼         ▼              ▼                ▼
 edu_fast   deep+mcp  deep+report   debater handoff    fast research
    │         │         │              │                │
    │         │         │              │                │
    ▼         ▼         ▼              ▼                ▼
┌────────┐ ┌────────┐ ┌────────────┐ ┌──────────┐   ┌──────────┐
│Vector  │ │Current │ │Deep pipeline│ │Marcus/   │   │yfinance  │
│search  │ │ECS deep│ │+ Report    │ │Victoria/ │   │+ news    │
│first   │ │+ MCP   │ │  Agent     │ │Zara/Reid/│   │          │
│        │ │        │ │+ PDF MCP   │ │Elena     │   │          │
│Fast    │ │        │ │→ S3 URL    │ │          │   │          │
│search  │ │        │ └────────────┘ └──────────┘   └──────────┘
│agent   │ │        │
│Ingest  │ │        │
└────────┘ └────────┘

┌─────────────────────────────────────────────────────────────────────────────┐
│  EARNINGS CALENDAR AGENT (autonomous — Phase C5)                             │
│  EventBridge daily → scan portfolio/watchlist → earnings_trend_signals       │
│  → dashboard card + chat context injection + optional SES digest             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Phase C1 — Education Fast Search + Vector Memory

**Goal:** Answer general financial questions efficiently; store answers in `research_vectors` when not already cached.

### Flow

```
POST /research/edu/stream
  1. Normalize query → canonical_key (lowercase, strip punctuation)
  2. Vector search research_vectors:
       - scope: global glossary + user_id (user's prior Q&A)
       - chunk_type IN ('education', 'glossary')
       - similarity threshold ≥ 0.82
  3. HIT  → stream cached answer + badge "From your knowledge base ✓"
  4. MISS → Edu Fast Search Agent:
       a. Seed glossary lookup (scripts/seed_finance_glossary.py — top 200 terms)
       b. Optional: 1-page fast fetch via Playwright MCP (investor.gov, Investopedia)
          — max 1 browse, 8s timeout, education sources allowlist only
       c. Nova Lite synthesize: 2–3 short paragraphs, bullets for steps
  5. Post-response (async, non-blocking):
       - Dedup: skip ingest if canonical_key exists (global or user)
       - ingest_financial_document(content, chunk_type='education', topic=canonical_key)
  6. SSE done event: { route: 'edu_fast', cached: bool, vector_id?: string }
```

### New Files

| File | Purpose |
|------|---------|
| `backend/researcher/edu_fast_agent.py` | Vector-first education pipeline |
| `backend/researcher/edu_search.py` | Glossary seed + allowlisted fast web fetch |
| `scripts/seed_finance_glossary.py` | Pre-load ~200 finance terms into `research_vectors` (`chunk_type=glossary`) |
| `scripts/tests/test_edu_fast.py` | Cache hit, miss+ingest, dedup, policy boundary |

### Glossary Seed Topics (Examples)

Bonds, short selling, stop loss, put option, call option, ETF, mutual fund, diversification, P/E ratio, dividend yield, margin, leverage, 401k, IRA, inflation, yield curve, market cap, IPO, bear market, bull market, asset allocation, compound interest, dollar-cost averaging, limit order, market order, etc.

### Ingest Rules

| Field | Value |
|-------|-------|
| `chunk_type` | `education` (user-generated) or `glossary` (seed) |
| `topic` | Canonical question key |
| `query` | Original user wording |
| `source` | `alex-edu-fast` / `alex-glossary-seed` |
| `user_id` | Set for user-specific Q&A; null for global glossary |
| Dedup | `canonical_key` hash — no duplicate vectors for same concept |

### Latency Targets

| Case | Target |
|------|--------|
| Vector cache hit | **< 1.5s** first token |
| Glossary seed hit | **< 3s** |
| Fast search + synthesize | **< 8s** |
| Ingest | Async — does not block stream |

---

## Phase C2 — SEC Filing Path (Keep Current)

**No architectural change.** Continue using:

- Route: `deep` + `deep_kind=mcp`
- Endpoint: `/research/deep/stream`
- Tools: `get_sec_filings`, Playwright MCP for EDGAR
- Signals: `10-k`, `10-q`, `8-k`, `filing`, `edgar`, `sec`, `proxy`, `form 4`, etc.

### Minor Enhancements (Optional, Same Phase)

| Enhancement | Detail |
|-------------|--------|
| Explicit 8-K labeling | Router intent `sec_8k` when query mentions material event / 8-K |
| Filing date in response | Pull `filedAt` from SEC tool metadata |
| Ingest filing summary | After deep SEC answer, ingest `chunk_type=sec_summary` for session memory |
| Citation block | Always show filing type + date + SEC link in markdown |

**Note:** User wrote "4-k" — treat as **8-K** (current events). 10-K and 10-Q remain primary annual/quarterly paths.

---

## Phase C3 — Deep Research Report + PDF Delivery

**Goal:** Deep research questions produce the full report as today, plus an optional **PDF artifact** delivered to the user.

### Trigger Signals

Router sets `deep_kind=report` when query contains:

- `pdf`, `report`, `memo`, `download`, `send me`, `write up`, `investment report`
- OR user clicks **"Export PDF"** button after any deep response

### Pipeline

```
deep research (existing parallel or mcp path)
  → Alex Synthesizer (hedge-fund memo format)
  → Report Agent (report_agent.py)
       1. Structure: Title, Executive Summary, Sections, Citations, Disclaimer
       2. Render markdown → PDF via PDF MCP
       3. Upload to S3 (alex-reports/{user_id}/{report_id}.pdf)
       4. Return presigned URL (24h expiry)
  → SSE: { type: 'artifact', format: 'pdf', url, report_id, pages }
  → Ingest summary chunk to research_vectors (chunk_type=report)
```

### PDF MCP (`backend/researcher/mcp/pdf_mcp.py`)

| Tool | Implementation |
|------|----------------|
| `render_markdown_pdf` | Markdown → HTML → PDF via **WeasyPrint** or **Playwright `page.pdf()`** on ECS |
| `upload_report` | S3 put + presigned GET |
| `get_report_metadata` | pages, size, created_at |

**Why MCP:** Same tool surface for chat agent and future email delivery; logged in `/observe`.

### Report Agent

**File:** `backend/researcher/report_agent.py`

- Input: synthesized markdown + query metadata + citations
- Output: S3 URL + report record in `research_reports` table
- Model: Nova Lite for section ordering only; content from synthesizer

### Frontend

- Deep response footer: **Download PDF** button
- SSE `artifact` event → toast with link
- `/research` session history shows past reports

### Guardrails

- PDF footer: *"Not financial advice. Generated by Alex AI for research purposes."*
- Max 25 pages; truncate with "continued in chat" section

---

## Phase C4 — Debater Handoff Intelligence

**Goal:** Questions that need a **specialist perspective** route to the right Trading Floor agent and render as a branded specialist card in chat.

### Expanded Agent Routing

| Agent | New / expanded patterns | Example questions |
|-------|------------------------|-------------------|
| **Marcus** (Growth) | `earnings growth`, `revenue trajectory`, `is X a good growth stock` | "Is NVDA still a growth story?" |
| **Victoria** (Bear) | `downside`, `too expensive`, `short thesis`, `red flags` | "Bear case on META" |
| **Zara** (Quant) | `put`, `call`, `options`, `rsi`, `macd`, `technical`, `support level` | "Explain NVDA put options" / "RSI on AAPL" |
| **Reid** (Macro) | `fed`, `rates`, `inflation impact`, `recession`, `sector rotation` | "How do rate cuts affect tech?" |
| **Elena** (Risk) | `stop loss for`, `position size`, `how much to allocate`, `portfolio risk`, `hedge` | "What stop loss on NVDA?" / "Am I too concentrated?" |

### Education vs Debater — Router Fix

Update `query_router.py` `classify_query` priority:

```
1. edu_fast if _is_educational_finance(query) AND NOT _needs_specialist_opinion(query)
2. debater if match_debater(query) score ≥ 1
```

**`_needs_specialist_opinion`:** ticker present + domain keywords (not bare "what is").

### Handoff UX (Chat)

SSE events:

```json
{ "type": "handoff", "debater": { "id": "zara", "name": "Zara Patel", "title": "Quantitative Strategist", "avatar": "..." } }
{ "type": "token", "content": "..." }
{ "type": "done", "route": "debater", "debater": "zara" }
```

**Frontend (`AlexChat.tsx`):** Specialist header chip above response — distinct color per agent.

### Context Enrichment

Before `run_debater_handoff`:

1. `portfolio_digests` for ticker (if exists)
2. `research_vectors` prior research on ticker
3. `simulated_trades` latest debate outcome (P6 bridge)
4. `earnings_trend_signals` if C5 live

### Multi-Specialist Mode (Addon — see C6)

When 2+ debaters score ≥ 1: optional **Committee** route — 2 agents + Executor synthesis (30s cap).

---

## Phase C5 — Earnings Calendar Agent

**Goal:** Autonomous agent scans earnings calendar, detects trends, proactively updates user.

### Agent Identity

| Field | Value |
|-------|-------|
| Name | **Earnings Scout** (or calendar display name: Calendar Agent) |
| Schedule | EventBridge **daily 6 AM ET** + **Sunday trend rollup** |
| Model | Nova Lite for trend narrative; yfinance/Finnhub for data |
| Storage | `earnings_calendar_events`, `earnings_trend_signals` |

### Data Sources

| Source | Data |
|--------|------|
| yfinance | `calendar` earnings dates per ticker |
| Finnhub MCP (P7) | `get_earnings_calendar`, `get_earnings_surprise` |
| User portfolio | `portfolios` tickers |
| Watchlist | `user_watchlist` (new table or extend `portfolios`) |

### Scan Logic

```
For each user (or batch):
  1. Load portfolio + watchlist tickers
  2. Fetch next 14 days earnings dates
  3. Upsert earnings_calendar_events
  4. Trend detection:
       - Beat/miss streak (last 4 quarters)
       - Guidance revision pattern
       - Peer cluster ("4 semiconductor names report this week")
       - Pre-earnings volatility vs historical
  5. Write earnings_trend_signals (JSONB trends + natural language summary)
  6. If earnings within 48h → dashboard alert card
  7. Optional: SES weekly digest "Your earnings week ahead"
```

### Chat Integration

| User asks | Handler |
|-----------|---------|
| When does NVDA report? | Fast lookup from `earnings_calendar_events` |
| Earnings trends for my portfolio | Inject `earnings_trend_signals` into prompt |
| Who reports this week? | Calendar agent data + markdown table |

### Proactive Dashboard Card

```
📅 Earnings This Week
NVDA — Wed Feb 26 (AMC) · Beat streak 3/4 · Vol +18% vs avg
ASML — Thu Feb 27 (BMO) · Peer cluster: semi equipment
[Ask Alex about NVDA earnings →]
```

### Files

| File | Purpose |
|------|---------|
| `backend/agents/earnings_calendar_agent.py` | Scan + trend logic |
| `backend/researcher/mcp/earnings_mcp.py` | Finnhub/yfinance tools (shared with deep sub-agents) |
| `terraform/6_agents/main.tf` | EventBridge `alex-earnings-calendar-daily` |
| `frontend/app/dashboard/page.tsx` | Earnings week card |

---

## Phase C6 — Additional Agentic Add-ons

Suggested upgrades to make Alex more agentic and use debater agents more in chat.

### C6.1 — Finance Glossary Fast Path (Pre-requisite for C1)

- Seed 200 terms at deploy (`seed_finance_glossary.py`)
- Sub-ms lookup before vector search for known canonical keys
- **Effort:** 0.5 day

### C6.2 — Committee Mini-Debate (Chat)

**When:** User asks contested questions — "Is NVDA overvalued?" (Marcus + Victoria), "Should I hedge?" (Elena + Reid)

```
Router → committee mode
  → 2 debaters stream opening positions (parallel)
  → Executor (Alex PM) synthesizes 1 paragraph verdict
  → ingest chunk_type=committee_debate
```

**Effort:** 2–3 days · **Reuse:** `debate_engine.py` vote structure, lightweight

### C6.3 — Clarification Router

**When:** Ambiguous query — "Tell me about Apple" (AAPL vs Apple Inc bond?)

```
Router confidence < 0.65 → clarification
SSE: { type: 'clarify', options: ['AAPL stock', 'Apple bonds', 'Apple supply chain'] }
User picks → re-route with full confidence
```

**Effort:** 1 day

### C6.4 — Proactive Suggestion Chips

After each response, generate 2–3 contextual follow-ups:

- After edu "what is a bond?" → "Steps to buy treasuries", "Bond vs CD comparison"
- After debater Zara → "Show NVDA options flow", "Elena: position size for this trade?"
- Powered by Nova Lite + route metadata

**Effort:** 1–2 days · **Frontend:** `AlexChat.tsx` chip row

### C6.5 — Cross-Session Memory Callback

When vector hit from **prior session**:

> "You asked about bonds 12 days ago — here's what I said, updated with today's rates context."

**Effort:** 1 day · **Depends:** C1 ingest live

### C6.6 — Scout Pulse (Intraday Chat Entry)

**When:** User opens chat or asks "what's moving?"

- Pull Scout agent snapshot (Trading Floor P9) — top movers in portfolio sector
- 1-paragraph market pulse before user types

**Effort:** 2 days · **Depends:** Trading Floor scout agent

### C6.7 — Executor Handoff for Portfolio Questions

**When:** "What should I do with my portfolio?" (not policy-flagged)

- Route to **Executor (Alex PM)** with full portfolio + digest + debate history
- Synthesized allocation commentary — **no auto-execution** (aligns with P1.5 approval)

**Effort:** 2 days · **Reuse:** `debate_engine.run_executor()`

### C6.8 — Ingest on All Routes

Today ingest is sparse. Extend:

| Route | Ingest |
|-------|--------|
| edu_fast | ✅ always (C1) |
| fast | summary chunk |
| deep | report summary |
| debater | specialist answer |
| committee | full debate summary |

**Effort:** 1 day · **File:** `post_response_ingest.py` hook in `server.py`

### C6.9 — Earnings-Aware Debater Context

Before Marcus/Victoria handoff on pre-earnings ticker:

- Inject `earnings_trend_signals` + implied move
- Zara gets pre-earnings IV rank

**Effort:** 0.5 day · **Depends:** C5

### Priority Ranking (If Sequencing Addons)

| Priority | Addon | Why |
|----------|-------|-----|
| 1 | C6.1 Glossary seed | Unblocks sub-second education |
| 2 | C6.8 Ingest on all routes | Memory compound effect |
| 3 | C6.4 Suggestion chips | Engagement, feels agentic |
| 4 | C6.2 Committee mini-debate | Showcases debater roster in chat |
| 5 | C6.5 Cross-session callback | Trust + memory proof |
| 6 | C6.3 Clarification router | Reduces wrong-route frustration |
| 7 | C6.7 Executor portfolio handoff | High value for portfolio users |
| 8 | C6.6 Scout pulse | Nice proactive touch |

---

## Router Changes

### New Route Types

```python
RouteName = Literal["fast", "deep", "chat", "debater", "edu_fast"]

class RouteDecision(BaseModel):
    route:       RouteName
    deep_kind:   Optional[Literal["mcp", "parallel", "report"]] = None
    intent:      str = "general"
    deliverable: Optional[Literal["pdf", "none"]] = None
    debater:     Optional[str] = None
    committee:   Optional[list[str]] = None  # C6.2
    ...
```

### `classify_query` Priority (Updated)

```python
# After guardrails / off-topic / greeting:
if _is_sec_filing_query(query):        return deep + mcp
if _wants_pdf_report(query):           return deep + report, deliverable=pdf
if _is_educational_finance(query) and not _needs_specialist_opinion(query):
    return edu_fast
dm = match_debater(query)
if dm:                                 return debater
if _needs_live_research(query):        return fast
...
```

### New Regex Patterns

```python
EDU_PROCEDURAL = re.compile(r"\b(steps to|how to invest|how do i buy|how to start)\b", re.I)
PDF_SIGNALS = ["pdf", "download report", "send me a report", "investment memo", "write up"]
COMMITTEE_SIGNALS = ["overvalued", "undervalued", "should i worry", "bull or bear"]
```

### Chat Route Handler Map (`frontend/app/api/alex/chat/route.ts`)

| `routing.route` | ECS path |
|-----------------|----------|
| `edu_fast` | `/research/edu/stream` *(new)* |
| `chat` | `/research/conversation/stream` |
| `debater` | `/research/debater/stream` |
| `deep` + `mcp` | `/research/deep/stream` |
| `deep` + `parallel` | planner + poll (existing) |
| `deep` + `report` | `/research/deep/report/stream` *(new)* |
| `fast` | `/research/stream` |

---

## Schema Extensions

Add to `scripts/aurora_warmup.py`:

```sql
-- Research PDF artifacts
CREATE TABLE IF NOT EXISTS research_reports (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL REFERENCES users(id),
  session_id VARCHAR(36),
  query TEXT NOT NULL,
  title VARCHAR(300),
  s3_key VARCHAR(500) NOT NULL,
  page_count INTEGER,
  file_size_bytes INTEGER,
  route VARCHAR(30) DEFAULT 'deep',
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Earnings calendar agent
CREATE TABLE IF NOT EXISTS earnings_calendar_events (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL REFERENCES users(id),
  ticker VARCHAR(10) NOT NULL,
  report_date DATE NOT NULL,
  report_time VARCHAR(10),  -- BMO, AMC, DMH
  fiscal_quarter VARCHAR(10),
  source VARCHAR(50) DEFAULT 'yfinance',
  updated_at TIMESTAMPTZ DEFAULT NOW(),
  UNIQUE(user_id, ticker, report_date)
);

CREATE TABLE IF NOT EXISTS earnings_trend_signals (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL REFERENCES users(id),
  ticker VARCHAR(10) NOT NULL,
  beat_streak INTEGER DEFAULT 0,
  miss_streak INTEGER DEFAULT 0,
  avg_surprise_pct NUMERIC(8,4),
  pre_earnings_iv_rank NUMERIC(6,2),
  peer_cluster JSONB DEFAULT '[]',
  trend_summary TEXT,
  computed_at TIMESTAMPTZ DEFAULT NOW(),
  UNIQUE(user_id, ticker)
);

CREATE INDEX IF NOT EXISTS rv_chunk_type_idx ON research_vectors (chunk_type);
CREATE INDEX IF NOT EXISTS rv_topic_trgm_idx ON research_vectors USING gin (topic gin_trgm_ops);
```

**`research_vectors.chunk_type` values:** `glossary` | `education` | `research` | `sec_summary` | `report` | `debater` | `committee_debate`

---

## API, SSE & Frontend

### New SSE Event Types

| Event | Payload | When |
|-------|---------|------|
| `cache_hit` | `{ source: 'vector' \| 'glossary', similarity }` | edu_fast hit |
| `artifact` | `{ format: 'pdf', url, report_id, pages }` | deep report done |
| `handoff` | `{ debater: { id, name, title } }` | debater start |
| `committee` | `{ agents: ['marcus','victoria'] }` | C6.2 |
| `clarify` | `{ options: string[] }` | C6.3 |
| `suggestions` | `{ chips: string[] }` | C6.4 post-response |

### `AlexChat.tsx` Changes

| Feature | Detail |
|---------|--------|
| Route badge | Show `Education` / `SEC Research` / `Zara · Quant` / `PDF Report` |
| PDF download | Button on `artifact` event |
| Debater card | Avatar + title header on handoff |
| Suggestion chips | Clickable follow-ups below message |
| Earnings chip | "3 earnings this week" → opens calendar card |

### Observability (`/observe`)

New panels:

- Education cache hit rate (7d)
- edu_fast P50/P95
- PDF reports generated
- Debater handoff distribution (Marcus 22%, Zara 18%, …)
- Earnings agent last run + tickers scanned

---

## Implementation Order & Estimates

| Phase | Scope | Effort | Depends |
|-------|-------|--------|---------|
| **C1** | Education fast search + vector ingest + glossary seed | **3–4 days** | P0 vectors ✅ |
| **C2** | SEC path hardening + sec_summary ingest | **1 day** | None |
| **C4** | Debater pattern expansion + chat card UX | **2 days** | None |
| **C3** | Deep report + PDF MCP + S3 | **3–4 days** | WeasyPrint/Playwright on ECS |
| **C5** | Earnings calendar agent + dashboard card | **3–4 days** | EventBridge Terraform |
| **C6.1–C6.4** | Glossary + ingest all routes + chips | **2–3 days** | C1 |
| **C6.2, C6.5–C6.7** | Committee, cross-session, Executor | **4–5 days** | C4, P6 |

**Recommended 3-week sprint:**

```
Week 1: C1 (edu_fast) + C6.1 glossary seed + C6.8 ingest hook
Week 2: C4 debater expansion + C2 SEC ingest + C6.4 suggestion chips
Week 3: C5 earnings agent OR C3 PDF reports (pick by user priority)
Week 4: C3 or C5 (whichever deferred) + C6.2 committee mode
```

**MVP (1 week):** C1 + C4 + glossary seed — immediately improves daily chat quality.

---

## Decision Points

| # | Decision | Options | Recommendation |
|---|----------|---------|----------------|
| 1 | Education web fetch | Glossary only vs allowlisted Playwright | **Glossary + allowlist** (investor.gov, investopedia) |
| 2 | PDF renderer | WeasyPrint vs Playwright `page.pdf()` | **Playwright** — already on ECS for MCP |
| 3 | Earnings agent scope | Portfolio only vs portfolio + watchlist | **Both** |
| 4 | Committee mode | Auto vs opt-in "get both sides" | **Auto** when Marcus+Victoria both score ≥ 1 |
| 5 | edu_fast route name | New route vs `chat` sub-intent | **New route `edu_fast`** — clearer observability |
| 6 | Vector scope for education | Global glossary + per-user | **Both** — global seed, user overlay |

---

## Related Documents

| Document | Relationship |
|----------|--------------|
| `Alex_AI_2.0.md` | Parent conversational AI vision — Phases A–I |
| `Alex_Master_Implementation_Plan.md` | P2 RAG engine, P6 context bridge, P15 sub-agents, **P22–P24 LangChain + Agentic RAG** |
| `Alex_Trading_Floor_2.0.md` | Debater agents, Executor, scout, P6 bridge |
| `Alex_report.md` | §33 change log — log all shipped chat intelligence work |
| `backend/researcher/query_router.py` | Router to extend |
| `backend/researcher/debater_registry.py` | Specialist patterns to expand |
| `DM_apply.md` | Demo talking points for agentic chat |

---

## Changelog

| Date | Change |
|------|--------|
| 2026-06-14 | Initial `Alex_chat_intelligence.md` — C1–C6 phases, router taxonomy, schema, estimates |
