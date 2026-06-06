"""
Reporter Lambda — triggered by SQS results_queue.
Generates comprehensive reports and stores in knowledge base.
"""
import os
import json
import boto3
import logging
import asyncio
import httpx
from datetime import datetime, timezone

logger = logging.getLogger(__name__)
UTC    = timezone.utc

bedrock = boto3.client('bedrock-runtime', region_name='us-east-1')

ALEX_API_ENDPOINT = os.environ.get('ALEX_API_ENDPOINT')
ALEX_API_KEY      = os.environ.get('ALEX_API_KEY')


def generate_report(topic: str, classification: dict) -> str:
    """Generate comprehensive report using Nova Pro."""
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
            "messages": [{"role": "user", "content": [{"text":prompt}]}],
            "inferenceConfig": {"maxTokens": 1000, "temperature": 0.3}
        })
    )

    result = json.loads(response['body'].read())
    return result['output']['message']['content'][0]['text']


def store_report(content: str, topic: str) -> bool:
    try:
        import httpx
        print(f"Storing report, content length: {len(content)}")
        print(f"First 200 chars: {content[:200]}")

        response = httpx.post(
            ALEX_API_ENDPOINT,
            headers={
                "Content-Type": "application/json",
                "x-api-key":    ALEX_API_KEY
            },
            json={
                "content": content,   # ← this is correct
                "topic":   topic
            },
            timeout=30
        )
        print(f"Store response: {response.status_code} {response.text[:100]}")
        return response.status_code == 200
    except Exception as e:
        print(f"Store error: {type(e).__name__}: {e}")
        return False


def lambda_handler(event, context):
    for record in event.get('Records', []):
        try:
            message        = json.loads(record['body'])
            topic          = message.get('topic', '')
            classification = message.get('classification', {})

            print(f"Generating report: {topic}")
            print(f"Classification: {classification}")

            report      = generate_report(topic, classification)
            print(f"Report generated, length: {len(report)}")

            topic_label = f"Report: {topic} {datetime.now(UTC).strftime('%b %d %Y')}"
            stored      = store_report(report, topic_label)

            if stored:
                print(f"Successfully stored: {topic_label}")
            else:
                print(f"Failed to store: {topic_label}")

        except Exception as e:
            print(f"Reporter error: {type(e).__name__}: {e}")
            import traceback
            traceback.print_exc()
            raise

    return {"statusCode": 200}
