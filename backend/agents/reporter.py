"""
Reporter Lambda — triggered by SQS results queue.
For portfolio tasks: calls ECS fast/deep research agents, builds card digests.
For user queries: generates Bedrock reports and pushes to frontend queue.
"""
import os
import json
import boto3
import logging
from datetime import datetime, timezone

from db_helper import execute_sql

logger = logging.getLogger(__name__)
UTC    = timezone.utc

bedrock = boto3.client('bedrock-runtime', region_name='us-east-1')
sqs     = boto3.client('sqs', region_name=os.environ.get('AWS_REGION', 'us-east-1'))

ALEX_API_ENDPOINT          = os.environ.get('ALEX_API_ENDPOINT')
ALEX_API_KEY               = os.environ.get('ALEX_API_KEY')
ECS_URL                    = os.environ.get('ECS_URL', '')
RESULTS_QUEUE_URL          = os.environ.get('RESULTS_QUEUE_URL')
FRONTEND_RESULTS_QUEUE_URL = os.environ.get('FRONTEND_RESULTS_QUEUE_URL')


def generate_report(topic: str, classification: dict) -> str:
    """Generate comprehensive report using Nova Pro (fallback / user queries)."""
    category = classification.get('category', 'general')
    tickers  = classification.get('tickers', [])
    sector   = classification.get('sector', 'general')

    prompt = f"""You are Alex, a professional financial reporter.
Generate a concise research report for:
Topic:    {topic}
Category: {category}
Sector:   {sector}
Tickers:  {', '.join(tickers) if tickers else 'N/A'}
Date:     {datetime.now(UTC).strftime('%B %d, %Y')}

Structure:
1. Executive Summary (2-3 sentences)
2. Key Findings (3-5 bullet points)
3. Market Context (1 paragraph)
4. Risk Factors (2-3 points)
5. Recommendation: BUY/HOLD/SELL with one sentence reasoning

Important: This is research not financial advice."""

    response = bedrock.invoke_model(
        modelId     = "us.amazon.nova-pro-v1:0",
        contentType = "application/json",
        accept      = "application/json",
        body        = json.dumps({
            "messages": [{
                "role":    "user",
                "content": [{"text": prompt}]
            }],
            "inferenceConfig": {
                "maxTokens":   1000,
                "temperature": 0.3
            }
        })
    )
    result = json.loads(response['body'].read())
    return result['output']['message']['content'][0]['text']


def call_ecs_research(topic: str, mode: str, user_id: str, session_id: str = "") -> str:
    """Invoke ECS fast or deep research agent with live market tools."""
    import httpx

    if not ECS_URL:
        print("ECS_URL not configured — falling back to Bedrock")
        return ""

    path    = "/research" if mode == "fast" else "/research/deep"
    timeout = 300 if mode == "fast" else 540

    try:
        print(f"Calling ECS {path} for: {topic[:80]}...")
        response = httpx.post(
            f"{ECS_URL.rstrip('/')}{path}",
            json    = {"topic": topic, "user_id": user_id, "session_id": session_id},
            timeout = timeout,
        )
        if response.status_code == 200:
            data = response.json()
            result = data.get("result", "")
            print(f"ECS {mode} research: {len(result)} chars")
            return result
        print(f"ECS error {response.status_code}: {response.text[:200]}")
    except Exception as e:
        print(f"ECS call failed: {type(e).__name__}: {e}")

    return ""


def generate_card_digest(
    ticker:     str,
    company:    str,
    dimension:  str,
    dim_label:  str,
    report:     str,
    dimensions: dict,
) -> dict:
    """Synthesize a user-facing card digest from dimension research."""
    dim_summary = "\n".join(
        f"- **{k}**: {v[:300]}..."
        for k, v in dimensions.items()
        if v
    )

    prompt = f"""You are Alex, a financial advisor AI. Create a concise portfolio digest card.

Stock: {ticker} ({company})
Latest dimension researched: {dim_label}
Fresh research:
{report[:2000]}

Prior dimension summaries:
{dim_summary or 'None yet'}

Respond ONLY with valid JSON:
{{
  "headline": "One compelling headline about {ticker} (max 12 words)",
  "sentiment": "bullish|bearish|neutral",
  "digest": "3-4 sentence markdown summary with **bold** key points and bullet list of top 3 trending news items. Relevant to a holder of {ticker}.",
  "key_news": ["news item 1", "news item 2", "news item 3"]
}}

Important: This is research not financial advice. Be specific to {ticker}."""

    try:
        response = bedrock.invoke_model(
            modelId     = "us.amazon.nova-pro-v1:0",
            contentType = "application/json",
            accept      = "application/json",
            body        = json.dumps({
                "messages": [{"role": "user", "content": [{"text": prompt}]}],
                "inferenceConfig": {"maxTokens": 600, "temperature": 0.3},
            }),
        )
        result = json.loads(response['body'].read())
        text   = result['output']['message']['content'][0]['text'].strip()
        if "```" in text:
            text = text.split("```")[1]
            if text.startswith("json"):
                text = text[4:]
        return json.loads(text.strip())
    except Exception as e:
        print(f"Digest generation error: {e}")
        return {
            "headline":  f"{ticker} — {dim_label} Update",
            "sentiment": "neutral",
            "digest":    report[:500],
            "key_news":  [],
        }


def upsert_portfolio_digest(
    user_id:    str,
    ticker:     str,
    company:    str,
    dimension:  str,
    dim_label:  str,
    report:     str,
    card:       dict,
) -> bool:
    """Merge dimension research into portfolio_digests and update card."""
    try:
        existing = execute_sql(
            """
            SELECT dimensions::text, digest
            FROM portfolio_digests
            WHERE user_id = :user_id::uuid AND ticker = :ticker
            """,
            [
                {"name": "user_id", "value": {"stringValue": user_id}},
                {"name": "ticker",  "value": {"stringValue": ticker}},
            ],
        )

        dimensions = {}
        if existing.get("records"):
            raw = existing["records"][0][0].get("stringValue", "{}")
            try:
                dimensions = json.loads(raw) if raw else {}
            except json.JSONDecodeError:
                dimensions = {}

        dimensions[dimension] = report[:3000]

        execute_sql(
            """
            INSERT INTO portfolio_digests
              (user_id, ticker, company, headline, sentiment, digest, dimensions, key_news, updated_at)
            VALUES
              (:user_id::uuid, :ticker, :company, :headline, :sentiment, :digest,
               :dimensions::jsonb, :key_news::jsonb, NOW())
            ON CONFLICT (user_id, ticker) DO UPDATE SET
              company    = EXCLUDED.company,
              headline   = EXCLUDED.headline,
              sentiment  = EXCLUDED.sentiment,
              digest     = EXCLUDED.digest,
              dimensions = EXCLUDED.dimensions,
              key_news   = EXCLUDED.key_news,
              updated_at = NOW()
            """,
            [
                {"name": "user_id",    "value": {"stringValue": user_id}},
                {"name": "ticker",     "value": {"stringValue": ticker}},
                {"name": "company",    "value": {"stringValue": company}},
                {"name": "headline",   "value": {"stringValue": card.get("headline", f"{ticker} Update")}},
                {"name": "sentiment",  "value": {"stringValue": card.get("sentiment", "neutral")}},
                {"name": "digest",     "value": {"stringValue": card.get("digest", report[:500])}},
                {"name": "dimensions", "value": {"stringValue": json.dumps(dimensions)}},
                {"name": "key_news",   "value": {"stringValue": json.dumps(card.get("key_news", []))}},
            ],
        )
        print(f"Upserted portfolio digest: {ticker} / {dimension}")
        return True
    except Exception as e:
        print(f"Portfolio digest upsert error: {e}")
        return False


def store_report(content: str, topic: str, clerk_id: str = "", session_id: str = "") -> bool:
    try:
        import httpx
        print(f"Storing report: {topic} ({len(content)} chars)")
        payload = {"content": content, "topic": topic}
        if clerk_id:
            payload["user_id"] = clerk_id
        if session_id:
            payload["session_id"] = session_id
        response = httpx.post(
            ALEX_API_ENDPOINT,
            headers = {
                "Content-Type": "application/json",
                "x-api-key":    ALEX_API_KEY,
            },
            json    = payload,
            timeout = 30,
        )
        print(f"Store response: {response.status_code}")
        return response.status_code == 200
    except Exception as e:
        print(f"Store error: {type(e).__name__}: {e}")
        return False


def push_to_frontend_queue(
    report:         str,
    topic:          str,
    task_id:        str,
    correlation_id: str,
) -> bool:
    try:
        queue_url = FRONTEND_RESULTS_QUEUE_URL
        if not queue_url:
            print("FRONTEND_RESULTS_QUEUE_URL not configured — skipping")
            return False

        message = {
            "correlationId": correlation_id,
            "result":        report,
            "topic":         topic,
            "task_id":       task_id,
            "timestamp":     datetime.now(UTC).isoformat(),
        }

        sqs.send_message(
            QueueUrl    = queue_url,
            MessageBody = json.dumps(message),
            MessageAttributes = {
                "correlationId": {
                    "StringValue": correlation_id,
                    "DataType":    "String",
                }
            },
        )
        return True
    except Exception as e:
        print(f"Frontend queue push error: {type(e).__name__}: {e}")
        return False


def handle_portfolio_research(message: dict) -> None:
    topic         = message.get('topic', '')
    ticker        = message.get('ticker', '')
    company       = message.get('company', ticker)
    dimension     = message.get('dimension', '')
    dim_label     = message.get('dimension_label', dimension)
    research_mode = message.get('research_mode', 'fast')
    user_id       = message.get('user_id', '')
    clerk_id      = message.get('clerk_id', '')
    classification = message.get('classification', {})

    print(f"Portfolio research: {ticker} / {dimension} ({research_mode})")

    # Use ECS fast/deep agents for live research
    report = call_ecs_research(topic, research_mode, clerk_id, message.get('session_id', ''))
    if not report:
        print("ECS unavailable — using Bedrock fallback")
        report = generate_report(topic, classification)

    # Load existing dimensions for digest synthesis
    existing_dims = {}
    try:
        row = execute_sql(
            "SELECT dimensions::text FROM portfolio_digests WHERE user_id = :uid::uuid AND ticker = :ticker",
            [
                {"name": "uid",    "value": {"stringValue": user_id}},
                {"name": "ticker", "value": {"stringValue": ticker}},
            ],
        )
        if row.get("records"):
            raw = row["records"][0][0].get("stringValue", "{}")
            existing_dims = json.loads(raw) if raw else {}
    except Exception:
        pass

    card = generate_card_digest(ticker, company, dimension, dim_label, report, existing_dims)
    upsert_portfolio_digest(user_id, ticker, company, dimension, dim_label, report, card)

    topic_label = f"[{ticker}] {dim_label} — {datetime.now(UTC).strftime('%b %d %Y')}"
    store_report(report, topic_label, clerk_id, message.get('session_id', ''))


def lambda_handler(event, context):
    for record in event.get('Records', []):
        try:
            message        = json.loads(record['body'])
            topic          = message.get('topic', '')
            classification = message.get('classification', {})
            task_id        = message.get('task_id', '0')
            correlation_id = message.get('correlationId', '')
            is_user_query  = bool(correlation_id)
            is_portfolio   = message.get('task_type') == 'portfolio_research'

            if is_portfolio:
                handle_portfolio_research(message)
                continue

            clerk_id       = message.get('clerk_id') or message.get('user_id', '')
            session_id     = message.get('session_id', '')

            print(f"Generating report: {topic}")
            if is_user_query and clerk_id:
                report = call_ecs_research(topic, 'fast', clerk_id, session_id)
                if not report:
                    print("ECS unavailable — using Bedrock fallback")
                    report = generate_report(topic, classification)
            else:
                report = generate_report(topic, classification)
            print(f"Report generated: {len(report)} chars")

            if is_user_query:
                push_to_frontend_queue(report, topic, task_id, correlation_id)

            topic_label = f"Report: {topic} {datetime.now(UTC).strftime('%b %d %Y')}"
            store_report(report, topic_label, clerk_id, session_id)

        except Exception as e:
            print(f"Reporter error: {type(e).__name__}: {e}")
            import traceback
            traceback.print_exc()

    return {"statusCode": 200}
