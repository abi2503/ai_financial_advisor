# Save as /tmp/check_queue.py and run
import boto3, time

sqs = boto3.client('sqs', region_name='us-east-1')
URL = 'https://sqs.us-east-1.amazonaws.com/381491881089/alex-frontend-results'

for i in range(20):
    r = sqs.receive_message(
        QueueUrl=URL,
        MaxNumberOfMessages=10,
        WaitTimeSeconds=2
    )
    msgs = r.get('Messages', [])
    print(f"{i*2}s: {len(msgs)} messages")
    if msgs:
        print(f"  Body: {msgs[0]['Body'][:100]}")
        break
    time.sleep(2)