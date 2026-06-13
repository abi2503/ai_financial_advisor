"""
Alex Trading Observer Agent
Tracks cost, ROI, accuracy per agent
Sends daily digest email
"""
import os, json, boto3, logging
from datetime import datetime, timezone

logger = logging.getLogger(__name__)
UTC    = timezone.utc

REGION      = os.environ.get("AWS_REGION_NAME", "us-east-1")
CLUSTER_ARN = os.environ.get("DB_CLUSTER_ARN", "")
SECRET_ARN  = os.environ.get("DB_SECRET_ARN", "")
DB_NAME     = os.environ.get("DB_NAME", "alex_db")
ALERT_EMAIL = os.environ.get("ALERT_EMAIL", "abhishek.suresh2503@gmail.com")

rds     = boto3.client("rds-data", region_name=REGION)
ses     = boto3.client("ses",      region_name=REGION)
bedrock = boto3.client("bedrock-runtime", region_name=REGION)


def sql(query, params=None):
    if params is None:
        params = []
    try:
        return rds.execute_statement(
            resourceArn=CLUSTER_ARN, secretArn=SECRET_ARN,
            database=DB_NAME, sql=query, parameters=params
        )
    except Exception as e:
        logger.error(f"SQL error: {e}")
        return {"records": []}


def get_agent_stats(days=1):
    r = sql(f"""
        SELECT
            agent_name,
            COUNT(*) as calls,
            SUM(input_tokens) as total_input,
            SUM(output_tokens) as total_output,
            SUM(total_tokens) as total_tokens,
            SUM(cost_usd) as total_cost,
            AVG(latency_ms) as avg_latency,
            SUM(CASE WHEN success THEN 1 ELSE 0 END) as successes,
            SUM(CASE WHEN guardrail_triggered THEN 1 ELSE 0 END) as guardrail_hits,
            COUNT(DISTINCT ticker) as unique_tickers
        FROM agent_observations
        WHERE created_at > NOW() - INTERVAL '{days} days'
        GROUP BY agent_name
        ORDER BY total_cost DESC
    """)

    stats = []
    for row in r.get("records", []):
        stats.append({
            "agent":          row[0]["stringValue"],
            "calls":          int(list(row[1].values())[0]),
            "input_tokens":   int(list(row[2].values())[0]),
            "output_tokens":  int(list(row[3].values())[0]),
            "total_tokens":   int(list(row[4].values())[0]),
            "total_cost":     float(list(row[5].values())[0]),
            "avg_latency_ms": int(float(list(row[6].values())[0])),
            "successes":      int(list(row[7].values())[0]),
            "guardrail_hits": int(list(row[8].values())[0]),
            "unique_tickers": int(list(row[9].values())[0]),
        })
    return stats


def get_platform_cost(days=1):
    r = sql(f"""
        SELECT
            SUM(cost_usd) as trading_cost,
            SUM(total_tokens) as total_tokens,
            COUNT(*) as total_calls
        FROM agent_observations
        WHERE created_at > NOW() - INTERVAL '{days} days'
    """)

    if r.get("records"):
        row = r["records"][0]
        return {
            "trading_cost": float(list(row[0].values())[0] or 0),
            "total_tokens": int(list(row[1].values())[0] or 0),
            "total_calls":  int(list(row[2].values())[0] or 0),
        }
    return {"trading_cost": 0, "total_tokens": 0, "total_calls": 0}


def generate_digest(stats, platform):
    stats_text = "\n".join([
        f"{s['agent']}: {s['calls']} calls, ${s['total_cost']:.4f}, "
        f"avg {s['avg_latency_ms']}ms, {s['guardrail_hits']} guardrail hits"
        for s in stats
    ])

    prompt = f"""You are the Alex AI Observer Agent. Analyze this trading agent performance data:

{stats_text}

Total platform cost today: ${platform['trading_cost']:.4f}
Total tokens used: {platform['total_tokens']:,}
Total API calls: {platform['total_calls']}

Write a 3-4 sentence executive summary covering:
1. Which agents performed best/worst
2. Cost efficiency observations
3. Any guardrail concerns
4. One recommendation to improve efficiency

Keep it concise and actionable."""

    try:
        response = bedrock.invoke_model(
            modelId="us.amazon.nova-lite-v1:0",
            contentType="application/json",
            accept="application/json",
            body=json.dumps({
                "messages": [{"role": "user", "content": [{"text": prompt}]}],
                "inferenceConfig": {"maxTokens": 200, "temperature": 0.3}
            })
        )
        result = json.loads(response["body"].read())
        return result["output"]["message"]["content"][0]["text"].strip()
    except Exception as e:
        logger.error(f"Digest error: {e}")
        return f"Platform cost today: ${platform['trading_cost']:.4f} across {platform['total_calls']} calls."


def send_digest_email(stats, platform, digest):
    rows = "".join([
        "<tr>"
        f"<td style='padding:8px;border-bottom:1px solid #333'>{s['agent'].title()}</td>"
        f"<td style='padding:8px;border-bottom:1px solid #333'>{s['calls']}</td>"
        f"<td style='padding:8px;border-bottom:1px solid #333'>{s['total_tokens']:,}</td>"
        f"<td style='padding:8px;border-bottom:1px solid #333'>${s['total_cost']:.5f}</td>"
        f"<td style='padding:8px;border-bottom:1px solid #333'>{s['avg_latency_ms']}ms</td>"
        f"<td style='padding:8px;border-bottom:1px solid #333'>{s['guardrail_hits']}</td>"
        "</tr>"
        for s in stats
    ])

    html = f"""
    <html><body style="font-family:monospace;background:#0a0a0a;color:#e5e7eb;padding:20px">
    <h2 style="color:#818cf8">Alex Trading Observer Report</h2>
    <p style="color:#9ca3af">{datetime.now(UTC).strftime('%B %d, %Y')}</p>
    <h3 style="color:#c4b5fd">AI Commentary</h3>
    <p style="background:#1f2937;padding:12px;border-radius:8px">{digest}</p>
    <h3 style="color:#c4b5fd">Agent Performance</h3>
    <table style="width:100%;border-collapse:collapse">
      <tr style="color:#6b7280;border-bottom:1px solid #374151">
        <th style="padding:8px;text-align:left">Agent</th>
        <th style="padding:8px;text-align:left">Calls</th>
        <th style="padding:8px;text-align:left">Tokens</th>
        <th style="padding:8px;text-align:left">Cost</th>
        <th style="padding:8px;text-align:left">Latency</th>
        <th style="padding:8px;text-align:left">Guardrails</th>
      </tr>
      {rows}
    </table>
    <h3 style="color:#c4b5fd">Platform Summary</h3>
    <p>Total cost today: <strong>${platform['trading_cost']:.4f}</strong></p>
    <p>Total tokens: <strong>{platform['total_tokens']:,}</strong></p>
    <p>Total API calls: <strong>{platform['total_calls']}</strong></p>
    <p>Monthly forecast: <strong>${platform['trading_cost'] * 30:.2f}</strong></p>
    </body></html>
    """

    try:
        ses.send_email(
            Source=ALERT_EMAIL,
            Destination={"ToAddresses": [ALERT_EMAIL]},
            Message={
                "Subject": {"Data": f"Alex Observer - {datetime.now(UTC).strftime('%b %d')} Agent Report"},
                "Body":    {"Html": {"Data": html}}
            }
        )
        print("Observer email sent")
    except Exception as e:
        logger.error(f"SES error: {e}")


def lambda_handler(event, context):
    now    = datetime.now(UTC)
    source = event.get("source", "manual")
    print(f"Observer Agent - {now.isoformat()} | source: {source}")

    stats    = get_agent_stats(days=1)
    platform = get_platform_cost(days=1)
    digest   = generate_digest(stats, platform)

    if source != "manual" or event.get("send_email"):
        send_digest_email(stats, platform, digest)

    return {
        "statusCode": 200,
        "body": json.dumps({
            "timestamp":   now.isoformat(),
            "agent_stats": stats,
            "platform":    platform,
            "digest":      digest,
        })
    }
