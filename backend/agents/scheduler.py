"""
Scheduler Lambda — triggered by EventBridge every 2 hours.
Reads all portfolio holdings and invokes the planner for per-user research.
"""
import os
import json
import boto3
import logging
from datetime import datetime, timezone

from db_helper import get_all_portfolio_holdings

logger = logging.getLogger(__name__)
UTC    = timezone.utc

lambda_client = boto3.client('lambda', region_name=os.environ.get('AWS_REGION_NAME', 'us-east-1'))
PLANNER_FUNCTION = os.environ.get('PLANNER_FUNCTION', 'alex-planner')


def invoke_portfolio_planner(user: dict, timestamp: str) -> bool:
    payload = {
        "task":     "portfolio_research",
        "user_id":  user["user_id"],
        "clerk_id": user["clerk_id"],
        "holdings": user["holdings"],
        "timestamp": timestamp,
    }
    try:
        lambda_client.invoke(
            FunctionName   = PLANNER_FUNCTION,
            InvocationType = 'Event',
            Payload        = json.dumps(payload),
        )
        logger.info(
            f"Invoked planner for {user['clerk_id']} "
            f"({len(user['holdings'])} holdings)"
        )
        return True
    except Exception as e:
        logger.error(f"Planner invoke failed for {user['clerk_id']}: {e}")
        return False


def lambda_handler(event, context):
    logger.info(f"Scheduler triggered: {json.dumps(event)}")

    timestamp     = datetime.now(UTC).isoformat()
    users_invoked = 0
    users         = get_all_portfolio_holdings()

    if not users:
        logger.info("No portfolio holdings found — nothing to research")
        return {
            "statusCode":    200,
            "users_invoked": 0,
            "message":       "No portfolio holdings",
            "timestamp":     timestamp,
        }

    for user in users:
        if invoke_portfolio_planner(user, timestamp):
            users_invoked += 1

    return {
        "statusCode":    200,
        "users_invoked": users_invoked,
        "total_users":   len(users),
        "timestamp":     timestamp,
        "message":       f"Portfolio research started for {users_invoked} users",
    }
