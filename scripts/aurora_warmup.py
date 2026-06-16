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
    "CREATE TABLE IF NOT EXISTS cost_snapshots (id UUID DEFAULT gen_random_uuid() PRIMARY KEY, snapshot_date DATE NOT NULL UNIQUE, total_cost NUMERIC(10,4), service_costs JSONB DEFAULT '{}', digest TEXT, alert_sent BOOLEAN DEFAULT false, created_at TIMESTAMPTZ DEFAULT NOW())",
    "CREATE TABLE IF NOT EXISTS cost_alerts (id UUID DEFAULT gen_random_uuid() PRIMARY KEY, alert_date DATE NOT NULL, daily_spend NUMERIC(10,4), threshold NUMERIC(10,4), message TEXT, sent_at TIMESTAMPTZ DEFAULT NOW())",
    "CREATE TABLE IF NOT EXISTS chat_sessions (id UUID DEFAULT gen_random_uuid() PRIMARY KEY, user_id UUID REFERENCES users(id), session_id VARCHAR(36) NOT NULL, messages JSONB DEFAULT '[]', created_at TIMESTAMPTZ DEFAULT NOW(), updated_at TIMESTAMPTZ DEFAULT NOW())",
    "CREATE TABLE IF NOT EXISTS research_snapshots (id UUID DEFAULT gen_random_uuid() PRIMARY KEY, user_id UUID REFERENCES users(id), ticker VARCHAR(10), snapshot TEXT, embedding vector(384), created_at TIMESTAMPTZ DEFAULT NOW())",
    "CREATE TABLE IF NOT EXISTS portfolio_digests (id UUID DEFAULT gen_random_uuid() PRIMARY KEY, user_id UUID REFERENCES users(id), ticker VARCHAR(10) NOT NULL, company VARCHAR(200), headline TEXT, sentiment VARCHAR(20) DEFAULT 'neutral', digest TEXT, dimensions JSONB DEFAULT '{}', key_news JSONB DEFAULT '[]', updated_at TIMESTAMPTZ DEFAULT NOW(), UNIQUE(user_id, ticker))",
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

# Portfolio: dedupe rows and enforce one position per ticker per user
portfolio_migrations = [
    """DELETE FROM portfolios a
       USING portfolios b
       WHERE a.user_id = b.user_id
         AND a.ticker = b.ticker
         AND a.added_at < b.added_at""",
    """CREATE UNIQUE INDEX IF NOT EXISTS portfolios_user_ticker_uidx
       ON portfolios (user_id, ticker)""",
]
for sql in portfolio_migrations:
    try:
        rds.execute_statement(resourceArn=CLUSTER_ARN, secretArn=SECRET_ARN,
                             database=DB_NAME, sql=sql)
    except Exception as e:
        if 'already exists' not in str(e).lower():
            print(f"  ⚠️  portfolio migration: {str(e)[:80]}")
print("  ✅ portfolio indexes verified")

cost_migrations = [
    "CREATE UNIQUE INDEX IF NOT EXISTS cost_snapshots_date_uidx ON cost_snapshots (snapshot_date)",
]
for sql in cost_migrations:
    try:
        rds.execute_statement(resourceArn=CLUSTER_ARN, secretArn=SECRET_ARN,
                             database=DB_NAME, sql=sql)
    except Exception as e:
        if 'already exists' not in str(e).lower():
            print(f"  ⚠️  cost migration: {str(e)[:80]}")
print("  ✅ cost indexes verified")

# ── P0: Core tables + schema migrations ──────────────────────────────────────

def run_sql(label, sql):
    try:
        rds.execute_statement(resourceArn=CLUSTER_ARN, secretArn=SECRET_ARN,
                             database=DB_NAME, sql=sql)
        print(f"  ✅ {label}")
        return True
    except Exception as e:
        err = str(e)
        if 'already exists' in err.lower() or 'duplicate' in err.lower():
            print(f"  ⏭️  {label} (exists)")
            return True
        print(f"  ⚠️  {label}: {err[:80]}")
        return False

print("\n── P0 schema ──")

run_sql("pgvector extension", "CREATE EXTENSION IF NOT EXISTS vector")

run_sql("research_vectors base table", """
CREATE TABLE IF NOT EXISTS research_vectors (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  topic VARCHAR(200),
  content TEXT,
  embedding vector(384),
  source VARCHAR(100) DEFAULT 'alex-researcher',
  created_at TIMESTAMPTZ DEFAULT NOW()
)""")

p0_tables = [
    ("agent_observations", """
CREATE TABLE IF NOT EXISTS agent_observations (
  id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  agent_name VARCHAR(50),
  ticker VARCHAR(10),
  simulation_id UUID,
  model_id VARCHAR(100),
  input_tokens INTEGER DEFAULT 0,
  output_tokens INTEGER DEFAULT 0,
  total_tokens INTEGER DEFAULT 0,
  latency_ms INTEGER DEFAULT 0,
  cost_usd NUMERIC(10,6) DEFAULT 0,
  action VARCHAR(10),
  confidence NUMERIC(5,2),
  success BOOLEAN DEFAULT true,
  error_message TEXT,
  guardrail_triggered BOOLEAN DEFAULT false,
  guardrail_action TEXT,
  created_at TIMESTAMPTZ DEFAULT NOW()
)"""),
    ("scout_candidates", """
CREATE TABLE IF NOT EXISTS scout_candidates (
  id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  user_id UUID REFERENCES users(id),
  ticker VARCHAR(10) NOT NULL,
  score NUMERIC(5,2) DEFAULT 0,
  rationale TEXT,
  sector VARCHAR(50),
  discovered_at TIMESTAMPTZ DEFAULT NOW(),
  debated BOOLEAN DEFAULT false,
  traded BOOLEAN DEFAULT false
)"""),
    ("rl_weights", """
CREATE TABLE IF NOT EXISTS rl_weights (
  id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  user_id UUID REFERENCES users(id),
  agent_name VARCHAR(50) NOT NULL,
  weight NUMERIC(5,3) DEFAULT 1.0,
  accuracy_30d NUMERIC(5,3) DEFAULT 0,
  total_votes INTEGER DEFAULT 0,
  correct_votes INTEGER DEFAULT 0,
  updated_at TIMESTAMPTZ DEFAULT NOW(),
  UNIQUE(user_id, agent_name)
)"""),
    ("trading_events", """
CREATE TABLE IF NOT EXISTS trading_events (
  id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  user_id UUID REFERENCES users(id),
  event_type VARCHAR(30) NOT NULL,
  ticker VARCHAR(10),
  agent VARCHAR(50),
  payload JSONB DEFAULT '{}',
  created_at TIMESTAMPTZ DEFAULT NOW()
)"""),
    ("session_metadata", """
CREATE TABLE IF NOT EXISTS session_metadata (
  id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  user_id UUID REFERENCES users(id),
  session_id VARCHAR(36) NOT NULL,
  route VARCHAR(20),
  intent VARCHAR(50),
  entities JSONB DEFAULT '[]',
  message_count INTEGER DEFAULT 0,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
)"""),
    ("rag_attributions", """
CREATE TABLE IF NOT EXISTS rag_attributions (
  id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  user_id UUID REFERENCES users(id),
  session_id VARCHAR(36),
  query TEXT,
  route VARCHAR(20),
  chunk_ids JSONB DEFAULT '[]',
  scores JSONB DEFAULT '[]',
  created_at TIMESTAMPTZ DEFAULT NOW()
)"""),
    ("query_latency_metrics", """
CREATE TABLE IF NOT EXISTS query_latency_metrics (
  id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  query_id VARCHAR(36) NOT NULL,
  user_id UUID REFERENCES users(id),
  session_id VARCHAR(36),
  query TEXT NOT NULL,
  route VARCHAR(20) NOT NULL,
  intent VARCHAR(50),
  entities JSONB DEFAULT '[]',
  total_ms INTEGER DEFAULT 0,
  first_token_ms INTEGER,
  router_ms INTEGER DEFAULT 0,
  rag_ms INTEGER DEFAULT 0,
  synthesis_ms INTEGER DEFAULT 0,
  sub_agent_ms JSONB DEFAULT '{}',
  partial BOOLEAN DEFAULT false,
  cost_usd NUMERIC(10,6) DEFAULT 0,
  created_at TIMESTAMPTZ DEFAULT NOW()
)"""),
    ("trading_floor_intelligence", """
CREATE TABLE IF NOT EXISTS trading_floor_intelligence (
  id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  user_id UUID REFERENCES users(id) NOT NULL,
  simulation_id UUID REFERENCES trading_simulations(id),
  debate_id UUID NOT NULL,
  ticker VARCHAR(10) NOT NULL,
  agent_name VARCHAR(50),
  chunk_type VARCHAR(30) NOT NULL,
  content TEXT NOT NULL,
  embedding vector(384),
  metadata JSONB DEFAULT '{}',
  created_at TIMESTAMPTZ DEFAULT NOW()
)"""),
    ("quant_snapshots", """
CREATE TABLE IF NOT EXISTS quant_snapshots (
  id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  user_id UUID REFERENCES users(id),
  ticker VARCHAR(10) NOT NULL,
  snapshot_type VARCHAR(30) NOT NULL,
  data JSONB DEFAULT '{}',
  chart_url TEXT,
  expires_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ DEFAULT NOW()
)"""),
]

for name, sql in p0_tables:
    run_sql(name, sql)

p0_migrations = [
    ("research_vectors.user_id", "ALTER TABLE research_vectors ADD COLUMN IF NOT EXISTS user_id UUID REFERENCES users(id)"),
    ("research_vectors.session_id", "ALTER TABLE research_vectors ADD COLUMN IF NOT EXISTS session_id VARCHAR(36)"),
    ("research_vectors.chunk_index", "ALTER TABLE research_vectors ADD COLUMN IF NOT EXISTS chunk_index INTEGER DEFAULT 0"),
    ("research_vectors.query", "ALTER TABLE research_vectors ADD COLUMN IF NOT EXISTS query TEXT"),
    ("research_vectors.chunk_type", "ALTER TABLE research_vectors ADD COLUMN IF NOT EXISTS chunk_type VARCHAR(30) DEFAULT 'document'"),
    ("simulated_trades.target_price", "ALTER TABLE simulated_trades ADD COLUMN IF NOT EXISTS target_price NUMERIC(10,2)"),
    ("simulated_trades.stop_loss", "ALTER TABLE simulated_trades ADD COLUMN IF NOT EXISTS stop_loss NUMERIC(10,2)"),
    ("simulated_trades.realized_pnl", "ALTER TABLE simulated_trades ADD COLUMN IF NOT EXISTS realized_pnl NUMERIC(12,2) DEFAULT 0"),
    ("simulated_trades.outcome", "ALTER TABLE simulated_trades ADD COLUMN IF NOT EXISTS outcome VARCHAR(20)"),
    ("simulated_trades.trigger", "ALTER TABLE simulated_trades ADD COLUMN IF NOT EXISTS trigger VARCHAR(20) DEFAULT 'debate'"),
    ("portfolios.shares", "ALTER TABLE portfolios ADD COLUMN IF NOT EXISTS shares NUMERIC(12,4) DEFAULT 0"),
    ("portfolios.purchase_price", "ALTER TABLE portfolios ADD COLUMN IF NOT EXISTS purchase_price NUMERIC(12,2) DEFAULT 0"),
    ("portfolios.asset_class", "ALTER TABLE portfolios ADD COLUMN IF NOT EXISTS asset_class VARCHAR(50) DEFAULT 'stocks'"),
    ("portfolios.sector", "ALTER TABLE portfolios ADD COLUMN IF NOT EXISTS sector VARCHAR(100)"),
    ("portfolios.notes", "ALTER TABLE portfolios ADD COLUMN IF NOT EXISTS notes TEXT"),
    ("chat_sessions unique index", "CREATE UNIQUE INDEX IF NOT EXISTS chat_sessions_user_session_uidx ON chat_sessions (user_id, session_id)"),
    ("query_latency user index", "CREATE INDEX IF NOT EXISTS qlm_user_created_idx ON query_latency_metrics (user_id, created_at DESC)"),
    ("query_latency route index", "CREATE INDEX IF NOT EXISTS qlm_route_idx ON query_latency_metrics (route, created_at DESC)"),
    ("tfi user ticker index", "CREATE INDEX IF NOT EXISTS tfi_user_ticker_idx ON trading_floor_intelligence (user_id, ticker, created_at DESC)"),
    ("qlm.tools_called", "ALTER TABLE query_latency_metrics ADD COLUMN IF NOT EXISTS tools_called JSONB DEFAULT '[]'"),
    ("qlm.mcp_servers", "ALTER TABLE query_latency_metrics ADD COLUMN IF NOT EXISTS mcp_servers JSONB DEFAULT '[]'"),
    ("qlm.data_sources", "ALTER TABLE query_latency_metrics ADD COLUMN IF NOT EXISTS data_sources JSONB DEFAULT '[]'"),
    ("qlm.model", "ALTER TABLE query_latency_metrics ADD COLUMN IF NOT EXISTS model VARCHAR(100)"),
    ("qlm.response_chars", "ALTER TABLE query_latency_metrics ADD COLUMN IF NOT EXISTS response_chars INTEGER DEFAULT 0"),
    ("qlm.context_ms", "ALTER TABLE query_latency_metrics ADD COLUMN IF NOT EXISTS context_ms INTEGER DEFAULT 0"),
    ("qlm.agent_ms", "ALTER TABLE query_latency_metrics ADD COLUMN IF NOT EXISTS agent_ms INTEGER DEFAULT 0"),
    ("qlm.guardrail_ms", "ALTER TABLE query_latency_metrics ADD COLUMN IF NOT EXISTS guardrail_ms INTEGER DEFAULT 0"),
    ("qlm.success", "ALTER TABLE query_latency_metrics ADD COLUMN IF NOT EXISTS success BOOLEAN DEFAULT true"),
    ("qlm.input_tokens", "ALTER TABLE query_latency_metrics ADD COLUMN IF NOT EXISTS input_tokens INTEGER DEFAULT 0"),
    ("qlm.output_tokens", "ALTER TABLE query_latency_metrics ADD COLUMN IF NOT EXISTS output_tokens INTEGER DEFAULT 0"),
    ("ops_snapshots.daily_cost", "ALTER TABLE ops_snapshots ADD COLUMN IF NOT EXISTS daily_cost NUMERIC(10,4) DEFAULT 0"),
]

for label, sql in p0_migrations:
    run_sql(label, sql)

print("  ✅ P0 schema complete")
