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
        Effect = "Allow"
        Action = [
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents"
        ]
        Resource = "*"
      },
      {
        Effect = "Allow"
        Action = [
          "sqs:SendMessage",
          "sqs:ReceiveMessage",
          "sqs:DeleteMessage",
          "sqs:GetQueueAttributes"
        ]
        Resource = [
          aws_sqs_queue.research_queue.arn,
          aws_sqs_queue.results_queue.arn,
          aws_sqs_queue.dlq.arn
        ]
      },
      {
        Effect = "Allow"
        Action = [
          "bedrock:InvokeModel",
          "bedrock:InvokeModelWithResponseStream"
        ]
        Resource = "*"
      },
      {
        Effect = "Allow"
        Action = [
          "rds-data:ExecuteStatement",
          "rds-data:BatchExecuteStatement"
        ]
        Resource = "*"
      },
      {
        Effect   = "Allow"
        Action   = ["secretsmanager:GetSecretValue"]
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
      ALEX_API_ENDPOINT = var.alex_api_endpoint
      ALEX_API_KEY      = var.alex_api_key
      DB_CLUSTER_ARN    = var.db_cluster_arn
      DB_SECRET_ARN     = var.db_secret_arn
      DB_NAME           = var.db_name
      AWS_REGION_NAME   = var.aws_region
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