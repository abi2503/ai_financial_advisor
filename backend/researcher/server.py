"""
Alex Researcher Service — Autonomous Investment Research Agent
Guide 8: Added CloudWatch metrics for observability
"""
import os
import time
import logging
import boto3
from datetime import datetime, UTC
from typing import Optional

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from dotenv import load_dotenv
from agents import Agent, Runner, trace
from agents.extensions.models.litellm_model import LitellmModel
from fastapi.middleware.cors import CORSMiddleware
import asyncio
logging.getLogger("LiteLLM").setLevel(logging.CRITICAL)

from prompts import get_agent_instructions, get_deep_research_instructions, DEFAULT_RESEARCH_PROMPT
from mcp_servers import create_playwright_mcp_server
from tools import ingest_financial_document, get_stock_data, get_sec_filings
GUARDRAIL_ID      = os.getenv("BEDROCK_GUARDRAIL_ID", "eea439luokx8")
GUARDRAIL_VERSION = os.getenv("BEDROCK_GUARDRAIL_VERSION", "1")

load_dotenv(override=True)

app = FastAPI(title="Alex Researcher Service")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

logger     = logging.getLogger(__name__)
cloudwatch = boto3.client('cloudwatch', region_name='us-east-1')

REGION = "us-east-1"
MODEL  = "bedrock/us.amazon.nova-pro-v1:0"


# ============================================
# CloudWatch Metrics
# Why: Every request emits business metrics
#      so we can monitor quality over time
# ============================================

def emit_metric(
    name:       str,
    value:      float,
    unit:       str = 'Count',
    dimensions: dict = None
):
    """
    Emit custom metric to CloudWatch.

    Why custom metrics vs default AWS metrics:
      AWS auto-tracks CPU, memory, invocations
      We need BUSINESS metrics:
        ResearchQueries     → how many per hour
        ResearchLatency     → how fast is Alex?
        ResearchSuccess     → what % succeed?
        ResearchMode        → fast vs deep usage
        IngestSuccess       → knowledge base growth
    """
    try:
        dims = [{'Name': 'Service', 'Value': 'alex-researcher'}]
        if dimensions:
            for k, v in dimensions.items():
                dims.append({'Name': k, 'Value': str(v)})

        cloudwatch.put_metric_data(
            Namespace  = 'AlexAI',
            MetricData = [{
                'MetricName': name,
                'Value':      value,
                'Unit':       unit,
                'Dimensions': dims
            }]
        )
        print(f"Metric emitted: {name}={value}")
    except Exception as e:
        print(f"Metric emission failed: {e}")


class ResearchRequest(BaseModel):
    topic: Optional[str] = None
    deep:  bool          = False


# ============================================
# Data Agent — Fast Research
# Why: No MCP servers = under Bedrock tool limit
#      Handles 95% of user queries
# ============================================

async def run_data_agent(topic: str) -> str:
    """
    Fast research agent using API tools only.
    No Playwright = no Bedrock tool count issues.
    """
    os.environ["AWS_REGION_NAME"]    = REGION
    os.environ["AWS_REGION"]         = REGION
    os.environ["AWS_DEFAULT_REGION"] = REGION

    model = LitellmModel(model=MODEL)

    with trace("Alex-Data-Agent"):
        agent = Agent(
            name         = "Alex Data Researcher",
            instructions = get_agent_instructions(),
            model        = model,
            tools        = [
                get_stock_data,
                ingest_financial_document,
            ],
            mcp_servers = [],
        )

        result = await Runner.run(
            agent,
            input     = f"Research this investment topic: {topic}",
            max_turns = 25,
        )

    return result.final_output

async def apply_guardrail(text: str) -> tuple[str, bool]:
    """
    Apply Bedrock Guardrail to agent output.
    
    Why post-processing approach:
      OpenAI Agents SDK doesn't support guardrail
      config natively. ApplyGuardrail API works
      independently of any agent framework.
    
    Returns:
      (filtered_text, was_blocked)
    """
    try:
        loop    = asyncio.get_event_loop()
        bedrock = boto3.client(
            'bedrock-runtime',
            region_name=REGION
        )

        # Run in executor since boto3 is synchronous
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
            print(f"Guardrail blocked response")
            # Emit metric for monitoring
            emit_metric('GuardrailBlock', 1)
            return (
                "I can only help with financial research topics. "
                "Please ask about stocks, markets, or investment analysis.",
                True
            )

        print(f"Guardrail passed")
        return (text, False)

    except Exception as e:
        # Fail open — if guardrail errors return original
        # Why: Better to show unfiltered than break the app
        print(f"Guardrail error (failing open): {e}")
        return (text, False)

# ============================================
# Deep Agent — SEC EDGAR Research
# Why: Playwright for documents no API provides
#      Fewer function tools to avoid tool limit
# ============================================

async def run_deep_agent(topic: str) -> str:
    """
    Deep research agent with Playwright MCP.
    Used for SEC filings, insider trading,
    earnings transcripts.
    """
    os.environ["AWS_REGION_NAME"]    = REGION
    os.environ["AWS_REGION"]         = REGION
    os.environ["AWS_DEFAULT_REGION"] = REGION

    model = LitellmModel(model=MODEL)

    with trace("Alex-Deep-Agent"):
        async with create_playwright_mcp_server(
            timeout_seconds=120
        ) as playwright_mcp:

            agent = Agent(
                name         = "Alex Deep Researcher",
                instructions = get_deep_research_instructions(),
                model        = model,
                tools        = [
                    ingest_financial_document,
                    get_sec_filings,
                ],
                mcp_servers = [playwright_mcp],
            )

            result = await Runner.run(
                agent,
                input     = f"Deep research: {topic}",
                max_turns = 20,
            )

    return result.final_output


# ============================================
# Endpoints
# ============================================

@app.get("/")
async def root():
    return {
        "service":   "Alex Researcher",
        "status":    "healthy",
        "timestamp": datetime.now(UTC).isoformat()
    }


@app.get("/health")
async def health():
    return {
        "service": "Alex Researcher",
        "status":  "healthy",
        "config": {
            "alex_api_configured": bool(
                os.getenv("ALEX_API_ENDPOINT") and
                os.getenv("ALEX_API_KEY")
            ),
            "aws_region":    REGION,
            "bedrock_model": MODEL,
        },
        "timestamp": datetime.now(UTC).isoformat()
    }


@app.post("/research")
async def research(request: ResearchRequest):
    start_time = time.time()
    topic      = request.topic or "trending financial topics today"

    emit_metric('ResearchQuery', 1, dimensions={'Mode': 'fast'})

    try:
        response = await run_data_agent(topic)

        # Apply guardrail post-processing
        filtered_response, was_blocked = await apply_guardrail(response)

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
    topic      = request.topic or "latest SEC filings"

    emit_metric('ResearchQuery', 1, dimensions={'Mode': 'deep'})

    try:
        response = await run_deep_agent(topic)
        latency  = time.time() - start_time

        # Only apply guardrail to OUTPUT not input
        # Deep research = legitimate SEC queries
        # Skip guardrail for SEC/filing queries
        sec_keywords = ['10-k', '10-q', '8-k', 'sec', 'filing', 
                        'edgar', 'insider', 'earnings', 'risk factor']
        is_sec_query = any(kw in topic.lower() for kw in sec_keywords)

        if not is_sec_query:
            filtered_response, was_blocked = await apply_guardrail(response)
            if was_blocked:
                emit_metric('GuardrailBlock', 1, dimensions={'Mode': 'deep'})
        else:
            filtered_response = response

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

@app.get("/research/auto")
async def research_auto():
    """
    Auto research — called by EventBridge scheduler.
    """
    emit_metric('AutoResearchTrigger', 1)
    try:
        response = await run_data_agent(
            "trending financial topics today"
        )
        emit_metric('AutoResearchSuccess', 1)
        return {
            "status":    "success",
            "timestamp": datetime.now(UTC).isoformat(),
            "preview":   response[:200] + "..."
        }
    except Exception as e:
        emit_metric('AutoResearchSuccess', 0)
        return {
            "status":    "error",
            "timestamp": datetime.now(UTC).isoformat(),
            "error":     str(e)
        }


@app.get("/test-network")
async def test_network():
    import httpx
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.get("https://finance.yahoo.com")
            return {
                "status":             "success",
                "http_status":        response.status_code,
                "can_reach_internet": True
            }
    except Exception as e:
        return {
            "status":             "error",
            "error":              str(e),
            "can_reach_internet": False
        }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)