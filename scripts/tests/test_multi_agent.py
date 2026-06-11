#!/usr/bin/env python3
"""
Test: Multi-Agent Pipeline
Tests: Planner → SQS → Tagger → Reporter → Results Queue
"""
import os
import sys
import json
import boto3
import time
import uuid

os.chdir(os.path.join(os.path.dirname(os.path.abspath(__file__)), "../.."))

REGION             = "us-east-1"
PLANNER_FUNCTION   = "alex-planner"
RESULTS_QUEUE_URL  = "https://sqs.us-east-1.amazonaws.com/381491881089/alex-results-queue"
RESEARCH_QUEUE_URL = "https://sqs.us-east-1.amazonaws.com/381491881489/alex-research-queue"

lmb = boto3.client("lambda", region_name=REGION)
sqs = boto3.client("sqs",    region_name=REGION)

print("\n🧪 Testing Multi-Agent Pipeline")
print("=" * 40)

# Generate correlation ID
correlation_id = str(uuid.uuid4())
print(f"\nCorrelation ID: {correlation_id}")

# Step 1 — Invoke Planner
print("\nStep 1: Invoking Planner Lambda...")
try:
    response = lmb.invoke(
        FunctionName   = PLANNER_FUNCTION,
        InvocationType = "RequestResponse",
        Payload        = json.dumps({
            "body": json.dumps({
                "question":      "Compare NVDA vs AVGO",
                "correlationId": correlation_id
            })
        })
    )
    result    = json.loads(response["Payload"].read())
    body      = json.loads(result.get("body", "{}"))
    tasks     = body.get("tasks_queued", [])
    taskCount = body.get("task_count", 0)

    print(f"  Tasks queued: {taskCount}")
    for i, task in enumerate(tasks):
        print(f"  Task {i+1}: {task[:60]}")
    print("  ✅ Planner working")

except Exception as e:
    print(f"  ❌ Planner failed: {e}")
    sys.exit(1)

# Step 2 — Poll results queue for 2 mins
print(f"\nStep 2: Polling results queue (2 min timeout)...")
print(f"  Waiting for {taskCount} results with correlationId={correlation_id[:8]}...")

results   = []
start     = time.time()
timeout   = 120

while len(results) < taskCount and time.time() - start < timeout:
    try:
        msgs = sqs.receive_message(
            QueueUrl               = RESULTS_QUEUE_URL,
            MaxNumberOfMessages    = 10,
            WaitTimeSeconds        = 5,
            VisibilityTimeout      = 30,
            MessageAttributeNames  = ["correlationId"]
        )

        for msg in msgs.get("Messages", []):
            body       = json.loads(msg["Body"])
            msg_corr   = body.get("correlationId", "")
            msg_result = body.get("result", "")

            if msg_corr == correlation_id and msg_result:
                results.append(msg_result)
                topic = body.get("topic", "unknown")
                print(f"  ✅ Got result {len(results)}/{taskCount}: {topic[:50]}")

                # Delete message
                sqs.delete_message(
                    QueueUrl      = RESULTS_QUEUE_URL,
                    ReceiptHandle = msg["ReceiptHandle"]
                )

    except Exception as e:
        print(f"  Poll error: {e}")

    elapsed = int(time.time() - start)
    if len(results) < taskCount:
        print(f"  Waiting... {len(results)}/{taskCount} results ({elapsed}s elapsed)")

# Step 3 — Results
print(f"\nStep 3: Results summary...")
print(f"  Got {len(results)}/{taskCount} results")
print(f"  Time: {int(time.time()-start)}s")

if results:
    print(f"  First result preview: {results[0][:200]}")
    print("  ✅ PASS — Multi-agent pipeline working!")
else:
    print("  ❌ FAIL — No results received")
    print("  Check Reporter Lambda logs:")
    print("  aws logs tail /aws/lambda/alex-reporter --region us-east-1 --since 3m")

print("\n" + "=" * 40)
print("✅ Multi-agent test complete")