"""
Tagger Lambda — triggered by SQS research_queue.
"""
import os
import json
import boto3
import logging
from datetime import datetime, timezone

# Configure logging for Lambda
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
UTC    = timezone.utc

sqs     = boto3.client('sqs',             region_name=os.environ.get('AWS_REGION_NAME', 'us-east-1'))
bedrock = boto3.client('bedrock-runtime', region_name='us-east-1')

RESULTS_QUEUE_URL = os.environ.get('RESULTS_QUEUE_URL')


def classify_topic(topic: str) -> dict:
    print(f"Classifying topic: {topic}")

    prompt = f"""Classify this financial research topic.
Topic: "{topic}"

Respond ONLY with valid JSON no other text:
{{
  "category": "stocks|crypto|macro|bonds|commodities|other",
  "priority": "high|medium|low",
  "tickers": ["relevant", "tickers"],
  "sector": "technology|healthcare|finance|energy|other",
  "sentiment_expected": "bullish|bearish|neutral"
}}"""

    try:
        response = bedrock.invoke_model(
            modelId     = "us.amazon.nova-lite-v1:0",
            contentType = "application/json",
            accept      = "application/json",
            body        = json.dumps({
                "messages": [
                    {
                        "role":    "user",
                        "content": [{"text": prompt}]
                    }
                ],
                "inferenceConfig": {"maxTokens": 300, "temperature": 0}
            })
        )

        result = json.loads(response['body'].read())
        print(f"Bedrock response: {result}")
        text   = result['output']['message']['content'][0]['text'].strip()

        if "```" in text:
            text = text.split("```")[1]
            if text.startswith("json"):
                text = text[4:]

        classification = json.loads(text.strip())
        print(f"Classification: {classification}")
        return classification

    except Exception as e:
        print(f"Classification error: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        # Return default classification so pipeline continues
        return {
            "category":           "other",
            "priority":           "normal",
            "tickers":            [],
            "sector":             "other",
            "sentiment_expected": "neutral"
        }


def lambda_handler(event, context):
    print(f"Tagger received event with {len(event.get('Records', []))} records")
    print(f"RESULTS_QUEUE_URL: {RESULTS_QUEUE_URL}")

    if not RESULTS_QUEUE_URL:
        print("ERROR: RESULTS_QUEUE_URL not set!")
        return {"statusCode": 500}

    for record in event.get('Records', []):
        try:
            message = json.loads(record['body'])
            topic   = message.get('topic', '')

            print(f"Processing topic: {topic}")

            classification = classify_topic(topic)

            enriched = {
                **message,
                "classification": classification,
                "tagged_at":      datetime.now(UTC).isoformat(),
                "status":         "tagged"
            }

            sqs.send_message(
                QueueUrl    = RESULTS_QUEUE_URL,
                MessageBody = json.dumps(enriched)
            )

            print(f"Successfully routed to reporter: {topic}")

        except Exception as e:
            print(f"Tagger handler error: {type(e).__name__}: {e}")
            import traceback
            traceback.print_exc()
            raise

    return {"statusCode": 200}