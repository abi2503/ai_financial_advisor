"""
Context Service — pgvector-powered memory for Alex.
Implements all 6 use cases of semantic memory.
"""
import os
import json
import boto3
import logging
from datetime import datetime, timezone, timedelta

logger = logging.getLogger(__name__)
UTC    = timezone.utc

CLUSTER_ARN = os.environ.get('DB_CLUSTER_ARN', '')
SECRET_ARN  = os.environ.get('DB_SECRET_ARN', '')
DB_NAME     = os.environ.get('DB_NAME', 'alex_db')
SM_ENDPOINT = os.environ.get('SAGEMAKER_ENDPOINT', 'alex-embedding')
REGION      = os.environ.get('AWS_REGION', 'us-east-1')

rds       = boto3.client('rds-data',        region_name=REGION)
sagemaker = boto3.client('sagemaker-runtime', region_name=REGION)


def execute_sql(sql: str, params: list = []) -> dict:
    try:
        return rds.execute_statement(
            resourceArn = CLUSTER_ARN,
            secretArn   = SECRET_ARN,
            database    = DB_NAME,
            sql         = sql,
            parameters  = params
      )
    except Exception as e:
        logger.error(f"SQL error: {e}")
        return {"records": []}


def embed_text(text: str) -> list:
    try:
        response = sagemaker.invoke_endpoint(
            EndpointName = SM_ENDPOINT,
            ContentType  = 'application/json',
            Body         = json.dumps({"inputs": text[:512]})
        )
        result = json.loads(response['Body'].read())
        if isinstance(result, list):
            embedding = result[0] if isinstance(result[0], list) else result
            if isinstance(embedding[0], list):
                embedding = embedding[0]
            return embedding
        return result
    except Exception as e:
        logger.error(f"Embedding error: {e}")
        return []


# ============================================
# Use Case 1 — Conversation Follow-ups
# ============================================
def get_conversation_context(user_id: str, session_id: str, limit: int = 5) -> str:
    try:
        result = execute_sql(
            "LECT messages FROM chat_sessions WHERE session_id = :sid ORDER BY updated_at DESC LIMIT 1",
            [{'name': 'sid', 'value': {'stringValue': session_id}}]
        )
        if not result['records']:
            return ""

        messages_json = result['records'][0][0].get('stringValue', '[]')
        messages      = json.loads(messages_json)
        recent        = messages[-limit:] if len(messages) > limit else messages

        if not recent:
            return ""

        formatted = "\n".join([
            f"{m['role'].upper()}: {m['content'][:300]}"
            for m in recent
        ])

        return f"\nCONVERSATION HISTORY (last {len(recent)} messages):\n{formatted}\n\nUse this to answer follow-up questions naturally.\n"
    except Exception as e:
        logger.error(f"Conversation context error: {e}")
        return ""


# ============================================
# Use Case 2 — Cross-Session Memory
# ============================================
def get_prior_research(query: str, userd: str, days: int = 30, top_k: int = 3) -> str:
    try:
        embedding = embed_text(query)
        if not embedding:
            return ""

        embedding_str = "[" + ",".join(map(str, embedding)) + "]"
        cutoff        = (datetime.now(UTC) - timedelta(days=days)).isoformat()

        result = execute_sql(
            f"""
            SELECT content, topic, created_at,
                   1 - (embedding <=> '{embedding_str}'::vector) as similarity
            FROM research_vectors
            WHERE created_at > :cutoff
            ORDER BY embedding <=> '{embedding_str}'::vector
            LIMIT :top_k
            """,
            [
                {'name': 'cutoff', 'value': {'stringValue': cutoff}},
                {'name': 'top_k',  'value': {'longValue':   top_k}}
            ]
        )

        if not result['records']:
            return ""

        relevant = []
        for row in result['records']:
            content    = row[0].get('stringValue', '')
            topic      = row[1].get('stringValue', '')
            created_at = row[2].get('stringValue', '')
            similarity = row[3].get('doubleValue',  0)

            if similarity > 0.65:
                try:
                    dt       = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                    days_ago = (datetime.now(UTC) - dt).days
                    date_str = "today" if days_ago == 0 else \
                               "yesterday" if days_ago == 1 else \
                               f"{days_ago} days ago"
                except:
                    date_str = "recently"

                relevant.append(f"[{date_str} - {topic}]\n{content[:400]}")

        if not relevant:
            return ""

        return f"\nPRIOR RESEARCH FROM KNOWLEDGE BASE:\n{'='*40}\n" + \
               "\n\n".join(relevant) + \
               f"\n{'='*40}\nReference this to give more informed answers.\n"

    except Exception as e:
        logger.error(f"Prior research error: {e}")
        return ""


# ============================================
# Use Case 3 — Portfolio Intelligence
# ============================================
def get_portfolio_context(user_id: str) -> str:
    try:
        holdings = execute_sql(
            """
            SELECT ps.ticker, ps.shares, ps.purchase_price
            FROM portfolio_stocks ps
            JOIN users u ON u.id = ps.user_id
            WHERE u.clerk_id = :user_id
            """,
            [{'name': 'user_id', 'value': {'stringValue': user_id}}]
        )

        if not holdings['records']:
            return ""

        tickers = [row[0].get('stringValue', '') for row in holdings['records']]
        if not tickers:
            return ""

        portfolio_context = []
        for ticker in tickers:
            result = execute_sql(
                "SELECT content, created_at FROM research_vectors WHERE topic ILIKE :ticker ORDER BY created_at DESC LIMIT 1",
                [{'name': 'ticker', 'value': {'stringValue': f'%{ticker}%'}}]
            )
            if result[ecords']:
                content = result['records'][0][0].get('stringValue', '')
                portfolio_context.append(f"{ticker}: {content[:300]}")

        holdings_str = ", ".join(tickers)
        context_str  = "\n".join(portfolio_context) if portfolio_context else "No research yet"

        return f"\nUSER PORTFOLIO: {holdings_str}\n\nRecent research:\n{context_str}\n\nUse for portfolio-aware answers.\n"

    except Exception as e:
        logger.error(f"Portfolio context error: {e}")
        return ""


# ============================================
# Use Case 4 — Contradiction Detection
# ============================================
def detect_contradictions(query: str, new_content: str, user_id: str) -> str:
    try:
        embedding = embed_text(query)
        if not embedding:
            return ""

        embedding_str = "[" + ",".join(map(str, embedding)) + "]"
        cutoff        = (datetime.now(UTC) - timedelta(days=14)).isoformat()

        result = execute_sql(
            f"""
          SELECT content, topic
            FROM research_vectors
            WHERE created_at > :cutoff
            ORDER BY embedding <=> '{embedding_str}'::vector
            LIMIT 1
            """,
            [{'name': 'cutoff', 'value': {'stringValue': cutoff}}]
        )

        if not result['records']:
            return ""

        prior_content = result['records'][0][0].get('stringValue', '')
        change_signals = [
            ('GUIDANCE',  ['raised', 'lowered', 'cut', 'revised', 'reduced']),
            ('REVENUE',   ['declined', 'missed', 'beat', 'fell', 'surged']),
            ('RATING',    ['upgrade', 'downgrade', 'buy', 'sell', 'hold']),
            ('EARNINGS',  ['beat', 'missed', 'inline', 'surprise']),
        ]

        changes = []
        new_lower   = new_content.lower()
        prior_lower = prior_content.lower()

        for signal, keywords in change_signals:
            new_kws   = [kw for kw in keywords if kw in new_lower]
            prior_kws = [kw for kw in keywords if kw in prior_lower]
            if new_kws and prior_kws and new_kws != prior_kws:
                changes.append(f"  {signal}: was '{prior_kws[0]}' now '{new_kws[0]}'")

        if not changes:
            return ""

        return f"\nIMPORTANT CHANGES vs prior research:\n" + "\n".join(changes) + \
               "\nProactively inform the user about these changes.\n"

    except Exception as e:
        logger.error(f"Contradiction detection error: {e}")
        return ""


# ============================================
# Use Case 5 — Sector Pattern Recognition
# ============================================
def detect_sector_patterns(user_id: str) -> str:
    try:
        result = execute_sql(
            "SELECT content FROM research_vectors WHERE created_at > NOW() - INTERVAL '30 days' ORDER BY created_at DESC LIMIT 20"
        )

        if not result['records'] or len(result['records']) < 5:
            return ""

        all_content = " ".join([
            row[0].get('stringValue', '') for row in resul'records']
        ]).lower()

        patterns = {
            'AI Capex Concerns':    ['capex', 'ai spending', 'infrastructure cost'],
            'Margin Pressure':      ['margin compression', 'margin pressure', 'declining margins'],
            'Analyst Downgrades':   ['downgrade', 'price target cut', 'reduce rating'],
            'Rate Sensitivity':     ['interest rate', 'fed rate', 'rate hike'],
            'China Risk':           ['china risk', 'geopolitical', 'export restriction'],
            'Earnings Beats':       ['beat estimates', 'exceeded expectations', 'earnings beat'],
            'Revenue Growth':       ['revenue growth', 'top line growth', 'strong revenue'],
        }

        found = []
        for name, keywords in patterns.items():
            count = sum(1 for kw in keywords if kw in all_content)
            if count >= 2:
                found.append(f"  - {name}")

        if not found:
            return ""

        return f"\nSECTOR PATTERNS across recent research:\n" + "\n".join(found) + \
               "\nMention if relevant to query.\n"

    except Exception as e:
        logger.error(f"Pattern detection error: {e}")
        return ""


# ============================================
# Use Case 6 — Proactive Suggestions
# ============================================
def get_proactive_suggestions(user_id: str) -> dict:
    try:
        holdings = execute_sql(
            """
            SELECT ps.ticker
            FROM portfolio_stocks ps
            JOIN users u ON u.id = ps.user_id
            WHERE u.clerk_id = :user_id
            """,
            [{'name': 'user_id', 'value': {'stringValue': user_id}}]
        )

        tickers     = [row[0].get('stringValue', '') for row in holdings.get('records', [])]
        suggestions = []

        for ticker in tickers[:5]:
            result = execute_sql(
                "SELECT created_at FROM research_vectors WHERE topic ILIKE :ticker ORDER BY created_at DESC LIMIT 1",
                [{'name': 'ticker', 'value': {'stringValue':'%{ticker}%'}}]
            )

            if result['records']:
                created_at = result['records'][0][0].get('stringValue', '')
                try:
                    dt       = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                    days_ago = (datetime.now(UTC) - dt).days
                    if days_ago >= 3:
                        suggestions.append({
                            "ticker":   ticker,
                            "message":  f"{ticker} — last researched {days_ago} days ago",
                            "action":   f"Update {ticker} analysis",
                            "priority": "high" if days_ago >= 7 else "medium"
                        })
                except:
                    pass
            else:
                suggestions.append({
                    "ticker":   ticker,
                    "message":  f"{ticker} — no research yet",
                    "action":   f"Research {ticker}",
                    "priority": "high"
            })

        return {"suggestions": suggestions[:3], "has_suggestions": len(suggestions) > 0}

    except Exception as e:
        logger.error(f"Suggestions error: {e}")
        return {"suggestions": [], "has_suggestions": False}


# ============================================
# Master Context Builder
# ============================================
def build_full_context(
    query:       str,
    user_id:     str,
    session_id:  str,
    new_content: str = ""
) -> str:
    parts = []

    conv = get_conversation_context(user_id, session_id)
    if conv:
        parts.append(conv)

    prior = get_prior_research(query, user_id)
    if prior:
        parts.append(prior)

    portfolio = get_portfolio_context(user_id)
    if portfolio:
        parts.append(portfolio)

    if new_content:
        contradictions = detect_contradictions(query, new_content, user_id)
        if contradictions:
            parts.append(contradictions)

    patterns = detect_sector_patterns(user_id)
    if patterns:
        parts.append(patterns)

    return "\n\n".join(parts) if parts else ""


# ============================================
# Session Management
# ============================================
def save_message(user_id: str, session_id: str, role: str, content: str):
    try:
        result = execute_sql(
            "SELECT id, messages FROM chat_sessions WHERE session_id = :sid LIMIT 1",
            [{'name': 'sid', 'value': {'stringValue': session_id}}]
        )

        new_msg = {"role": role, "content": content[:2000], "time": datetime.now(UTC).isoformat()}

        if result['records']:
            session_id_db = result['records'][0][0].get('stringValue', '')
            messages_json = result['records'][0][1].get('stringValue', '[]')
            messages      = json.loads(messages_json)
            messages.append(new_msg)
            # Keep last 20 messages
            messages = messages[-20:]
            execute_sql(
                "UPDATE chat_sessions SET messages = :msgs::jsonb, updated_at = NOW() WHERE session_id = :sid",
                [
                    {'name': 'msgs', 'value': {'stringValue': json.dumps(messages)}},
                    {'name': 'sid',  'value': {'stringValue': session_id}}
                ]
            )
        else:
            messages = [new_msg]
            execute_sql(
                """
                INSERT INTO chat_sessions (user_id, session_id, messages)
                SELECT id, :sid, :msgs::jsonb
                FROM users WHERE clerk_id = :user_id
                """,
                [
                    {'name': 'sid',     'value': {'stringValue': session_id}},
                    {'name': 'msgs',    'value': {'stringValue': json.dumps(messages)}},
                    {'name': 'user_id', 'value': {'stringValue': user_id}}
                ]
            )
    except Exception as e:
        logger.error(f"Save message error: {e}")
