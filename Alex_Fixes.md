# Alex Fixes — Chat Intelligence Audit Log

**Document:** `Alex_Fixes.md`  
**Purpose:** Audit trail of platform fixes (chat routing, RAG, ops, observability) — problem → fix → files → verification.  
**Companion:** `Alex_report.md` §33 (CL entries), `Alex_chat_intelligence.md` (spec)

### Standing policy (user-mandated, June 15 2026)

**Agents MUST update this file automatically** whenever chat routing, agent behavior, conversation-path, **RAG/vector**, **ops/dashboard**, or **observability** bugs are fixed — **without waiting for the user to ask**. Each fix gets:

1. Sequential **FIX-NNN** ID in the index
2. Full entry: problem → root cause → fix → files → test queries → deploy status
3. Matching **CL-NNN** entry in `Alex_report.md` §33 (one CL can cover a batch of related FIXes)
4. CI test additions in `scripts/tests/test_p1_router.py` when routing logic changes

**Do not** commit secrets. **Do** note ECS redeploy when production is affected.

---

## Fix Index

| ID | Date | Title | Status |
|----|------|-------|--------|
| FIX-001 | 2026-06-15 | Deep SEC stub response (Micron) | ✅ Fixed |
| FIX-002 | 2026-06-15 | Follow-up context lost (NVDA → ASML) | ✅ Fixed |
| FIX-003 | 2026-06-15 | Scoped deep research (10-K / 8-K / full SEC) | ✅ Fixed |
| FIX-004 | 2026-06-15 | Conceptual SEC questions misrouted to deep | ✅ Fixed |
| FIX-005 | 2026-06-15 | SEC education canned as off-scope + ALEX ticker hallucination | ✅ Fixed + deployed |
| FIX-006 | 2026-06-15 | Follow-up sentiment loses Micron context | ✅ Fixed + deployed |
| FIX-007 | 2026-06-15 | Observe page LLM tokens + AWS cost per query | ✅ Fixed + deployed |
| FIX-008 | 2026-06-15 | Dashboard ops “Refresh now” does not run ops agent | ✅ Fixed + deployed |
| FIX-009 | 2026-06-15 | pgvector semantic search 502 / 0 results / Micron RAG | ✅ Fixed + deployed |
| FIX-010 | 2026-06-15 | "explain stop loss?" canned as off-topic | ✅ Fixed + deployed |
| FIX-011 | 2026-06-16 | LLM finance gate for ambiguous education (no regex sprawl) | ✅ Fixed + deployed |
| FIX-012 | 2026-06-16 | Vague follow-up after insider/SEC research → deep not chat | ✅ Fixed + deployed |
| FIX-013 | 2026-06-16 | CEO/leadership queries return officers, not market snapshot | ✅ Fixed (pending ECS deploy) |

### Report cross-reference

| Fix IDs | Change log | Deploy |
|---------|------------|--------|
| FIX-001 – FIX-005 | **CL-019** in `Alex_report.md` §33 | ECS — 2026-06-15 (2 deploys) |
| FIX-006 | **CL-020** in `Alex_report.md` §33 | ECS — 2026-06-15 23:04 UTC |
| FIX-007 | **CL-021** in `Alex_report.md` §33 | ECS — 2026-06-15 23:13 UTC |
| FIX-008 | **CL-022** in `Alex_report.md` §33 | Frontend only |
| FIX-009 | **CL-023** in `Alex_report.md` §33 | Lambda ingest + ECS — 2026-06-15 23:46 UTC |
| FIX-010 | **CL-024** in `Alex_report.md` §33 | ECS — 2026-06-16 00:00 UTC (approx) |
| FIX-011 | **CL-025** in `Alex_report.md` §33 | ECS — 2026-06-16 |
| FIX-012 | **CL-026** in `Alex_report.md` §33 | ECS — 2026-06-16 00:14 UTC |
| FIX-013 | **CL-028** in `Alex_report.md` §33 | ECS — pending |

---

## FIX-001 — Deep SEC returns storage stub, not filing content

### Problem
Query: *"SEC filing details about micron"*  
Router correctly chose Deep Research (`sec_research`), but the agent returned a short confirmation (*"research completed and stored, BUY recommendation"*) instead of actual 10-K / SEC content.

### Root cause
- Agent called `ingest_financial_document` last and surfaced the ingest success message as `final_output`
- Prior RAG context could shortcut the agent away from fresh `get_sec_filings` calls

### Fix
- Stub detection + SEC fallback via direct `get_sec_filings` call
- Stronger deep prompts: return full analysis, not storage confirmation
- `ingest_financial_document` return message instructs agent to reply with full analysis
- Company alias map (`micron` → `MU`)

### Files edited
| File | Change |
|------|--------|
| `backend/researcher/server.py` | `_is_stub_response`, `_recover_deep_sec_response`, `_prepare_deep_research` |
| `backend/researcher/prompts.py` | Deep critical rules, ingest guidance |
| `backend/researcher/tools.py` | Ingest return message |
| `backend/researcher/query_router.py` | `COMPANY_ALIASES`, entity resolution |

### Test queries
| Query | Expected |
|-------|----------|
| `SEC filing details about micron` | Deep → real SEC content (not stub) |
| `Analyze NVDA SEC 10-K filing risks` | Deep → 10-K sections with quotes |

---

## FIX-002 — Follow-up pronoun loses session ticker

### Problem
After NVDA analysis, user asked *"give its PE ratio"* → Fast Research returned **ASML** data instead of NVDA.

### Root cause
1. `"PE"` in `"PE ratio"` extracted as false ticker
2. `"its"` not recognized as follow-up pronoun → session context not passed
3. Fast agent defaulted to portfolio holding (ASML) over conversation history

### Fix
- `PE`, `EPS`, etc. added to `NON_TICKER_WORDS`
- Follow-up detection: `its`, `it`, `the stock`, `give me`, …
- `extract_tickers_from_context()` reads last ALEX message `(NVDA)`
- `ACTIVE TICKER` directive injected into fast/deep agent instructions

### Files edited
| File | Change |
|------|--------|
| `backend/researcher/query_router.py` | `resolve_entities`, `_looks_like_followup`, `NON_TICKER_WORDS` |
| `backend/researcher/context_service.py` | Conversation history pronoun guidance |
| `backend/researcher/server.py` | `_active_ticker_directive` |

### Test queries
| Query | Context | Expected |
|-------|---------|----------|
| `give its PE ratio` | Prior ALEX message about NVDA | Fast → NVDA |
| `give its PE ratio` | No context | Chat (not false `PE` ticker) |

---

## FIX-003 — Deep research over-fetches (10-K question gets full pipeline)

### Problem
Query: *"tell me about 10k filings for NVDA"* returned Insider Trading, Analyst Ratings, and Options Flow — user only asked for 10-K.

### Root cause
Deep prompt mandated a fixed 4-source pipeline (10-K + Form 4 + analyst + options) for every SEC query.

### Fix
- `infer_research_scope()` — detects scope from query
- `build_deep_scope_directive()` — tells agent exactly which tools and sections to use
- Dynamic reasoning steps in deep stream (no analyst step for 10-K-only)

### Scope matrix
| User asks | Scope | Tools |
|-----------|-------|-------|
| `10-K` / `10k filing` | `filing_10k` | `get_sec_filings(10-K)` only |
| `8-K` | `filing_8k` | `get_sec_filings(8-K)` only |
| `Form 4` / insider | `filing_form4` | `get_sec_filings(4)` only |
| Broad `SEC filings` / `EDGAR` | `sec_full` | 10-K + Form 4 + analyst + options |
| `analyst ratings` only | `analyst_only` | MarketBeat browser |
| Ambiguous | `inferred` | Minimum tools from keywords |

### Files edited
| File | Change |
|------|--------|
| `backend/researcher/query_router.py` | `ResearchScope`, `infer_research_scope`, `deep_reasoning_steps` |
| `backend/researcher/prompts.py` | Scoped directives, per-form output formats |
| `backend/researcher/server.py` | `_prepare_deep_research`, scoped stream steps |
| `scripts/tests/test_p1_router.py` | `test_research_scope` |

### Test queries
| Query | Expected route | Expected scope |
|-------|----------------|----------------|
| `tell me about 10k filings for NVDA` | deep | `filing_10k` |
| `show me the 8-K for TSLA` | deep | `filing_8k` |
| `SEC filing details about micron` | deep | `sec_full` |
| `NVDA analyst ratings from MarketBeat` | deep | `analyst_only` |

---

## FIX-004 — Conceptual SEC questions misrouted to deep research

### Problem
Query: *"diffirence b/w 10k, 8k and 4k filing of a stock?"*  
Routed to **Deep Research** (`sec_research`) — fetched EDGAR, 10-K, analyst ratings (~31s) for a **definitions / comparison** question with no ticker.

Answer content was acceptable (LLM explained filing types), but routing was wrong: wasted latency and irrelevant tools.

### Root cause
- Any mention of `10-k`, `8-k`, `filing` matched `MCP_SIGNALS` → forced deep route
- `_is_educational_finance()` explicitly returned `False` when MCP signals present
- No distinction between *"what is a 10-K?"* (education) vs *"NVDA's 10-K"* (live data)

### Fix
- New `_is_sec_conceptual_education()` — detects comparative/conceptual SEC questions **without ticker**
- Routes to `chat` / `sec_education` before MCP deep override
- `_is_off_topic()` updated — SEC/filing education no longer misclassified as off-topic
- Conversation prompt adds SEC-education instructions (no fake EDGAR fetch claims)
- Typo tolerance: `diffirence`, `b/w`, `4k filing` (Form 4 alias)

### Routing rule (added)
```
"what is / difference between / explain" + filing types + NO ticker  →  chat (sec_education)
"[TICKER]'s 10-K" / "SEC filings for [company]"                    →  deep (scoped)
```

### Files edited
| File | Change |
|------|--------|
| `backend/researcher/query_router.py` | `SEC_FILING_PATTERN`, `SEC_COMPARE_FRAME`, `_is_sec_conceptual_education`, `classify_query` early override, `routing_steps` |
| `backend/researcher/server.py` | `_build_conversation_prompt` — `sec_education` intent |
| `scripts/tests/test_p1_router.py` | `test_sec_conceptual_education` |
| `Alex_Fixes.md` | This document |

### Test queries (manual + CI)

**Should route → `chat` / `sec_education` (no deep, no EDGAR):**
```
diffirence b/w 10k, 8k and 4k filing of a stock?
what is the difference between 10-K and 8-K?
explain Form 4 insider filings
what is a 10-K filing?
compare 10-Q vs 10-K
when do companies file an 8-K?
purpose of SEC Form 4
```

**Should still route → `deep` (live SEC / scoped):**
```
SEC filing details about micron
tell me about 10k filings for NVDA
show NVDA 8-K from EDGAR
Analyze AAPL SEC 10-K filing risks
```

### Run CI tests
```bash
python3 scripts/tests/test_p1_router.py
```

---

## FIX-005 — SEC education blocked by canned reply + ALEX ticker hallucination

### Problem (post-deploy screenshots, 2026-06-15 evening)

1. **`purpose of SEC Form 4`**, **`explain Form 4`**, **`what is a 10-K?`**, **`compare 10-Q vs 10-K`**  
   Routed correctly to `chat` / `sec_education` but conversation handler returned instant canned:  
   *"That question is outside my scope"* (0.1s, no LLM).

2. **`when do companies file an 8-K?`**  
   Routed to **deep** / `filing_8k` instead of education. Agent then searched ticker **ALEX** (from chat role prefix `ALEX:` in session history) and failed.

### Root cause
1. `_conversation_canned_reply()` did not exempt `sec_education` intent — educational-frame + no finance-topic pattern triggered off-scope block.
2. `_is_sec_conceptual_education()` missed timing/rule questions (`when do companies file…`) when only one filing type mentioned.
3. `extract_tickers_from_context()` parsed **`ALEX`** from the `ALEX:` role label in conversation lines.
4. `_active_ticker_directive()` fell back to context ticker extraction even without follow-up pronouns.

### Fix
- Simplified SEC education detection: any SEC/filing mention **without** live-data signals (ticker, company name, "details about", "analyze", etc.) → `sec_education`
- `_conversation_canned_reply`: skip canned block for `sec_education` and `_is_sec_conceptual_education()`
- `ALEX`, `USER` added to `NON_TICKER_WORDS`; context parser strips role prefix before ticker scan
- `_active_ticker_directive`: only use tickers from query or explicit follow-up resolution — never blind context scan

### Files edited
| File | Change |
|------|--------|
| `backend/researcher/query_router.py` | `LIVE_SEC_REQUEST`, `_is_live_sec_data_request`, simplified `_is_sec_conceptual_education`, context parser fix |
| `backend/researcher/server.py` | `_conversation_canned_reply`, `_active_ticker_directive` |
| `scripts/tests/test_p1_router.py` | Added `when do…` and `purpose of…` cases |
| `Alex_Fixes.md` | FIX-005 entry |

| `Alex_Fixes.md` | FIX-005 entry |

### Deploy
- **ECS:** `backend/researcher/deploy.sh` — 2026-06-15 22:51 UTC
- **ALB:** `http://alex-alb-1816782403.us-east-1.elb.amazonaws.com`
- **Verification:** Live `/research/route` → `chat sec_education` for `when do companies file an 8-K?`, `purpose of SEC Form 4`

---

## FIX-006 — Follow-up sentiment loses Micron context

### Problem
After *"SEC filing details about micron"* (deep research on MU), user asked *"what is its market sentiment?"* → instant canned *"outside my scope"* instead of MU sentiment data.

### Root cause
1. Follow-up fast route required `METRIC_SIGNALS` match — `sentiment` was not included; pronoun follow-ups without metric keywords fell through to `chat`/`conversation` with **empty entities**.
2. `_conversation_canned_reply()` blocked the query: `what is` (educational frame) + no finance-topic pattern → off-scope canned reply.

### Fix
- Any pronoun/follow-up query with resolved session ticker → **fast** / `follow_up` (not only metric keywords).
- Expanded `METRIC_SIGNALS` with sentiment, news, catalyst, momentum, etc.
- `_conversation_canned_reply`: skip canned block for pronoun/follow-up queries (safety net if chat path is hit).

### Files edited
| File | Change |
|------|--------|
| `backend/researcher/query_router.py` | Broad follow-up → fast; expanded signals |
| `backend/researcher/server.py` | Canned reply bypass for follow-ups |
| `scripts/tests/test_p1_router.py` | Micron sentiment follow-up test |

### Test queries
| Query | Context | Expected |
|-------|---------|----------|
| `what is its market sentiment?` | Prior ALEX message on Micron (MU) | Fast → MU |
| `give its PE ratio` | Prior NVDA analysis | Fast → NVDA |

---

## FIX-007 — Observe page LLM tokens + AWS cost per query

### Problem
`/observe` showed latency and model ID per query but not **input tokens**, **output tokens**, or **AWS Bedrock cost**. Chat route cards displayed tag `chat` instead of **chat observability**.

### Root cause
- `query_latency_metrics` had `cost_usd` but it was always `0` — no token capture from Bedrock streams
- No `input_tokens` / `output_tokens` columns in Aurora
- Frontend observe API and UI did not surface token/cost fields

### Fix
1. **`bedrock_cost.py`** — Nova Lite/Pro/Micro + Claude list pricing; `calculate_cost()` and `estimate_tokens()` fallback
2. **`latency_tracker.py`** — `set_token_usage()` from Bedrock metadata; `_finalize_tokens()` estimates when metadata missing; flush writes `input_tokens`, `output_tokens`, `cost_usd`
3. **`server.py`** — `stream_bedrock_conversation()` reads `metadata.usage.inputTokens/outputTokens` from response stream
4. **`scripts/aurora_warmup.py`** — migration adds `input_tokens`, `output_tokens` columns
5. **`frontend/app/api/observe/route.ts`** — returns per-query and 7d rollup token/cost stats
6. **`frontend/app/observe/page.tsx`** — LLM stats section per card; 7d cost summary; `ROUTE_LABELS.chat` → **chat observability**

### How cost is calculated
| Step | Detail |
|------|--------|
| Primary | Bedrock stream `metadata.usage` → exact `inputTokens` / `outputTokens` |
| Pricing | Nova Lite: $0.00006/1K in, $0.00024/1K out (AWS list price) |
| Fallback | `chars // 4` estimate for fast/deep agent paths without usage metadata |
| Storage | `query_latency_metrics.cost_usd` per query |
| Display | `/observe` Research tab — per-card + 7d rollup |

### Files edited
| File | Change |
|------|--------|
| `backend/researcher/bedrock_cost.py` | **NEW** — model pricing + cost helpers |
| `backend/researcher/latency_tracker.py` | Token/cost capture + DB flush |
| `backend/researcher/server.py` | Stream usage metadata → tracker |
| `scripts/aurora_warmup.py` | `input_tokens`, `output_tokens` columns |
| `frontend/app/api/observe/route.ts` | Token/cost in API response |
| `frontend/app/observe/page.tsx` | LLM stats UI + chat observability tag |

### Verification
- Aurora migration: `python3 scripts/aurora_warmup.py` — `qlm.input_tokens`, `qlm.output_tokens` ✅
- New queries after ECS deploy populate token/cost fields on `/observe`

---

## FIX-008 — Dashboard ops “Refresh now” stale / non-functional

### Problem
On `/dashboard`, **Refresh now** in the AWS Cost & Ops Monitor widget did not update data. **Last refresh** stayed at old timestamps (e.g. `2026-06-14 04:44:16`) even after clicking.

### Root cause
`OpsCostWidget` only called `GET /api/ops`, which reads cached `cost_snapshots` / `ops_snapshots` from Aurora. There was no `POST` handler to invoke `alex-ops-agent`, so refresh never triggered a live health/cost run.

### Fix
1. **`POST /api/ops`** — invokes `alex-ops-agent` with `{ source: 'manual', action: 'monitor' }`
2. **`OpsCostWidget.tsx`** — Refresh now: `POST` → wait → `GET`; shows “Running ops agent…” and error text on failure

### Files edited
| File | Change |
|------|--------|
| `frontend/app/api/ops/route.ts` | `POST` Lambda invoke for manual ops run |
| `frontend/components/OpsCostWidget.tsx` | `refreshNow()` + loading/error UI |

### Verification
- `aws lambda invoke alex-ops-agent` — `health_score: 100`, fresh timestamp ✅
- Dashboard Refresh now updates **Last refresh** after ~15s

---

## FIX-009 — pgvector semantic search: 502, 0 results, Micron RAG weak

### Problem
1. API Gateway `/search` returned **502** intermittently
2. Semantic search returned **0 results** for valid queries (e.g. *"Micron MU SEC filing"*) while NVDA queries worked
3. **48 debug-test vectors** polluted top-K results
4. Micron had only **1 monolithic chunk** — similarity scores below 0.65 RAG threshold

### Root cause
| Issue | Cause |
|-------|-------|
| 502 | SageMaker `ThrottlingException` uncaught in `alex-ingest` → Lambda crash → API GW 502 |
| 0 results | RDS Data API returns empty for `ORDER BY embedding <=> vector` on full table (921 rows); subquery `ORDER BY score DESC` works |
| Junk results | Jun 11 debug reporter runs left in `research_vectors` |
| Weak Micron | Single 2.6K-char ingest; MiniLM embeds first 300 chars only per chunk |

### Fix
1. **`ingest_pgvector.py`** — SageMaker throttle retry; search/ingest try/except → proper JSON errors; **subquery similarity** pattern; exclude `debug test` topics; **auto-chunk** ingest via `rag_utils.chunk_content()` (1200 chars)
2. **`rag_utils.py`** — paragraph-aware chunking (new)
3. **`context_service.py`** — same subquery pattern for `get_prior_research` + portfolio change detection
4. **`frontend/app/api/search/route.ts`** — Lambda invoke primary; API Gateway fallback; 45s timeout
5. **`scripts/rag_maintenance.py`** — delete debug vectors; re-ingest Micron as 3 chunks
6. **`scripts/test_pgvector_rag.py`** — step-by-step pgvector verification harness

### Maintenance run (2026-06-15)
| Action | Result |
|--------|--------|
| Delete debug/final-test vectors | 48 removed (969 → 921) |
| Re-ingest Micron | 3 chunked vectors |
| Search verify | Micron top score **0.67–0.72** (above 0.65 threshold) |

### Files edited
| File | Change |
|------|--------|
| `backend/ingest/ingest_pgvector.py` | Throttle retry, subquery search, chunk ingest, error handling |
| `backend/ingest/rag_utils.py` | **NEW** — `chunk_content()` |
| `backend/researcher/context_service.py` | Subquery semantic search |
| `frontend/app/api/search/route.ts` | Lambda-first search |
| `scripts/deploy_ingest.sh` | Package `rag_utils.py` |
| `scripts/rag_maintenance.py` | **NEW** — cleanup + Micron re-ingest |
| `scripts/test_pgvector_rag.py` | **NEW** — RAG step tests |

### Verification
```bash
python3 scripts/test_pgvector_rag.py --step 6 --search "Micron MU SEC filing memory chip risks"
python3 scripts/rag_maintenance.py --verify
# API Gateway: HTTP 200, Micron top score 0.72
```

---

## FIX-010 — "explain stop loss?" canned as off-topic

### Problem
Query: *"explain stop loss?"* → instant canned *"I can't help with that one"* (chat / off_topic, 0.1s) instead of a trading education answer.

### Root cause
1. `stop loss` was not in `FINANCE_TOPIC_PATTERNS` — `_has_finance_topic()` returned False
2. `_is_off_topic()` treated **any** educational frame (`explain`, `what is`) without finance topic match as off_topic
3. `_conversation_canned_reply()` duplicated that logic with `_has_educational_frame && ! _has_finance_topic`

### Fix
- Added `INVESTING_EDU_PATTERNS` — stop loss, take profit, DCA, position sizing, order types, etc.
- `_has_finance_topic()` checks both pattern lists
- `_is_off_topic()` — educational frame only off_topic when `OFF_TOPIC_SIGNALS` match (e.g. quantum physics), not all unexplained concepts
- `_conversation_canned_reply()` — removed redundant educational-frame canned block; relies on `_is_off_topic()` only
- Added `finance_anchor` terms: `stop loss`, `take profit`, `margin`, `option`, `dividend`

### Files edited
| File | Change |
|------|--------|
| `backend/researcher/query_router.py` | `INVESTING_EDU_PATTERNS`, `_is_off_topic` fix |
| `backend/researcher/server.py` | Canned reply bypass for trading education |
| `scripts/tests/test_p1_router.py` | `test_trading_education()` — 4 cases |

### Test queries
| Query | Expected |
|-------|----------|
| `explain stop loss?` | chat → education |
| `what is a stop loss` | chat → education |
| `explain quantum physics` | chat → off_topic (unchanged) |

### Verification
- `python3 scripts/tests/test_p1_router.py` — 55/55 pass

---

## FIX-011 — LLM finance gate (stop regex sprawl for education)

### Problem
User feedback: Alex cannot rely on growing regex / few-shot pattern lists for every concept (*"explain vega"*, *"what is gamma"*, etc.). FIX-010 added `INVESTING_EDU_PATTERNS` — necessary short-term but not scalable.

### Solution — hybrid router
| Layer | When | Cost |
|-------|------|------|
| **Regex fast-path** | Policy flags, SEC education, follow-ups, tickers, known patterns | 0 ms |
| **LLM finance gate** | Ambiguous `explain/what is` without regex match | ~1 Nova Lite call |
| **Chat LLM** | Answer the question | Bedrock stream |

### `_llm_finance_gate()` (Nova Lite)
- One compact prompt: *"Is this finance-related?"* with **principle-based** scope (not per-concept examples)
- Returns `{finance: bool, intent: education|off_topic|conversation}`
- Env: `ROUTER_USE_LLM_GATE=true` (default on); set `false` to disable

### Routing order (deterministic first)
1. Policy flag → 2. Greeting → 3. SEC education → 4. Follow-up → **5. LLM gate** → 6. Regex off_topic

### Files edited
| File | Change |
|------|--------|
| `backend/researcher/query_router.py` | `_should_llm_finance_gate`, `_llm_finance_gate`, classify order |
| `backend/researcher/server.py` | Skip canned reply for `education`/`conversation` intents |
| `scripts/tests/test_p1_router.py` | `test_llm_finance_gate_unknown_concepts()` with mock |

### Verification
- `python3 scripts/tests/test_p1_router.py` — 59/59 pass
- Live: *"explain vega"* → LLM gate → education → Alex explains (no new regex)

---

## FIX-012 — Vague follow-up after insider research routes to chat

### Problem
After *"insider trade details for AMD"* (Form 4 + accession `0000002488-26-000109`), follow-up *"are there any other details I can know?"* routed to **chat** (~1.2s) and returned generic insider-trading education — no AMD ticker, no EDGAR fetch.

### Root cause
1. Query did not match `_looks_like_followup()` or `_has_pronoun_reference()` — no pronouns, no ticker.
2. `resolve_entities()` only pulled session tickers for pronoun/follow-up patterns → **AMD lost**.
3. Router fell through to default conversational chat.
4. `_prepare_deep_research()` re-inferred scope from vague query text → would not get `filing_form4` even if routed deep.

### Fix
| Piece | Behavior |
|-------|----------|
| `_is_vague_continuation()` | Detects *"any other details"*, *"what else"*, *"tell me more"*, etc. |
| `_infer_context_topic()` | Reads last ALEX message — insider / sec / sentiment / market |
| `_follow_up_route_decision()` | Insider topic → **deep MCP** with `filing_form4` scope |
| `enrich_follow_up_query()` | Expands vague query to e.g. *"AMD additional Form 4 insider trading…"* |
| `_prepare_deep_research()` | Uses enriched topic + forced scope for agent input |

### Test queries
| Query | Context | Expected |
|-------|---------|----------|
| `are there any other details I can know?` | AMD Form 4 ALEX reply | deep MCP, AMD, `filing_form4` |
| Same without context | — | chat (no ticker) |
| `give its PE ratio` | NVDA context | fast NVDA (unchanged) |

### Files edited
| File | Change |
|------|--------|
| `backend/researcher/query_router.py` | vague continuation, context topic, enrich, follow-up routing |
| `backend/researcher/server.py` | `enrich_follow_up_query` in deep + fast stream prep |
| `scripts/tests/test_p1_router.py` | AMD insider vague follow-up cases |

### Verification
- `python3 scripts/tests/test_p1_router.py` — 62/62 pass

---

## FIX-013 — CEO/leadership queries return market snapshot, not answer

### Problem
Query: *"CEO of TSLA"*  
Router chose Fast Research correctly, but response was a full price/news table — **never named Elon Musk or any CEO**.

### Root cause
1. `get_stock_data` did not include `companyOfficers` from yfinance (data was available)
2. Fast agent prompt always forced full analysis template regardless of question type
3. Analyst target printed with excessive precision (`$420.54633`)

### Fix
| Piece | Behavior |
|-------|----------|
| `format_company_leadership()` | KEY PEOPLE block from yfinance `companyOfficers` |
| `get_stock_data` | Includes CEO/CFO/officers; rounds price/target to 2 decimals |
| Fast prompt | Question-first: narrow factual vs broad research templates |
| `_is_leadership_query()` | Router intent `leadership` for CEO/CFO/founder queries |
| Fast stream | Leadership hint + "👤 Looking up company leadership..." reasoning step |

### Test queries
| Query | Expected |
|-------|----------|
| `CEO of TSLA` | fast / leadership / TSLA → names CEO from KEY PEOPLE |
| `who is the CFO of NVDA` | fast / leadership / NVDA |
| `NVDA price today` | fast / market_research (unchanged) |

### Files edited
| File | Change |
|------|--------|
| `backend/researcher/tools.py` | `format_company_leadership`, KEY PEOPLE in tool output |
| `backend/researcher/prompts.py` | Question-first fast mode instructions |
| `backend/researcher/query_router.py` | `_is_leadership_query`, `leadership` intent |
| `backend/researcher/server.py` | Leadership hint in fast stream |
| `scripts/tests/test_p1_router.py` | Leadership routing tests |

### Verification
- `python3 scripts/tests/test_p1_router.py` — 65/65 pass

---

## Deploy log

| Date (UTC) | Image digest (short) | Notes |
|------------|----------------------|-------|
| 2026-06-15 22:32 | `601bfb42…` | FIX-001–004: routing, scope, sec_education |
| 2026-06-15 22:51 | `ba3e1acf…` | FIX-005: canned reply + ALEX ticker |
| 2026-06-15 23:04 | `df58fdc6…` | FIX-006: sentiment follow-up context |
| 2026-06-15 23:13 | `7bdb7cfb…` | FIX-007: LLM tokens + cost observability |
| 2026-06-15 23:41 | ingest λ | FIX-009: chunk ingest + subquery search (pass 1) |
| 2026-06-15 23:44 | ingest λ | FIX-009: subquery search fix (pass 2) |
| 2026-06-15 23:46 | ECS researcher | FIX-009: `context_service` subquery search |
| 2026-06-16 00:00 | ECS researcher | FIX-010: trading education (stop loss) |
| 2026-06-16 00:14 | ECS researcher | FIX-012: vague insider follow-up → deep Form 4 |

---

## Future work

| Item | Priority | Notes |
|------|----------|-------|
| ~~Deploy researcher image to ECS~~ | ~~P0~~ | ✅ Done 2026-06-15 |
| ~~Log FIX entries to `Alex_report.md` §33 as CL-019+~~ | ~~P1~~ | ✅ CL-019 added |
| LLM router fallback for edge-case SEC education | P2 | Regex covers most cases; LLM for ambiguous phrasing |
| Frontend badge for `sec_education` vs `education` | P3 | Show "Explaining" instead of "Deep Research" |
| Scope-aware stub recovery for 8-K / Form 4 only | P2 | Fallback already uses scope form type |
| Session-aware SEC education follow-ups | P2 | ~~Partial: vague continuation after live Form 4 (FIX-012)~~; still need after `sec_education` chat |
| Golden-set regression harness | P2 | JSON file of 50+ routing cases run in CI |
| Aurora SQL type cast in `get_prior_research` | P2 | Logged: `timestamp > text` error in ECS logs |
| pgvector HNSW index on `research_vectors` | P3 | Subquery fix works; index would speed ORDER BY at scale |
| Periodic `rag_maintenance.py` cron | P3 | Auto-purge debug vectors + re-chunk stale tickers |

---

## Changelog

| Date | Author | Change |
|------|--------|--------|
| 2026-06-15 | Cursor Agent | Created doc; FIX-001–004 |
| 2026-06-15 | Cursor Agent | FIX-005: canned reply + ALEX ticker fixes |
| 2026-06-15 | Cursor Agent | FIX-006: Micron sentiment follow-up context |
| 2026-06-15 | Cursor Agent | FIX-007: Observe LLM tokens + AWS cost per query |
| 2026-06-15 | Cursor Agent | Standing policy extended to RAG/ops/observability (user request) |
| 2026-06-15 | Cursor Agent | FIX-008: Dashboard ops refresh invokes alex-ops-agent |
| 2026-06-15 | Cursor Agent | FIX-009: pgvector search 502, subquery fix, Micron chunk re-ingest |
| 2026-06-15 | Cursor Agent | FIX-010: explain stop loss canned off-topic → education |
| 2026-06-16 | Cursor Agent | FIX-011: LLM finance gate — scalable education routing |
| 2026-06-16 | Cursor Agent | FIX-012: vague follow-up after insider/SEC → deep Form 4 |
| 2026-06-16 | Cursor Agent | FIX-013: CEO/leadership queries — KEY PEOPLE + question-first fast |
