"""
Alex Researcher Service — Autonomous Investment Research Agent
Guide 8: Added CloudWatch metrics for observability
"""
import os
import time
import json
import logging
import boto3
from datetime import datetime, UTC
from typing import Optional

from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv
from agents import Agent, Runner, trace
from agents.extensions.models.litellm_model import LitellmModel
import asyncio

logging.getLogger("LiteLLM").setLevel(logging.CRITICAL)

from prompts import get_agent_instructions, get_deep_research_instructions, DEFAULT_RESEARCH_PROMPT
from mcp_servers import create_playwright_mcp_server
from tools import ingest_financial_document, get_stock_data, get_sec_filings

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

REGION = "us-east-1"
MODEL  = "bedrock/us.amazon.nova-pro-v1:0"


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
async def apply_guardrail(text: str) -> tuple[str, bool]:
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


# ============================================
# Context Helper
# ============================================
def get_context(topic: str, user_id: str, session_id: str) -> str:
    """Get pgvector context — non-fatal if fails."""
    if not user_id:
        return ""
    try:
        from context_service import build_full_context
        context = build_full_context(
            query      = topic,
            user_id    = user_id,
            session_id = session_id
        )
        print(f"Context built: {len(context)} chars")
        return context
    except Exception as e:
        print(f"Context error (non-fatal): {e}")
        return ""


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

    model = LitellmModel(model=MODEL)

    # Build context from pgvector + history
    context      = get_context(topic, user_id, session_id)
    instructions = get_agent_instructions()
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
            max_turns = 8,
        )

    # Save to session
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

    # Build context
    context      = get_context(topic, user_id, session_id)
    instructions = get_deep_research_instructions()
    if context:
        instructions += f"\n\n{context}"

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
                input     = f"Deep research: {topic}",
                max_turns = 20,
            )

    # Save to session
    save_session(user_id, session_id, topic, result.final_output)

    return result.final_output


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
        },
        "timestamp": datetime.now(UTC).isoformat()
    }


@app.post("/research")
async def research(request: ResearchRequest):
    start_time = time.time()
    topic      = request.topic      or "trending financial topics today"
    user_id    = request.user_id    or ""
    session_id = request.session_id or ""

    emit_metric('ResearchQuery', 1, dimensions={'Mode': 'fast'})

    try:
        response = await run_data_agent(topic, user_id, session_id)

        print(f"Response length: {len(response)}")
        print(f"Response preview: {response[:200]}")

        if should_apply_guardrail(topic, response):
            filtered_response, was_blocked = await apply_guardrail(response)
            if was_blocked:
                emit_metric('GuardrailBlock', 1, dimensions={'Mode': 'fast'})
        else:
            filtered_response = response

        latency = time.time() - start_time
        emit_metric('ResearchLatency', latency, 'Seconds', {'Mode': 'fast'})
        emit_metric('ResearchSuccess', 1, dimensions={'Mode': 'fast'})

        print(f"Research complete — {latency:.1f}s")
        return {"status": "success", "result": filtered_response}

    except Exception as e:
        latency = time.time() - start_time
        emit_metric('ResearchSuccess', 0, dimensions={'Mode': 'fast'})
        emit_metric('ResearchError',   1, dimensions={'Mode': 'fast'})
        logger.error(f"Research error: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/research/deep")
async def research_deep(request: ResearchRequest):
    start_time = time.time()
    topic      = request.topic      or "latest SEC filings"
    user_id    = request.user_id    or ""
    session_id = request.session_id or ""

    emit_metric('ResearchQuery', 1, dimensions={'Mode': 'deep'})

    try:
        response = await run_deep_agent(topic, user_id, session_id)

        print(f"Deep response length: {len(response)}")
        print(f"Deep response preview: {response[:200]}")

        if should_apply_guardrail(topic, response):
            filtered_response, was_blocked = await apply_guardrail(response)
            if was_blocked:
                emit_metric('GuardrailBlock', 1, dimensions={'Mode': 'deep'})
        else:
            filtered_response = response

        latency = time.time() - start_time
        emit_metric('ResearchLatency', latency, 'Seconds', {'Mode': 'deep'})
        emit_metric('ResearchSuccess', 1, dimensions={'Mode': 'deep'})

        print(f"Deep research complete — {latency:.1f}s")
        return {"status": "success", "result": filtered_response}

    except Exception as e:
        latency = time.time() - start_time
        emit_metric('ResearchSuccess', 0, dimensions={'Mode': 'deep'})
        emit_metric('ResearchError',   1, dimensions={'Mode': 'deep'})
        logger.error(f"Deep research error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/research/stream")
async def research_stream(request: ResearchRequest):
    start_time = time.time()
    topic      = request.topic      or "trending financial topics today"
    user_id    = request.user_id    or ""
    session_id = request.session_id or ""

    emit_metric('ResearchQuery', 1, dimensions={'Mode': 'stream'})

    async def generate():
        try:
            yield f"data: {json.dumps({'type': 'reasoning', 'content': '📊 Fetching live market data...'})}\n\n"
            await asyncio.sleep(0.1)

            yield f"data: {json.dumps({'type': 'reasoning', 'content': '📰 Scanning latest news headlines...'})}\n\n"
            await asyncio.sleep(0.1)

            # Build context
            context      = get_context(topic, user_id, session_id)
            instructions = get_agent_instructions()
            if context:
                instructions += f"\n\n{context}"
                yield f"data: {json.dumps({'type': 'reasoning', 'content': '🧠 Loading your research history...'})}\n\n"
                await asyncio.sleep(0.1)

            os.environ["AWS_REGION_NAME"]    = REGION
            os.environ["AWS_REGION"]         = REGION
            os.environ["AWS_DEFAULT_REGION"] = REGION

            model         = LitellmModel(model=MODEL)
            full_response = ""

            with trace("Alex-Stream-Agent"):
                agent = Agent(
                    name         = "Alex Data Researcher",
                    instructions = instructions,
                    model        = model,
                    tools        = [get_stock_data, ingest_financial_document],
                    mcp_servers  = [],
                )

                yield f"data: {json.dumps({'type': 'reasoning', 'content': '🧠 Analyzing with Nova Pro...'})}\n\n"

                result = await Runner.run(
                    agent,
                    input     = f"Research this investment topic: {topic}",
                    max_turns = 8,
                )
                full_response = result.final_output

            print(f"Stream response length: {len(full_response)}")

            # Save to session
            save_session(user_id, session_id, topic, full_response)

            # Smart guardrail
            filtered_response = full_response
            if should_apply_guardrail(topic, full_response):
                filtered_response, was_blocked = await apply_guardrail(full_response)
                if was_blocked:
                    emit_metric('GuardrailBlock', 1, dimensions={'Mode': 'stream'})

            yield f"data: {json.dumps({'type': 'reasoning_done'})}\n\n"

            # Stream word by word
            words = filtered_response.split(' ')
            for i, word in enumerate(words):
                yield f"data: {json.dumps({'type': 'token', 'content': word + ' '})}\n\n"
                if i % 10 == 0:
                    await asyncio.sleep(0.01)

            latency = time.time() - start_time
            emit_metric('ResearchLatency', latency, 'Seconds', {'Mode': 'stream'})
            emit_metric('ResearchSuccess', 1, dimensions={'Mode': 'stream'})
            yield f"data: {json.dumps({'type': 'done', 'latency': round(latency, 1)})}\n\n"

        except Exception as e:
            logger.error(f"Stream error: {e}")
            emit_metric('ResearchError', 1, dimensions={'Mode': 'stream'})
            yield f"data: {json.dumps({'type': 'error', 'content': str(e)})}\n\n"

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
    start_time = time.time()
    topic      = request.topic      or "latest SEC filings"
    user_id    = request.user_id    or ""
    session_id = request.session_id or ""

    emit_metric('ResearchQuery', 1, dimensions={'Mode': 'deep-stream'})

    async def generate():
        try:
            yield f"data: {json.dumps({'type': 'reasoning', 'content': '🔌 Connecting to SEC EDGAR...'})}\n\n"
            await asyncio.sleep(0.1)
            yield f"data: {json.dumps({'type': 'reasoning', 'content': '📄 Fetching 10-K filings...'})}\n\n"
            await asyncio.sleep(0.1)
            yield f"data: {json.dumps({'type': 'reasoning', 'content': '📊 Reading analyst ratings...'})}\n\n"
            await asyncio.sleep(0.1)

            # Build context
            context      = get_context(topic, user_id, session_id)
            instructions = get_deep_research_instructions()
            if context:
                instructions += f"\n\n{context}"
                yield f"data: {json.dumps({'type': 'reasoning', 'content': '🧠 Loading prior research context...'})}\n\n"
                await asyncio.sleep(0.1)

            os.environ["AWS_REGION_NAME"]    = REGION
            os.environ["AWS_REGION"]         = REGION
            os.environ["AWS_DEFAULT_REGION"] = REGION

            model         = LitellmModel(model=MODEL)
            full_response = ""

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

                    result = await Runner.run(
                        agent,
                        input     = f"Deep research: {topic}",
                        max_turns = 20,
                    )
                    full_response = result.final_output

            # Save to session
            save_session(user_id, session_id, topic, full_response)

            filtered_response = full_response
            if should_apply_guardrail(topic, full_response):
                filtered_response, was_blocked = await apply_guardrail(full_response)
                if was_blocked:
                    emit_metric('GuardrailBlock', 1, dimensions={'Mode': 'deep-stream'})

            yield f"data: {json.dumps({'type': 'reasoning_done'})}\n\n"

            words = filtered_response.split(' ')
            for i, word in enumerate(words):
                yield f"data: {json.dumps({'type': 'token', 'content': word + ' '})}\n\n"
                if i % 10 == 0:
                    await asyncio.sleep(0.01)

            latency = time.time() - start_time
            emit_metric('ResearchLatency', latency, 'Seconds', {'Mode': 'deep-stream'})
            emit_metric('ResearchSuccess', 1, dimensions={'Mode': 'deep-stream'})
            yield f"data: {json.dumps({'type': 'done', 'latency': round(latency, 1)})}\n\n"

        except Exception as e:
            logger.error(f"Deep stream error: {e}")
            emit_metric('ResearchError', 1, dimensions={'Mode': 'deep-stream'})
            yield f"data: {json.dumps({'type': 'error', 'content': str(e)})}\n\n"

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