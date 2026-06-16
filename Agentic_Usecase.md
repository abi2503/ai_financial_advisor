# Agentic Use Cases — Alex Current Setup

> **Status:** Strategic reference — grounded in **live** Alex stack (June 2026)  
> **Created:** June 14, 2026  
> **Purpose:** Concrete agentic workflows you can run, demo, or productize **today** on Alex — plus minimal extensions  
> **Sources:** `Alex_report.md`, `query_router.py`, `Alex_chat_intelligence.md`, `Alex_Trading_Floor_2.0.md`, `usecases.md`  
> **Distinction from `usecases.md`:** That file maps Alex **beyond finance** (startups, cross-industry). **This file** is what Alex is agentic **for in finance** with your deployed architecture.

---

## Table of Contents

1. [What Makes These "Agentic" on Alex](#1-what-makes-these-agentic-on-alex)
2. [Infrastructure You Already Have](#2-infrastructure-you-already-have)
3. [Tier A — Use Today (No New Code)](#3-tier-a--use-today-no-new-code)
4. [Tier B — 1–3 Day Extensions](#4-tier-b--13-day-extensions)
5. [Tier C — Composed Workflows (Stack Existing Agents)](#5-tier-c--composed-workflows-stack-existing-agents)
6. [Tier D — Interview & Demo Packs](#6-tier-d--interview--demo-packs)
7. [Tier E — B2B / White-Label Angles](#7-tier-e--b2b--white-label-angles)
8. [Use Case Matrix](#8-use-case-matrix)
9. [What Is NOT Agentic Yet (Honest Gaps)](#9-what-is-not-agentic-yet-honest-gaps)
10. [Recommended Build Order](#10-recommended-build-order)
11. [Document Index](#11-document-index)

---

## 1. What Makes These "Agentic" on Alex

A use case belongs here only if it uses **two or more** of:

| Agentic property | Alex implementation |
|------------------|---------------------|
| **Routing** | `query_router.py` → fast / deep / chat / debater / parallel |
| **Specialists** | 5 debater personas + 6 trading-floor agents + planner/reporter |
| **Tools / MCP** | yfinance, SEC EDGAR, Playwright MCP, ingest |
| **Memory** | `research_vectors`, `chat_sessions`, `portfolio_digests` |
| **Autonomy** | EventBridge 2h portfolio research, trading orchestrator |
| **Observability** | `/observe`, `query_latency_metrics`, `agent_observations` |
| **Guardrails** | Policy flags, off-topic block, Bedrock guardrail |

**Not listed:** Single-prompt ChatGPT-style Q&A with no tools, memory, or scheduling.

---

## 2. Infrastructure You Already Have

```
┌─────────────────────────────────────────────────────────────────────────┐
│  SYNC (user-triggered)                                                   │
│  AlexChat → /api/alex/chat → ECS query_router                           │
│    ├─ fast      → yfinance + news (~60s)                                │
│    ├─ deep+mcp  → SEC + Playwright MCP (3–5 min)                        │
│    ├─ deep+parallel → planner → SQS → reporter                          │
│    ├─ debater   → Marcus / Victoria / Zara / Reid / Elena               │
│    └─ chat      → Nova Lite conversation + guardrails                   │
└─────────────────────────────────────────────────────────────────────────┘
┌─────────────────────────────────────────────────────────────────────────┐
│  ASYNC (scheduled)                                                       │
│  EventBridge 2h → scheduler → planner → tagger → reporter             │
│    → portfolio_digests → dashboard cards                                  │
│  Manual: Trading UI → orchestrator → 6-agent debate → simulated_trades    │
└─────────────────────────────────────────────────────────────────────────┘
┌─────────────────────────────────────────────────────────────────────────┐
│  DATA + OPS                                                              │
│  Aurora pgvector · SQS · Lambda · ECS · SageMaker embeddings            │
│  /observe · ops_agent · Terraform (12 AWS services)                     │
└─────────────────────────────────────────────────────────────────────────┘
```

| Component | Status | Key files / tables |
|-----------|--------|-------------------|
| Unified chat + router | ✅ Live | `AlexChat.tsx`, `query_router.py`, `/api/alex/chat` |
| Fast research | ✅ Live | `server.py` → `run_data_agent` |
| Deep SEC + MCP | ✅ Live | `mcp_servers.py`, `/research/deep/stream` |
| Multi-ticker compare | ✅ Live | `planner.py`, `deepResearch.ts` |
| Debater handoffs | ✅ Live | `debater_registry.py`, `debater_handoff.py` |
| Portfolio digests (2h) | ✅ Live | `scheduler.py`, `portfolio_digests` |
| Trading floor debate | ✅ Live (advisory) | `debate_engine.py`, `simulated_trades` |
| Vector RAG + ingest | ✅ Live | `ingest_pgvector.py`, `research_vectors` |
| Observability | ✅ Live | `/observe`, `latency_tracker.py` |
| Paper positions update | 🔲 Gap | Trades log only — P1 Trading Floor |
| Edu fast search + PDF | 📝 Spec | `Alex_chat_intelligence.md` |

---

## 3. Tier A — Use Today (No New Code)

These work **now** — add portfolio tickers, enable scheduler, ask in chat or open `/trading`.

---

### A1 — Autonomous Portfolio Research Desk

**User story:** *"I hold NVDA, ASML, AAPL — I want fresh research without asking every morning."*

| Dimension | Detail |
|-----------|--------|
| **Agents** | Scheduler → Planner (dimension rotation) → Tagger → Reporter |
| **Autonomy** | EventBridge every **2 hours** |
| **Output** | `portfolio_digests` cards on `/dashboard` |
| **Why agentic** | User doesn't trigger; system watches holdings and produces **confirmed** structured digests |
| **Try it** | Add holdings → wait for scheduler → check dashboard digest cards |
| **Alex reuse** | **100%** |

---

### A2 — Live Ticker Pulse (Fast Research)

**User story:** *"What's NVDA trading at and what's the news?"*

| Dimension | Detail |
|-----------|--------|
| **Route** | `fast` |
| **Agents** | ECS data agent + yfinance + Yahoo RSS |
| **Latency** | ~30–60s |
| **Memory** | Optional ingest to `research_vectors` |
| **Why agentic** | Tool calls with live data — not LLM recall |
| **Example queries** | "NVDA price today", "Latest news on TSLA", "How is ASML doing?" |
| **Alex reuse** | **100%** |

---

### A3 — SEC Filing Deep Dive

**User story:** *"Show me NVDA's 10-K risk factors and recent 8-K events."*

| Dimension | Detail |
|-----------|--------|
| **Route** | `deep` + `mcp` |
| **Agents** | Deep researcher + Playwright MCP + `get_sec_filings` |
| **Tools** | EDGAR, browser automation |
| **Why agentic** | Multi-turn tool use across fragmented SEC + web surfaces |
| **Example queries** | "NVDA 10-K risks", "AAPL latest 8-K", "MSFT proxy statement executive comp" |
| **Alex reuse** | **100%** |

---

### A4 — Multi-Ticker Investment Committee (Parallel Deep)

**User story:** *"Compare NVDA vs AMD for next quarter — full breakdown."*

| Dimension | Detail |
|-----------|--------|
| **Route** | `deep` + `parallel` |
| **Agents** | Planner decomposes → parallel SQS tasks → Reporter → synthesis |
| **Why agentic** | Map-reduce over specialists — one chat question, many sub-research jobs |
| **Example queries** | "NVDA vs AMD", "Which is better ASML or AMAT?", "Compare META vs GOOG ad revenue outlook" |
| **Alex reuse** | **100%** |

---

### A5 — Specialist Chat Handoff (Debater Agents)

**User story:** *"I want a quant view on AAPL technicals, not a generic answer."*

| Dimension | Detail |
|-----------|--------|
| **Route** | `debater` |
| **Agents** | Marcus (growth), Victoria (bear), Zara (quant), Reid (macro), Elena (risk) |
| **UX** | Handoff banner in `AlexChat` — named specialist streams answer |
| **Why agentic** | Router delegates to **role-bound** agent with domain prompt + market context |
| **Example queries** | "Bear case on TSLA", "RSI on NVDA", "Fed impact on tech", "Position size for ASML" |
| **Alex reuse** | **100%** |

---

### A6 — Trading Floor War Room (Manual Debate)

**User story:** *"Run a full 6-agent committee on my largest holding."*

| Dimension | Detail |
|-----------|--------|
| **Trigger** | `/trading` → Run Analysis |
| **Agents** | Marcus, Victoria, Zara, Reid, Elena → Executor (Alex PM) |
| **Output** | `simulated_trades` + full vote transparency |
| **Why agentic** | Parallel multi-perspective debate → structured decision artifact |
| **Caveat** | Advisory only until P1 paper executor — positions don't move yet |
| **Alex reuse** | **95%** |

---

### A7 — Financial Education + Guardrailed Advice

**User story:** *"What is short selling?" (education) vs "Help me short TSLA aggressively" (blocked).*

| Dimension | Detail |
|-----------|--------|
| **Route** | `chat` — `education` or `policy_flag` |
| **Agents** | Nova Lite conversation + policy patterns |
| **Why agentic** | Intent classification + safety layer — not one blunt prompt |
| **Example queries** | "What is a bond?", "Explain put options", "What is stop loss?" |
| **Gap** | No vector cache yet — see `Alex_chat_intelligence.md` C1 |
| **Alex reuse** | **85%** |

---

### A8 — Session Memory Research

**User story:** *"Last week I researched ASML — continue where we left off."*

| Dimension | Detail |
|-----------|--------|
| **Route** | Any research route + `session_id` |
| **Memory** | `chat_sessions`, `research_vectors` (user-scoped), `context_service` |
| **Why agentic** | Retrieval-augmented follow-ups across sessions |
| **Example** | "What about their EUV exposure?" after prior ASML deep dive |
| **Alex reuse** | **90%** |

---

### A9 — Ops & Cost Observability Agent

**User story:** *"Is Alex healthy and what did it cost this month?"*

| Dimension | Detail |
|-----------|--------|
| **Agents** | `ops_agent` (scheduled), Cost Explorer integration |
| **Surface** | `/observe` — latency, MCP pass/fail, guardrails, cost widget |
| **Why agentic** | Autonomous health + cost monitoring — ops as a product |
| **Alex reuse** | **100%** |

---

### A10 — Off-Topic & Compliance Boundary

**User story:** *"User asks about recipes or illegal trades — Alex stays in lane."*

| Dimension | Detail |
|-----------|--------|
| **Route** | `chat` + `off_topic` or `policy_flag` |
| **Why agentic** | Router + canned guardrail responses — auditable decline |
| **Demo value** | Shows production safety for RIA/fintech interviews |
| **Alex reuse** | **100%** |

---

## 4. Tier B — 1–3 Day Extensions

Minimal code on current stack — highest ROI agentic upgrades.

---

### B1 — Education Fast Search + Vector Memory

**Spec:** `Alex_chat_intelligence.md` Phase C1

| Field | Detail |
|-------|--------|
| **Problem** | "What is a bond?" re-generates every time |
| **Fix** | Vector lookup → glossary → answer → ingest `chunk_type=education` |
| **Effort** | 3–4 days |
| **Unlocks** | Sub-second repeat education; RAG warms up on concepts |
| **Alex reuse** | **92%** |

---

### B2 — Chat → Trading Context Bridge

**Spec:** `Alex_Master_Implementation_Plan.md` P6

| Field | Detail |
|-------|--------|
| **User story** | Chat answer references latest trading floor vote on same ticker |
| **Fix** | Inject `simulated_trades` + `portfolio_digests` into debater/fast prompts |
| **Effort** | 2–3 days |
| **Why agentic** | Brain (chat) and Hands (trading) share intelligence |
| **Alex reuse** | **88%** |

---

### B3 — Earnings Week Proactive Agent

**Spec:** `Alex_chat_intelligence.md` Phase C5

| Field | Detail |
|-------|--------|
| **User story** | "Tell me before my holdings report earnings" |
| **Fix** | Daily EventBridge scan → `earnings_calendar_events` → dashboard card |
| **Effort** | 3–4 days |
| **Why agentic** | Autonomous calendar + trend detection — user doesn't ask |
| **Alex reuse** | **85%** |

---

### B4 — Deep Research PDF Export

**Spec:** `Alex_chat_intelligence.md` Phase C3

| Field | Detail |
|-------|--------|
| **User story** | "Send me the NVDA memo as a PDF" |
| **Fix** | Report agent + Playwright `page.pdf()` + S3 presigned URL |
| **Effort** | 3–4 days |
| **Why agentic** | Deliverable artifact, not chat-only |
| **Alex reuse** | **80%** |

---

### B5 — Committee Mini-Debate in Chat

**Spec:** `Alex_chat_intelligence.md` C6.2

| Field | Detail |
|-------|--------|
| **User story** | "Is NVDA overvalued?" → Marcus bull + Victoria bear + Executor verdict |
| **Fix** | Router detects contested query → 2 debaters + synthesis in chat |
| **Effort** | 2–3 days |
| **Why agentic** | Multi-agent disagreement visible to user |
| **Alex reuse** | **90%** |

---

### B6 — Post-Response Ingest on All Routes

| Field | Detail |
|-------|--------|
| **User story** | Every answer becomes retrievable later |
| **Fix** | `post_response_ingest.py` hook after fast/deep/debater streams |
| **Effort** | 1 day |
| **Why agentic** | Compounding memory — platform learns per user |
| **Alex reuse** | **95%** |

---

### B7 — Suggestion Chips (Follow-Up Agent)

| Field | Detail |
|-------|--------|
| **User story** | After "what is a bond?", Alex suggests "steps to buy treasuries" |
| **Fix** | Nova Lite generates 2–3 chips from route metadata |
| **Effort** | 1–2 days |
| **Why agentic** | Proactive next-step agent — feels like a team |
| **Alex reuse** | **90%** |

---

### B8 — Paper Trade Executor (Closed Loop)

**Spec:** `Alex_Trading_Floor_2.0.md` Phase 1

| Field | Detail |
|-------|--------|
| **User story** | Debate BUY actually updates `agent_positions` |
| **Fix** | `trade_executor.py` after debate consensus |
| **Effort** | 3–5 days |
| **Why agentic** | Simulation **executes** — not just advises |
| **Alex reuse** | **85%** |

---

## 5. Tier C — Composed Workflows (Stack Existing Agents)

Multi-step journeys using **only live** or **Tier B** capabilities.

---

### C1 — Morning Investor Briefing

```
6 AM  (B3) Earnings agent → "3 reports this week"
8 AM  (A1) portfolio_digests already refreshed overnight (2h cycle)
8:05  User opens dashboard → digest cards + earnings card
8:10  User asks in chat: "Summarize my week" → fast + RAG over digests (A8)
```

**Agentic proof:** Three autonomous sources → one user moment.

---

### C2 — Pre-Earnings Deep Dive Pack

```
(T-2 days) Earnings agent alerts NVDA report
User: "Full NVDA earnings prep" 
  → A3 deep SEC (10-Q / 8-K)
  → A5 Zara (technicals / IV)
  → A5 Marcus (growth narrative)
  → A4 optional: NVDA vs AMD parallel
User: (B4) Export PDF memo
```

**Agentic proof:** Router orchestrates specialist sequence from one intent.

---

### C3 — New Position Due Diligence

```
User adds TSLA to portfolio
2h later: A1 digest card auto-generated
User: "Bear case" → A5 Victoria
User: "Risk size for 5% allocation" → A5 Elena
User: A6 full trading floor debate
User: (B2) Chat cites debate votes in follow-up questions
```

**Agentic proof:** Async research + sync specialists + committee decision.

---

### C4 — Macro Shock Response

```
News: Fed surprise rate cut
User: "How does this affect my portfolio?" → A5 Reid (macro)
Per holding: fast research on each ticker (A2) — parallel user questions
A6 trading floor runs on largest holding
/observe: spike in fast route latency + MCP calls
```

**Agentic proof:** Event-driven multi-route response with observability.

---

### C5 — Learning Loop for Beginners

```
User: A7 "What is a bond?"
User: A7 "Steps to invest in treasuries?"
(B1) Both ingested to education vectors
Next session: A8 "Remind me about bonds" → vector hit < 1.5s
(B7) Chips suggest "bond vs CD", "yield curve"
```

**Agentic proof:** Memory compounds; platform teaches over time.

---

### C6 — RIA Client Research Trail (White-Label Ready)

```
Advisor researches CRM for client meeting
A3 deep SEC + A4 compare → ingested with user_id
(B4) PDF report to client folder
/observe: audit trail of tools used
Guardrails: no personalized buy/sell (A10)
```

**Spec depth:** `RIA.md`

---

## 6. Tier D — Interview & Demo Packs

5-minute demos that show **agentic** vs chatbot.

| Demo | Script | Routes used | Wow moment |
|------|--------|-------------|------------|
| **D1 — Router transparency** | Ask education → fast → deep → debater in sequence | chat, fast, deep, debater | User sees routing steps in SSE |
| **D2 — SEC live** | "NVDA 10-K risk factors" | deep+mcp | Playwright browses real EDGAR |
| **D3 — Committee** | Run trading floor on NVDA | orchestrator + debate | 6 votes + transparency |
| **D4 — Autonomous** | Show dashboard digests without user ask | scheduler pipeline | "Alex watched while you slept" |
| **D5 — Guardrail** | "Help me YOLO short everything" | policy_flag | Safe decline + redirect |
| **D6 — Observe** | Run query → open `/observe` | all | Cost, latency, MCP pass/fail |
| **D7 — Handoff** | "RSI on AAPL" | debater → Zara | Named specialist banner |

**One-liner for interviews:**

> *"ChatGPT answers from memory. Alex routes to specialists, calls live tools, schedules research on your portfolio, debates decisions with six agents, and logs every step on `/observe`."*

---

## 7. Tier E — B2B / White-Label Angles

Agentic use cases sellable on **current** infra with prompt/schema swaps.

| Product | Agentic core | Alex components | Effort to white-label |
|---------|--------------|-----------------|----------------------|
| **RIA Copilot** | Research + compliance guardrails + PDF | Chat, deep, debater, observe | 6–8 wk — `RIA.md` |
| **Family Office Digest** | 2h autonomous multi-asset brief | Scheduler, digests, dashboard | 2–3 wk — swap prompts |
| **BriefingAI** | Topic watchlist → daily email brief | Scheduler, reporter, SES | 1 wk — `usecases.md` |
| **Paper Trading Simulator** | 6-agent debate + sim positions | Trading floor, debate engine | 3 wk — P1 executor |
| **Agentic Research API** | Router + MCP as a service | ECS researcher, query_router | 4 wk — API keys + tenant |
| **FinOps Cost Agent** | Daily AWS cost synthesis email | ops_agent, P21 spec | 3–4 wk — `Alex_Master_Implementation_Plan.md` P21 |

---

## 8. Use Case Matrix

| ID | Use case | Tier | Routes / agents | Autonomous? | Alex reuse |
|----|----------|------|-----------------|-------------|------------|
| A1 | Portfolio research desk | A | scheduler pipeline | ✅ 2h | 100% |
| A2 | Live ticker pulse | A | fast | ❌ | 100% |
| A3 | SEC filing dive | A | deep+mcp | ❌ | 100% |
| A4 | Multi-ticker compare | A | deep+parallel | ❌ | 100% |
| A5 | Debater handoff | A | debater ×5 | ❌ | 100% |
| A6 | Trading floor debate | A | 6-agent debate | Manual | 95% |
| A7 | Education + guardrails | A | chat | ❌ | 85% |
| A8 | Session memory | A | all + RAG | ❌ | 90% |
| A9 | Ops / cost observe | A | ops_agent | ✅ scheduled | 100% |
| A10 | Compliance boundary | A | guardrails | ❌ | 100% |
| B1 | Edu fast search | B | edu_fast | ❌ | 92% |
| B2 | Chat ↔ trading bridge | B | P6 context | ❌ | 88% |
| B3 | Earnings calendar | B | calendar agent | ✅ daily | 85% |
| B4 | PDF research export | B | report agent | ❌ | 80% |
| B5 | Committee mini-debate | B | 2 debaters + executor | ❌ | 90% |
| B6 | Ingest all routes | B | post-hook | ❌ | 95% |
| B7 | Suggestion chips | B | follow-up agent | ❌ | 90% |
| B8 | Paper trade executor | B | trade_executor | Manual→auto | 85% |
| C1 | Morning briefing | C | A1+A3+B3 | ✅ | 95% |
| C2 | Pre-earnings pack | C | A3+A5+A4 | Partial | 90% |
| C3 | New position DD | C | A1+A5+A6 | Partial | 92% |
| C4 | Macro shock | C | A5+A2+A6 | ❌ | 88% |
| C5 | Learning loop | C | A7+B1 | ❌ | 90% |
| C6 | RIA client trail | C | A3+A4+B4 | ❌ | 85% |

---

## 9. What Is NOT Agentic Yet (Honest Gaps)

| Gap | What users might expect | Plan reference |
|-----|-------------------------|----------------|
| Trades don't move positions | Paper sim feels advisory | `Alex_Trading_Floor_2.0.md` P1 |
| Chat ignores trading votes | "What did the floor decide?" needs manual `/trading` | P6 context bridge |
| Education not cached | Repeat "what is a bond?" hits LLM | `Alex_chat_intelligence.md` C1 |
| No PDF delivery | Can't email client a memo | C3 |
| No earnings proactive alerts | User must ask dates | C5 |
| No autonomous trading schedule | Must click Run Analysis | P5 EventBridge |
| No RL agent learning | Weights static | Trading Floor P5 |
| Synthesizer not shipped | Raw agent output voice | `Alex_AI_2.0.md` P3 |

---

## 10. Recommended Build Order

If goal is **maximum agentic feel** with least effort:

```
Week 1 (feel agentic fast)
  B6 ingest all routes
  B7 suggestion chips
  B1 edu fast search (or glossary seed only — 0.5 day)

Week 2 (connect the brain)
  B2 chat ↔ trading bridge
  B5 committee mini-debate

Week 3 (autonomous proactive)
  B3 earnings calendar agent
  OR B8 paper trade executor (if trading narrative priority)

Week 4 (deliverables)
  B4 PDF export
  C1 morning briefing composed workflow in dashboard
```

**If demoing in 48 hours:** Run **D1–D7** from Tier D — all live today.

**If shipping a product:** **A1 + A5 + B2 + B3 + RIA guardrails** = credible investor/RIA copilot.

---

## 11. Document Index

| Document | Use |
|----------|-----|
| `Agentic_Usecase.md` | **This file** — agentic use cases on current Alex setup |
| `usecases.md` | Cross-industry patterns, startups, Ophelia projects |
| `Alex_report.md` | Live status, APIs, schema, metrics |
| `Alex_chat_intelligence.md` | Chat routing upgrades (edu, PDF, earnings) |
| `Alex_Trading_Floor_2.0.md` | Trading simulation, RL, autonomy |
| `Alex_AI_2.0.md` | Conversational AI vision, RAG, synthesizer |
| `Alex_Master_Implementation_Plan.md` | Unified phase order P0–P21 |
| `RIA.md` | White-label advisor product |
| `DM_apply.md` | Demo talking points for outreach |
| `Ophelia.md` | Execution-layer interview framing |

---

## Changelog

| Date | Change |
|------|--------|
| 2026-06-14 | Initial `Agentic_Usecase.md` — Tier A–E use cases mapped to live Alex stack |
