"""
Planner Lambda — orchestrates the multi-agent system.
Breaks complex questions into tasks OR plans portfolio research per stock.
"""
import os
import json
import boto3
import logging
from datetime import datetime, timezone

from portfolio_research import dimensions_for_cycle, format_topic

logger = logging.getLogger(__name__)
UTC    = timezone.utc

sqs     = boto3.client('sqs',             region_name=os.environ.get('AWS_REGION_NAME', 'us-east-1'))
bedrock = boto3.client('bedrock-runtime', region_name='us-east-1')

RESEARCH_QUEUE_URL = os.environ.get('RESEARCH_QUEUE_URL')
RESULTS_QUEUE_URL  = os.environ.get('RESULTS_QUEUE_URL')


def break_into_tasks(question: str) -> list:
    """Use Nova Pro to decompose complex question into tasks."""
    prompt = f"""You are a financial research planner.
Break this question into specific research tasks:

Question: "{question}"

Respond ONLY with valid JSON array no other text:
[
  {{
    "task_id":  "1",
    "topic":    "specific research topic",
    "priority": "high|medium|low"
  }}
]

Maximum 5 tasks. Be specific and actionable."""

    response = bedrock.invoke_model(
        modelId     = "us.amazon.nova-pro-v1:0",
        contentType = "application/json",
        accept      = "application/json",
        body        = json.dumps({
            "messages": [{"role": "user", "content": [{"text": prompt}]}],
            "inferenceConfig": {"maxTokens": 500, "temperature": 0}
        })
    )

    result = json.loads(response['body'].read())
    text   = result['output']['message']['content'][0]['text'].strip()

    if "```" in text:
        text = text.split("```")[1]
        if text.startswith("json"):
            text = text[4:]

    return json.loads(text.strip())


def plan_portfolio_research(body: dict) -> dict:
    """Queue dimension-specific research tasks for each portfolio holding."""
    holdings  = body.get('holdings', [])
    user_id   = body.get('user_id', '')
    clerk_id  = body.get('clerk_id', '')
    timestamp = body.get('timestamp', datetime.now(UTC).isoformat())

    if not holdings:
        return {
            "statusCode": 200,
            "body": json.dumps({"message": "No holdings to research", "tasks_queued": 0}),
        }

    dims         = dimensions_for_cycle()
    tasks_queued = []
    task_num     = 0

    for holding in holdings:
        ticker  = holding.get('ticker', '')
        company = holding.get('company', ticker)
        if not ticker:
            continue

        for dim in dims:
            task_num += 1
            topic = format_topic(dim, ticker, company)
            message = {
                "task_type":     "portfolio_research",
                "task_id":       str(task_num),
                "topic":         topic,
                "ticker":        ticker,
                "company":       company,
                "dimension":     dim["id"],
                "dimension_label": dim["label"],
                "research_mode": dim["mode"],
                "user_id":       user_id,
                "clerk_id":      clerk_id,
                "priority":      "high",
                "timestamp":     timestamp,
                "source":        "portfolio_planner",
            }
            sqs.send_message(
                QueueUrl    = RESEARCH_QUEUE_URL,
                MessageBody = json.dumps(message),
            )
            tasks_queued.append(f"{ticker}:{dim['id']}")
            logger.info(f"Queued portfolio task: {ticker} / {dim['id']} ({dim['mode']})")

    return {
        "statusCode": 200,
        "body": json.dumps({
            "task":         "portfolio_research",
            "user_id":      user_id,
            "tasks_queued": tasks_queued,
            "task_count":   len(tasks_queued),
            "dimensions":   [d["id"] for d in dims],
            "timestamp":    timestamp,
            "message":      f"Queued {len(tasks_queued)} portfolio research tasks",
        }),
    }


def lambda_handler(event, context):
    if isinstance(event.get('body'), str):
        body = json.loads(event['body'])
    else:
        body = event.get('body', event)

    # Portfolio research mode — triggered by scheduler
    if body.get('task') == 'portfolio_research':
        logger.info(f"Portfolio research for user {body.get('clerk_id')}")
        return plan_portfolio_research(body)

    question       = body.get('question', '')
    correlation_id = body.get('correlationId', '')
    user_id        = body.get('user_id', '') or body.get('clerk_id', '')
    session_id     = body.get('session_id', '')
    timestamp      = datetime.now(UTC).isoformat()

    if not question:
        return {
            "statusCode": 400,
            "body": json.dumps({"error": "Missing question"}),
        }

    logger.info(f"Planning: {question}")
    if correlation_id:
        logger.info(f"CorrelationId: {correlation_id}")

    tasks        = break_into_tasks(question)
    tasks_queued = []

    for task in tasks:
        message = {
            "question":      question,
            "task_id":       task['task_id'],
            "topic":         task['topic'],
            "priority":      task['priority'],
            "timestamp":     timestamp,
            "source":        "planner",
            "correlationId": correlation_id,
            "user_id":       user_id,
            "clerk_id":      user_id,
            "session_id":    session_id,
        }
        sqs.send_message(
            QueueUrl    = RESEARCH_QUEUE_URL,
            MessageBody = json.dumps(message),
        )
        tasks_queued.append(task['topic'])
        logger.info(f"Queued: {task['topic']}")

    return {
        "statusCode": 200,
        "body": json.dumps({
            "question":     question,
            "tasks_queued": tasks_queued,
            "task_count":   len(tasks_queued),
            "timestamp":    timestamp,
            "message":      f"Queued {len(tasks_queued)} research tasks",
        }),
    }
