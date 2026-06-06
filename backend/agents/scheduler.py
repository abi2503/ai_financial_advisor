"""
Scheduler Lambda — triggered by EventBridge every 2 hours.
Queues auto-research tasks into SQS research queue.
"""
import os
import json
import boto3
import logging
from datetime import datetime, timezone

logger = logging.getLogger(__name__)
UTC    = timezone.utc

sqs = boto3.client('sqs', region_name=os.environ.get('AWS_REGION_NAME', 'us-east-1'))

RESEARCH_QUEUE_URL = os.environ.get('RESEARCH_QUEUE_URL')

AUTO_RESEARCH_TOPICS = [
    "Top stock market movers today",
    "Latest AI technology sector news",
    "Federal Reserve interest rate updates",
    "Cryptocurrency market performance",
    "Energy sector and oil prices today",
]


def lambda_handler(event, context):
    logger.info(f"Scheduler triggered: {json.dumps(event)}")

    timestamp    = datetime.now(UTC).isoformat()
    tasks_queued = 0

    for topic in AUTO_RESEARCH_TOPICS:
        try:
            message = {
                "task_type": "auto_research",
                "topic":     topic,
                "timestamp": timestamp,
                "source":    "eventbridge_scheduler",
                "priority":  "normal"
            }

            sqs.send_message(
                QueueUrl    = RESEARCH_QUEUE_URL,
                MessageBody = json.dumps(message)
            )

            tasks_queued += 1
            logger.info(f"Queued: {topic}")

        except Exception as e:
            logger.error(f"Failed to queue '{topic}': {e}")

    return {
        "statusCode":   200,
        "tasks_queued": tasks_queued,
        "timestamp":    timestamp
    }