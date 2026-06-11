"""
Reporter Lambda — triggered by SQS research queue.
Generates comprehensive reports and stores in knowledge base.
Option C: Also pushes to SQS results queue for user-triggered queries.
"""
import os
import json
import boto3
import logging
from datetime import datetime, timezone

logger = logging.getLogger(__name__)
UTC    = timezone.utc

bedrock = boto3.client('bedrock-runtime', region_name='us-east-1')
sqs     = boto3.client('sqs', region_name=os.environ.get('AWS_REGION', 'us-east-1'))

ALEX_API_ENDPOINT  = os.environ.get('ALEX_API_ENDPOINT')
ALEX_API_KEY       = os.environ.get('ALEX_API_KEY')
RESULTS_QUEUE_URL  = os.environ.get('RESULTS_QUEUE_URL')
FRONTEND_RESULTS_QUEUE_URL = os.environ.get('FRONTEND_RESULTS_QUEUE_URL')
RESULTS_QUEUE_URL          = os.environ.get('RESULTS_QUEUE_URL')

def push_to_results_queue(
    report:         str,
    topic:          str,
    task_id:        str,
    correlation_id: str
) -> bool:
    """
    Push to FRONTEND results queue for user-triggered queries.
    Separate from RESULTS queue (which Tagger→Reporter use)
    to avoid infinite loop.
    """
    try:
        # Use FRONTEND queue — separate from Tagger→Reporter queue
        queue_url = FRONTEND_RESULTS_QUEUE_URL or RESULTS_QUEUE_URL
        
        if not queue_url:
            print("No results queue URL configured")
            return False

        message = {
            "correlationId": correlation_id,
            "result":        report,
            "topic":         topic,
            "task_id":       task_id,
            "timestamp":     datetime.now(UTC).isoformat()
        }

        sqs.send_message(
            QueueUrl    = queue_url,
            MessageBody = json.dumps(message),
            MessageAttributes = {
                "correlationId": {
                    "StringValue": correlation_id,
                    "DataType":    "String"
                }
            }
        )
        print(f"Pushed to frontend results queue: {correlation_id[:8]} task={task_id}")
        return True

    except Exception as e:
        print(f"SQS push error: {type(e).__name__}: {e}")
        return False

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


def store_report(content: str, topic: str) -> bool:
    """Store report to pgvector knowledge base via ingest API."""
    try:
        import httpx
        print(f"Storing report: {topic} ({len(content)} chars)")

        response = httpx.post(
            ALEX_API_ENDPOINT,
            headers = {
                "Content-Type": "application/json",
                "x-api-key":    ALEX_API_KEY
            },
            json    = {
                "content": content,
                "topic":   topic
            },
            timeout = 30
        )
        print(f"Store response: {response.status_code}")
        return response.status_code == 200

    except Exception as e:
        print(f"Store error: {type(e).__name__}: {e}")
        return False


def push_to_results_queue(
    report:         str,
    topic:          str,
    task_id:        str,
    correlation_id: str
) -> bool:
    """
    Push report to SQS results queue for user-triggered queries.
    
    Why:
      Autonomous research → only pgvector (for knowledge base)
      User-triggered      → pgvector + SQS results queue
      
      Frontend polls SQS results queue with correlationId filter
      This allows frontend to get results back in real-time
    """
    try:
        if not RESULTS_QUEUE_URL:
            print("RESULTS_QUEUE_URL not configured — skipping SQS push")
            return False

        message = {
            "correlationId": correlation_id,
            "result":        report,
            "topic":         topic,
            "task_id":       task_id,
            "timestamp":     datetime.now(UTC).isoformat()
        }

        sqs.send_message(
            QueueUrl    = RESULTS_QUEUE_URL,
            MessageBody = json.dumps(message),
            MessageAttributes = {
                "correlationId": {
                    "StringValue": correlation_id,
                    "DataType":    "String"
                }
            }
        )
        print(f"Pushed to results queue: correlationId={correlation_id} task={task_id}")
        return True

    except Exception as e:
        print(f"SQS push error: {type(e).__name__}: {e}")
        return False


def lambda_handler(event, context):
    for record in event.get('Records', []):
        try:
            message        = json.loads(record['body'])
            topic          = message.get('topic', '')
            classification = message.get('classification', {})
            task_id        = message.get('task_id', '0')

            # Option C — check if user-triggered query
            correlation_id = message.get('correlationId', '')
            is_user_query  = bool(correlation_id)

            print(f"Generating report: {topic}")
            print(f"Classification:    {classification}")
            print(f"User query:        {is_user_query}")
            if is_user_query:
                print(f"CorrelationId:     {correlation_id}")

            # Generate report
            report = generate_report(topic, classification)
            print(f"Report generated: {len(report)} chars")

            # Always store to pgvector knowledge base
            topic_label = f"Report: {topic} {datetime.now(UTC).strftime('%b %d %Y')}"
            stored      = store_report(report, topic_label)

            if stored:
                print(f"Stored to pgvector: {topic_label}")
            else:
                print(f"Failed to store: {topic_label}")

            # If user-triggered → also push to SQS results queue
            if is_user_query:
                pushed = push_to_results_queue(
                    report         = report,
                    topic          = topic,
                    task_id        = task_id,
                    correlation_id = correlation_id
                )
                if pushed:
                    print(f"Pushed to results queue for frontend")
                else:
                    print(f"Failed to push to results queue")

        except Exception as e:
            print(f"Reporter error: {type(e).__name__}: {e}")
            import traceback
            traceback.print_exc()
            raise

    return {"statusCode": 200}