import boto3, time, sys

CLUSTER_ARN = 'arn:aws:rds:us-east-1:381491881089:cluster:alex-aurora'
SECRET_ARN  = 'arn:aws:secretsmanager:us-east-1:381491881089:secret:alex/aurora/credentials-2HP8fm'
DB_NAME     = 'alex_db'

rds = boto3.client('rds-data', region_name='us-east-1')

# Warm up
for i in range(8):
    try:
        rds.execute_statement(resourceArn=CLUSTER_ARN, secretArn=SECRET_ARN,
                             database=DB_NAME, sql='SELECT 1')
        print(f"  ✅ Aurora connected")
        break
    except Exception as e:
        if 'resuming' in str(e).lower() or 'paused' in str(e).lower():
            print(f"  ⏳ Aurora resuming... ({i+1}/8)")
            time.sleep(15)
        else:
            print(f"  ✅ Aurora ready")
            break

# Ensure all tables exist
tables = [
    "CREATE TABLE IF NOT EXISTS ops_snapshots (id UUID DEFAULT gen_random_uuid() PRIMARY KEY, snapshot_time TIMESTAMPTZ DEFAULT NOW(), health_status JSONB DEFAULT '{}', dost NUMERIC(10,4), digest TEXT, created_at TIMESTAMPTZ DEFAULT NOW())",
    "CREATE TABLE IF NOT EXISTS cost_snapshots (id UUID DEFAULT gen_random_uuid() PRIMARY KEY, snapshot_date DATE NOT NULL, total_cost NUMERIC(10,4), service_costs JSONB DEFAULT '{}', digest TEXT, alert_sent BOOLEAN DEFAULT false, created_at TIMESTAMPTZ DEFAULT NOW())",
    "CREATE TABLE IF NOT EXISTS cost_alerts (id UUID DEFAULT gen_random_uuid() PRIMARY KEY, alert_date DATE NOT NULL, daily_spend NUMERIC(10,4), threshold NUMERIC(10,4), message TEXT, sent_at TIMESTAMPTZ DEFAULT NOW())",
    "CREATE TABLE IF NOT EXISTS chat_sessions (id UUID DEFAULT gen_random_uuid() PRIMARY KEY, user_id UUID REFERENCES users(id), session_id VARCHAR(36) NOT NULL, messages JSONB DEFAULT '[]', created_at TIMESTAMPTZ DEFAULT NOW(), updated_at TIMESTAMPTZ DEFAULT NOW())",
    "CREATE TABLE IF NOT EXISTS research_snapshots (id UUID DEFAULT gen_random_uuid() PRIMARY KEY, user_id UUID REFERENCES users(id), ticker VARCHAR(10), snapshot TEXT, embedding vector(384), created_at TIMESTAMPTZ DEFAULT NOW())",
    "CREATE TABLE IF NOT EXISTS trading_simulations (id UUID DEFAULT gen_random_uuid() PRIMARY KEY, user_id UUID REFERENCES users(id), mode VARCHAR(20) NOT NULL DEFAULT 'neutral', status VARCHAR(20) DEFAULT 'active', initial_value NUMERIC(12,2) DEFAULT 0, current_value NUMERIC(12,2) DEFAULT 0, cash_balance NUMERIC(12,2) DEFAULT 0, total_pnl NUMERIC(12,2) DEFAULT 0, total_trades INTEGER DEFAULT 0, win_count INTEGER DEFAULT 0, loss_count INTEGER DEFAULT 0, started_at TIMESTAMPTZ DEFAULT NOW(), updated_at TIMESTAMPTZ DEFAULT NOW())",
    "CREATE TABLE IF NOT EXISTS simulated_trades (id UUID DEFAULT gen_random_uuid() PRIMARY KEY, simulation_id UUID REFERENCES trading_simulations(id), user_id UUID REFERENCES users(id), ticker VARCHAR(10) NOT NULL, action VARCHAR(10) NOT NULL, shares INTEGER DEFAULT 0, price NUMERIC(10,2) DEFAULT 0, total_value NUMERIC(12,2) DEFAULT 0, rationale TEXT, agent_votes JSONB DEFAULT '{}', agent_debate JSONB DEFAULT '[]', confidence NUMERIC(5,2) DEFAULT 0, mode VARCHAR(20), llm_used VARCHAR(100), pnl NUMERIC(12,2) DEFAULT 0, executed_at TIMESTAMPTZ DEFAULT NOW())",
    "CREATE TABLE IF NOT EXISTS agent_positions (id UUID DEFAULT gen_random_uuid() PRIMARY KEY, simulation_id UUID REFERENCES trading_simulations(id), user_id UUID REFERENCES users(id), ticker VARCHAR(10) NOT NULL, shares INTEGER DEFAULT 0, avg_cost NUMERIC(10,2) DEFAULT 0, current_price NUMERIC(10,2) DEFAULT 0, current_value NUMERIC(12,2) DEFAULT 0, pnl NUMERIC(12,2) DEFAULT 0, pnl_pct NUMERIC(8,4) DEFAULT 0, last_action VARCHAR(10), last_updated TIMESTAMPTZ DEFAULT NOW(), UNIQUE(simulation_id, ticker))",
    "CREATE TABLE IF NOT EXISTS trading_daily_pnl (id UUID DEFAULT gen_random_uuid() PRIMARY KEY, simulation_id UUID REFERENCES trading_simulations(id), user_id UUID REFERENCES users(id), trade_date DATE NOT NULL, daily_pnl NUMERIC(12,2) DEFAULT 0, daily_pnl_pct NUMERIC(8,4) DEFAULT 0, trades_count INTEGER DEFAULT 0, digest TEXT, created_at TIMESTAMPTZ DEFAULT NOW(), UNIQUE(simulation_id, trade_date))",
    "CREATE TABLE IF NOT EXISTS user_trading_config (id UUID DEFAULT gen_random_uuid() PRIMARY KEY, user_id UUID REFERENCES users(id) UNIQUE, trading_mode VARCHAR(20) DEFAULT 'neutral', autonomous BOOLEAN DEFAULT true, model_marcus VARCHAR(100) DEFAULT 'us.amazon.nova-pro-v1:0', model_victoria VARCHAR(100) DEFAULT 'us.amazon.nova-pro-v1:0', model_zara VARCHAR(100) DEFAULT 'us.amazon.nova-pro-v1:0', model_reid VARCHAR(100) DEFAULT 'us.amazon.nova-pro-v1:0', model_elena VARCHAR(100) DEFAULT 'us.amazon.nova-lite-v1:0', model_executor VARCHAR(100) DEFAULT 'us.amazon.nova-pro-v1:0', max_position_pct NUMERIC(5,2) DEFAULT 25.0, stop_loss_pct NUMERIC(5,2) DEFAULT 8.0, max_daily_trades INTEGER DEFAULT 10, created_at TIMESTAMPTZ DEFAULT NOW(), updated_at TIMESTAMPTZ DEFAULT NOW())",
    "CREATE TABLE IF NOT EXISTS ragas_evaluations (id UUID DEFAULT gen_random_uuid() PRIMARY KEY, query TEXT, response TEXT, faithfulness NUMERIC(4,3), answer_relevancy NUMERIC(4,3), context_precision NUMERIC(4,3), context_recall NUMERIC(4,3), overall_score NUMERIC(4,3), passed BOOLEAN DEFAULT false, gate VARCHAR(50), evaluated_at TIMESTAMPTZ DEFAULT NOW())",
    "CREATE TABLE IF NOT EXISTS knowledge_graph_entities (id UUID DEFAULT gen_random_uuid() PRIMARY KEY, entity_type VARCHAR(50), name VARCHAR(200), ticker VARCHAR(10), description TEXT, metadata JSONB DEFAULT '{}', created_at TIMESTAMPTZ DEFAULT NOW())",
    "CREATE TABLE IF NOT EXISTS knowledge_graph_relationships (id UUID DEFAULT gen_random_uuid() PRIMARY KEY, from_entity VARCHAR(200), relationship_type VARCHAR(100), to_entity VARCHAR(200), confidence NUMERIC(4,3) DEFAULT 1.0, source TEXT, created_at TIMESTAMPTZ DEFAULT NOW())",
    "CREATE TABLE IF NOT EXISTS agent_performance (id UUID DEFAULT gen_random_uuid() PRIMARY KEY, agent_name VARCHAR(50), ticker VARCHAR(10), action VARCHAR(10), confidence NUMERIC(5,2), outcome VARCHAR(20), pnl_pct NUMERIC(8,4), correct BOOLEAN, week_of DATE, created_at TIMESTAMPTZ DEFAULT NOW())",
]

ok = 0
for sql in tables:
    try:
        rds.execute_statement(resourceArn=CLUSTER_ARN, secretArn=SECRET_ARN,
                             database=DB_NAME, sql=sql)
        ok += 1
    except Exception as e:
        if 'already exists' not in str(e).lower():
            print(f"  ⚠️  {str(e)[:60]}")

print(f"  ✅ {ok}/{len(tables)} tables verified")
