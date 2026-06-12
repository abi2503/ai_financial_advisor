"""
Cost Monitor Lambda — Daily AWS spend tracking.
Triggered by EventBridge daily at 8AM.
"""
import os
import json
import boto3
import logging
from datetime import datetime, timezone, timedelta

logger = logging.getLogger(__name__)
UTC    = timezone.utc

CLUSTER_ARN     = os.environ.get('DB_CLUSTER_ARN', '')
SECRET_ARN      = os.environ.get('DB_SECRET_ARN', '')
DB_NAME         = os.environ.get('DB_NAME', 'alex_db')
ALERT_THRESHOLD = float(os.environ.get('DAILY_COST_THRESHOLD', '10.0'))
ALERT_EMAIL     = os.environ.get('ALERT_EMAIL', '')
FROM_EMAIL      = os.environ.get('FROM_EMAIL', '')
REGION          = os.environ.get('AWS_REGION', 'us-east-1')

rds     = boto3.client('rds-data',        region_name=REGION)
ce      = boto3.client('ce',              region_name='us-east-1')
bedrock = boto3.client('bedrock-runtime', region_name=REGION)
ses     = boto3.client('ses',             region_name=REGION)


def execute_sql(sql, params=[]):
    try:
        return rds.execute_statement(
            resourceArn=CLUSTER_ARN,
            secretArn=SECRET_ARN,
            database=DB_NAME,
            sql=sql,
            parameters=params
        )
    except Exception as e:
        logger.error(f"SQL error: {e}")
        return {"records": []}


def get_daily_costs(date):
    try:
        next_day = (datetime.strptime(date, '%Y-%m-%d') + timedelta(days=1)).strftime('%Y-%m-%d')
        response = ce.get_cost_and_usage(
            TimePeriod={'Start': date, 'End': next_day},
            Granularity='DAILY',
            Metrics=['UnblendedCost'],
            GroupBy=[{'Type': 'DIMENSION', 'Key': 'SERVICE'}]
        )
        service_costs = {}
        total = 0.0
        for result in response['ResultsByTime']:
            for group in result['Groups']:
                service = group['Keys'][0]
                amount  = float(group['Metrics']['UnblendedCost']['Amount'])
                if amount > 0.001:
                    service_costs[service] = round(amount, 4)
                    total += amount
        return {'total': round(total, 4), 'services': service_costs, 'date': date}
    except Exception as e:
        logger.error(f"Cost Explorer error: {e}")
        return {'total': 0, 'services': {}, 'date': date}


def get_weekly_costs():
    try:
        end   = datetime.now(UTC).strftime('%Y-%m-%d')
        start = (datetime.now(UTC) - timedelta(days=7)).strftime('%Y-%m-%d')
        response = ce.get_cost_and_usage(
            TimePeriod={'Start': start, 'End': end},
            Granularity='DAILY',
            Metrics=['UnblendedCost']
        )
        daily = []
        for result in response['ResultsByTime']:
            daily.append({
                'date':   result['TimePeriod']['Start'],
                'amount': round(float(result['Total']['UnblendedCost']['Amount']), 4)
            })
        return {'daily': daily, 'total': round(sum(d['amount'] for d in daily), 4)}
    except Exception as e:
        logger.error(f"Weekly cost error: {e}")
        return {'daily': [], 'total': 0}


def generate_digest(costs, weekly):
    try:
        sorted_services = sorted(costs['services'].items(), key=lambda x: x[1], reverse=True)[:8]
        services_str = "\n".join([f"  {svc}: ${amt}" for svc, amt in sorted_services])
        weekly_str   = "\n".join([f"  {d['date']}: ${d['amount']}" for d in weekly['daily']])

        prompt = f"""You are Alex's AWS cost monitoring agent for an AI financial advisor platform.

Today's AWS spend: ${costs['total']}
Alert threshold:  ${ALERT_THRESHOLD}/day

Top services today:
{services_str}

Last 7 days:
{weekly_str}
Weekly total: ${weekly['total']}

Generate a concise cost digest (under 300 words):
1. Daily spend summary and status
2. Top 3 cost drivers with brief explanation
3. Week-over-week trend
4. 2 specific cost optimization tips
5. Overall status: ON TRACK / MONITOR / ALERT

Be specific and actionable. Not financial advice."""

        response = bedrock.invoke_model(
            modelId='us.amazon.nova-lite-v1:0',
            contentType='application/json',
            accept='application/json',
            body=json.dumps({
                "messages": [{"role": "user", "content": [{"text": prompt}]}],
                "inferenceConfig": {"maxTokens": 500, "temperature": 0.3}
            })
        )
        result = json.loads(response['body'].read())
        return result['output']['message']['content'][0]['text']
    except Exception as e:
        logger.error(f"Digest error: {e}")
        top = sorted(costs['services'].items(), key=lambda x: x[1], reverse=True)[:5]
        lines = [f"Daily Cost Report — {costs['date']}", f"Total: ${costs['total']}", ""]
        for svc, amt in top:
            lines.append(f"  {svc}: ${amt}")
        lines.append(f"\nWeekly total: ${weekly['total']}")
        return "\n".join(lines)


def send_email(subject, body):
    if not ALERT_EMAIL or not FROM_EMAIL:
        print("SES not configured — skipping email")
        return
    try:
        ses.send_email(
            Source=FROM_EMAIL,
        Destination={'ToAddresses': [ALERT_EMAIL]},
            Message={
                'Subject': {'Data': subject},
                'Body':    {'Text': {'Data': body}}
            }
        )
        print(f"Email sent to {ALERT_EMAIL}")
    except Exception as e:
        logger.error(f"SES error: {e}")


def store_snapshot(date, costs, digest):
    try:
        execute_sql(
            "INSERT INTO cost_snapshots (snapshot_date, total_cost, service_costs, digest) VALUES (:date, :total, :services::jsonb, :digest) ON CONFLICT DO NOTHING",
            [
                {'name': 'date',     'value': {'stringValue': date}},
                {'name': 'total',    'value': {'doubleValue': costs['total']}},
                {'name': 'services', 'value': {'stringValue': json.dumps(costs['services'])}},
                {'name': 'digest',   'value': {'stringValue': digest}}
            ]
        )
        print(f"Stored snapshot for {date}")
    except Exception as e:
        logger.error(f"Store snapshot error: {e}")


def lambda_handler(event, context):
    today     = datetime.now(UTC).strftime('%Y-%m-%d')
    is_monday = datetime.now(UTC).weekday() == 0

    print(f"Cost Monitor running for {today}, threshold=${ALERT_THRESHOLD}")

    costs  = get_daily_costs(today)
    weekly = get_weekly_costs()

    print(f"Today: ${costs['total']}, Weekly: ${weekly['total']}")

    digest = generate_digest(costs, weekly)
    print(f"Digest: {len(digest)} chars")

    store_snapshot(today, costs, digest)

    if costs['total'] >= ALERT_THRESHOLD:
        print(f"ALERT triggered: ${costs['total']} >= ${ALERT_THRESHOLD}")
        subject = f"Alex AI Cost Alert — ${costs['total']:.2f} today (threshold: ${ALERT_THRESHOLD})"
        send_email(subject, digest)
        execute_sql(
            "INSERT INTO cost_alerts (alert_date, daily_spend, threshold, message) VALUES (:date, :spend, :threshold, :msg)",
            [
                {'name': 'date',      'value': {'stringValue': today}},
                {'name': 'spend',     'value': {'doubleValue': costs['total']}},
                {'name': 'threshold', 'value': {'doubleValue': ALERT_THRESHOLD}},
                {'name': 'msg',       'value': {'stringValue': digest[:500]}}
            ]
        )
    elif is_monday:
        subject = f"Alex AI Weekly Cost Digest — ${weekly['total']:.2f} this week"
        send_email(subject, digest)

    return {
        "statusCode": 200,
        "body": json.dumps({
            "date":   today,
            "total":  costs['total'],
            "status": "alert" if costs['total'] >= ALERT_THRESHOLD else "ok",
            "digest": digest[:200]
        })
    }
