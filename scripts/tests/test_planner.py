#!/usr/bin/env python3
"""
Test: Planner Lambda — query decomposition + SQS
Tests:
  1. Direct Lambda invoke with complex query
  2. SQS message appears in research queue
  3. Task decomposition quality
"""
import os
import sys
import json
import boto3
from datetime import datetime

os.chdir(os.path.join(os.path.dirname(os.path.abspath(__file__)), "../.."))

REGION             = "us-east-1"
PLANNER_FUNCTION   = "alex-planner"
RESEARCH_QUEUE_URL = "https://sqs.us-east-1.amazonaws.com/381491881089/alex-research-queue"
RESULTS_QUEUE_URL  = "https://sqs.us-east-1.amazonaws.com/381491881089/alex-results-queue"

lmb = boto3.client("lambda", region_name=REGION)
sqs = boto3.client("sqs",    region_name=REGION)

print("\n🧪 Testing Planner Lambda")
print("=" * 40)

# Test 1 — Direct invoke
print("\nTest 1: Direct Lambda invoke...")
try:
    response = lmb.invoke(
        FunctionName   = PLANNER_FUNCTION,
        InvocationType = "RequestResponse",
        Payload        = json.dumps({
            "body": json.dumps({
                "question": "Compare NVIDIA vs AMD for AI chip market in 2026"
            })
        })
    )
    result  = json.loads(response["Payload"].read())
    body    = json.loads(result.get("body", "{}"))
    tasks   = body.get("tasks_queued", [])
    count   = body.get("task_count", 0)

    print(f"  Task count: {count}")
    for i, task in enumerate(tasks):
        print(f"  Task {i+1}: {task}")

    if count >= 2:
        print("  ✅ PASS — decomposed into multiple tasks")
    else:
        print("  ⚠️  Only 1 task — may not be decomposing")

except Exception as e:
    print(f"  ❌ FAIL: {e}")

# Test 2 — Check SQS queue
print("\nTest 2: SQS research queue messages...")
try:
    msgs = sqs.receive_message(
        QueueUrl            = RESEARCH_QUEUE_URL,
        MaxNumberOfMessages = 5,
        WaitTimeSeconds     = 3,
        VisibilityTimeout   = 5
    )
    messages = msgs.get("Messages", [])
    print(f"  Messages in queue: {len(messages)}")

    for msg in messages:
        body = json.loads(msg["Body"])
        print(f"  Topic: {body.get('topic', 'unknown')}")
        print(f"  Source: {body.get('source', 'unknown')}")

        # Return message to queue (don't consume)
        sqs.change_message_visibility(
            QueueUrl          = RESEARCH_QUEUE_URL,
            ReceiptHandle     = msg["ReceiptHandle"],
            VisibilityTimeout = 0
        )

    if messages:
        print("  ✅ PASS — messages in SQS queue")
    else:
        print("  ⚠️  No messages — queue may be empty")

except Exception as e:
    print(f"  ❌ FAIL: {e}")

# Test 3 — Complex query detection
print("\nTest 3: Query complexity detection...")
COMPLEX_PATTERNS = ["compare", "vs", "versus", "should i", "analyze multiple", "both"]
test_queries = [
    ("Compare NVDA vs AMD",                True),
    ("What is NVDA stock price?",          False),
    ("Should I buy AAPL or MSFT?",         True),
    ("Analyze NVDA earnings",              False),
    ("TSLA vs RIVN for EV market",         True),
]

correct = 0
for query, expected in test_queries:
    is_complex = any(p in query.lower() for p in COMPLEX_PATTERNS)
    status     = "✅" if is_complex == expected else "❌"
    print(f"  {status} '{query[:40]}' → {'complex' if is_complex else 'simple'}")
    if is_complex == expected:
        correct += 1

print(f"  Score: {correct}/{len(test_queries)}")
if correct == len(test_queries):
    print("  ✅ PASS")
else:
    print("  ⚠️  Some queries misclassified")

print("\n" + "=" * 40)
print("✅ Planner test complete")