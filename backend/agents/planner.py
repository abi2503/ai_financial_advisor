"""
Planner Lambda — orchestrates the multi-agent system.
Breaks complex questions into tasks for specialist agents.
"""
import os
import json
import boto3
import logging
from datetime import datetime, timezone

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
            "messages": [{"role": "user", "content": [{"text":prompt}]}],
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


def lambda_handler(event, context):
    # Parse input
    if isinstance(event.get('body'), str):
        body = json.loads(event['body'])
    else:
        body = event.get('body', event)

    question  = body.get('question', '')
    timestamp = datetime.now(UTC).isoformat()

    if not question:
        return {
            "statusCode": 400,
            "body": json.dumps({"error": "Missing question"})
        }

    logger.info(f"Planning: {question}")

    tasks        = break_into_tasks(question)
    tasks_queued = []

    for task in tasks:
        message = {
            "question":  question,
            "task_id":   task['task_id'],
            "topic":     task['topic'],
            "priority":  task['priority'],
            "timestamp": timestamp,
            "source":    "planner"
        }

        sqs.send_message(
            QueueUrl    = RESEARCH_QUEUE_URL,
            MessageBody = json.dumps(message)
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
            "message":      f"Queued {len(tasks_queued)} research tasks. Results stored in knowledge base shortly."
        })
    }