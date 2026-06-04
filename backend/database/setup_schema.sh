#!/bin/bash
set -e

# Load environment
source ../../.env

echo "🗄️  Setting up Aurora schema..."
echo "Cluster: $DB_CLUSTER_ARN"
echo "Database: $DB_NAME"
echo ""

# Wait for Aurora to wake up if paused
echo "⏳ Waiting for Aurora to be ready..."
sleep 60

run_sql() {
    local description=$1
    local sql=$2
    
    aws rds-data execute-statement \
        --resource-arn "$DB_CLUSTER_ARN" \
        --secret-arn "$DB_SECRET_ARN" \
        --database "$DB_NAME" \
        --region us-east-1 \
        --sql "$sql" > /dev/null
    
    echo "✅ $description"
}

# Table 1 — Users
run_sql "Users table" "
CREATE TABLE IF NOT EXISTS users (
    id         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    clerk_id   VARCHAR(255) UNIQUE NOT NULL,
    email      VARCHAR(255) UNIQUE NOT NULL,
    name       VARCHAR(255),
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);"

# Table 2 — Research Sessions
run_sql "Research sessions table" "
CREATE TABLE IF NOT EXISTS research_sessions (
    id         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id    UUID REFERENCES users(id) ON DELETE CASCADE,
    topic      VARCHAR(500),
    result     TEXT,
    vector_id  VARCHAR(255),
    created_at TIMESTAMP DEFAULT NOW()
);"

# Table 3 — Portfolios
run_sql "Portfolios table" "
CREATE TABLE IF NOT EXISTS portfolios (
    id         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id    UUID REFERENCES users(id) ON DELETE CASCADE,
    ticker     VARCHAR(20) NOT NULL,
    company    VARCHAR(255),
    added_at   TIMESTAMP DEFAULT NOW()
);"

# Table 4 — Preferences
run_sql "Preferences table" "
CREATE TABLE IF NOT EXISTS preferences (
    id             UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id        UUID REFERENCES users(id) ON DELETE CASCADE UNIQUE,
    risk_tolerance VARCHAR(50) DEFAULT 'moderate',
    sectors        TEXT[],
    updated_at     TIMESTAMP DEFAULT NOW()
);"

# Verify all tables created
echo ""
echo "📋 Verifying tables..."
aws rds-data execute-statement \
    --resource-arn "$DB_CLUSTER_ARN" \
    --secret-arn "$DB_SECRET_ARN" \
    --database "$DB_NAME" \
    --region us-east-1 \
    --sql "SELECT table_name FROM information_schema.tables 
           WHERE table_schema = 'public' 
           ORDER BY table_name;" \
    --query "records[*][0].stringValue" \
    --output table

echo ""
echo "✅ Schema setup complete!"


chmod +x backend/database/setup_schema.sh

