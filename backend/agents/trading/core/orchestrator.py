"""
Alex Trading Floor Orchestrator
Intuition: Like a head trader who assigns research
tasks to specialist analysts before market open.
Every morning it reads the user's portfolio and
spins up 6 agents to debate each holding.
"""
import os
import json
import boto3
import logging
from datetime import datetime, timezone, timedelta
from decimal import Decimal

logger = logging.getLogger(__name__)
UTC    = timezone.utc

REGION      = os.environ.get('AWS_REGION_NAME', 'us-east-1')
CLUSTER_ARN = os.environ.get('DB_CLUSTER_ARN', '')
SECRET_ARN  = os.environ.get('DB_SECRET_ARN', '')
DB_NAME     = os.environ.get('DB_NAME', 'alex_db')
QUEUE_URL   = os.environ.get('TRADING_QUEUE_URL', '')

rds    = boto3.client('rds-data', region_name=REGION)
sqs    = boto3.client('sqs',      region_name=REGION)
ssm    = boto3.client('ssm',      region_name=REGION)
bedrock = boto3.client('bedrock-runtime', region_name=REGION)


def sql(query, params=[]):
    try:
        return rds.execute_statement(
            resourceArn=CLUSTER_ARN,
            secretArn=SECRET_ARN,
            database=DB_NAME,
            sql=query,
            parameters=params
        )
    except Exception as e:
        logger.error(f"SQL error: {e}")
        return {"records": []}


def get_ssm(key, default=''):
    try:
        return ssm.get_parameter(Name=f'/alex/trading/{key}')['Parameter']['Value']
    except:
        return default


def is_trading_enabled():
    return get_ssm('enabled', 'true').lower() == 'true'


def get_user_portfolio(user_id: str) -> list:
    """
    Intuition: Before any debate, agents need to know
    what stocks are in the portfolio. This reads the
    user's actual holdings from Aurora.
    """
    try:
        r = sql(
            """
            SELECT p.ticker, p.shares, p.purchase_price,
                   p.purchase_price, (p.shares * p.purchase_price)
            FROM portfolios p
            JOIN users u ON u.id = p.user_id
            WHERE u.clerk_id = :user_id
            """,
            [{'name': 'user_id', 'value': {'stringValue': user_id}}]
        )
        holdings = []
        for row in r.get('records', []):
            holdings.append({
                'ticker':         row[0].get('stringValue', ''),
                'shares':         row[1].get('longValue', 0),
                'purchase_price': float(row[2].get('stringValue', '0') or '0'),
                'current_price':  float(row[3].get('stringValue', '0') or '0'),
                'total_value':    float(row[4].get('stringValue', '0') or '0'),
            })
        return holdings
    except Exception as e:
        logger.error(f"Portfolio error: {e}")
        return []


def get_or_create_simulation(user_id: str, mode: str, portfolio: list) -> str:
    """
    Intuition: Each user has one active simulation.
    If it doesn't exist, create it from their portfolio.
    Like opening a new paper trading account mirroring
    their real portfolio on day 1.
    """
    try:
        # Check for existing active simulation
        r = sql(
            """
            SELECT ts.id, ts.current_value FROM trading_simulations ts
            JOIN users u ON u.id = ts.user_id
            WHERE u.clerk_id = :uid AND ts.status = 'active'
            ORDER BY ts.started_at DESC LIMIT 1
            """,
            [{'name': 'uid', 'value': {'stringValue': user_id}}]
        )

        if r.get('records'):
            sim_id = r['records'][0][0]['stringValue']
            print(f"Existing simulation: {sim_id}")
            return sim_id

        # Create new simulation
        # Initial value = sum of portfolio
        initial_value = sum(h['total_value'] for h in portfolio)
        if initial_value == 0:
            initial_value = 10000  # Default $10k if no portfolio

        r2 = sql(
            """
            INSERT INTO trading_simulations
              (user_id, mode, initial_value, current_value, cash_balance)
            SELECT id, :mode, :init, :init, :cash
            FROM users WHERE clerk_id = :uid
            RETURNING id
            """,
            [
                {'name': 'mode', 'value': {'stringValue': mode}},
                {'name': 'init', 'value': {'doubleValue': initial_value}},
                {'name': 'cash', 'value': {'doubleValue': initial_value * 0.05}},
                {'name': 'uid',  'value': {'stringValue': user_id}}
            ]
        )

        sim_id = r2['records'][0][0]['stringValue']
        print(f"Created simulation: {sim_id} (${initial_value:.2f})")

        # Initialize positions from real portfolio
        for holding in portfolio:
            if holding['ticker'] and holding['shares'] > 0:
                sql(
                    """
                    INSERT INTO agent_positions
                      (simulation_id, user_id, ticker, shares, avg_cost,
                       current_price, current_value, cost_basis)
                    SELECT :sim, id, :ticker, :shares, :avg_cost,
                           :price, :value, :basis
                    FROM users WHERE clerk_id = :uid
                    ON CONFLICT (simulation_id, ticker) DO NOTHING
                    """,
                    [
                        {'name': 'sim',      'value': {'stringValue': sim_id}},
                        {'name': 'ticker',   'value': {'stringValue': holding['ticker']}},
                        {'name': 'shares',   'value': {'longValue':   holding['shares']}},
                        {'name': 'avg_cost', 'value': {'doubleValue': holding['purchase_price']}},
                        {'name': 'price',    'value': {'doubleValue': holding['current_price']}},
                        {'name': 'value',    'value': {'doubleValue': holding['total_value']}},
                        {'name': 'basis',    'value': {'doubleValue': holding['purchase_price'] * holding['shares']}},
                        {'name': 'uid',      'value': {'stringValue': user_id}}
                    ]
                )
        print(f"Initialized {len(portfolio)} positions")
        return sim_id

    except Exception as e:
        logger.error(f"Simulation error: {e}")
        return ''


def queue_agent_tasks(sim_id: str, user_id: str, portfolio: list,
                      mode: str, config: dict):
    """
    Intuition: Like a trading desk manager distributing
    research assignments. Each ticker gets analyzed by
    all 6 agents. Tasks go to SQS for parallel execution.
    """
    tasks_queued = []

    for holding in portfolio:
        ticker = holding['ticker']
        if not ticker:
            continue

        task = {
            'simulation_id': sim_id,
            'user_id':       user_id,
            'ticker':        ticker,
            'shares':        holding['shares'],
            'avg_cost':      holding['purchase_price'],
            'current_price': holding['current_price'],
            'mode':          mode,
            'config':        config,
            'timestamp':     datetime.now(UTC).isoformat()
        }

        try:
            sqs.send_message(
                QueueUrl=QUEUE_URL,
                MessageBody=json.dumps(task),
                MessageGroupId=sim_id  # FIFO ordering per simulation
            )
            tasks_queued.append(ticker)
            print(f"Queued: {ticker}")
        except Exception as e:
            print(f"Queue error for {ticker}: {e}")

    return tasks_queued


def run_direct_analysis(sim_id: str, user_id: str,
                        portfolio: list, mode: str, config: dict) -> list:
    """
    Intuition: When SQS is not available or for
    immediate analysis, run all agents in-process.
    This is the synchronous version of the trading floor.
    Slower but works without queue infrastructure.
    """
    from core.debate_engine import run_debate
    results = []

    for holding in portfolio:
        ticker = holding['ticker']
        if not ticker:
            continue

        print(f"Analyzing {ticker}...")
        try:
            result = run_debate(
                ticker        = ticker,
                holding       = holding,
                sim_id        = sim_id,
                user_id       = user_id,
                mode          = mode,
                config        = config
            )
            results.append(result)
            print(f"  {ticker}: {result.get('action')} "
                  f"(confidence: {result.get('confidence')}%)")
        except Exception as e:
            print(f"  {ticker}: Error — {e}")

    return results




def warm_aurora():
    import time
    rds_client = boto3.client('rds-data', region_name=REGION)
    for i in range(12):
        try:
            rds_client.execute_statement(
                resourceArn=CLUSTER_ARN,
                secretArn=SECRET_ARN,
                database=DB_NAME,
                sql='SELECT 1'
            )
            print(f"Aurora ready ({i+1})")
            return True
        except Exception as e:
            err = str(e).lower()
            if 'resuming' in err or 'paused' in err or 'unavailable' in err:
                print(f"Aurora resuming {i+1}/12...")
                time.sleep(10)
            else:
                print(f"Aurora ready")
                return True
    return False

def lambda_handler(event, context):
    """
    Triggered by:
      1. EventBridge (daily 9:30 AM, 2PM, 3:45PM)
      2. Manual (user clicks "Run Analysis")
      3. API Gateway (frontend request)
    """
    now      = datetime.now(UTC)
    user_id  = event.get('user_id', '')
    trigger  = event.get('trigger', 'manual')
    force    = event.get('force', False)

    print(f"Trading Orchestrator — {now.isoformat()}")
    print(f"User: {user_id} | Trigger: {trigger}")

    # Check if trading is enabled
    if not is_trading_enabled() and not force:
        return {
            'statusCode': 200,
            'body': json.dumps({'status': 'disabled', 'message': 'Trading floor is OFF'})
        }

    # Load config from SSM
    mode   = get_ssm('mode', 'neutral')
    config = {
        'mode':             mode,
        'max_position_pct': float(get_ssm('max_position_pct', '25')),
        'stop_loss_pct':    float(get_ssm('stop_loss_pct', '8')),
        'max_daily_trades': int(get_ssm('max_daily_trades', '10')),
        'models': {
            'marcus':   get_ssm('models/marcus',   'us.amazon.nova-pro-v1:0'),
            'victoria': get_ssm('models/victoria', 'us.amazon.nova-pro-v1:0'),
            'zara':     get_ssm('models/zara',     'us.amazon.nova-pro-v1:0'),
            'reid':     get_ssm('models/reid',     'us.amazon.nova-pro-v1:0'),
            'elena':    get_ssm('models/elena',    'us.amazon.nova-lite-v1:0'),
            'executor': get_ssm('models/executor', 'us.amazon.nova-pro-v1:0'),
        }
    }

    print(f"Mode: {mode} | Config: {config['models']}")

    # Get all users if no specific user
    users_to_process = []
    if user_id:
        users_to_process = [user_id]
    else:
        # Get all users with active simulations or portfolios
        r = sql("SELECT clerk_id FROM users WHERE clerk_id IS NOT NULL LIMIT 50")
        users_to_process = [row[0]['stringValue'] for row in r.get('records', [])]

    print(f"Processing {len(users_to_process)} users")

    all_results = []
    for uid in users_to_process:
        portfolio = get_user_portfolio(uid)
        if not portfolio:
            print(f"No portfolio for user {uid}")
            continue

        print(f"User {uid}: {len(portfolio)} holdings")
        sim_id = get_or_create_simulation(uid, mode, portfolio)
        if not sim_id:
            continue

        # Try SQS first, fallback to direct
        if QUEUE_URL:
            tasks = queue_agent_tasks(sim_id, uid, portfolio, mode, config)
            all_results.append({
                'user_id': uid,
                'sim_id':  sim_id,
                'queued':  tasks
            })
        else:
            results = run_direct_analysis(sim_id, uid, portfolio, mode, config)
            all_results.append({
                'user_id': uid,
                'sim_id':  sim_id,
                'results': results
            })

    return {
        'statusCode': 200,
        'body': json.dumps({
            'timestamp':   now.isoformat(),
            'trigger':     trigger,
            'mode':        mode,
            'users':       len(users_to_process),
            'results':     all_results
        })
    }
