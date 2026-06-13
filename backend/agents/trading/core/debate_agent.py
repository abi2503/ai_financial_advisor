import os, json, boto3, logging
from datetime import datetime, timezone

logger = logging.getLogger(__name__)
UTC    = timezone.utc
REGION = os.environ.get("AWS_REGION_NAME", "us-east-1")
cw     = boto3.client("cloudwatch", region_name=REGION)

def emit_metric(name, value, dims=None):
    try:
        d = [{"Name": "Service", "Value": "alex-trading"}]
        if dims:
            for k, v in dims.items():
                d.append({"Name": k, "Value": str(v)})
        cw.put_metric_data(Namespace="AlexAI/Trading",
            MetricData=[{"MetricName": name, "Value": value,
                        "Unit": "Count", "Dimensions": d,
                        "Timestamp": datetime.now(UTC)}])
    except Exception:
        pass

def warm_aurora():
    import time, boto3, os
    rds_client = boto3.client("rds-data", region_name=os.environ.get("AWS_REGION_NAME", "us-east-1"))
    cluster_arn = os.environ.get("DB_CLUSTER_ARN", "")
    secret_arn  = os.environ.get("DB_SECRET_ARN", "")
    for i in range(8):
        try:
            rds_client.execute_statement(resourceArn=cluster_arn, secretArn=secret_arn, database="alex_db", sql="SELECT 1")
            print(f"Aurora ready ({i+1})")
            return True
        except Exception as e:
            if "resuming" in str(e).lower() or "paused" in str(e).lower():
                print(f"Aurora resuming {i+1}/8...")
                time.sleep(10)
            else:
                return True
    return False


def lambda_handler(event, context):
    now = datetime.now(UTC)
    print(f"Debate Agent {now.isoformat()}")
    warm_aurora()
    results = []
    for record in event.get("Records", []):
        try:
            body    = json.loads(record["body"])
            ticker  = body.get("ticker", "")
            sim_id  = body.get("simulation_id", "")
            user_id = body.get("user_id", "")
            mode    = body.get("mode", "neutral")
            config  = body.get("config", {})
            holding = {
                "ticker":         ticker,
                "shares":         body.get("shares", 0),
                "purchase_price": body.get("avg_cost", 0),
                "current_price":  body.get("current_price", 0),
                "total_value":    body.get("shares", 0) * body.get("avg_cost", 0),
            }
            if not ticker or ticker.isdigit() or len(ticker) > 5:
                print(f"Skip invalid: {ticker}")
                continue
            print(f"Debating: {ticker} mode:{mode}")
            emit_metric("DebateStarted", 1, {"Ticker": ticker})
            from core.debate_engine import run_debate
            result = run_debate(ticker=ticker, holding=holding,
                               sim_id=sim_id, user_id=user_id,
                               mode=mode, config=config)
            results.append({"ticker": ticker,
                           "action": result.get("final_action"),
                           "confidence": result.get("confidence"),
                           "shares": result.get("shares"),
                           "price": result.get("price")})
            emit_metric("DebateCompleted", 1, {"Ticker": ticker})
            print(f"Done: {ticker} {result.get('final_action')} {result.get('confidence')}%")
        except Exception as e:
            logger.error(f"Error: {e}")
            import traceback; traceback.print_exc()
            emit_metric("DebateError", 1)
    return {"statusCode": 200, "body": json.dumps({"processed": len(results), "results": results})}
