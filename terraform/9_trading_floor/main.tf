terraform {
  required_version = ">= 1.5"
  required_providers {
    aws = { source = "hashicorp/aws", version = "~> 5.0" }
  }
}

provider "aws" { region = "us-east-1" }

data "aws_caller_identity" "current" {}

locals {
  project     = "alex"
  region      = "us-east-1"
  agent_role  = "arn:aws:iam::${data.aws_caller_identity.current.account_id}:role/alex-agent-role"
  eb_role     = "arn:aws:iam::${data.aws_caller_identity.current.account_id}:role/alex-eventbridge-role"
  cluster_arn = "arn:aws:rds:us-east-1:${data.aws_caller_identity.current.account_id}:cluster:alex-aurora"
  secret_arn  = "arn:aws:secretsmanager:us-east-1:${data.aws_caller_identity.current.account_id}:secret:alex/aurora/credentials-2HP8fm"
}

resource "aws_sqs_queue" "trading_queue" {
  name                       = "alex-trading-queue"
  visibility_timeout_seconds = 300
  message_retention_seconds  = 3600
  receive_wait_time_seconds  = 20
  tags                       = { Project = local.project }
}

resource "aws_sqs_queue" "trading_results" {
  name                      = "alex-trading-results"
  message_retention_seconds = 3600
  tags                      = { Project = local.project }
}

resource "aws_lambda_function" "trading_orchestrator" {
  filename      = "../../backend/agents/trading/orchestrator.zip"
  function_name = "alex-trading-orchestrator"
  role          = local.agent_role
  handler       = "orchestrator.lambda_handler"
  runtime       = "python3.12"
  timeout       = 300
  memory_size   = 512
  environment {
    variables = {
      DB_CLUSTER_ARN    = local.cluster_arn
      DB_SECRET_ARN     = local.secret_arn
      DB_NAME           = "alex_db"
      TRADING_QUEUE_URL = aws_sqs_queue.trading_queue.url
      AWS_REGION_NAME   = local.region
    }
  }
  tags = { Project = local.project }
}

resource "aws_cloudwatch_log_group" "trading_logs" {
  name              = "/aws/lambda/alex-trading-orchestrator"
  retention_in_days = 7
  tags              = { Project = local.project }
}

resource "aws_lambda_permission" "trading_scheduler" {
  statement_id  = "AllowEventBridgeTrading"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.trading_orchestrator.function_name
  principal     = "scheduler.amazonaws.com"
}

resource "aws_ssm_parameter" "trading_enabled" {
  name      = "/alex/trading/enabled"
  type      = "String"
  value     = "true"
  overwrite = true
  tags      = { Project = local.project }
}

resource "aws_ssm_parameter" "trading_mode" {
  name      = "/alex/trading/mode"
  type      = "String"
  value     = "neutral"
  overwrite = true
  tags      = { Project = local.project }
}

output "trading_queue_url" {
  value = aws_sqs_queue.trading_queue.url
}

output "orchestrator_function" {
  value = aws_lambda_function.trading_orchestrator.function_name
}

resource "aws_iam_role_policy" "trading_sqs_policy" {
  name = "alex-trading-sqs-policy"
  role = "alex-agent-role"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect   = "Allow"
      Action   = ["sqs:SendMessage", "sqs:ReceiveMessage",
                  "sqs:DeleteMessage", "sqs:GetQueueAttributes"]
      Resource = [
        aws_sqs_queue.trading_queue.arn,
        aws_sqs_queue.trading_results.arn
      ]
    }]
  })
}
