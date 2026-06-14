# Alex AI 2.0 — Intelligent Conversational Financial Intelligence

> **Status:** PARKED — awaiting approval before implementation  
> **Created:** June 13, 2026  
> **Companion doc:** `Alex_Trading_Floor_2.0.md`  
> **Unified implementation:** `Alex_Master_Implementation_Plan.md`

---

## Table of Contents

1. [Vision](#vision)
2. [Current State & Gaps](#current-state--gaps)
3. [Target Experience](#target-experience)
4. [Architecture Overview](#architecture-overview)
5. [Phase A — Alex Query Router (Remove Manual Toggle)](#phase-a--alex-query-router)
6. [Phase B — Fast & Deep Agent Delegation](#phase-b--fast--deep-agent-delegation)
7. [Phase C — MCP Expansion for Deep Researcher](#phase-c--mcp-expansion)
8. [Phase D — Alex Synthesizer (Commentary Layer)](#phase-d--alex-synthesizer)
9. [Phase E — Session Memory & RAG Engine](#phase-e--session-memory--rag-engine)
10. [Phase F — Per-User Vector Store & Ingest](#phase-f--per-user-vector-store--ingest)
11. [Phase G — Trading Floor Context Bridge](#phase-g--trading-floor-context-bridge)
12. [Phase H — Unified Guardrails](#phase-h--unified-guardrails)
13. [Phase I — Conversational UX & Proactive Intelligence](#phase-i--conversational-ux)
14. [Aurora Schema Extensions](#aurora-schema-extensions)
15. [API & Frontend Changes](#api--frontend-changes)
16. [Observability Mapping](#observability-mapping)
17. [Decision Points](#decision-points)

---

## Vision

Alex becomes a **single conversational financial intelligence** — the user asks anything about any ticker, company name, CEO statement, or market event in natural language. Alex:

1. **Understands** the question (entity extraction, intent classification, complexity scoring)
2. **Reasons** whether to delegate to Fast Research, Deep Research, or Multi-Agent Planner
3. **Researches** using live tools and MCP servers
4. **Synthesizes** commentary — concise for fast queries, hedge-fund-manager depth for deep research
5. **Remembers** everything per user session in the vector store (RAG)
6. **Shares intelligence** with Trading Floor agents to enrich their debates
7. **Stays in bounds** — financial questions only, guardrailed, portfolio-aware
8. **Proactively compares** trading floor simulation performance vs user's real portfolio

**No more manual Fast/Deep toggle.** Alex decides.

### Example Queries Alex Must Handle

| User asks | Router decision | Why |
|-----------|----------------|-----|
| "Will NVDA go up?" | Fast → Synthesizer | Price + sentiment + technicals sufficient |
| "Jensen Huang said AI demand is insatiable — what does that mean for NVDA?" | Deep → Synthesizer | Needs web/news verification + earnings context |
| "Compare NVDA vs AMD for next quarter" | Multi-Agent Planner → Synthesizer | Multi-ticker comparative analysis |
| "What's my ASML position worth today?" | Fast + Portfolio context | Portfolio-aware price lookup |
| "Show me NVDA's latest 10-K risks" | Deep (SEC MCP) | Filing-level depth required |
| "What did the trading floor decide on NVDA today?" | Fast + Trading context | Reads simulated_trades + agent votes |
| "What's the weather in Paris?" | Reject (guardrail) | Off-topic — polite redirect |
| "Should I put my life savings in TSLA?" | Fast + Guardrail | Harmful advice pattern — guarded response |

---

## Current State & Gaps

### What Exists

| Component | File | Status |
|-----------|------|--------|
| Fast researcher (ECS) | `backend/researcher/server.py` → `run_data_agent()` | ✅ Live market tools |
| Deep researcher (ECS) | `server.py` → `run_deep_agent()` | ✅ SEC + Playwright MCP |
| Multi-agent planner | `backend/agents/planner.py` | ✅ Task decomposition |
| Context service (6 use cases) | `backend/researcher/context_service.py` | ⚠️ Designed but **broken** (SQL typos) |
| Ingest pipeline | `backend/ingest/ingest_pgvector.py` | ✅ Global vector store |
| Chat sessions | `chat_sessions` table | ⚠️ Partially wired |
| Research sessions | `research_sessions` table | ⚠️ Non-stream path only |
| Guardrails (Bedrock) | `terraform/7_guardrails/main.tf` | ✅ Researcher only |
| Manual Fast/Deep toggle | `frontend/app/research/page.tsx` | ✅ To be **removed** |
| Regex complexity routing | `frontend/app/api/research/route.ts` | ⚠️ Duplicated, regex-only |

### Critical Gaps

| Gap | Impact |
|-----|--------|
| **Manual Fast/Deep toggle** — user must choose mode | Poor UX; users don't know which mode to pick |
| **No LLM intent router** — regex-only routing | "Jensen Huang said X" doesn't route to deep |
| **Deep routes omit `user_id` + `session_id`** | Deep mode has no memory |
| **`context_service.py` SQL bugs** (`LECT`, `result[ecords]`, `resul'records']`) | Context retrieval fails silently |
| **`portfolio_stocks` vs `portfolios` table mismatch** | Portfolio context returns empty |
| **`research_vectors` has no `user_id` or `session_id`** | Global-only memory, no per-user RAG |
| **Stream responses not saved** to `research_sessions` | Primary UX path loses history |
| **No chunking** — full responses ingested as single vector | Poor RAG retrieval for long answers |
| **Multi-agent reporter uses Bedrock only** — no ECS tools | Complex queries lack live data |
| **Trading agents have zero research memory** | Debates ignore all Alex intelligence |
| **No synthesis layer** — raw agent output shown to user | No Alex personality or commentary style |
| **Guardrails not on reporter/multi-agent path** | Safety gap |
| **No trading floor performance comparison** | Missed proactive insight |

---

## Target Experience

```
User: "Jensen Huang said AI demand is insatiable at the GTC keynote — 
       will NVDA go up because of this?"

Alex (reasoning visible):
  🔍 Analyzing query...
  📌 Entities: NVDA, Jensen Huang, GTC keynote
  🧠 Intent: news_event + price_opinion
  ⚡ Complexity: medium-high (needs source verification)
  → Delegating to: Deep Research Agent
  🔌 Connecting SEC EDGAR + news sources...

Alex (response — hedge fund manager style):

  **NVDA — Post-GTC Demand Commentary**
  
  Jensen Huang's "insatiable demand" framing at GTC aligns with three 
  concrete data points I've verified:
  
  1. **Hyperscaler capex** — MSFT, GOOG, META collectively guided 
     $180B+ in 2026 AI infrastructure spend (↑12% QoQ)
  2. **NVDA data center revenue** grew 112% YoY last quarter; Blackwell 
     backlog extends into Q3 per supply chain checks
  3. **Risk**: China export restrictions could cap ~15% of data center TAM
  
  **My read:** Bullish near-term (6-12 months) on demand thesis. 
  Valuation at 38x forward P/E prices in much of this optimism.
  
  *Your portfolio: 0 NVDA shares. Trading floor simulation bought 
  5 shares @ $142 yesterday (Marcus 82% confidence). Sim is +2.3% 
  today vs your portfolio +0.8%.*
  
  [Stored to your session memory ✓]
```

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────────┐
│                     USER — Single Chat Interface                       │
│                     /research (no Fast/Deep toggle)                      │
└──────────────────────────────┬──────────────────────────────────────────┘
                               │ POST /api/alex/chat
                               ▼
┌──────────────────────────────────────────────────────────────────────────┐
│                     ALEX QUERY ROUTER (new)                               │
│  1. Entity extraction (tickers, companies, people, events)              │
│  2. Intent classification (Nova Lite — fast, cheap)                      │
│  3. Complexity scoring                                                    │
│  4. Financial-only gate (reject off-topic)                                │
│  5. Route decision: FAST | DEEP | MULTI | PORTFOLIO | TRADING | REJECT  │
└───────┬──────────────┬──────────────┬──────────────┬────────────────────┘
        │              │              │              │
        ▼              ▼              ▼              ▼
   ┌─────────┐  ┌───────────┐  ┌──────────┐  ┌──────────────┐
   │  FAST   │  │   DEEP    │  │  MULTI   │  │   CONTEXT    │
   │Researcher│  │Researcher │  │ Planner  │  │   ONLY       │
   │  /research│  │/research/deep│  │+ Reporter│  │(portfolio/ │
   │  8 turns │  │ 20 turns  │  │          │  │ trading Q)  │
   └────┬────┘  └─────┬─────┘  └────┬─────┘  └──────┬───────┘
        │              │              │              │
        └──────────────┴──────────────┴──────────────┘
                               │
                               ▼
┌──────────────────────────────────────────────────────────────────────────┐
│                     RAG CONTEXT ENGINE (fixed + extended)                   │
│  • Session conversation history (chat_sessions)                           │
│  • Per-user vector memory (research_vectors scoped by user_id)            │
│  • Portfolio context (portfolios + portfolio_digests)                     │
│  • Trading floor context (simulated_trades + agent votes)                 │
│  • Contradiction detection + sector patterns                              │
│  • Chunking + reranking + MMR diversity                                   │
└──────────────────────────────┬───────────────────────────────────────────┘
                               │
                               ▼
┌──────────────────────────────────────────────────────────────────────────┐
│                     ALEX SYNTHESIZER (new)                                │
│  Fast path  → concise commentary (2-3 paragraphs, bullet highlights)    │
│  Deep path  → hedge fund manager memo (structured, detailed, sourced)     │
│  Multi path → unified comparative report                                  │
│  + Proactive trading floor comparison (when relevant)                     │
└──────────────────────────────┬───────────────────────────────────────────┘
                               │
                               ▼
┌──────────────────────────────────────────────────────────────────────────┐
│                     MEMORY PERSISTENCE                                      │
│  • chat_sessions — turn-by-turn JSONB                                     │
│  • research_sessions — full Q&A with vector_id link                       │
│  • research_vectors — chunked, user_id + session_id scoped                │
│  • ingest pipeline — SageMaker embeddings → pgvector                        │
└──────────────────────────────┬───────────────────────────────────────────┘
                               │
                               ▼
┌──────────────────────────────────────────────────────────────────────────┐
│                     TRADING FLOOR BRIDGE                                  │
│  Debate agents read session vectors + digests for ticker context          │
│  agent_observations.data_used logs which RAG chunks influenced vote       │
└──────────────────────────────────────────────────────────────────────────┘
```

---

## Phase A — Alex Query Router

**Goal:** Replace manual Fast/Deep toggle and regex routing with an intelligent LLM-powered router.

### New Module

**File:** `backend/researcher/query_router.py`

```python
class RouteDecision(BaseModel):
    route:        Literal['fast', 'deep', 'multi', 'portfolio', 'trading', 'reject']
    confidence:   float
    entities:     list[str]   # tickers, companies, people
    intent:       str         # price_opinion, news_event, sec_filing, comparison, ...
    reasoning:    str         # shown to user as "Alex is thinking..."
    complexity:   Literal['low', 'medium', 'high']
```

### Router Logic (Nova Lite — ~200ms, cheap)

```
Prompt: Classify this financial query and decide routing.

Query: "{user_query}"

Respond ONLY with JSON:
{
  "route": "fast|deep|multi|portfolio|trading|reject",
  "intent": "...",
  "entities": ["NVDA", "Jensen Huang"],
  "complexity": "low|medium|high",
  "reasoning": "One sentence explaining routing decision",
  "confidence": 0.0-1.0
}

Routing rules:
- fast: price checks, simple news, single-ticker sentiment, quick facts
- deep: SEC filings, CEO/executive statements, earnings deep dives, 
        regulatory analysis, "X said Y" verification, 10-K/10-Q
- multi: compare 2+ tickers, portfolio-wide analysis, "which is better"
- portfolio: "my holdings", "my ASML position", personal portfolio questions
- trading: "what did agents decide", "trading floor", simulation performance
- reject: non-financial topics (weather, recipes, coding, etc.)
```

### Routing Decision Matrix

| Signal | → Route |
|--------|---------|
| 2+ tickers + comparison language | `multi` |
| SEC, 10-K, 10-Q, filing, proxy | `deep` |
| CEO/executive name + "said/told/announced" | `deep` |
| "my portfolio", "my holdings", "my position" | `portfolio` (+ fast context) |
| "trading floor", "agents decided", "simulation" | `trading` (+ context) |
| Single ticker + price/sentiment/news | `fast` |
| Non-financial keywords | `reject` |
| Ambiguous | `fast` (default, upgrade to deep if confidence < 0.6) |

### Frontend Change

**Remove** Fast/Deep toggle buttons from `/research`.  
**Add** reasoning steps panel showing router decision:
```
🔍 Analyzing your question...
📌 Detected: NVDA, Jensen Huang, GTC keynote
🧠 Intent: news_event + price_opinion
→ Routing to: Deep Research Agent
```

### API Change

**New unified endpoint:** `POST /api/alex/chat` (replaces separate fast/deep/multi paths)

```typescript
// Request
{ query: string, session_id: string }

// Response (streaming SSE)
{ type: 'routing', content: RouteDecision }
{ type: 'reasoning', content: '...' }
{ type: 'token', content: '...' }
{ type: 'done', metadata: { route, vector_ids, session_id } }
```

---

## Phase B — Fast & Deep Agent Delegation

### Fast Researcher (unchanged core, enriched context)

- **Endpoint:** ECS `POST /research` or `/research/stream`
- **Tools:** `get_stock_data`, `ingest_financial_document`
- **Max turns:** 8
- **When:** Router says `fast`, `portfolio`, or low-complexity queries
- **Change:** Receives full RAG context from context engine (not just broken `build_full_context`)

### Deep Researcher (expanded MCP, enriched context)

- **Endpoint:** ECS `POST /research/deep` or `/research/deep/stream`
- **Tools:** `ingest_financial_document`, `get_sec_filings` + MCP servers (Phase C)
- **Max turns:** 20
- **When:** Router says `deep`, or CEO/news/filing queries
- **Change:** Always receives `user_id` + `session_id` (currently missing in deep API routes)

### Multi-Agent Path (upgraded)

- **When:** Router says `multi`
- **Current:** Planner → Tagger → Reporter (Bedrock only, no tools)
- **Proposed:** Planner → ECS fast/deep per task (based on sub-task intent) → Synthesizer
- **Alternative MVP:** Keep planner pipeline but inject RAG context into reporter prompts + call ECS for data-heavy sub-tasks

### Portfolio & Trading Context-Only Routes

Some queries don't need full research — just context retrieval:

| Route | Handler |
|-------|---------|
| `portfolio` | RAG engine + portfolio DB + live prices → Synthesizer |
| `trading` | RAG engine + `simulated_trades` + `agent_positions` → Synthesizer |

---

## Phase C — MCP Expansion for Deep Researcher

### Current MCP

| Server | Status | File |
|--------|--------|------|
| Playwright | ✅ Active | `backend/researcher/mcp_servers.py` |

### Proposed MCP Servers

| MCP Server | Tools | Use Case |
|------------|-------|----------|
| **Playwright** (existing) | `browse`, `screenshot`, `extract_text` | News sites, analyst pages, investor relations |
| **SEC EDGAR MCP** (new) | `search_filings`, `get_10k_section`, `get_insider_trades` | "Show me NVDA 10-K risk factors" |
| **Financial News MCP** (new) | `search_news`, `get_earnings_transcript`, `get_analyst_ratings` | "Jensen Huang said X at GTC" |
| **Market Data MCP** (new) | `get_quote`, `get_options_flow`, `get_short_interest` | Price context for deep analysis |
| **Earnings MCP** (new) | `get_earnings_surprise`, `get_guidance`, `get_consensus` | Earnings-related deep queries |

### MCP Assignment by Route

| Route | MCP Servers |
|-------|-------------|
| Fast | None (uses Python tools only — stays under Bedrock tool limit) |
| Deep | Playwright + SEC EDGAR + Financial News |
| Multi (per sub-task) | Assigned per sub-task intent by router |

### Implementation

**Directory:** `backend/researcher/mcp/`

```
mcp/
  __init__.py
  playwright_server.py    # existing, move from mcp_servers.py
  sec_edgar_mcp.py        # wraps edgartools + SEC API
  financial_news_mcp.py   # NewsAPI / Finnhub / RSS aggregation
  market_data_mcp.py      # thin wrapper over tools/market_data.py
  earnings_mcp.py         # earnings transcripts + surprises
  mcp_gateway.py          # selects servers per route, manages lifecycle
```

### MCP Observability

Every MCP call logged:
```json
{
  "tool": "sec_edgar.search_filings",
  "ticker": "NVDA",
  "latency_ms": 1200,
  "success": true,
  "result_chars": 4500
}
```

Stored in `agent_observations.data_used` → visible on `/observe`.

---

## Phase D — Alex Synthesizer (Commentary Layer)

**Goal:** Transform raw agent output into Alex's voice — concise for fast, hedge-fund depth for deep.

### New Module

**File:** `backend/researcher/synthesizer.py`

### Fast Commentary Style

```
Prompt: You are Alex, a sharp financial analyst. Synthesize this research 
into a clear, concise response (2-3 paragraphs max).

Include:
- Direct answer to the user's question
- 3 bullet key findings
- One-line risk caveat
- Reference prior session context if relevant

Style: Confident, accessible, no jargon walls.
NOT financial advice.
```

### Deep Commentary Style (Hedge Fund Manager Memo)

```
Prompt: You are Alex, a senior hedge fund analyst writing an internal memo.

Structure:
1. **Executive Summary** (3 sentences — the answer)
2. **Thesis** (why this matters now)
3. **Supporting Evidence** (data points with sources)
4. **Variant Perception** (what consensus gets wrong)
5. **Risk Factors** (what could invalidate the thesis)
6. **Positioning Implication** (BUY/HOLD/SELL framing — not advice)
7. **What to Watch** (next catalysts, dates)

Style: Detailed, sourced, institutional quality. Use **bold** for key metrics.
Length: 500-1000 words.
NOT financial advice.
```

### Multi-Agent Synthesis Style

```
Prompt: Synthesize these parallel research tasks into a unified report.

Tasks completed: {task_list}
Results: {task_results}

Structure:
## Executive Summary
## {Ticker 1} Analysis
## {Ticker 2} Analysis
## Comparative Assessment
## Recommendation Framework
```

### Proactive Trading Floor Comparison

Synthesizer appends when relevant (user has active simulation + asked about a held ticker):

```
---
📊 **Trading Floor Update**
Your simulation is **+2.3%** today vs your real portfolio **+0.8%**.
Latest agent decision on {ticker}: BUY (Marcus 82%, Victoria dissent SELL).
[View full debate →](/trading)
```

Triggered when:
- User query mentions a ticker in their portfolio or simulation
- Trading floor has run today
- Simulation return ≠ portfolio return (any difference worth noting)

---

## Phase E — Session Memory & RAG Engine

**Goal:** Full context engineering with chunking, hybrid retrieval, and per-user scoping.

### Fix Existing Bugs (P0)

**File:** `backend/researcher/context_service.py`

| Bug | Fix |
|-----|-----|
| `"LECT messages"` | → `"SELECT messages"` |
| `result[ecords]` | → `result['records']` |
| `resul'records']` | → `result['records']` |
| `portfolio_stocks` table | → `portfolios` |
| `get_prior_research(userd: str)` typo | → `user_id` |
| No user filter in vector search | → Add `user_id` filter |

### RAG Pipeline Architecture

**File:** `backend/researcher/rag_engine.py` (new)

```
build_context(query, user_id, session_id) → ContextBundle

ContextBundle:
  conversation:  str   # last 5 turns from chat_sessions
  prior_research: str  # semantic search on research_vectors (user-scoped)
  portfolio:     str   # holdings + portfolio_digests
  trading:       str   # latest simulated_trades + agent votes
  contradictions: str  # changes vs prior research
  sector_patterns: str # cross-ticker themes
  chunks_used:   list  # for observability attribution
```

### RAG Techniques

| Technique | Implementation | Purpose |
|-----------|---------------|---------|
| **Semantic chunking** | Split responses at paragraph/section boundaries (~500 tokens) | Better retrieval granularity |
| **Hybrid search** | pgvector cosine + keyword `ILIKE` on topic | Catch exact ticker matches |
| **MMR (Maximal Marginal Relevance)** | Deduplicate similar chunks in retrieval | Diversity in context |
| **Reranking** | Nova Lite scores chunk relevance to query (top 5 from top 20) | Precision |
| **Context compression** | Summarize chunks > 400 chars before injection | Fit token budget |
| **Recency bias** | Weight recent chunks 1.5x in scoring | Fresh information preferred |
| **User scoping** | `WHERE user_id = :uid OR user_id IS NULL` | Personal + global knowledge |
| **Session scoping** | Prioritize current `session_id` chunks | Conversation continuity |
| **Contradiction detection** | Existing `detect_contradictions()` — fix bugs | Alert user to changes |
| **Token budget** | Max 4000 tokens context; priority: conversation > portfolio > vectors > trading | Prevent prompt overflow |

### Context Priority Order

```
1. Current session conversation (last 5 messages)     — always included
2. Portfolio holdings + digests for mentioned tickers — if ticker detected
3. Trading floor latest decision for mentioned ticker — if exists
4. Per-user vector chunks (top 5, reranked)           — semantic match
5. Global vector chunks (top 3)                       — institutional knowledge
6. Sector patterns                                     — if 5+ recent vectors
7. Contradiction alerts                                — if detected
```

---

## Phase F — Per-User Vector Store & Ingest

### Schema Extension

```sql
-- Extend research_vectors
ALTER TABLE research_vectors ADD COLUMN IF NOT EXISTS user_id UUID REFERENCES users(id);
ALTER TABLE research_vectors ADD COLUMN IF NOT EXISTS session_id VARCHAR(36);
ALTER TABLE research_vectors ADD COLUMN IF NOT EXISTS chunk_index INTEGER DEFAULT 0;
ALTER TABLE research_vectors ADD COLUMN IF NOT EXISTS query TEXT;
ALTER TABLE research_vectors ADD COLUMN IF NOT EXISTS chunk_type VARCHAR(20) DEFAULT 'response';
-- chunk_type: 'query', 'response', 'summary', 'digest'

CREATE INDEX IF NOT EXISTS rv_user_session_idx ON research_vectors (user_id, session_id);
CREATE INDEX IF NOT EXISTS rv_user_created_idx ON research_vectors (user_id, created_at DESC);
```

### Ingest Flow (per chat turn)

```
User asks question
  → Router decides route
  → Agent researches (with RAG context)
  → Synthesizer produces commentary
  → Chunking engine splits response (500-token paragraphs)
  → For each chunk:
      POST /ingest { content, topic, user_id, session_id, chunk_index, query }
  → Link vector_ids to research_sessions.vector_id (first chunk)
  → Save full Q&A to research_sessions
  → Save turn to chat_sessions
```

### Chunking Strategy

**File:** `backend/researcher/chunking.py`

```python
def chunk_response(query: str, response: str, route: str) -> list[Chunk]:
    # 1. Always store the user query as chunk_type='query'
    # 2. Split response by markdown headers (## sections)
    # 3. If no headers, split by paragraphs (~500 tokens)
    # 4. Store executive summary as chunk_type='summary' (first 200 words)
    # 5. Max 10 chunks per response
```

### Update Ingest Lambda

**File:** `backend/ingest/ingest_pgvector.py`

Accept new fields: `user_id`, `session_id`, `chunk_index`, `query`, `chunk_type`.

---

## Phase G — Trading Floor Context Bridge

**Goal:** Trading debate agents consume Alex AI session intelligence.

### Context Injection into Debate Engine

**File:** `backend/agents/trading/core/context_builder.py` (from Trading Floor 2.0)

```python
def build_trading_context(user_id: str, ticker: str) -> str:
    parts = []
    
    # 1. Portfolio digest (from portfolio research pipeline)
    digest = get_portfolio_digest(user_id, ticker)
    
    # 2. Latest Alex AI research on this ticker (from research_vectors)
    ai_research = rag_engine.search(
        query=f"{ticker} analysis outlook",
        user_id=user_id,
        top_k=3
    )
    
    # 3. Latest trading floor decision
    last_trade = get_latest_simulated_trade(user_id, ticker)
    
    # 4. Session conversation mentioning this ticker
    session_mentions = rag_engine.search_session(
        user_id=user_id,
        ticker=ticker,
        top_k=2
    )
    
    return formatted_context
```

### Performance Attribution

When a trading agent vote is influenced by RAG context, log to `agent_observations`:

```json
{
  "data_used": [
    {"source": "portfolio_digest", "ticker": "NVDA", "relevance": 0.89},
    {"source": "research_vector", "chunk_id": "uuid", "relevance": 0.82},
    {"source": "session_memory", "query": "Will NVDA go up?", "relevance": 0.75},
    {"source": "market_data", "tool": "get_stock_data", "latency_ms": 450}
  ]
}
```

Visible on `/observe` per agent: "Context sources used" breakdown.

### Bidirectional Intelligence Flow

```
Alex AI Chat ──→ research_vectors ──→ Trading Floor agents
     ↑                                        │
     └──── trading results / agent votes ─────┘
```

---

## Phase H — Unified Guardrails

### Current Guardrail Layers

| Layer | Where | Coverage |
|-------|-------|----------|
| Bedrock Guardrail (Terraform) | Researcher output | Fast/deep ECS paths only |
| Smart skip | `should_apply_guardrail()` | May bypass if 3+ financial keywords |
| Trading programmatic | `base_agent.apply_guardrails()` | Confidence caps, action validation |
| None | Reporter/multi-agent, synthesizer | **Gap** |

### Unified Guardrail Architecture

**File:** `backend/shared/guardrails.py` (new — shared by researcher + trading)

```
Layer 1: INPUT GATE (Router)
  - Reject non-financial queries before any agent runs
  - Detect harmful advice patterns ("put life savings", "guaranteed returns")
  - PII detection in user input

Layer 2: AGENT GUARDRAILS (per agent call)
  - Bedrock guardrail on all LLM outputs (research + trading + synthesizer)
  - Trading: confidence 10-95%, valid actions only
  - Research: financial signal check before smart-skip

Layer 3: OUTPUT GATE (Synthesizer)
  - Append "This is research, not financial advice" disclaimer
  - Strip PII from synthesized output
  - Block guaranteed return language
  - Cap response length (prevent runaway generation)

Layer 4: INGEST GATE
  - Don't store responses that failed guardrails
  - Don't store off-topic content in vector store
```

### Financial-Only Conversational Gate

Router `reject` route returns:

```
"I'm Alex, your financial intelligence assistant. I can help with 
stocks, markets, your portfolio, and trading analysis — but I can't 
help with [topic]. Try asking me about a stock or market trend!"
```

### Guardrail Observability

All guardrail events → `agent_observations` + `trading_events` → `/observe` guardrail panel (existing, extend coverage).

---

## Phase I — Conversational UX & Proactive Intelligence

### Single Chat Interface

**Page:** `/research` (redesigned)

| Removed | Added |
|---------|-------|
| Fast/Deep toggle buttons | Router reasoning panel (auto) |
| Manual multi-agent detection | Automatic routing indicator |
| Separate stream endpoints | Unified `/api/alex/chat` SSE stream |
| Local-only message state | Hydrate from `chat_sessions` on load |

### Conversation Features

| Feature | Implementation |
|---------|---------------|
| **Follow-up questions** | Session RAG provides conversation history |
| **"What about ASML?"** after NVDA discussion | Entity tracking in session context |
| **Portfolio awareness** | "You hold 10 shares of ASML at $1,500 avg" |
| **Trading floor awareness** | "Agents voted BUY on NVDA yesterday" |
| **Proactive suggestions** | Existing `get_proactive_suggestions()` — fix bugs, show in chat |
| **Contradiction alerts** | "Note: last week I said HOLD, but new earnings change this" |
| **Performance comparison** | "Simulation +2.3% vs your portfolio +0.8% today" |

### Session Lifecycle

```
1. User opens /research
2. Frontend loads session_id from sessionStorage (or creates new)
3. Hydrate prior messages from chat_sessions API
4. User types question
5. POST /api/alex/chat (streaming)
6. Router → Agent → Synthesizer → Stream tokens
7. Save to chat_sessions + research_sessions + research_vectors
8. Next question uses full RAG context
```

### Suggested Questions (Contextual)

Dashboard/research page shows dynamic suggestions based on:
- Portfolio holdings ("What's the latest on your ASML position?")
- Stale research ("NVDA — last researched 5 days ago")
- Trading floor activity ("Agents debated NVDA today — see results")
- Market events ("Fed meeting tomorrow — how does it affect your holdings?")

---

## Aurora Schema Extensions

```sql
-- research_vectors extensions (see Phase F)

-- Link research_sessions to vectors
ALTER TABLE research_sessions ADD COLUMN IF NOT EXISTS route VARCHAR(20);
ALTER TABLE research_sessions ADD COLUMN IF NOT EXISTS intent VARCHAR(50);
ALTER TABLE research_sessions ADD COLUMN IF NOT EXISTS entities JSONB DEFAULT '[]';

-- Session metadata
CREATE TABLE IF NOT EXISTS session_metadata (
  id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  user_id UUID REFERENCES users(id),
  session_id VARCHAR(36) NOT NULL,
  title VARCHAR(200),
  tickers_discussed JSONB DEFAULT '[]',
  message_count INTEGER DEFAULT 0,
  last_route VARCHAR(20),
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW(),
  UNIQUE(user_id, session_id)
);

-- RAG attribution log
CREATE TABLE IF NOT EXISTS rag_attributions (
  id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  user_id UUID REFERENCES users(id),
  session_id VARCHAR(36),
  query TEXT,
  chunks_used JSONB DEFAULT '[]',
  route VARCHAR(20),
  agent_name VARCHAR(50),
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- chat_sessions: add unique constraint
CREATE UNIQUE INDEX IF NOT EXISTS chat_sessions_user_sid_uidx
  ON chat_sessions (user_id, session_id);
```

---

## API & Frontend Changes

### New / Modified API Routes

| Route | Method | Purpose |
|-------|--------|---------|
| `/api/alex/chat` | POST (SSE) | **Unified** chat endpoint with router |
| `/api/alex/sessions` | GET | List user's chat sessions |
| `/api/alex/sessions/[id]` | GET | Load session messages |
| `/api/alex/suggestions` | GET | Contextual question suggestions |
| `/api/research/*` | — | **Deprecated** — redirect to `/api/alex/chat` |

### Frontend File Changes

| File | Change |
|------|--------|
| `frontend/app/research/page.tsx` | Remove Fast/Deep toggle; unified stream; router reasoning panel |
| `frontend/context/ChatContext.tsx` | Sync with Aurora sessions; hydrate on load |
| `frontend/app/dashboard/page.tsx` | Contextual Alex suggestions card |
| `frontend/components/AlexChat.tsx` (new) | Reusable chat component with markdown + reasoning |

---

## Observability Mapping

Every Alex AI 2.0 action reports to `/observe`:

| Panel | Data | Source |
|-------|------|--------|
| **Query Routing** (new) | Route distribution: fast/deep/multi/reject % | `rag_attributions.route` |
| **RAG Performance** (new) | Chunks retrieved, relevance scores, cache hits | `rag_attributions` |
| **MCP Tool Usage** (new) | Tools called per route, latency, errors | `agent_observations.data_used` |
| **Session Activity** (new) | Active sessions, messages/day, top tickers | `session_metadata` |
| **Synthesis Latency** (new) | Router + agent + synthesizer breakdown | `agent_observations` |
| **Guardrail Coverage** (extend) | All paths including synthesizer + router reject | `agent_observations` |
| **Context Bridge** (new) | Trading agents using AI research context | `agent_observations.data_used` |
| Platform cost (existing) | — | `agent_observations` |
| Per-agent stats (existing) | — | `agent_observations` |

---

## Decision Points

| # | Decision | Options | Recommendation |
|---|----------|---------|----------------|
| 1 | Router model | Nova Lite vs Nova Pro vs rule-based | Nova Lite (fast, cheap, sufficient for classification) |
| 2 | Multi-agent upgrade | ECS per task vs enriched reporter | ECS per task in v2; enriched reporter for MVP |
| 3 | MCP scope (day 1) | Playwright + SEC only vs full suite | Playwright + SEC + News for MVP |
| 4 | Chunk size | 300 vs 500 vs 800 tokens | 500 tokens with markdown-aware splitting |
| 5 | Global vs user vectors | User-only vs user+global hybrid | Hybrid — user-scoped first, global fallback |
| 6 | Session persistence | sessionStorage only vs Aurora primary | Aurora primary, sessionStorage as cache |
| 7 | Trading comparison frequency | Every response vs only when relevant | Only when ticker mentioned + simulation exists |
| 8 | Off-topic handling | Hard reject vs gentle redirect | Gentle redirect with financial suggestions |

---

## Key Files

### Existing (to fix/extend)

```
backend/researcher/context_service.py     # FIX bugs, extend
backend/researcher/server.py              # Wire router + synthesizer
backend/researcher/tools.py               # Ingest with user_id
backend/ingest/ingest_pgvector.py         # User-scoped vectors
frontend/app/research/page.tsx            # Remove toggle, unified chat
frontend/app/api/research/route.ts         # Deprecate → /api/alex/chat
frontend/context/ChatContext.tsx           # Aurora session sync
```

### New (to create)

```
backend/researcher/query_router.py         # Intent classification + routing
backend/researcher/synthesizer.py          # Commentary generation
backend/researcher/rag_engine.py           # Full RAG pipeline
backend/researcher/chunking.py             # Response chunking
backend/researcher/mcp/sec_edgar_mcp.py    # SEC MCP server
backend/researcher/mcp/financial_news_mcp.py
backend/researcher/mcp/market_data_mcp.py
backend/researcher/mcp/earnings_mcp.py
backend/researcher/mcp/mcp_gateway.py      # MCP lifecycle manager
backend/shared/guardrails.py               # Unified guardrail layer
frontend/app/api/alex/chat/route.ts        # Unified chat API
frontend/app/api/alex/sessions/route.ts    # Session management
frontend/components/AlexChat.tsx           # Reusable chat component
```

---

*This document is the single source of truth for Alex AI 2.0. See `Alex_Master_Implementation_Plan.md` for unified implementation order alongside Trading Floor 2.0.*
