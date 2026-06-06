"""
Alex Researcher Service — Autonomous Investment Research Agent
"""
import os
import logging
from datetime import datetime, UTC
from typing import Optional

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from dotenv import load_dotenv
from agents import Agent, Runner, trace
from agents.extensions.models.litellm_model import LitellmModel


# Suppress noisy LiteLLM warnings
logging.getLogger("LiteLLM").setLevel(logging.CRITICAL)

from prompts import get_agent_instructions, DEFAULT_RESEARCH_PROMPT
from mcp_servers import create_playwright_mcp_server
from tools import ingest_financial_document, get_stock_data, get_current_date

load_dotenv(override=True)

app = FastAPI(title="Alex Researcher Service")

from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

logger = logging.getLogger(__name__)


class ResearchRequest(BaseModel):
    topic: Optional[str] = None

class FinancialAnalysis(BaseModel):
    url: list[str] = Field(description="The URL of the pages researched where the data was found")
    date: str = Field(description="The date and time the data was found")
    numbers: list[str] = Field(description="The numbers found on the page")
    analysis: str = Field(description="The final analysis considering all urls along with output specified in the prompt")

async def run_research_agent(topic: str = None) -> FinancialAnalysis:
    """
    Core function — assembles and runs the research agent.
    """

    # Build the user query
    if topic:
        query = f"Research this investment topic: {topic}"
    else:
        query = DEFAULT_RESEARCH_PROMPT

    # Configure Bedrock region — must set all three for compatibility
    REGION = "us-east-1"
    os.environ["AWS_REGION_NAME"]    = REGION
    os.environ["AWS_REGION"]         = REGION
    os.environ["AWS_DEFAULT_REGION"] = REGION

    # Nova Pro — supports tool calling (Nova Lite does NOT)
    MODEL = "bedrock/us.amazon.nova-pro-v1:0"
    model = LitellmModel(model=MODEL)

    # Assemble and run agent
    with trace("Alex-Researcher"):
        async with create_playwright_mcp_server(timeout_seconds=120) as playwright_mcp:

            agent = Agent(
    name="Alex Investment Researcher",
    instructions=get_agent_instructions(),
    model=model,
    tools=[
        ingest_financial_document,
        get_stock_data,
        get_current_date,
    ],
    mcp_servers=[playwright_mcp],
)

            result = await Runner.run(
                agent,
                input=query,
                max_turns=15,
            )

    return result.final_output


# ─── Endpoints ───────────────────────────────────────────────

@app.get("/")
async def root():
    """Root health check."""
    return {
        "service":   "Alex Researcher",
        "status":    "healthy",
        "timestamp": datetime.now(UTC).isoformat()
    }


@app.get("/health")
async def health():
    """Detailed health check — used by ALB."""
    return {
        "service": "Alex Researcher",
        "status":  "healthy",
        "config": {
            "alex_api_configured": bool(
                os.getenv("ALEX_API_ENDPOINT") and
                os.getenv("ALEX_API_KEY")
            ),
            "aws_region":    os.environ.get("AWS_DEFAULT_REGION", "not set"),
            "bedrock_model": "bedrock/us.amazon.nova-pro-v1:0",
        },
        "timestamp": datetime.now(UTC).isoformat()
    }


@app.post("/research")
async def research(request: ResearchRequest):
    """
    Run research agent on a specific topic.
    If no topic provided, agent picks a trending topic.
    """
    try:
        response = await run_research_agent(request.topic)
        return {"status": "success", "result": response}
    except Exception as e:
        logger.error(f"Research error: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/research/auto")
async def research_auto():
    """
    Automated research endpoint.
    Called by EventBridge scheduler for periodic updates.
    """
    try:
        response = await run_research_agent(topic=None)
        return {
            "status":    "success",
            "timestamp": datetime.now(UTC).isoformat(),
            "preview":   response[:200] + "..." if len(response) > 200 else response
        }
    except Exception as e:
        logger.error(f"Auto research error: {e}")
        return {
            "status":    "error",
            "timestamp": datetime.now(UTC).isoformat(),
            "error":     str(e)
        }
@app.get("/test-network")
async def test_network():
    """Test outbound internet connectivity."""
    import httpx
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.get("https://finance.yahoo.com")
            return {
                "status": "success",
                "http_status": response.status_code,
                "can_reach_internet": True
            }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
            "can_reach_internet": False
        }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)