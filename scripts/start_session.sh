#!/bin/bash
# ============================================
# Alex AI — Reliable Session Starter
# Handles ALL infrastructure automatically
# ============================================
set -e
cd "$(dirname "$0")/.."

echo ""
echo "🚀 Starting Alex AI Development Session"
echo "========================================"
echo "$(date)"
echo ""

# Load env vars
if [ -f ".env" ]; then
  set -a
  source <(grep -v '^#' .env | sed 's/ *= */=/g')
  set +a
else
  echo "❌ .env not found"
  exit 1
fi

REGION=${DEFAULT_AWS_REGION:-us-east-1}
CLUSTER_ARN="arn:aws:rds:us-east-1:381491881089:cluster:alex-aurora"
SECRET_ARN="arn:aws:secretsmanager:us-east-1:381491881089:secret:alex/aurora/credentials-2HP8fm"
DB_NAME="alex_db"

# ============================================
# Helper functions
# ============================================
check_pass() { echo "  ✅ $1"; }
check_fail() { echo "  ❌ $1"; }
check_warn() { echo "  ⚠️  $1"; }
check_wait() { echo "  ==========================================
# Step 0 — Fix IAM trust policies (always)
# ============================================
echo "🔐 Step 0: Fixing IAM trust policies..."
aws iam update-assume-role-policy \
  --role-name alex-sagemaker-role \
  --policy-document '{"Version":"2012-10-17","Statement":[{"Effect":"Allow","Principal":{"Service":"sagemaker.amazonaws.com"},"Action":"sts:AssumeRole"}]}' 2>/dev/null && \
  check_pass "SageMaker role trust policy verified" || \
  check_warn "SageMaker role update skipped"

# ============================================
# Step 1 — SageMaker
# ============================================
echo ""
echo "🧠 Step 1: SageMaker embedding endpoint..."

SM_STATUS=$(aws sagemaker describe-endpoint \
  --endpoint-name alex-embedding \
  --region $REGION \
  --query "EndpointStatus" \
  --output text 2>/dev/null || echo "NOT_FOUND")

echo "  Status: $SM_STATUS"

if [ "$SM_STATUS" = "InService" ]; then
  check_pass "SageMaker running"

elif [ "$SM_STATUS" = "Creat| [ "$SM_STATUS" = "Updating" ]; then
  check_wait "Waiting for SageMaker..."
  aws sagemaker wait endpoint-in-service \
    --endpoint-name alex-embedding \
    --region $REGION
  check_pass "SageMaker ready"

elif [ "$SM_STATUS" = "Failed" ] || [ "$SM_STATUS" = "NOT_FOUND" ]; then
  check_warn "SageMaker needs recreation — using Terraform..."
  cd terraform/2_sagemaker

  # Clean state completely
  terraform state rm aws_sagemaker_endpoint.embedding_endpoint 2>/dev/null || true
  terraform state rm aws_sagemaker_endpoint_configuration.embedding_config 2>/dev/null || true
  terraform state rm aws_sagemaker_model.embedding_model 2>/dev/null || true

  # Delete AWS resources cleanly
  aws sagemaker delete-endpoint --endpoint-name alex-embedding --region $REGION 2>/dev/null || true
  aws sagemaker delete-endpoint-config --endpoint-config-name alex-embedding-config --region $REGION 2>/dev/null || true
  aws sagemaker delete-model --model-name alex-embedding-model --region $REGION 2>/dev/null || true

  sleep0

  terraform apply -auto-approve -compact-warnings 2>&1 | tail -3
  cd ../..

  check_wait "Waiting for SageMaker InService (3-5 mins)..."
  aws sagemaker wait endpoint-in-service \
    --endpoint-name alex-embedding \
    --region $REGION
  check_pass "SageMaker ready"
fi

# ============================================
# Step 2 — ECS + ALB via Terraform
# ============================================
echo ""
echo "🐳 Step 2: ECS + ALB infrastructure..."

# Check if ALB exists
ALB_COUNT=$(aws elbv2 describe-load-balancers \
  --region $REGION \
  --query "length(LoadBalancers)" \
  --output text 2>/dev/null || echo "0")

ECS_STATUS=$(aws ecs describe-services \
  --cluster alex-cluster \
  --services alex-researcher \
  --region $REGION \
  --query "services[0].status" \
  --output text 2>/dev/null || echo "NOT_FOUND")

ECS_RUNNING=$(aws ecs describe-services \
  --cluster alex-cluster \
  --services alex-researcher \
  --region $REGION \
  --query "services[0].runningCount" \
  --output text 2>/dev/nu| echo "0")

if [ "$ECS_STATUS" = "ACTIVE" ] && [ "$ECS_RUNNING" != "0" ] && [ "$ALB_COUNT" != "0" ]; then
  check_pass "ECS running ($ECS_RUNNING tasks) + ALB exists"
else
  check_warn "ECS/ALB needs recreation — using Terraform..."
  cd terraform/4_researcher
  terraform apply -auto-approve -compact-warnings 2>&1 | tail -5
  cd ../..
  check_pass "ECS + ALB created"

  # Start ECS task
  aws ecs update-service \
    --cluster alex-cluster \
    --service alex-researcher \
    --desired-count 1 \
    --force-new-deployment \
    --region $REGION > /dev/null 2>&1 || true
  check_pass "ECS task starting"
fi

# ============================================
# Step 3 — Update SSM with ALB URL
# ============================================
echo ""
echo "🔗 Step 3: Updating SSM config..."

ALB_DNS=$(aws elbv2 describe-load-balancers \
  --region $REGION \
  --query "LoadBalancers[0].DNSName" \
  --output text 2>/dev/null || echo "")

if [ ! -z "$ALB_DNS" ] && [ "$ALB_DNS" != "None" ]; then
  ALB_URL="http://DNS}"

  aws ssm put-parameter \
    --name "/alex/ecs_url" \
    --value "$ALB_URL" \
    --type "String" \
    --overwrite \
    --region $REGION > /dev/null 2>&1
  check_pass "ALB URL: $ALB_URL"

  # Update ops agent with ALB URL
  aws lambda update-function-configuration \
    --function-name alex-ops-agent \
    --region $REGION \
    --environment "Variables={DB_CLUSTER_ARN=$CLUSTER_ARN,DB_SECRET_ARN=$SECRET_ARN,DB_NAME=$DB_NAME,ALERT_EMAIL=abhishek.suresh2503@gmail.com,FROM_EMAIL=abhishek.suresh2503@gmail.com,DAILY_COST_THRESHOLD=10.0,AUTONOMOUS_MODE=false,ALB_URL=$ALB_URL}" \
    > /dev/null 2>&1 && check_pass "Ops Agent ALB_URL updated" || true
else
  check_warn "No ALB found — ECS may still be creating"
fi

# ============================================
# Step 4 — Aurora warm-up + table verification
# ============================================
echo ""
echo "🗄️  Step 4: Aurora warm-up + tables..."

python3 - << PYEOF
import boto3, time, sys

rds = boto3.client('rds-data', region_name='us)
CLUSTER_ARN = 'arn:aws:rds:us-east-1:381491881089:cluster:alex-aurora'
SECRET_ARN  = 'arn:aws:secretsmanager:us-east-1:381491881089:secret:alex/aurora/credentials-2HP8fm'
DB_NAME     = 'alex_db'

# Warm up Aurora
for i in range(8):
    try:
        rds.execute_statement(resourceArn=CLUSTER_ARN, secretArn=SECRET_ARN, database=DB_NAME, sql='SELECT 1')
        print(f"  ✅ Aurora connected")
        break
    except Exception as e:
        if 'resuming' in str(e).lower() or 'paused' in str(e).lower():
            print(f"  ⏳ Aurora resuming... ({i+1}/8)")
            time.sleep(15)
        else:
            print(f"  ✅ Aurora ready ({str(e)[:40]})")
            break

# Ensure all critical tables exist
tables = [
    "CREATE TABLE IF NOT EXISTS ops_snapshots (id UUID DEFAULT gen_random_uuid() PRIMARY KEY, snapshot_time TIMESTAMPTZ DEFAULT NOW(), health_status JSONB DEFAULT '{}', daily_cost NUMERIC(10,4), digest TEXT, created_at TIMESTAMPTZ DEFAULT NOW())",
    "CREATE INDEX IF NOT EXISTS idx_ops_snapshoe ON ops_snapshots(snapshot_time)",
    "CREATE TABLE IF NOT EXISTS cost_snapshots (id UUID DEFAULT gen_random_uuid() PRIMARY KEY, snapshot_date DATE NOT NULL, total_cost NUMERIC(10,4), service_costs JSONB DEFAULT '{}', digest TEXT, alert_sent BOOLEAN DEFAULT false, created_at TIMESTAMPTZ DEFAULT NOW())",
    "CREATE INDEX IF NOT EXISTS idx_cost_snapshots_date ON cost_snapshots(snapshot_date)",
    "CREATE TABLE IF NOT EXISTS cost_alerts (id UUID DEFAULT gen_random_uuid() PRIMARY KEY, alert_date DATE NOT NULL, daily_spend NUMERIC(10,4), threshold NUMERIC(10,4), message TEXT, sent_at TIMESTAMPTZ DEFAULT NOW())",
    "CREATE TABLE IF NOT EXISTS chat_sessions (id UUID DEFAULT gen_random_uuid() PRIMARY KEY, user_id UUID REFERENCES users(id), session_id VARCHAR(36) NOT NULL, messages JSONB DEFAULT '[]', created_at TIMESTAMPTZ DEFAULT NOW(), updated_at TIMESTAMPTZ DEFAULT NOW())",
    "CREATE INDEX IF NOT EXISTS idx_chat_sessions_session ON chat_sessions(session_id)",
    "CREATE TABLE IF NOT EXISTS research_snapshots (id UUID DEFAULT gen_random_uuid() PRIMARY KEY, user_id UUID REFERENCES users(id), ticker VARCHAR(10), snapshot TEXT, embedding vector(384), created_at TIMESTAMPTZ DEFAULT NOW())",
    "CREATE TABLE IF NOT EXISTS trading_simulations (id UUID DEFAULT gen_random_uuid() PRIMARY KEY, user_id UUID REFERENCES users(id), mode VARCHAR(20) NOT NULL DEFAULT 'neutral', status VARCHAR(20) DEFAULT 'active', llm_config JSONB DEFAULT '{}', initial_value NUMERIC(12,2) DEFAULT 0, current_value NUMERIC(12,2) DEFAULT 0, cash_balance NUMERIC(12,2) DEFAULT 0, total_pnl NUMERIC(12,2) DEFAULT 0, total_pnl_pct NUMERIC(8,4) DEFAULT 0, total_trades INTEGER DEFAULT 0, win_count INTEGER DEFAULT 0, loss_count INTEGER DEFAULT 0, benchmark_pnl NUMERIC(12,2) DEFAULT 0, alpha NUMERIC(8,4) DEFAULT 0, started_at TIMESTAMPTZ DEFAULT NOW(), updated_at TIMESTAMPTZ DEFAULT NOW())",
    "CREATE INDEX IF NOT EXISTS idx_trading_sim_user ON trading_simulations(user_id)",
    "CREATE TABLE IF NOT EXISTS simulated_trades (id UUID DEFAULT gen_random_uuid() PRIMARY KEY, simulation_id UUID REFERENCES trading_simulations(id), user_id UUID REFERENCES users(id), ticker VARCHAR(10) NOT NULL, action VARCHAR(10) NOT NULL, shares INTEGER DEFAULT 0, price NUMERIC(10,2) DEFAULT 0, total_value NUMERIC(12,2) DEFAULT 0, target_price NUMERIC(10,2) DEFAULT 0, stop_loss NUMERIC(10,2) DEFAULT 0, rationale TEXT, agent_votes JSONB DEFAULT '{}', agent_debate JSONB DEFAULT '[]', confidence NUMERIC(5,2) DEFAULT 0, mode VARCHAR(20), llm_used VARCHAR(100), pnl NUMERIC(12,2) DEFAULT 0, trigger VARCHAR(50) DEFAULT 'auto', executed_at TIMESTAMPTZ DEFAULT NOW())",
    "CREATE INDEX IF NOT EXISTS idx_trades_sim ON simulated_trades(simulation_id)",
    "CREATE INDEX IF NOT EXISTS idx_trades_user ON simulated_trades(user_id)",
    "CREATE TABLE IF NOT EXISTS agent_positions (id UUID DEFAULT gen_random_uuid() PRIMARY KEY, simulation_id UUID REFERENCES trading_simulations(id), user_id UUID REFERENCES users(id), ticker VARCHAR(10) NOT NULL, shares INTEGER DEFAULT 0, avg_cost NUMERIC(10,2) DEFAULT 0, current_price NUMERIC(10,2) DEFAULT 0, current_value NUMERIC(12,2) DEFAULT 0, cost_basis NUMERIC(12,2) DEFAULT 0, pnl NUMERIC(12,2) DEFAULT 0, pnl_pct NUMERIC(8,4) DEFAULT 0, weight_pct NUMERIC(8,4) DEFAULT 0, last_action VARCHAR(10), last_updated TIMESTAMPTZ DEFAULT NOW(), UNIQUE(simulation_id, ticker))",
    "CREATE TABLE IF NOT EXISTS trading_daily_pnl (id UUID DEFAULT gen_random_uuid() PRIMARY KEY, simulation_id UUID REFERENCES trading_simulations(id), user_id UUID REFERENCES users(id), trade_date DATE NOT NULL, open_value NUMERIC(12,2) DEFAULT 0, close_value NUMERIC(12,2) DEFAULT 0, daily_pnl NUMERIC(12,2) DEFAULT 0, daily_pnl_pct NUMERIC(8,4) DEFAULT 0, trades_count INTEGER DEFAULT 0, spy_pnl_pct NUMERIC(8,4) DEFAULT 0, alpha NUMERIC(8,4) DEFAULT 0, digest TEXT, created_at TIMESTAMPTZ DEFAULT NOW(), UNIQUE(simulation_id, trade_date))",
    "CREATE TABLE IF NOT EXISTS user_trading_config (id UUID DEFAULT gen_random_uuid() PRIMARY KEY, user_id UUID REFERENCES users(id) UNIQUE, trading_mode VARCHAR(20) DEFAULT 'neutral', autonomous BOOLEAN DEFAULT true, model_marcus VARCHAR(100) DEFAULT 'us.amazon.nova-pro-v1:0', model_victoria VARCHAR(100) DEFAULT 'us.amazon.nova-pro-v1:0', model_zara VARCHAR(100) DEFAULT 'us.amazon.nova-pro-v1:0', model_reid VARCHAR(100) DEFAULT 'us.amazon.nova-pro-v1:0', model_elena VARCHAR(100) DEFAULT 'us.amazon.nova-lite-v1:0', model_executor VARCHAR(100) DEFAULT 'us.amazon.nova-pro-v1:0', max_position_pct NUMERIC(5,2) DEFAULT 25.0, stop_loss_pct NUMERIC(5,2) DEFAULT 8.0, max_daily_trades INTEGER DEFAULT 10, created_at TIMESTAMPTZ DEFAULT NOW(), updated_at TIMESTAMPTZ DEFAULT NOW())",
    "CREATE TABLE IF NOT EXISTS ragas_evaluations (id UUID DEFAULT gen_random_uuid() PRIMARY KEY, research_id UUID, query TEXT, response TEXT, faithfulness NUMERIC(4,3), answer_relevancy NUMERIC(4,3), context_precision NUMERIC(4,3), context_recall NUMERIC(4,3), overall_score NUMERIC(4,3), passed BOOLEAN DEFAULT false, gate VARCHAR(50), evaluated_at TIMESTAMPTZ DEFAULT NOW())",
    "CREATE TABLE IF NOT EXISTS knowledge_graph_entities (id UUID DEFAULT gen_random_uuid() PRIMARY KEY, entity_type VARCHAR(50), name VARCHAR(200), ticker VARCHAR(10), description TEXT, metadata JSONB DEFAULT '{}', created_at TIMESTAMPTZ DEFAULT NOW(), UNIQUE(name, entity_type))",
    "CREATE TABLE IF NOT EXISTS knowledge_graph_relationships (id UUID DEFAULT gen_random_uuid() PRIMARY KEY, from_entity VARCHAR(200), relationship_type VARCHAR(100), to_entity VARCHAR(200), confidence NUMERIC(4,3) DEFAULT 1.0, source TEXT, created_at TIMESTAMPTZ DEFAULT NOW())",
]

ok = 0
for sql in tables:
    try:
        rds.execute_statement(resourceArn=CLUSTER_ARN, secretArn=SECRET_ARN, database=DB_NAME, sql=sql)
        ok += 1
    except Exception as e:
        if 'already exists' not in str(e).lower():
            print(f"  ⚠️  {str(e)[:80]}")

print(f"  ✅ {ok}/{len(tables)} tables verified")
PYEOF

# ============================================
# Step 5 — Lambda agents health
# ========================================= ""
echo "⚡ Step 5: Lambda agents check..."

for fn in alex-planner alex-tagger alex-reporter alex-cost-monitor alex-ops-agent; do
  STATUS=$(aws lambda get-function \
    --function-name $fn \
    --region $REGION \
    --query "Configuration.State" \
    --output text 2>/dev/null || echo "NOT_FOUND")
  if [ "$STATUS" = "Active" ]; then
    check_pass "$fn: Active"
  else
    check_warn "$fn: $STATUS"
  fi
done

# ============================================
# Step 6 — EventBridge schedules
# ============================================
echo ""
echo "📅 Step 6: EventBridge schedules..."

for schedule in alex-ops-agent-30min alex-cost-monitor-daily; do
  STATE=$(aws scheduler get-schedule \
    --name $schedule \
    --region $REGION \
    --query "State" \
    --output text 2>/dev/null || echo "NOT_FOUND")
  if [ "$STATE" = "ENABLED" ]; then
    check_pass "$schedule: ENABLED"
  else
    check_warn "$schedule: $STATE — enabling..."
    aws scheduler update-schedule \
      --name $schedule \
       $REGION \
      --state ENABLED \
      --flexible-time-window Mode=OFF \
      --schedule-expression "$(aws scheduler get-schedule --name $schedule --region $REGION --query 'ScheduleExpression' --output text 2>/dev/null)" \
      --target "$(aws scheduler get-schedule --name $schedule --region $REGION --query 'Target' --output json 2>/dev/null)" \
      > /dev/null 2>&1 && check_pass "$schedule: re-enabled" || check_warn "$schedule: could not enable"
  fi
done

# ============================================
# Step 7 — Final health check
# ============================================
echo ""
echo "🏥 Step 7: Final health check..."
sleep 8

ALB_URL=$(aws ssm get-parameter \
  --name "/alex/ecs_url" \
  --region $REGION \
  --query "Parameter.Value" \
  --output text 2>/dev/null || echo "")

if [ ! -z "$ALB_URL" ]; then
  HEALTH=$(curl -s --max-time 15 $ALB_URL/health 2>/dev/null | \
    python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('status','unknown'))" 2>/dev/null || echo "starting..  echo "  ECS API:    $HEALTH ($ALB_URL)"
else
  echo "  ECS API:    ALB not available yet"
fi

SM_STATUS=$(aws sagemaker describe-endpoint \
  --endpoint-name alex-embedding \
  --region $REGION \
  --query "EndpointStatus" \
  --output text 2>/dev/null || echo "unknown")
echo "  SageMaker:  $SM_STATUS"

FRONTEND_STATUS=$(curl -s -o /dev/null -w "%{http_code}" \
  --max-time 5 \
  "https://ai-financial-advisor-t6kt-abi2503s-projects.vercel.app" 2>/dev/null || echo "000")
echo "  Frontend:   HTTP $FRONTEND_STATUS"

# ============================================
# Done
# ============================================
echo ""
echo "========================================"
echo "✅ Session ready!"
echo ""
echo "ALB URL: ${ALB_URL:-not available yet}"
echo ""
echo "Commands:"
echo "  cd frontend && npm run dev    # Start frontend"
echo "  bash scripts/stop_session.sh  # Stop + save costs"
echo ""
echo "Test ECS:"
echo "  curl -s \$ALB/health | python3 -m json.tool"
echo ""
echo "Run ops check:"
echo "  aws lamb invoke --function-name alex-ops-agent \\"
echo "    --region us-east-1 \\"
echo "    --payload '{\"source\":\"manual\",\"action\":\"monitor\"}' \\"
echo "    --cli-binary-format raw-in-base64-out /tmp/ops.json \\"
echo "    && cat /tmp/ops.json | python3 -m json.tool"
echo "========================================"
