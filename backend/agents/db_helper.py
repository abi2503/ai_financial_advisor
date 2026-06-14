"""
Shared Aurora RDS Data API helper for agent Lambdas.
"""
import os
import time
import boto3
import logging

logger = logging.getLogger(__name__)

REGION      = os.environ.get('AWS_REGION_NAME', os.environ.get('AWS_REGION', 'us-east-1'))
CLUSTER_ARN = os.environ.get('DB_CLUSTER_ARN', '')
SECRET_ARN  = os.environ.get('DB_SECRET_ARN', '')
DB_NAME     = os.environ.get('DB_NAME', 'alex_db')

rds_client = boto3.client('rds-data', region_name=REGION)


def execute_sql(sql: str, parameters: list = None, max_retries: int = 3) -> dict:
    if not CLUSTER_ARN or not SECRET_ARN:
        logger.warning("DB_CLUSTER_ARN or DB_SECRET_ARN not configured")
        return {"records": []}

    kwargs = {
        "resourceArn": CLUSTER_ARN,
        "secretArn":   SECRET_ARN,
        "database":    DB_NAME,
        "sql":         sql,
    }
    if parameters:
        kwargs["parameters"] = parameters

    for attempt in range(max_retries):
        try:
            return rds_client.execute_statement(**kwargs)
        except rds_client.exceptions.DatabaseResumingException:
            wait = 15 * (attempt + 1)
            logger.warning(f"Aurora resuming — waiting {wait}s")
            time.sleep(wait)
        except Exception as e:
            if 'resuming' in str(e).lower() or 'paused' in str(e).lower():
                time.sleep(15 * (attempt + 1))
            else:
                logger.error(f"SQL error: {e}")
                raise

    return {"records": []}


def get_all_portfolio_holdings() -> list:
    """Return all active holdings grouped by user."""
    response = execute_sql(
        """
        SELECT u.id::text, u.clerk_id, p.ticker, COALESCE(p.company, p.ticker), p.shares
        FROM portfolios p
        JOIN users u ON u.id = p.user_id
        WHERE p.shares > 0
        ORDER BY u.clerk_id, p.ticker
        """
    )

    users = {}
    for row in response.get("records", []):
        user_id  = row[0].get("stringValue", "")
        clerk_id = row[1].get("stringValue", "")
        ticker   = row[2].get("stringValue", "")
        company  = row[3].get("stringValue", ticker)
        shares   = float(row[4].get("doubleValue") or row[4].get("stringValue") or 0)

        if not user_id or not ticker:
            continue

        if user_id not in users:
            users[user_id] = {
                "user_id":  user_id,
                "clerk_id": clerk_id,
                "holdings": [],
            }
        users[user_id]["holdings"].append({
            "ticker":  ticker,
            "company": company,
            "shares":  shares,
        })

    return list(users.values())
