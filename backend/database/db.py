"""
Aurora database helper for Alex.
Uses RDS Data API — no persistent connections needed.
Works perfectly with Lambda serverless architecture.
"""
import os
import json
import boto3
import logging
from datetime import datetime, UTC
from typing import Optional

logger = logging.getLogger(__name__)

# Initialize RDS Data API client
rds_client = boto3.client('rds-data', region_name=os.environ.get('AWS_REGION', 'us-east-1'))

# Config from environment
CLUSTER_ARN = os.environ.get('DB_CLUSTER_ARN')
SECRET_ARN  = os.environ.get('DB_SECRET_ARN')
DB_NAME     = os.environ.get('DB_NAME', 'alex_db')


def execute_sql(sql: str, parameters: list = None) -> dict:
    """
    Execute SQL via RDS Data API.
    
    Args:
        sql:        SQL statement to execute
        parameters: List of parameter dicts for parameterized queries
        
    Returns:
        RDS Data API response
    """
    kwargs = {
        "resourceArn": CLUSTER_ARN,
        "secretArn":   SECRET_ARN,
        "database":    DB_NAME,
        "sql":         sql,
    }

    if parameters:
        kwargs["parameters"] = parameters

    try:
        response = rds_client.execute_statement(**kwargs)
        return response
    except Exception as e:
        logger.error(f"SQL execution error: {e}")
        logger.error(f"SQL: {sql}")
        raise


def create_user(clerk_id: str, email: str, name: str = None) -> dict:
    """
    Create a new user or return existing one.
    Called when user first logs in via Clerk.
    """
    sql = """
        INSERT INTO users (clerk_id, email, name)
        VALUES (:clerk_id, :email, :name)
        ON CONFLICT (clerk_id) DO UPDATE
            SET email      = EXCLUDED.email,
                name       = EXCLUDED.name,
                updated_at = NOW()
        RETURNING id, clerk_id, email, name, created_at
    """

    parameters = [
        {"name": "clerk_id", "value": {"stringValue": clerk_id}},
        {"name": "email",    "value": {"stringValue": email}},
        {"name": "name",     "value": {"stringValue": name or ""}},
    ]

    response = execute_sql(sql, parameters)
    records  = response.get("records", [])

    if records:
        return {
            "id":         records[0][0]["stringValue"],
            "clerk_id":   records[0][1]["stringValue"],
            "email":      records[0][2]["stringValue"],
            "name":       records[0][3]["stringValue"],
            "created_at": records[0][4]["stringValue"],
        }
    return None


def save_research_session(
    user_id:   str,
    topic:     str,
    result:    str,
    vector_id: str = None
) -> dict:
    """
    Save a research session to Aurora.
    Called after agent completes research.
    Links the session to the vector stored in S3 Vectors.
    """
    sql = """
        INSERT INTO research_sessions (user_id, topic, result, vector_id)
        VALUES (:user_id, :topic, :result, :vector_id)
        RETURNING id, topic, created_at
    """

    parameters = [
        {"name": "user_id",   "value": {"stringValue": user_id}},
        {"name": "topic",     "value": {"stringValue": topic}},
        {"name": "result",    "value": {"stringValue": result}},
        {"name": "vector_id", "value": {"stringValue": vector_id or ""}},
    ]

    response = execute_sql(sql, parameters)
    records  = response.get("records", [])

    if records:
        return {
            "id":         records[0][0]["stringValue"],
            "topic":      records[0][1]["stringValue"],
            "created_at": records[0][2]["stringValue"],
        }
    return None


def get_research_history(user_id: str, limit: int = 10) -> list:
    """
    Get user's research history.
    Used by frontend to show past research.
    """
    sql = """
        SELECT id, topic, result, vector_id, created_at
        FROM research_sessions
        WHERE user_id = :user_id
        ORDER BY created_at DESC
        LIMIT :limit
    """

    parameters = [
        {"name": "user_id", "value": {"stringValue": user_id}},
        {"name": "limit",   "value": {"longValue": limit}},
    ]

    response = execute_sql(sql, parameters)
    records  = response.get("records", [])

    return [
        {
            "id":         r[0]["stringValue"],
            "topic":      r[1]["stringValue"],
            "result":     r[2]["stringValue"],
            "vector_id":  r[3]["stringValue"],
            "created_at": r[4]["stringValue"],
        }
        for r in records
    ]


def add_to_portfolio(user_id: str, ticker: str, company: str) -> dict:
    """
    Add a stock to user's portfolio.
    """
    sql = """
        INSERT INTO portfolios (user_id, ticker, company)
        VALUES (:user_id, :ticker, :company)
        ON CONFLICT DO NOTHING
        RETURNING id, ticker, company, added_at
    """

    parameters = [
        {"name": "user_id",  "value": {"stringValue": user_id}},
        {"name": "ticker",   "value": {"stringValue": ticker.upper()}},
        {"name": "company",  "value": {"stringValue": company}},
    ]

    response = execute_sql(sql, parameters)
    records  = response.get("records", [])

    if records:
        return {
            "id":       records[0][0]["stringValue"],
            "ticker":   records[0][1]["stringValue"],
            "company":  records[0][2]["stringValue"],
            "added_at": records[0][3]["stringValue"],
        }
    return None


def get_portfolio(user_id: str) -> list:
    """
    Get user's portfolio.
    """
    sql = """
        SELECT id, ticker, company, added_at
        FROM portfolios
        WHERE user_id = :user_id
        ORDER BY added_at DESC
    """

    parameters = [
        {"name": "user_id", "value": {"stringValue": user_id}},
    ]

    response = execute_sql(sql, parameters)
    records  = response.get("records", [])

    return [
        {
            "id":       r[0]["stringValue"],
            "ticker":   r[1]["stringValue"],
            "company":  r[2]["stringValue"],
            "added_at": r[3]["stringValue"],
        }
        for r in records
    ]


def save_preferences(
    user_id:        str,
    risk_tolerance: str = "moderate",
    sectors:        list = None
) -> dict:
    """
    Save or update user preferences.
    """
    sectors_str = "{" + ",".join(sectors or []) + "}"

    sql = """
        INSERT INTO preferences (user_id, risk_tolerance, sectors)
        VALUES (:user_id, :risk_tolerance, :sectors)
        ON CONFLICT (user_id) DO UPDATE
            SET risk_tolerance = EXCLUDED.risk_tolerance,
                sectors        = EXCLUDED.sectors,
                updated_at     = NOW()
        RETURNING id, risk_tolerance, sectors, updated_at
    """

    parameters = [
        {"name": "user_id",        "value": {"stringValue": user_id}},
        {"name": "risk_tolerance", "value": {"stringValue": risk_tolerance}},
        {"name": "sectors",        "value": {"stringValue": sectors_str}},
    ]

    response = execute_sql(sql, parameters)
    records  = response.get("records", [])

    if records:
        return {
            "id":             records[0][0]["stringValue"],
            "risk_tolerance": records[0][1]["stringValue"],
            "updated_at":     records[0][3]["stringValue"],
        }
    return None