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


def _parse_field_number(field: dict, default: float = 0.0) -> float:
    """Aurora Data API may return NUMERIC as stringValue — same pattern as portfolio API."""
    if not field:
        return default
    if 'doubleValue' in field:
        return float(field['doubleValue'])
    if 'longValue' in field:
        return float(field['longValue'])
    if 'stringValue' in field:
        try:
            return float(field['stringValue'])
        except (TypeError, ValueError):
            return default
    return default


# ============================================
# Use Case 1 — Conversation Follow-ups
# ============================================
def get_conversation_context(user_id: str, session_id: str, limit: int = 5) -> str:
    if not user_id or not session_id:
        return ""
    try:
        result = execute_sql(
            """
            SELECT cs.messages FROM chat_sessions cs
            JOIN users u ON u.id = cs.user_id
            WHERE cs.session_id = :sid AND u.clerk_id = :user_id
            ORDER BY cs.updated_at DESC LIMIT 1
            """,
            [
                {'name': 'sid',      'value': {'stringValue': session_id}},
                {'name': 'user_id',  'value': {'stringValue': user_id}},
            ]
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
def get_prior_research(query: str, user_id: str, days: int = 30, top_k: int = 3) -> str:
    try:
        embedding = embed_text(query)
        if not embedding:
            return ""

        embedding_str = "[" + ",".join(map(str, embedding)) + "]"
        cutoff        = (datetime.now(UTC) - timedelta(days=days)).isoformat()

        # user_id is Clerk ID — include global vectors (user_id NULL) + this user's vectors
        result = execute_sql(
            f"""
            SELECT rv.content, rv.topic, rv.created_at,
                   1 - (rv.embedding <=> '{embedding_str}'::vector) as similarity
            FROM research_vectors rv
            LEFT JOIN users u ON u.id = rv.user_id
            WHERE rv.created_at > :cutoff
              AND (rv.user_id IS NULL OR u.clerk_id = :user_id)
            ORDER BY rv.embedding <=> '{embedding_str}'::vector
            LIMIT :top_k
            """,
            [
                {'name': 'cutoff',   'value': {'stringValue': cutoff}},
                {'name': 'user_id',  'value': {'stringValue': user_id}},
                {'name': 'top_k',    'value': {'longValue':   top_k}}
            ]
        )

        if not result['records']:
            return ""

        relevant = []
        for row in result['records']:
            content    = row[0].get('stringValue', '')
            topic      = row[1].get('stringValue', '')
            created_at = row[2].get('stringValue', '')
            similarity = _parse_field_number(row[3], 0)

            if similarity > 0.65:
                try:
                    dt       = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                    days_ago = (datetime.now(UTC) - dt).days
                    date_str = "today" if days_ago == 0 else \
                               "yesterday" if days_ago == 1 else \
                               f"{days_ago} days ago"
                except Exception:
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
            SELECT p.ticker, p.shares, p.purchase_price
            FROM portfolios p
            JOIN users u ON u.id = p.user_id
            WHERE u.clerk_id = :user_id
            ORDER BY p.ticker
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
            if result['records']:
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
            SELECT rv.content, rv.topic
            FROM research_vectors rv
            LEFT JOIN users u ON u.id = rv.user_id
            WHERE rv.created_at > :cutoff
              AND (rv.user_id IS NULL OR u.clerk_id = :user_id)
            ORDER BY rv.embedding <=> '{embedding_str}'::vector
            LIMIT 1
            """,
            [
                {'name': 'cutoff',  'value': {'stringValue': cutoff}},
                {'name': 'user_id', 'value': {'stringValue': user_id}}
            ]
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
            """
            SELECT rv.content
            FROM research_vectors rv
            LEFT JOIN users u ON u.id = rv.user_id
            WHERE rv.created_at > NOW() - INTERVAL '30 days'
              AND (rv.user_id IS NULL OR u.clerk_id = :user_id)
            ORDER BY rv.created_at DESC
            LIMIT 20
            """,
            [{'name': 'user_id', 'value': {'stringValue': user_id}}]
        )

        if not result['records'] or len(result['records']) < 5:
            return ""

        all_content = " ".join([
            row[0].get('stringValue', '') for row in result['records']
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
            SELECT p.ticker
            FROM portfolios p
            JOIN users u ON u.id = p.user_id
            WHERE u.clerk_id = :user_id
            ORDER BY p.ticker
            """,
            [{'name': 'user_id', 'value': {'stringValue': user_id}}]
        )

        tickers     = [row[0].get('stringValue', '') for row in holdings.get('records', [])]
        suggestions = []

        for ticker in tickers[:5]:
            result = execute_sql(
                "SELECT created_at FROM research_vectors WHERE topic ILIKE :ticker ORDER BY created_at DESC LIMIT 1",
                [{'name': 'ticker', 'value': {'stringValue': f'%{ticker}%'}}]
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
                except Exception:
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
    new_content: str = "",
    fast:        bool = False,
) -> str:
    """Assemble context blocks. fast=True skips RAG embed + sector scans (~2-4s saved)."""
    from concurrent.futures import ThreadPoolExecutor, as_completed

    if fast:
        tasks = {
            'conv':      lambda: get_conversation_context(user_id, session_id),
            'portfolio': lambda: get_portfolio_context(user_id),
        }
        try:
            from query_trace import record_api
            record_api("Aurora RDS", "chat_sessions + portfolios", success=True)
        except ImportError:
            pass
    else:
        tasks = {
            'conv':       lambda: get_conversation_context(user_id, session_id),
            'prior':      lambda: get_prior_research(query, user_id),
            'portfolio':  lambda: get_portfolio_context(user_id),
            'patterns':   lambda: detect_sector_patterns(user_id),
        }
        try:
            from query_trace import record_api
            record_api("Aurora RDS", "research_vectors + chat_sessions", success=True)
            record_api("SageMaker", "alex-embedding", success=True)
        except ImportError:
            pass
        if new_content:
            tasks['contradictions'] = lambda: detect_contradictions(query, new_content, user_id)

    parts = []
    with ThreadPoolExecutor(max_workers=len(tasks)) as pool:
        futures = {pool.submit(fn): key for key, fn in tasks.items()}
        for future in as_completed(futures):
            try:
                result = future.result()
                if result:
                    parts.append(result)
            except Exception as e:
                logger.error(f"Context task {futures[future]} failed: {e}")
                try:
                    from query_trace import record_api
                    record_api("Aurora RDS", futures[future], success=False, error=str(e)[:120])
                except ImportError:
                    pass

    return "\n\n".join(parts) if parts else ""


# ============================================
# Session Management
# ============================================
def save_message(user_id: str, session_id: str, role: str, content: str):
    if not user_id or not session_id:
        return
    try:
        result = execute_sql(
            """
            SELECT cs.id, cs.messages FROM chat_sessions cs
            JOIN users u ON u.id = cs.user_id
            WHERE cs.session_id = :sid AND u.clerk_id = :user_id
            LIMIT 1
            """,
            [
                {'name': 'sid',     'value': {'stringValue': session_id}},
                {'name': 'user_id', 'value': {'stringValue': user_id}},
            ]
        )

        new_msg = {"role": role, "content": content[:2000], "time": datetime.now(UTC).isoformat()}

        if result['records']:
            messages_json = result['records'][0][1].get('stringValue', '[]')
            messages      = json.loads(messages_json)
            messages.append(new_msg)
            messages = messages[-20:]
            execute_sql(
                """
                UPDATE chat_sessions cs SET messages = :msgs::jsonb, updated_at = NOW()
                FROM users u
                WHERE cs.user_id = u.id AND cs.session_id = :sid AND u.clerk_id = :user_id
                """,
                [
                    {'name': 'msgs',    'value': {'stringValue': json.dumps(messages)}},
                    {'name': 'sid',     'value': {'stringValue': session_id}},
                    {'name': 'user_id', 'value': {'stringValue': user_id}},
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


def load_session_messages(user_id: str, session_id: str, limit: int = 30) -> list:
    """Load chat history for session hydration."""
    if not user_id or not session_id:
        return []
    try:
        result = execute_sql(
            """
            SELECT cs.messages FROM chat_sessions cs
            JOIN users u ON u.id = cs.user_id
            WHERE cs.session_id = :sid AND u.clerk_id = :user_id
            LIMIT 1
            """,
            [
                {'name': 'sid',     'value': {'stringValue': session_id}},
                {'name': 'user_id', 'value': {'stringValue': user_id}},
            ],
        )
        if not result['records']:
            return []
        raw = result['records'][0][0].get('stringValue', '[]')
        messages = json.loads(raw)
        return messages[-limit:] if len(messages) > limit else messages
    except Exception as e:
        logger.error(f"Load session error: {e}")
        return []


def sync_session_messages(user_id: str, session_id: str, messages: list) -> None:
    """Replace session messages (frontend sync)."""
    if not user_id or not session_id:
        return
    try:
        trimmed = messages[-30:]
        result = execute_sql(
            """
            SELECT cs.id FROM chat_sessions cs
            JOIN users u ON u.id = cs.user_id
            WHERE cs.session_id = :sid AND u.clerk_id = :user_id
            LIMIT 1
            """,
            [
                {'name': 'sid',     'value': {'stringValue': session_id}},
                {'name': 'user_id', 'value': {'stringValue': user_id}},
            ],
        )
        payload = json.dumps(trimmed)
        if result['records']:
            execute_sql(
                """
                UPDATE chat_sessions cs SET messages = :msgs::jsonb, updated_at = NOW()
                FROM users u
                WHERE cs.user_id = u.id AND cs.session_id = :sid AND u.clerk_id = :user_id
                """,
                [
                    {'name': 'msgs',    'value': {'stringValue': payload}},
                    {'name': 'sid',     'value': {'stringValue': session_id}},
                    {'name': 'user_id', 'value': {'stringValue': user_id}},
                ],
            )
        else:
            execute_sql(
                """
                INSERT INTO chat_sessions (user_id, session_id, messages)
                SELECT id, :sid, :msgs::jsonb
                FROM users WHERE clerk_id = :user_id
                """,
                [
                    {'name': 'sid',     'value': {'stringValue': session_id}},
                    {'name': 'msgs',    'value': {'stringValue': payload}},
                    {'name': 'user_id', 'value': {'stringValue': user_id}},
                ],
            )
    except Exception as e:
        logger.error(f"Sync session error: {e}")
