# ============================================
# Data Sources
# ============================================

data "aws_caller_identity" "current" {}
data "aws_region" "current" {}

data "aws_vpc" "main" {
  tags = { Name = "alex-vpc" }
}

# ============================================
# SQS Queues
# ============================================

resource "aws_sqs_queue" "dlq" {
  name                      = "${var.project_name}-dlq"
  message_retention_seconds = 86400

  tags = { Project = var.project_name }
}

resource "aws_sqs_queue" "research_queue" {
  name                       = "${var.project_name}-research-queue"
  visibility_timeout_seconds = 300
  message_retention_seconds  = 3600
  receive_wait_time_seconds  = 20

  redrive_policy = jsonencode({
    deadLetterTargetArn = aws_sqs_queue.dlq.arn
    maxReceiveCount     = 3
  })

  tags = { Project = var.project_name }
}

resource "aws_sqs_queue" "results_queue" {
  name                       = "${var.project_name}-results-queue"
  visibility_timeout_seconds = 120
  message_retention_seconds  = 3600
  receive_wait_time_seconds  = 20

  redrive_policy = jsonencode({
    deadLetterTargetArn = aws_sqs_queue.dlq.arn
    maxReceiveCount     = 3
  })

  tags = { Project = var.project_name }
}
resource "aws_sqs_queue" "frontend_results_queue" {
  name                       = "${var.project_name}-frontend-results"
  visibility_timeout_seconds = 120
  message_retention_seconds  = 300

  tags = { Project = var.project_name }
}
# ============================================
# IAM Role for Agent Lambdas
# ============================================

resource "aws_iam_role" "agent_role" {
  name = "${var.project_name}-agent-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { Service = "lambda.amazonaws.com" }
      Action    = "sts:AssumeRole"
    }]
  })

  tags = { Project = var.project_name }
}

resource "aws_iam_role_policy" "agent_policy" {
  name = "${var.project_name}-agent-policy"
  role = aws_iam_role.agent_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect   = "Allow"
        Action   = ["logs:CreateLogGroup", "logs:CreateLogStream",
                    "logs:PutLogEvents", "logs:FilterLogEvents",
                    "logs:GetLogEvents", "logs:DescribeLogGroups"]
        Resource = "*"
      },
      {
        Effect   = "Allow"
        Action   = ["sqs:SendMessage", "sqs:ReceiveMessage",
                    "sqs:DeleteMessage", "sqs:GetQueueAttributes"]
        Resource = [
          aws_sqs_queue.research_queue.arn,
          aws_sqs_queue.results_queue.arn,
          aws_sqs_queue.frontend_results_queue.arn,
          aws_sqs_queue.dlq.arn
        ]
      },
      {
        Effect   = "Allow"
        Action   = ["bedrock:InvokeModel", "bedrock:InvokeModelWithResponseStream",
                    "bedrock:ApplyGuardrail"]
        Resource = "*"
      },
      {
        Effect   = "Allow"
        Action   = ["rds-data:ExecuteStatement", "rds-data:BatchExecuteStatement"]
        Resource = "*"
      },
      {
        Effect   = "Allow"
        Action   = ["secretsmanager:GetSecretValue"]
        Resource = "*"
      },
      {
        Effect   = "Allow"
        Action   = ["ecs:DescribeServices", "ecs:DescribeClusters",
                    "ecs:UpdateService", "ecs:ListTasks", "ecs:DescribeTasks"]
        Resource = "*"
      },
      {
        Effect   = "Allow"
        Action   = ["sagemaker:DescribeEndpoint", "sagemaker:ListEndpoints"]
        Resource = "*"
      },
      {
        Effect   = "Allow"
        Action   = ["cloudwatch:GetMetricStatistics", "cloudwatch:PutMetricData",
                    "cloudwatch:ListMetrics", "cloudwatch:GetMetricData"]
        Resource = "*"
      },
      {
        Effect   = "Allow"
        Action   = ["ce:GetCostAndUsage", "ce:GetCostForecast", "ce:GetDimensionValues"]
        Resource = "*"
      },
      {
        Effect   = "Allow"
        Action   = ["ses:SendEmail", "ses:SendRawEmail"]
        Resource = "*"
      },
      {
        Effect   = "Allow"
        Action   = ["ssm:PutParameter", "ssm:GetParameter", "ssm:GetParameters"]
        Resource = "*"
      },
      {
        Effect   = "Allow"
        Action   = ["lambda:GetAccountSettings", "lambda:InvokeFunction", "lambda:GetFunction"]
        Resource = "*"
      }
    ]
  })
}


# ============================================
# Lambda Functions
# ============================================

resource "aws_lambda_function" "scheduler" {
  filename      = "../../backend/agents/scheduler.zip"
  function_name = "${var.project_name}-scheduler"
  role          = aws_iam_role.agent_role.arn
  handler       = "scheduler.lambda_handler"
  runtime       = "python3.12"
  timeout       = 60
  memory_size   = 256

  environment {
    variables = {
      RESEARCH_QUEUE_URL = aws_sqs_queue.research_queue.url
      AWS_REGION_NAME    = var.aws_region
    }
  }

  tags = { Project = var.project_name }
}

resource "aws_lambda_function" "tagger" {
  filename      = "../../backend/agents/tagger.zip"
  function_name = "${var.project_name}-tagger"
  role          = aws_iam_role.agent_role.arn
  handler       = "tagger.lambda_handler"
  runtime       = "python3.12"
  timeout       = 60
  memory_size   = 256

  environment {
    variables = {
      RESULTS_QUEUE_URL = aws_sqs_queue.results_queue.url
      AWS_REGION_NAME   = var.aws_region
    }
  }

  tags = { Project = var.project_name }
}

resource "aws_lambda_function" "reporter" {
  filename      = "../../backend/agents/reporter.zip"
  function_name = "${var.project_name}-reporter"
  role          = aws_iam_role.agent_role.arn
  handler       = "reporter.lambda_handler"
  runtime       = "python3.12"
  timeout       = 120
  memory_size   = 512

  environment {
    variables = {
      ALEX_API_ENDPOINT          = var.alex_api_endpoint
      ALEX_API_KEY               = var.alex_api_key
      DB_CLUSTER_ARN             = var.db_cluster_arn
      DB_SECRET_ARN              = var.db_secret_arn
      DB_NAME                    = var.db_name
      AWS_REGION_NAME            = var.aws_region
      RESULTS_QUEUE_URL          = aws_sqs_queue.results_queue.url
      FRONTEND_RESULTS_QUEUE_URL = aws_sqs_queue.frontend_results_queue.url
    }
  }

  tags = { Project = var.project_name }
}

resource "aws_lambda_function" "planner" {
  filename      = "../../backend/agents/planner.zip"
  function_name = "${var.project_name}-planner"
  role          = aws_iam_role.agent_role.arn
  handler       = "planner.lambda_handler"
  runtime       = "python3.12"
  timeout       = 300
  memory_size   = 512

  environment {
    variables = {
      RESEARCH_QUEUE_URL = aws_sqs_queue.research_queue.url
      RESULTS_QUEUE_URL  = aws_sqs_queue.results_queue.url
      OPENAI_API_KEY     = var.openai_api_key
      AWS_REGION_NAME    = var.aws_region
    }
  }

  tags = { Project = var.project_name }
}

# ============================================
# SQS → Lambda Triggers
# ============================================

# When message arrives in research_queue → trigger tagger
resource "aws_lambda_event_source_mapping" "tagger_trigger" {
  event_source_arn = aws_sqs_queue.research_queue.arn
  function_name    = aws_lambda_function.tagger.arn
  batch_size       = 1
  enabled          = true
}

# When message arrives in results_queue → trigger reporter
resource "aws_lambda_event_source_mapping" "reporter_trigger" {
  event_source_arn = aws_sqs_queue.results_queue.arn
  function_name    = aws_lambda_function.reporter.arn
  batch_size       = 1
  enabled          = true
}

# ============================================
# EventBridge Scheduler
# ============================================

resource "aws_iam_role" "eventbridge_role" {
  name = "${var.project_name}-eventbridge-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { Service = "scheduler.amazonaws.com" }
      Action    = "sts:AssumeRole"
    }]
  })
}

resource "aws_iam_role_policy" "eventbridge_policy" {
  name = "${var.project_name}-eventbridge-policy"
  role = aws_iam_role.eventbridge_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect   = "Allow"
      Action   = ["lambda:InvokeFunction"]
      Resource = aws_lambda_function.scheduler.arn
    }]
  })
}

resource "aws_scheduler_schedule" "auto_research" {
  name  = "${var.project_name}-auto-research"
  state = "DISABLED"

  flexible_time_window {
    mode = "OFF"
  }

  schedule_expression = "rate(2 hours)"

  target {
    arn      = aws_lambda_function.scheduler.arn
    role_arn = aws_iam_role.eventbridge_role.arn

    input = jsonencode({
      source = "eventbridge-scheduler"
      task   = "auto-research"
    })
  }
}

# ============================================
# CloudWatch Log Groups
# ============================================

resource "aws_cloudwatch_log_group" "scheduler_logs" {
  name              = "/aws/lambda/${var.project_name}-scheduler"
  retention_in_days = 7
  tags              = { Project = var.project_name }
}

resource "aws_cloudwatch_log_group" "tagger_logs" {
  name              = "/aws/lambda/${var.project_name}-tagger"
  retention_in_days = 7
  tags              = { Project = var.project_name }
}

resource "aws_cloudwatch_log_group" "reporter_logs" {
  name              = "/aws/lambda/${var.project_name}-reporter"
  retention_in_days = 7
  tags              = { Project = var.project_name }
}

resource "aws_cloudwatch_log_group" "planner_logs" {
  name              = "/aws/lambda/${var.project_name}-planner"
  retention_in_days = 7
  tags              = { Project = var.project_name }
}
# Add RESULTS_QUEUE_URL to reporter env
# (Already added via CLI — this makes it permanent)

# ============================================
# Cost Monitor Lambda
# ============================================
resource "aws_lambda_function" "cost_monitor" {
  filename      = "../../backend/agents/cost_monitor.zip"
  function_name = "${var.project_name}-cost-monitor"
  role          = aws_iam_role.agent_role.arn
  handler       = "cost_monitor.lambda_handler"
  runtime       = "python3.12"
  timeout       = 120
  memory_size   = 256

  environment {
    variables = {
      DB_CLUSTER_ARN       = var.db_cluster_arn
      DB_SECRET_ARN        = var.db_secret_arn
      DB_NAME              = var.db_name
      AWS_REGION_NAME      = var.aws_region
      ALERT_EMAIL          = var.alert_email
      FROM_EMAIL           = var.alert_email
      DAILY_COST_THRESHOLD = "10.0"
    }
  }

  tags = { Project = var.project_name }
}

resource "aws_cloudwatch_log_group" "cost_monitor_logs" {
  name              = "/aws/lambda/${var.project_name}-cost-monitor"
  retention_in_days = 7
  tags              = { Project = var.project_name }
}

resource "aws_scheduler_schedule" "cost_monitor_daily" {
  name  = "${var.project_name}-cost-monitor-daily"
  state = "ENABLED"

  flexible_time_window { mode = "OFF" }
  schedule_expression = "cron(0 8 * * ? *)"

  target {
    arn      = aws_lambda_function.cost_monitor.arn
    role_arn = aws_iam_role.eventbridge_role.arn
    input    = jsonencode({ source = "eventbridge", task = "daily-cost-monitor" })
  }
}

resource "aws_lambda_permission" "cost_monitor_scheduler" {
  statement_id  = "AllowEventBridgeCostMonitor"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.cost_monitor.function_name
  principal     = "scheduler.amazonaws.com"
}

# ============================================
# Ops Agent Lambda
# ============================================
resource "aws_lambda_function" "ops_agent" {
  filename      = "../../backend/agents/ops_agent.zip"
  function_name = "${var.project_name}-ops-agent"
  role          = aws_iam_role.agent_role.arn
  handler       = "ops_agent.lambda_handler"
  runtime       = "python3.12"
  timeout       = 300
  memory_size   = 512

  environment {
    variables = {
      DB_CLUSTER_ARN       = var.db_cluster_arn
      DB_SECRET_ARN        = var.db_secret_arn
      DB_NAME              = var.db_name
      AWS_REGION_NAME      = var.aws_region
      ALERT_EMAIL          = var.alert_email
      FROM_EMAIL           = var.alert_email
      DAILY_COST_THRESHOLD = "10.0"
      AUTONOMOUS_MODE      = "false"
      FRONTEND_URL         = var.frontend_url
      ALB_URL              = var.alb_url
    }
  }

  tags = { Project = var.project_name }
}

resource "aws_cloudwatch_log_group" "ops_agent_logs" {
  name              = "/aws/lambda/${var.project_name}-ops-agent"
  retention_in_days = 7
  tags              = { Project = var.project_name }
}

resource "aws_scheduler_schedule" "ops_agent_30min" {
  name  = "${var.project_name}-ops-agent-30min"
  state = "ENABLED"

  flexible_time_window { mode = "OFF" }
  schedule_expression = "rate(30 minutes)"

  target {
    arn      = aws_lambda_function.ops_agent.arn
    role_arn = aws_iam_role.eventbridge_role.arn
    input    = jsonencode({ source = "eventbridge", action = "monitor" })
  }
}

resource "aws_scheduler_schedule" "ops_agent_weekly" {
  name  = "${var.project_name}-ops-agent-weekly"
  state = "ENABLED"

  flexible_time_window { mode = "OFF" }
  schedule_expression = "cron(0 8 ? * 2 *)"

  target {
    arn      = aws_lambda_function.ops_agent.arn
    role_arn = aws_iam_role.eventbridge_role.arn
    input    = jsonencode({ source = "eventbridge-weekly", action = "monitor" })
  }
}

resource "aws_lambda_permission" "ops_agent_scheduler" {
  statement_id  = "AllowEventBridgeOpsAgent"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.ops_agent.function_name
  principal     = "scheduler.amazonaws.com"
}
