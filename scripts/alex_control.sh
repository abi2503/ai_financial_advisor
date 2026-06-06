#!/bin/bash

# ============================================
# Alex Master Control Script
# Controls all Alex infrastructure
# ============================================

source ../../.env
REGION=${DEFAULT_AWS_REGION:-us-east-1}

case "$1" in
start)
    echo "🚀 Starting Alex infrastructure..."
    echo ""

    echo "1️⃣  Starting Guide 4 (ECS Researcher)..."
    cd terraform/4_researcher
    terraform apply -auto-approve > /dev/null
    cd ../..
    echo "✅ ECS Researcher up"

    echo ""
    echo "2️⃣  Enabling EventBridge scheduler..."
    bash scripts/toggle_eventbridge.sh enable

    echo ""
    echo "✅ Alex is fully running!"
    echo ""
    echo "URLs:"
    cd terraform/4_researcher
    echo "  Researcher: http://$(terraform output -raw alb_dns_name)"
    cd ../..
    ;;

  stop)
    echo "🛑 Stopping Alex infrastructure..."
    echo ""

    echo "1️⃣  Disabling EventBridge scheduler..."
    bash scripts/toggle_eventbridge.sh disable

    echo ""
    echo "2️⃣  Destroying Guide 4 (ECS)..."
    cd terraform/4_researcher

    aws ecs update-service \
      --cluster alex-cluster \
      --service alex-researcher \
      --desired-count 0 \
      --region $REGION > /dev/null

    sleep 10
    terraform destroy -auto-approve > /dev/null
    cd ../..
    echo "✅ ECS destroyed"

    echo ""
    echo "✅ Alex stopped — no more charges accumulating"
    echo ""
    echo "Permanent resources still running (free/near-free):"
    echo "  ✅ VPC (free)"
    echo "  ✅ Aurora (scales to zero)"
    echo "  ✅ S3 Vectors (~\$0)"
    echo "  ✅ SQS queues (~\$0)"
    ;;

  status)
    echo "📊 Alex Infrastructure Status"
    echo "================================"

    # ECS Status
    ECS_STATUS=$(aws ecs describe-services \
      --cluster alex-cluster \
      --services alex-researcher \
      --region $REGION \
      --query "services[0].{Running:runningCount,Desired:desiredCount}" \
      --output json 2>/dev/null)

    if [ $? -eq 0 ]; then
      RUNNING=$(echo $ECS_STATUS | python3 -c "import json,sys; d=json.load(sys.stdin); print(d['Running'])")
      DESIRED=$(echo $ECS_STATUS | python3 -c "import json,sys; d=json.load(sys.stdin); print(d['Desired'])")
      if [ "$RUNNING" == "$DESIRED" ] && [ "$RUNNING" != "0" ]; then
        echo "✅ ECS Researcher: RUNNING ($RUNNING/$DESIRED)"
      else
        echo "🔴 ECS Researcher: STOPPED ($RUNNING/$DESIRED)"
      fi
    else
      echo "🔴 ECS Researcher: NOT DEPLOYED"
    fi

    # EventBridge Status
    bash scripts/toggle_eventbridge.sh status

    # Aurora Status
    AURORA=$(aws rds describe-db-clusters \
      --db-cluster-identifier alex-aurora \
      --region $REGION \
      --query "DBClusters[0].Status" \
      --output text 2>/dev/null)
    echo "✅ Aurora: $AURORA"

    # SQS Queue depths
    echo ""
    echo "📬 Queue Status:"
    if [ ! -z "$SQS_RESEARCH_QUEUE_URL" ]; then
      DEPTH=$(aws sqs get-queue-attributes \
        --queue-url $SQS_RESEARCH_QUEUE_URL \
        --attribute-names ApproximateNumberOfMessages \
        --query "Attributes.ApproximateNumberOfMessages" \
        --output text 2>/dev/null)
      echo "   Research queue: $DEPTH messages"
    fi
    ;;

  *)
    echo "Usage: bash scripts/alex_control.sh [start|stop|status]"
    echo ""
    echo "Commands:"
    echo "  start  → Start ECS + enable EventBridge"
    echo "  stop   → Destroy ECS + disable EventBridge"
    echo "  status → Check all infrastructure"
    ;;

esac

echo "Make the script executable"
chmod +x scripts/alex_control.sh