import os
import logging
import httpx
from agents import function_tool

logger=logging.getLogger(__name__)

@function_tool
def get_current_date() -> str:
    """
    Get today's exact date and time.
    Call this first before any research to timestamp your work.
    Returns current date so you can verify data is recent.
    """
    from datetime import datetime, UTC
    now = datetime.now(UTC)
    return f"Current date and time: {now.strftime('%B %d, %Y at %H:%M UTC')}"

@function_tool
async def ingest_financial_document(content: str, topic: str) -> str:
    """
    Store financial research in the Alex knowledge base.
    Call this after completing research to save findings.

    Args:
        content: The research analysis text to store
        topic:   Short label describing what was researched

    Returns:
        Success or error message
    """

    api_endpoint = os.getenv("ALEX_API_ENDPOINT")
    api_key      = os.getenv("ALEX_API_KEY")

    # Log what we have for debugging
    logger.info(f"API Endpoint: {api_endpoint}")
    logger.info(f"API Key set: {bool(api_key)}")
    logger.info(f"Content length: {len(content) if content else 0}")
    logger.info(f"Topic: {topic}")

    if not api_endpoint or not api_key:
        logger.error("Missing API endpoint or key")
        return "Error: ALEX_API_ENDPOINT or ALEX_API_KEY not configured"

    try:
        async with httpx.AsyncClient(timeout=30) as client:
            logger.info(f"Posting to: {api_endpoint}")
            response = await client.post(
                api_endpoint,
                headers={
                    "Content-Type": "application/json",
                    "x-api-key":    api_key
                },
                json={
                    "content": content,
                    "topic":   topic
                }
            )
            logger.info(f"Response status: {response.status_code}")
            logger.info(f"Response body: {response.text[:200]}")

        if response.status_code == 200:
            logger.info(f"Successfully stored: {topic}")
            return f"Successfully stored research for topic: {topic}"
        else:
            logger.error(f"Failed: {response.status_code} {response.text}")
            return f"Failed to store research: {response.status_code} - {response.text}"

    except httpx.TimeoutException as e:
        logger.error(f"Timeout calling API: {e}")
        return f"Error: API call timed out after 30 seconds"

    except httpx.ConnectError as e:
        logger.error(f"Connection error: {e}")
        return f"Error: Could not connect to API endpoint"

    except Exception as e:
        logger.error(f"Unexpected error: {type(e).__name__}: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return f"Error storing research: {type(e).__name__}: {str(e)}"

   
    
