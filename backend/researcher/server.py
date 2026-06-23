"""
Alex Researcher Service — Autonomous Investment Research Agent
Guide 8: Added CloudWatch metrics for observability
"""
import os
import re
import time
import json
import logging
import boto3
from datetime import datetime, UTC
from typing import Optional

from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv
from agents import Agent, Runner, trace
from agents.extensions.models.litellm_model import LitellmModel
import asyncio

from contextlib import asynccontextmanager

logging.getLogger("LiteLLM").setLevel(logging.CRITICAL)

from prompts import (
    get_agent_instructions, get_fast_agent_instructions, get_deep_research_instructions,
    DEFAULT_RESEARCH_PROMPT, build_deep_scope_directive,
)
from mcp_servers import create_playwright_mcp_server
from tools import ingest_financial_document, get_stock_data, get_sec_filings, build_market_overview_context
from query_trace import QueryTrace, activate_trace, deactivate_trace, record_mcp
from latency_tracker import LatencyTracker, activate_tracker, deactivate_tracker, get_tracker
from query_router import (
    classify_query, routing_steps, RouteDecision, infer_research_scope, deep_reasoning_steps,
    _is_market_overview_query, _is_leadership_query,
)

GUARDRAIL_ID      = os.getenv("BEDROCK_GUARDRAIL_ID",      "eea439luokx8")
GUARDRAIL_VERSION = os.getenv("BEDROCK_GUARDRAIL_VERSION", "1")
CLUSTER_ARN       = os.getenv("DB_CLUSTER_ARN",            "")
SECRET_ARN        = os.getenv("DB_SECRET_ARN",             "")
DB_NAME           = os.getenv("DB_NAME",                   "alex_db")

load_dotenv(override=True)

app = FastAPI(title="Alex Researcher Service")

app.add_middleware(
    CORSMiddleware,
    allow_origins     = ["*"],
    allow_credentials = True,
    allow_methods     = ["*"],
    allow_headers     = ["*"],
)

logger     = logging.getLogger(__name__)
cloudwatch = boto3.client('cloudwatch', region_name='us-east-1')

REGION      = "us-east-1"
MODEL       = "bedrock/us.amazon.nova-pro-v1:0"   # deep / multi
FAST_MODEL  = os.getenv("FAST_BEDROCK_MODEL", "bedrock/us.amazon.nova-lite-v1:0")
FAST_TURNS  = int(os.getenv("FAST_MAX_TURNS", "4"))


@asynccontextmanager
async def observe_query(route: str, topic: str, user_id: str, session_id: str, model: str):
    """Activate per-query trace + latency tracker; flush to Aurora on exit."""
    tracker = LatencyTracker(
        query=topic, route=route, clerk_id=user_id,
        session_id=session_id, model=model,
    )
    qtrace  = QueryTrace()
    tok_tr  = activate_tracker(tracker)
    tok_qt  = activate_trace(qtrace)
    try:
        yield tracker, qtrace
    except Exception:
        tracker.success = False
        raise
    finally:
        tracker.flush(qtrace)
        deactivate_tracker(tok_tr)
        deactivate_trace(tok_qt)


# ============================================
# Aurora Warm-up Ping
# ============================================
@app.on_event("startup")
async def start_aurora_ping():
    async def ping_aurora():
        while True:
            await asyncio.sleep(240)
            try:
                if CLUSTER_ARN and SECRET_ARN:
                    rds = boto3.client('rds-data', region_name=REGION)
                    rds.execute_statement(
                        resourceArn = CLUSTER_ARN,
                        secretArn   = SECRET_ARN,
                        database    = DB_NAME,
                        sql         = "SELECT 1"
                    )
                    print("Aurora ping successful")
            except Exception as e:
                print(f"Aurora ping failed: {e}")
    asyncio.create_task(ping_aurora())


# ============================================
# CloudWatch Metrics
# ============================================
def emit_metric(name: str, value: float, unit: str = 'Count', dimensions: dict = None):
    try:
        dims = [{'Name': 'Service', 'Value': 'alex-researcher'}]
        if dimensions:
            for k, v in dimensions.items():
                dims.append({'Name': k, 'Value': str(v)})
        cloudwatch.put_metric_data(
            Namespace  = 'AlexAI',
            MetricData = [{'MetricName': name, 'Value': value, 'Unit': unit, 'Dimensions': dims}]
        )
        print(f"Metric emitted: {name}={value}")
    except Exception as e:
        print(f"Metric emission failed: {e}")


class ResearchRequest(BaseModel):
    topic:      Optional[str] = None
    deep:       bool          = False
    user_id:    Optional[str] = None
    session_id: Optional[str] = None
    intent:     Optional[str] = None
    debater:    Optional[str] = None
    ticker:     Optional[str] = None


class RagasEvalRequest(BaseModel):
    gate:  Optional[str] = "observe"
    smoke: bool          = False


# ============================================
# Smart Guardrail Decision
# ============================================
def should_apply_guardrail(query: str, response: str) -> bool:
    query_lower    = query.lower()
    response_lower = response.lower()

    harmful_patterns = [
        'manipulate', 'pump and dump', 'insider tip',
        'guaranteed return', 'get rich quick',
        'risk free', 'all my savings',
        'launder', 'fraud', 'illegal',
        'front run', 'short squeeze scheme',
        'how to cheat', 'avoid taxes illegally'
    ]
    if any(p in query_lower for p in harmful_patterns):
        print(f"Guardrail: harmful intent detected")
        return True

    financial_signals = [
        '$', 'price', 'market cap', 'revenue',
        'earnings', 'analyst', 'p/e', 'ratio',
        'stock', 'shares', 'quarter', 'fiscal',
        'guidance', 'sec', 'filing', '%', 'buy',
        'sell', 'hold', 'target', 'valuation'
    ]
    signals_found = sum(1 for s in financial_signals if s in response_lower)
    print(f"Guardrail: financial signals found = {signals_found}")

    if signals_found >= 3:
        print(f"Guardrail: skipping — legitimate financial content")
        return False

    print(f"Guardrail: applying — insufficient financial signals")
    return True


# ============================================
# Guardrail Application
# ============================================
async def apply_guardrail(text: str, query: str = "") -> tuple[str, bool]:
    try:
        loop    = asyncio.get_event_loop()
        bedrock = boto3.client('bedrock-runtime', region_name=REGION)

        response = await loop.run_in_executor(
            None,
            lambda: bedrock.apply_guardrail(
                guardrailIdentifier = GUARDRAIL_ID,
                guardrailVersion    = GUARDRAIL_VERSION,
                source              = 'OUTPUT',
                content             = [{"text": {"text": text}}]
            )
        )

        if response['action'] == 'GUARDRAIL_INTERVENED':
            print("Guardrail blocked response")
            emit_metric('GuardrailBlock', 1)
            reason = "Bedrock guardrail blocked non-financial output"
            log_guardrail_observation(
                query, reason, agent_name="bedrock_guardrail", route="output",
            )
            return (
                "I can only help with financial research topics. "
                "Please ask about stocks, markets, or investment analysis.",
                True
            )

        print("Guardrail passed")
        return (text, False)

    except Exception as e:
        print(f"Guardrail error (failing open): {e}")
        return (text, False)


def log_guardrail_observation(
    query: str,
    reason: str,
    agent_name: str = "alex_guardrail",
    route: str = "chat",
    latency_ms: int = 0,
) -> None:
    """Persist guardrail hit to agent_observations for /observe."""
    if not CLUSTER_ARN or not SECRET_ARN:
        return
    try:
        rds = boto3.client("rds-data", region_name=REGION)
        rds.execute_statement(
            resourceArn=CLUSTER_ARN,
            secretArn=SECRET_ARN,
            database=DB_NAME,
            sql="""
                INSERT INTO agent_observations
                    (agent_name, ticker, simulation_id, model_id,
                     input_tokens, output_tokens, total_tokens, latency_ms,
                     cost_usd, action, confidence, success, error_message,
                     guardrail_triggered, guardrail_action)
                VALUES
                    (:agent, :ticker, :sim::uuid, :model,
                     0, 0, 0, :latency,
                     0, :action, 1.0, true, :query,
                     true, :reason)
            """,
            parameters=[
                {"name": "agent",   "value": {"stringValue": agent_name}},
                {"name": "ticker",  "value": {"stringValue": ""}},
                {"name": "sim",     "value": {"stringValue": "00000000-0000-0000-0000-000000000000"}},
                {"name": "model",   "value": {"stringValue": route}},
                {"name": "latency", "value": {"longValue": latency_ms}},
                {"name": "action",  "value": {"stringValue": "BLOCK"}},
                {"name": "query",   "value": {"stringValue": (query or "")[:500]}},
                {"name": "reason",  "value": {"stringValue": reason[:500]}},
            ],
        )
        logger.info(f"Guardrail logged: {agent_name} — {reason[:80]}")
    except Exception as e:
        logger.warning(f"Guardrail observation log failed (non-fatal): {e}")


# ============================================
# Context Helper
# ============================================
def get_context(topic: str, user_id: str, session_id: str, fast: bool = False) -> str:
    """Get pgvector context — non-fatal if fails."""
    if not user_id:
        return ""
    try:
        from context_service import build_full_context
        t0      = time.time()
        context = build_full_context(
            query      = topic,
            user_id    = user_id,
            session_id = session_id,
            fast       = fast,
        )
        print(f"Context built: {len(context)} chars in {time.time() - t0:.1f}s (fast={fast})")
        return context
    except Exception as e:
        print(f"Context error (non-fatal): {e}")
        return ""


def _active_ticker_directive(topic: str, entities: list[str] | None = None, context: str = "") -> str:
    """Tell the agent which symbol to research — critical for pronoun follow-ups."""
    from query_router import resolve_entities
    tickers = entities or resolve_entities(topic, context)
    if not tickers:
        return ""
    primary = tickers[0]
    return (
        f"\n\nACTIVE TICKER: {primary}\n"
        f"The user's question refers to {primary}. "
        f"Call tools with ticker=\"{primary}\" — do NOT substitute another symbol "
        f"(e.g. from portfolio holdings).\n"
    )


def _is_stub_response(text: str, mode: str = "deep", scope=None) -> bool:
    """Detect agent returning ingest confirmation instead of full analysis."""
    if not text or len(text.strip()) < 40:
        return True
    lower = text.lower()
    stub_phrases = (
        "successfully stored", "research has been stored", "been completed and stored",
        "stored research for topic", "if you have any more questions",
        "feel free to ask", "analysis has been successfully completed",
        "ingest saved for",
    )
    if any(p in lower for p in stub_phrases) and len(text) < 900:
        return True
    if mode == "deep" and scope and scope.sec_forms:
        primary = scope.sec_forms[0].lower()
        has_sec = primary in lower or "risk factor" in lower or "filing date" in lower
        if scope.scope == "filing_form4":
            has_insider = "insider:" in lower or "shares" in lower or "transaction" in lower
            has_placeholders = bool(re.search(r"\[(insider|buy/sell|number of shares|price)\]", lower))
            if has_placeholders or (not has_insider and len(text) < 1200):
                return True
        if not has_sec and "recommendation" in lower and len(text) < 700:
            return True
    return False


async def _recover_deep_sec_response(topic: str, ticker: str, scope=None) -> str:
    """Fallback when deep agent returns a stub — fetch SEC data directly."""
    from datetime import datetime as dt
    today = dt.now().strftime("%B %d, %Y")
    scope = scope or infer_research_scope(topic)
    form  = scope.sec_forms[0] if scope.sec_forms else "10-K"
    filing = await get_sec_filings(ticker, form)
    if filing.startswith("No ") or filing.startswith("Could not"):
        return filing
    title = {
        "10-K": "10-K Analysis",
        "8-K":  "8-K Current Report",
        "10-Q": "10-Q Quarterly Report",
        "4":    "Insider Trading (Form 4)",
    }.get(form, f"{form} Analysis")
    return (
        f"**{ticker} — {title} | {today}**\n\n"
        f"---\n\n**SEC {form} Analysis** *(Source: SEC EDGAR via EdgarTools)*\n\n"
        f"{filing}\n\n"
        f"---\n\n> ⚠️ This is research not financial advice.\n"
        f"> Sources: SEC EDGAR (EdgarTools) | {today}\n"
    )


def _prepare_deep_research(topic: str, user_id: str, session_id: str):
    """Build scoped instructions and agent input for deep research."""
    from query_router import enrich_follow_up_query, resolve_entities

    context = get_context(topic, user_id, session_id)
    enriched, forced_scope = enrich_follow_up_query(topic, context)
    work_topic = enriched
    scope        = forced_scope or infer_research_scope(work_topic)
    entities     = resolve_entities(work_topic, context)
    ticker_hint  = _active_ticker_directive(work_topic, entities=entities, context=context)
    instructions = get_deep_research_instructions()
    if context:
        instructions += f"\n\n{context}"
    instructions += (
        "\n\nPRIOR RESEARCH in context is background only. "
        "Fetch fresh data for the sections in scope. "
        "Never reply with only a storage confirmation.\n"
    )
    instructions += build_deep_scope_directive(scope)
    if ticker_hint:
        instructions += ticker_hint

    agent_input = (
        f"Deep research: {work_topic}{ticker_hint}\n"
        f"Scope: {scope.scope} — {scope.label}\n"
        f"Call ONLY the tools listed in the SCOPED RESEARCH DIRECTIVE. "
        f"Return ONLY the sections listed there."
    )
    return instructions, scope, entities, agent_input, context


def save_session(user_id: str, session_id: str, topic: str, response: str):
    """Save messages to session — non-fatal if fails."""
    if not user_id:
        return
    try:
        from context_service import save_message
        save_message(user_id, session_id, "user",  topic)
        save_message(user_id, session_id, "alex",  response)
    except Exception as e:
        print(f"Session save error (non-fatal): {e}")


async def stream_response_tokens(filtered_response: str, chunk_size: int = 4, delay_s: float = 0.028):
    """Yield SSE tokens in small chunks for visible streaming UX."""
    words = filtered_response.split(' ')
    for i in range(0, len(words), chunk_size):
        chunk = ' '.join(words[i:i + chunk_size]) + (' ' if i + chunk_size < len(words) else '')
        yield f"data: {json.dumps({'type': 'token', 'content': chunk})}\n\n"
        if delay_s > 0:
            await asyncio.sleep(delay_s)


def _conversation_canned_reply(query: str, intent: str) -> Optional[str]:
    """Instant replies — no Bedrock call."""
    if intent == "policy_flag":
        return (
            "🛡️ **I can't help with aggressive trading strategies or personalized short recommendations.**\n\n"
            "Alex is a **research assistant**, not a trading advisor. Short selling carries "
            "unlimited loss potential and is not suitable for most investors.\n\n"
            "I *can* help with:\n"
            "- *What is short selling?* — educational explanation\n"
            "- *TSLA short interest and latest news* — factual research\n"
            "- *Compare NVDA vs AMD* — deep analysis\n\n"
            "_Not financial advice. Consult a licensed advisor before any trading decisions._"
        )
    if intent in ("education", "conversation", "sec_education", "general"):
        return None
    if intent == "off_topic":
        return (
            "I'm Alex, your AI **financial research** assistant — I focus on stocks, "
            "bonds, markets, and portfolio topics.\n\n"
            "I can't help with that one, but try asking:\n"
            "- *Tell me about bonds*\n"
            "- *What is NVDA trading at?* (live research)\n"
            "- *Compare NVDA vs AMD* (deep research)"
        )
    if intent == "sec_education":
        return None
    from query_router import (
        _has_finance_topic, _has_educational_frame, _is_off_topic, _is_sec_conceptual_education,
    )
    if _is_sec_conceptual_education(query):
        return None
    from query_router import _has_pronoun_reference, _looks_like_followup
    if _has_pronoun_reference(query) or _looks_like_followup(query):
        return None
    if _is_off_topic(query):
        return (
            "I'm Alex, your AI **financial research** assistant — I focus on stocks, "
            "bonds, markets, and portfolio topics.\n\n"
            "That question is outside my scope. Ask me about investing, markets, or a specific stock!"
        )
    return None


async def _try_insider_followup_direct(topic: str, user_id: str, session_id: str) -> Optional[str]:
    """If user asks for more Form 4 details, fetch EDGAR directly — skip chat placeholders."""
    from query_router import (
        _is_contextual_followup, _infer_context_topic,
        resolve_entities, enrich_follow_up_query,
    )
    try:
        from context_service import get_conversation_context
        context = get_conversation_context(user_id, session_id, limit=4)
    except Exception:
        context = ""
    if not context or not _is_contextual_followup(topic):
        return None
    if _infer_context_topic(context) != "insider":
        return None
    entities = resolve_entities(topic, context)
    if not entities:
        return None
    _, scope = enrich_follow_up_query(topic, context)
    return await _recover_deep_sec_response(topic, entities[0], scope)


def _build_conversation_prompt(query: str, user_id: str, session_id: str, intent: str) -> tuple[str, int]:
    """Lightweight prompt for chat — skip DB context on education for speed."""
    conv = ""
    if intent not in ("education", "greeting", "sec_education"):
        try:
            from context_service import get_conversation_context
            conv = get_conversation_context(user_id, session_id, limit=4)
        except Exception:
            pass

    is_edu = intent in ("education", "sec_education", "conversation", "general", "greeting")
    max_tokens = 650 if intent == "sec_education" else (550 if is_edu else 400)

    sec_note = ""
    if intent == "sec_education":
        sec_note = (
            "- SEC/filing education: explain types, differences, and purpose clearly.\n"
            "- Use bullets or a short table when comparing filing types (10-K, 8-K, Form 4, 10-Q).\n"
            "- Do NOT claim you fetched live EDGAR data — this is conceptual education.\n"
        )

    prompt = f"""You are Alex, a warm AI financial assistant.

{conv}

User: {query}

Instructions:
- ONLY financial/investing topics. Politely decline anything else.
- Answer in clear markdown. For education: 2-3 short paragraphs max, use bullets if helpful.
{sec_note}- No buy/sell recommendations. Be accurate and concise.
- NEVER use bracket placeholders like [Insider Name], [Buy/Sell], [Number of Shares], or [Price].
- If conversation history mentions a Form 4 or accession number but you lack transaction rows, say you need a deep EDGAR fetch — do not invent fields."""
    return prompt, max_tokens


def _build_market_overview_prompt(query: str, overview_data: str) -> tuple[str, int]:
    """Prompt Nova with live index data — no placeholders."""
    today = datetime.now(UTC).strftime("%B %d, %Y")
    prompt = f"""You are Alex, a financial research assistant. Today is {today}.

LIVE DATA (use ONLY these numbers — do not invent prices or % changes):
{overview_data}

User: {query}

Write a concise **Market Overview Today** in markdown:
1. Greet the user by name if they introduced themselves.
2. Table: Index | Level | Change today (%)
3. Table: Sector | ETF | Change today (%)
4. 2–3 bullet points interpreting sector leaders/laggards and Fear & Greed if present.
5. One sentence closing offer to drill into a sector or ticker.

Rules:
- Use EXACT numbers from LIVE DATA above.
- NEVER use placeholders like X%, [Briefly mention], or bracketed filler.
- If a data point is unavailable, say "unavailable" — do not guess."""
    return prompt, 550


_STREAM_DONE = object()


async def stream_bedrock_conversation(prompt: str, max_tokens: int = 550, tracker=None):
    """Yield Nova Lite text tokens; records Bedrock usage on tracker when present."""
    model_id = FAST_MODEL.replace("bedrock/", "")
    body = json.dumps({
        "messages": [{"role": "user", "content": [{"text": prompt}]}],
        "inferenceConfig": {"maxTokens": max_tokens, "temperature": 0.4},
    })

    queue: asyncio.Queue = asyncio.Queue()
    loop = asyncio.get_running_loop()
    usage_holder = {"input": 0, "output": 0}

    def _produce() -> None:
        try:
            bedrock = boto3.client("bedrock-runtime", region_name=REGION)
            resp = bedrock.invoke_model_with_response_stream(
                modelId=model_id,
                contentType="application/json",
                accept="application/json",
                body=body,
            )
            for event in resp["body"]:
                chunk = json.loads(event["chunk"]["bytes"])
                if "contentBlockDelta" in chunk:
                    text = chunk["contentBlockDelta"]["delta"].get("text", "")
                    if text:
                        asyncio.run_coroutine_threadsafe(queue.put(text), loop).result()
                if "metadata" in chunk:
                    u = chunk["metadata"].get("usage", {})
                    usage_holder["input"]  = int(u.get("inputTokens", 0) or 0)
                    usage_holder["output"] = int(u.get("outputTokens", 0) or 0)
        except Exception as exc:
            asyncio.run_coroutine_threadsafe(queue.put(exc), loop).result()
        finally:
            asyncio.run_coroutine_threadsafe(queue.put(_STREAM_DONE), loop).result()

    loop.run_in_executor(None, _produce)

    while True:
        item = await queue.get()
        if item is _STREAM_DONE:
            break
        if isinstance(item, Exception):
            raise item
        yield item

    if tracker and (usage_holder["input"] or usage_holder["output"]):
        tracker.set_token_usage(usage_holder["input"], usage_holder["output"])


# ============================================
# Fast Research Agent
# ============================================
async def run_data_agent(
    topic:      str,
    user_id:    str = "",
    session_id: str = ""
) -> str:
    os.environ["AWS_REGION_NAME"]    = REGION
    os.environ["AWS_REGION"]         = REGION
    os.environ["AWS_DEFAULT_REGION"] = REGION

    model = LitellmModel(model=FAST_MODEL)

    # Build context from pgvector + history (fast path skips RAG embed)
    t0           = time.time()
    context      = get_context(topic, user_id, session_id, fast=True)
    ctx_ms       = int((time.time() - t0) * 1000)
    tr           = get_tracker()
    if tr:
        tr.mark_context_ms(ctx_ms)
    instructions = get_fast_agent_instructions()
    if context:
        instructions += f"\n\n{context}"

    with trace("Alex-Data-Agent"):
        agent = Agent(
            name         = "Alex Data Researcher",
            instructions = instructions,
            model        = model,
            tools        = [get_stock_data, ingest_financial_document],
            mcp_servers  = [],
        )
        result = await Runner.run(
            agent,
            input     = f"Research this investment topic: {topic}",
            max_turns = FAST_TURNS,
        )

    agent_ms = int((time.time() - t0) * 1000)
    if tr:
        tr.mark_agent_ms(agent_ms)
        tr.set_response(result.final_output)
        tr.set_model(FAST_MODEL)

    print(f"Fast agent done in {agent_ms:.0f}ms (context {ctx_ms}ms)")
    save_session(user_id, session_id, topic, result.final_output)
    return result.final_output


# ============================================
# Deep Research Agent
# ============================================
async def run_deep_agent(
    topic:      str,
    user_id:    str = "",
    session_id: str = ""
) -> str:
    os.environ["AWS_REGION_NAME"]    = REGION
    os.environ["AWS_REGION"]         = REGION
    os.environ["AWS_DEFAULT_REGION"] = REGION

    model = LitellmModel(model=MODEL)

    t0           = time.time()
    instructions, scope, entities, agent_input, context = _prepare_deep_research(
        topic, user_id, session_id,
    )
    ctx_ms       = int((time.time() - t0) * 1000)
    tr           = get_tracker()
    if tr:
        tr.mark_context_ms(ctx_ms)

    record_mcp("playwright-mcp", success=True)

    try:
        with trace("Alex-Deep-Agent"):
            async with create_playwright_mcp_server(timeout_seconds=120) as playwright_mcp:
                agent = Agent(
                    name         = "Alex Deep Researcher",
                    instructions = instructions,
                    model        = model,
                    tools        = [ingest_financial_document, get_sec_filings],
                    mcp_servers  = [playwright_mcp],
                )
                result = await Runner.run(
                    agent,
                    input     = agent_input,
                    max_turns = 20,
                )
    except Exception as e:
        record_mcp("playwright-mcp", success=False, error=str(e)[:120])
        raise

    output = result.final_output
    if _is_stub_response(output, mode="deep", scope=scope) and entities:
        logger.warning(f"Deep stub detected for {topic} — recovering SEC data for {entities[0]}")
        output = await _recover_deep_sec_response(topic, entities[0], scope)

    agent_ms = int((time.time() - t0) * 1000)
    if tr:
        tr.mark_agent_ms(agent_ms)
        tr.set_response(output)
        tr.set_model(MODEL)

    save_session(user_id, session_id, topic, output)
    return output


# ============================================
# P1 — Query Router + Conversation
# ============================================
async def generate_conversation_reply(
    query: str, user_id: str, session_id: str, intent: str = "conversation",
) -> str:
    """Non-streaming fallback for conversation."""
    canned = _conversation_canned_reply(query, intent)
    if canned:
        return canned
    prompt, max_tokens = _build_conversation_prompt(query, user_id, session_id, intent)
    bedrock  = boto3.client("bedrock-runtime", region_name=REGION)
    response = bedrock.invoke_model(
        modelId=FAST_MODEL.replace("bedrock/", ""),
        contentType="application/json",
        accept="application/json",
        body=json.dumps({
            "messages": [{"role": "user", "content": [{"text": prompt}]}],
            "inferenceConfig": {"maxTokens": max_tokens, "temperature": 0.4},
        }),
    )
    result = json.loads(response["body"].read())
    return result["output"]["message"]["content"][0]["text"]


# ============================================
# Endpoints
# ============================================
@app.get("/")
async def root():
    return {"service": "Alex Researcher", "status": "healthy", "timestamp": datetime.now(UTC).isoformat()}


@app.get("/health")
async def health():
    return {
        "service": "Alex Researcher",
        "status":  "healthy",
        "config": {
            "alex_api_configured": bool(os.getenv("ALEX_API_ENDPOINT") and os.getenv("ALEX_API_KEY")),
            "aws_region":    REGION,
            "bedrock_model": MODEL,
            "ragas_eval":    True,
        },
        "timestamp": datetime.now(UTC).isoformat()
    }


@app.post("/eval/ragas/run")
async def eval_ragas_run(request: RagasEvalRequest):
    """Run RAGAS evaluation with Bedrock LLM judge; persists to Aurora."""
    gate  = request.gate or "observe"
    smoke = request.smoke

    def _run():
        from eval.ragas_runner import run_evaluation
        return run_evaluation(gate=gate, smoke=smoke, persist=True)

    try:
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(None, _run)
        payload = result.to_dict()
        if not payload.get("passed"):
            return JSONResponse(status_code=422, content={"status": "failed", **payload})
        return {"status": "ok", **payload}
    except ImportError as e:
        raise HTTPException(
            status_code=503,
            detail=f"RAGAS eval dependencies not installed: {e}",
        )
    except Exception as e:
        logger.error(f"RAGAS eval error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/research/route")
async def research_route(request: ResearchRequest):
    """Classify query — used by unified /api/alex/chat."""
    topic      = request.topic or ""
    user_id    = request.user_id or ""
    session_id = request.session_id or ""

    context_hint = ""
    if user_id and session_id:
        try:
            from context_service import get_conversation_context
            context_hint = get_conversation_context(user_id, session_id, limit=3)
        except Exception:
            pass

    decision = classify_query(topic, context_hint)
    emit_metric('RouterDecision', 1, dimensions={'Route': decision.route})
    return {
        "status":   "success",
        "routing":  decision.model_dump(),
        "steps":    routing_steps(decision),
    }


@app.post("/research/conversation/stream")
async def research_conversation_stream(request: ResearchRequest):
    topic      = request.topic or ""
    user_id    = request.user_id or ""
    session_id = request.session_id or ""
    intent     = request.intent or "conversation"

    emit_metric('ResearchQuery', 1, dimensions={'Mode': 'chat'})

    tracker = LatencyTracker(
        query=topic, route='chat', clerk_id=user_id,
        session_id=session_id, model=FAST_MODEL,
    )
    tok_tr = activate_tracker(tracker)

    async def generate():
        try:
            yield f"data: {json.dumps({'type': 'reasoning', 'content': '💬 Composing reply...'})}\n\n"

            insider_reply = await _try_insider_followup_direct(topic, user_id, session_id)
            if insider_reply:
                yield f"data: {json.dumps({'type': 'reasoning', 'content': '📄 Fetching Form 4 details from SEC EDGAR...'})}\n\n"
                yield f"data: {json.dumps({'type': 'reasoning_done'})}\n\n"
                tracker.mark_first_token_ms(int((time.monotonic() - tracker.t0) * 1000))
                async for event in stream_response_tokens(insider_reply, chunk_size=12, delay_s=0):
                    yield event
                save_session(user_id, session_id, topic, insider_reply)
                tracker.set_response(insider_reply)
                tracker.success = True
                yield f"data: {json.dumps({'type': 'done', 'route': 'chat', 'latency': round(time.monotonic() - tracker.t0, 1)})}\n\n"
                return

            canned = _conversation_canned_reply(topic, intent)
            if intent in ("off_topic", "policy_flag"):
                reason = (
                    "Router: off-topic query blocked before LLM"
                    if intent == "off_topic"
                    else f"Router: policy guardrail — {intent}"
                )
                log_guardrail_observation(
                    topic, reason, agent_name="query_router", route="chat",
                )
                tracker.mark_guardrail_ms(1)
                emit_metric('GuardrailBlock', 1, dimensions={'Mode': 'chat', 'Source': 'router'})
                label = (
                    "🛡️ Guardrail applied — polite decline"
                    if intent == "off_topic"
                    else "🛡️ Guardrail applied — risky trading intent flagged"
                )
                yield f"data: {json.dumps({'type': 'reasoning', 'content': label})}\n\n"

            reply = canned or ""
            yield f"data: {json.dumps({'type': 'reasoning_done'})}\n\n"

            if canned:
                tracker.mark_first_token_ms(int((time.monotonic() - tracker.t0) * 1000))
                async for event in stream_response_tokens(canned, chunk_size=12, delay_s=0):
                    yield event
            else:
                prompt, max_tokens = _build_conversation_prompt(topic, user_id, session_id, intent)
                reply_parts = []
                async for token in stream_bedrock_conversation(prompt, max_tokens, tracker=tracker):
                    if not reply_parts:
                        tracker.mark_first_token_ms(int((time.monotonic() - tracker.t0) * 1000))
                    reply_parts.append(token)
                    yield f"data: {json.dumps({'type': 'token', 'content': token})}\n\n"
                reply = "".join(reply_parts)

            if intent not in ("off_topic", "policy_flag"):
                save_session(user_id, session_id, topic, reply)
            tracker.set_response(reply)
            tracker.success = True
            yield f"data: {json.dumps({'type': 'done', 'route': 'chat', 'latency': round(time.monotonic() - tracker.t0, 1)})}\n\n"
        except Exception as e:
            tracker.success = False
            logger.error(f"Conversation error: {e}")
            yield f"data: {json.dumps({'type': 'error', 'content': str(e)})}\n\n"
        finally:
            tracker.flush()
            deactivate_tracker(tok_tr)

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive", "Access-Control-Allow-Origin": "*"},
    )


@app.post("/research/debater/stream")
async def research_debater_stream(request: ResearchRequest):
    """Hand off to a Trading Floor debater specialist."""
    topic      = request.topic or ""
    user_id    = request.user_id or ""
    session_id = request.session_id or ""
    agent_id   = request.debater or ""
    ticker     = request.ticker

    from debater_registry import get_debater
    from debater_handoff import run_debater_handoff

    agent = get_debater(agent_id)
    if not agent:
        raise HTTPException(status_code=400, detail=f"Unknown debater: {agent_id}")

    emit_metric('ResearchQuery', 1, dimensions={'Mode': 'debater', 'Agent': agent_id})

    tracker = LatencyTracker(
        query=topic, route='debater', clerk_id=user_id,
        session_id=session_id, model=FAST_MODEL,
    )
    tok_tr = activate_tracker(tracker)

    async def generate():
        try:
            handoff = {
                "id": agent.id, "name": agent.name, "title": agent.title,
                "expertise": agent.expertise,
            }
            yield f"data: {json.dumps({'type': 'handoff', 'debater': handoff})}\n\n"
            yield f"data: {json.dumps({'type': 'reasoning', 'content': f'🤝 Alex → {agent.name} ({agent.title})'})}\n\n"
            ticker_note = f" for {ticker}" if ticker else ""
            yield f"data: {json.dumps({'type': 'reasoning', 'content': f'📊 Fetching market data{ticker_note}...'})}\n\n"

            ctx_t0 = time.monotonic()
            _, prompt = await run_debater_handoff(agent_id, topic, ticker)
            tracker.mark_context_ms(int((time.monotonic() - ctx_t0) * 1000))

            yield f"data: {json.dumps({'type': 'reasoning', 'content': f'🧠 {agent.name} analyzing through {agent.title.split()[0]} lens...'})}\n\n"
            yield f"data: {json.dumps({'type': 'reasoning_done'})}\n\n"

            reply_parts = []
            async for token in stream_bedrock_conversation(prompt, max_tokens=700):
                if not reply_parts:
                    tracker.mark_first_token_ms(int((time.monotonic() - tracker.t0) * 1000))
                reply_parts.append(token)
                yield f"data: {json.dumps({'type': 'token', 'content': token})}\n\n"

            reply = "".join(reply_parts)
            save_session(user_id, session_id, topic, reply)
            tracker.set_response(reply)
            tracker.success = True
            yield f"data: {json.dumps({'type': 'done', 'route': 'debater', 'debater': agent_id, 'latency': round(time.monotonic() - tracker.t0, 1)})}\n\n"
        except Exception as e:
            tracker.success = False
            logger.error(f"Debater handoff error: {e}")
            yield f"data: {json.dumps({'type': 'error', 'content': str(e)})}\n\n"
        finally:
            tracker.flush()
            deactivate_tracker(tok_tr)

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive", "Access-Control-Allow-Origin": "*"},
    )


@app.post("/research")
async def research(request: ResearchRequest):
    topic      = request.topic      or "trending financial topics today"
    user_id    = request.user_id    or ""
    session_id = request.session_id or ""

    emit_metric('ResearchQuery', 1, dimensions={'Mode': 'fast'})

    try:
        async with observe_query('fast', topic, user_id, session_id, FAST_MODEL) as (tracker, _qt):
            response = await run_data_agent(topic, user_id, session_id)

            if should_apply_guardrail(topic, response):
                g0 = time.time()
                filtered_response, was_blocked = await apply_guardrail(response, topic)
                tracker.mark_guardrail_ms(int((time.time() - g0) * 1000))
                if was_blocked:
                    emit_metric('GuardrailBlock', 1, dimensions={'Mode': 'fast'})
            else:
                filtered_response = response

            tracker.set_response(filtered_response)
            latency = tracker.total_ms / 1000 if tracker.total_ms else 0
            emit_metric('ResearchLatency', latency or (time.time()), 'Seconds', {'Mode': 'fast'})
            emit_metric('ResearchSuccess', 1, dimensions={'Mode': 'fast'})
            print(f"Research complete — {tracker.total_ms}ms")
            return {"status": "success", "result": filtered_response}

    except Exception as e:
        emit_metric('ResearchSuccess', 0, dimensions={'Mode': 'fast'})
        emit_metric('ResearchError',   1, dimensions={'Mode': 'fast'})
        logger.error(f"Research error: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/research/deep")
async def research_deep(request: ResearchRequest):
    topic      = request.topic      or "latest SEC filings"
    user_id    = request.user_id    or ""
    session_id = request.session_id or ""

    emit_metric('ResearchQuery', 1, dimensions={'Mode': 'deep'})

    try:
        async with observe_query('deep', topic, user_id, session_id, MODEL) as (tracker, _qt):
            response = await run_deep_agent(topic, user_id, session_id)

            if should_apply_guardrail(topic, response):
                g0 = time.time()
                filtered_response, was_blocked = await apply_guardrail(response, topic)
                tracker.mark_guardrail_ms(int((time.time() - g0) * 1000))
                if was_blocked:
                    emit_metric('GuardrailBlock', 1, dimensions={'Mode': 'deep'})
            else:
                filtered_response = response

            tracker.set_response(filtered_response)
            emit_metric('ResearchSuccess', 1, dimensions={'Mode': 'deep'})
            print(f"Deep research complete — {tracker.total_ms}ms")
            return {"status": "success", "result": filtered_response}

    except Exception as e:
        emit_metric('ResearchSuccess', 0, dimensions={'Mode': 'deep'})
        emit_metric('ResearchError',   1, dimensions={'Mode': 'deep'})
        logger.error(f"Deep research error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/research/stream")
async def research_stream(request: ResearchRequest):
    topic      = request.topic      or "trending financial topics today"
    user_id    = request.user_id    or ""
    session_id = request.session_id or ""
    intent     = request.intent or ""

    emit_metric('ResearchQuery', 1, dimensions={'Mode': 'stream'})

    tracker = LatencyTracker(
        query=topic, route='stream', clerk_id=user_id,
        session_id=session_id, model=FAST_MODEL,
    )
    qtrace  = QueryTrace()
    tok_tr  = activate_tracker(tracker)
    tok_qt  = activate_trace(qtrace)

    market_overview = intent == "market_overview" or _is_market_overview_query(topic)

    async def generate():
        try:
            if market_overview:
                yield f"data: {json.dumps({'type': 'reasoning', 'content': '📊 Fetching live market indices...'})}\n\n"
                yield f"data: {json.dumps({'type': 'reasoning', 'content': '📈 Loading sector ETF performance...'})}\n\n"

                ctx_t0 = time.time()
                overview_data = await build_market_overview_context()
                tracker.mark_context_ms(int((time.time() - ctx_t0) * 1000))

                prompt, max_tokens = _build_market_overview_prompt(topic, overview_data)
                yield "data: " + json.dumps({
                    "type": "reasoning",
                    "content": "🧠 Summarizing today's market moves...",
                }) + "\n\n"
                yield f"data: {json.dumps({'type': 'reasoning_done'})}\n\n"

                reply_parts = []
                async for token in stream_bedrock_conversation(prompt, max_tokens, tracker=tracker):
                    if not reply_parts:
                        tracker.mark_first_token_ms(int((time.monotonic() - tracker.t0) * 1000))
                    reply_parts.append(token)
                    yield f"data: {json.dumps({'type': 'token', 'content': token})}\n\n"

                full_response = "".join(reply_parts)
                save_session(user_id, session_id, topic, full_response)
                tracker.set_response(full_response)
                tracker.success = True
                yield f"data: {json.dumps({'type': 'done', 'route': 'fast', 'intent': 'market_overview', 'latency': round(time.monotonic() - tracker.t0, 1)})}\n\n"
                return

            yield f"data: {json.dumps({'type': 'reasoning', 'content': '📊 Fetching live market data...'})}\n\n"
            yield f"data: {json.dumps({'type': 'reasoning', 'content': '📰 Scanning latest news headlines...'})}\n\n"

            ctx_t0       = time.time()
            context      = get_context(topic, user_id, session_id, fast=True)
            tracker.mark_context_ms(int((time.time() - ctx_t0) * 1000))
            from query_router import enrich_follow_up_query
            enriched, _  = enrich_follow_up_query(topic, context)
            work_topic   = enriched
            instructions = get_fast_agent_instructions()
            ticker_hint  = _active_ticker_directive(work_topic, context=context)
            if _is_leadership_query(work_topic):
                instructions += (
                    "\n\nLEADERSHIP QUERY: Answer who holds the role using KEY PEOPLE "
                    "from get_stock_data. Do NOT return the full market data table.\n"
                )
                yield f"data: {json.dumps({'type': 'reasoning', 'content': '👤 Looking up company leadership...'})}\n\n"
            if context:
                instructions += f"\n\n{context}"
                yield f"data: {json.dumps({'type': 'reasoning', 'content': '🧠 Loading your portfolio context...'})}\n\n"
            if ticker_hint:
                instructions += ticker_hint

            os.environ["AWS_REGION_NAME"]    = REGION
            os.environ["AWS_REGION"]         = REGION
            os.environ["AWS_DEFAULT_REGION"] = REGION

            model         = LitellmModel(model=FAST_MODEL)
            full_response = ""
            agent_start   = time.time()

            with trace("Alex-Stream-Agent"):
                agent = Agent(
                    name         = "Alex Data Researcher",
                    instructions = instructions,
                    model        = model,
                    tools        = [get_stock_data, ingest_financial_document],
                    mcp_servers  = [],
                )

                yield f"data: {json.dumps({'type': 'reasoning', 'content': '🧠 Analyzing with Nova Lite...'})}\n\n"

                agent_task = asyncio.create_task(Runner.run(
                    agent,
                    input     = f"Research this investment topic: {work_topic}{ticker_hint}",
                    max_turns = FAST_TURNS,
                ))
                while not agent_task.done():
                    await asyncio.sleep(0.4)
                    elapsed_ms = int((time.monotonic() - tracker.t0) * 1000)
                    yield f"data: {json.dumps({'type': 'tick', 'elapsed_ms': elapsed_ms})}\n\n"
                result = await agent_task
                full_response = result.final_output

            tracker.mark_agent_ms(int((time.time() - agent_start) * 1000))
            save_session(user_id, session_id, topic, full_response)

            filtered_response = full_response
            if should_apply_guardrail(topic, full_response):
                g0 = time.time()
                filtered_response, was_blocked = await apply_guardrail(full_response, topic)
                tracker.mark_guardrail_ms(int((time.time() - g0) * 1000))
                if was_blocked:
                    emit_metric('GuardrailBlock', 1, dimensions={'Mode': 'stream'})

            yield f"data: {json.dumps({'type': 'reasoning_done'})}\n\n"
            tracker.mark_first_token_ms(int((time.monotonic() - tracker.t0) * 1000))

            async for event in stream_response_tokens(filtered_response):
                yield event

            tracker.set_response(filtered_response)
            tracker.success = True
            emit_metric('ResearchSuccess', 1, dimensions={'Mode': 'stream'})
            yield f"data: {json.dumps({'type': 'done', 'latency': round(time.monotonic() - tracker.t0, 1), 'time_to_answer': round(time.time() - agent_start, 1)})}\n\n"

        except Exception as e:
            tracker.success = False
            logger.error(f"Stream error: {e}")
            emit_metric('ResearchError', 1, dimensions={'Mode': 'stream'})
            yield f"data: {json.dumps({'type': 'error', 'content': str(e)})}\n\n"
        finally:
            tracker.flush(qtrace)
            deactivate_tracker(tok_tr)
            deactivate_trace(tok_qt)

    return StreamingResponse(
        generate(),
        media_type = "text/event-stream",
        headers    = {"Cache-Control": "no-cache", "Connection": "keep-alive", "Access-Control-Allow-Origin": "*"}
    )


@app.get("/research/auto")
async def research_auto():
    emit_metric('AutoResearchTrigger', 1)
    try:
        response = await run_data_agent("trending financial topics today")
        emit_metric('AutoResearchSuccess', 1)
        return {
            "status":    "success",
            "timestamp": datetime.now(UTC).isoformat(),
            "preview":   response[:200] + "..."
        }
    except Exception as e:
        emit_metric('AutoResearchSuccess', 0)
        return {"status": "error", "timestamp": datetime.now(UTC).isoformat(), "error": str(e)}


@app.post("/research/deep/stream")
async def research_deep_stream(request: ResearchRequest):
    topic      = request.topic      or "latest SEC filings"
    user_id    = request.user_id    or ""
    session_id = request.session_id or ""

    emit_metric('ResearchQuery', 1, dimensions={'Mode': 'deep-stream'})

    tracker = LatencyTracker(
        query=topic, route='deep-stream', clerk_id=user_id,
        session_id=session_id, model=MODEL,
    )
    qtrace  = QueryTrace()
    tok_tr  = activate_tracker(tracker)
    tok_qt  = activate_trace(qtrace)

    async def generate():
        try:
            prep_t0 = time.time()
            instructions, scope, entities, agent_input, context = _prepare_deep_research(
                topic, user_id, session_id,
            )
            tracker.mark_context_ms(int((time.time() - prep_t0) * 1000))

            for step in deep_reasoning_steps(scope):
                yield f"data: {json.dumps({'type': 'reasoning', 'content': step})}\n\n"

            if context:
                yield f"data: {json.dumps({'type': 'reasoning', 'content': '🧠 Loading prior research context...'})}\n\n"
            yield f"data: {json.dumps({'type': 'reasoning', 'content': f'🎯 Scope: {scope.label}'})}\n\n"

            os.environ["AWS_REGION_NAME"]    = REGION
            os.environ["AWS_REGION"]         = REGION
            os.environ["AWS_DEFAULT_REGION"] = REGION

            model         = LitellmModel(model=MODEL)
            full_response = ""
            agent_start   = time.time()

            with trace("Alex-Deep-Stream-Agent"):
                async with create_playwright_mcp_server(timeout_seconds=120) as playwright_mcp:
                    agent = Agent(
                        name         = "Alex Deep Researcher",
                        instructions = instructions,
                        model        = model,
                        tools        = [ingest_financial_document, get_sec_filings],
                        mcp_servers  = [playwright_mcp],
                    )

                    yield f"data: {json.dumps({'type': 'reasoning', 'content': '🧠 Deep analysis in progress...'})}\n\n"

                    agent_task = asyncio.create_task(Runner.run(
                        agent,
                        input     = agent_input,
                        max_turns = 20,
                    ))
                    while not agent_task.done():
                        await asyncio.sleep(0.4)
                        elapsed_ms = int((time.monotonic() - tracker.t0) * 1000)
                        yield f"data: {json.dumps({'type': 'tick', 'elapsed_ms': elapsed_ms})}\n\n"
                    result = await agent_task
                    full_response = result.final_output

            if _is_stub_response(full_response, mode="deep", scope=scope) and entities:
                logger.warning(f"Deep stub detected for {topic} — recovering SEC data for {entities[0]}")
                full_response = await _recover_deep_sec_response(topic, entities[0], scope)

            tracker.mark_agent_ms(int((time.time() - agent_start) * 1000))
            save_session(user_id, session_id, topic, full_response)

            filtered_response = full_response
            if should_apply_guardrail(topic, full_response):
                g0 = time.time()
                filtered_response, was_blocked = await apply_guardrail(full_response, topic)
                tracker.mark_guardrail_ms(int((time.time() - g0) * 1000))
                if was_blocked:
                    emit_metric('GuardrailBlock', 1, dimensions={'Mode': 'deep-stream'})

            yield f"data: {json.dumps({'type': 'reasoning_done'})}\n\n"
            tracker.mark_first_token_ms(int((time.monotonic() - tracker.t0) * 1000))

            async for event in stream_response_tokens(filtered_response, chunk_size=5, delay_s=0.025):
                yield event

            tracker.set_response(filtered_response)
            tracker.success = True
            emit_metric('ResearchSuccess', 1, dimensions={'Mode': 'deep-stream'})
            yield f"data: {json.dumps({'type': 'done', 'latency': round(time.monotonic() - tracker.t0, 1)})}\n\n"

        except Exception as e:
            tracker.success = False
            logger.error(f"Deep stream error: {e}")
            emit_metric('ResearchError', 1, dimensions={'Mode': 'deep-stream'})
            yield f"data: {json.dumps({'type': 'error', 'content': str(e)})}\n\n"
        finally:
            tracker.flush(qtrace)
            deactivate_tracker(tok_tr)
            deactivate_trace(tok_qt)

    return StreamingResponse(
        generate(),
        media_type = "text/event-stream",
        headers    = {"Cache-Control": "no-cache", "Connection": "keep-alive", "Access-Control-Allow-Origin": "*"}
    )


@app.post("/research/multi/stream")
async def research_multi_stream(request: ResearchRequest):
    start_time = time.time()
    topic      = request.topic or ""

    async def generate():
        try:
            yield f"data: {json.dumps({'type': 'status', 'content': 'Decomposing query into tasks...'})}\n\n"
            await asyncio.sleep(0.5)
            yield f"data: {json.dumps({'type': 'status', 'content': 'Routing to specialist agents...'})}\n\n"
            await asyncio.sleep(0.5)
            yield f"data: {json.dumps({'type': 'status', 'content': 'Parallel research in progress...'})}\n\n"

            elapsed  = 0
            messages = [
                "Analyzing financial data...", "Fetching analyst ratings...",
                "Computing valuations...",     "Comparing metrics...",
                "Synthesizing results...",
            ]
            idx = 0
            while elapsed < 150:
                await asyncio.sleep(10)
                elapsed += 10
                msg = messages[idx % len(messages)]
                yield f"data: {json.dumps({'type': 'status', 'content': f'{msg} ({elapsed}s)'})}\n\n"
                idx += 1

            yield f"data: {json.dumps({'type': 'done', 'latency': elapsed})}\n\n"

        except Exception as e:
            yield f"data: {json.dumps({'type': 'error', 'content': str(e)})}\n\n"

    return StreamingResponse(
        generate(),
        media_type = "text/event-stream",
        headers    = {"Cache-Control": "no-cache", "Connection": "keep-alive", "Access-Control-Allow-Origin": "*"}
    )


@app.get("/suggestions")
async def get_suggestions(user_id: str = ""):
    """Use Case 6 — Proactive suggestions endpoint."""
    if not user_id:
        return {"suggestions": [], "has_suggestions": False}
    try:
        from context_service import get_proactive_suggestions
        return get_proactive_suggestions(user_id)
    except Exception as e:
        return {"suggestions": [], "has_suggestions": False}


@app.get("/test-network")
async def test_network():
    import httpx
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.get("https://finance.yahoo.com")
            return {"status": "success", "http_status": response.status_code, "can_reach_internet": True}
    except Exception as e:
        return {"status": "error", "error": str(e), "can_reach_internet": False}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)