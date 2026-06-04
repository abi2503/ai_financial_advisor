data "aws_caller_identity" "current" {}

# ========================================
# Reference Shared VPC from 0_vpc
# ========================================

data "aws_vpc" "main" {
  tags = {
    Name = "alex-vpc"
  }
}

# ========================================
# Private Subnets for Aurora
# (public subnets live in 0_vpc)
# ========================================

# REPLACE WITH these data sources:
data "aws_subnet" "private_1" {
  tags = { Name = "alex-private-1" }
}

data "aws_subnet" "private_2" {
  tags = { Name = "alex-private-2" }
}

# ========================================
# DB Subnet Group
# ========================================

resource "aws_db_subnet_group" "aurora" {
  name       = "${var.project_name}-aurora-subnet-group"
  subnet_ids = [data.aws_subnet.private_1.id, data.aws_subnet.private_2.id]

  tags = {
    Project = var.project_name
  }
}

# ========================================
# Security Group for Aurora
# Only allows connections from inside VPC
# ========================================

resource "aws_security_group" "aurora" {
  name        = "${var.project_name}-aurora-sg"
  description = "Security group for Aurora database"
  vpc_id      = data.aws_vpc.main.id

  ingress {
    from_port   = 5432
    to_port     = 5432
    protocol    = "tcp"
    cidr_blocks = ["10.0.0.0/16"]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Project = var.project_name
  }
}

# ========================================
# Secrets Manager — DB Credentials
# Never hardcode passwords anywhere
# ========================================

resource "random_password" "aurora" {
  length  = 32
  special = false
}

resource "aws_secretsmanager_secret" "aurora_credentials" {
  name                    = "${var.project_name}/aurora/credentials"
  recovery_window_in_days = 0

  tags = {
    Project = var.project_name
  }
}

resource "aws_secretsmanager_secret_version" "aurora_credentials" {
  secret_id = aws_secretsmanager_secret.aurora_credentials.id

  secret_string = jsonencode({
    username = var.db_username
    password = random_password.aurora.result
    dbname   = var.db_name
    engine   = "aurora-postgresql"
    port     = 5432
    host     = aws_rds_cluster.aurora.endpoint
  })
}

# ========================================
# Aurora Serverless v2 Cluster
# ========================================

resource "aws_rds_cluster" "aurora" {
  cluster_identifier     = "${var.project_name}-aurora"
  engine                 = "aurora-postgresql"
  engine_mode            = "provisioned"
  engine_version         = "16.6"
  database_name          = var.db_name
  master_username        = var.db_username
  master_password        = random_password.aurora.result
  db_subnet_group_name   = aws_db_subnet_group.aurora.name
  vpc_security_group_ids = [aws_security_group.aurora.id]

  serverlessv2_scaling_configuration {
    min_capacity = 0
    max_capacity = 4
  }

  # Enables RDS Data API — lets Lambda call DB without
  # persistent connections (required for serverless)
  enable_http_endpoint = true

  # Skip backup on destroy — fine for development
  skip_final_snapshot = true

  tags = {
    Project = var.project_name
    Guide   = "5"
  }
}

resource "aws_rds_cluster_instance" "aurora" {
  cluster_identifier = aws_rds_cluster.aurora.id
  instance_class     = "db.serverless"
  engine             = aws_rds_cluster.aurora.engine
  engine_version     = aws_rds_cluster.aurora.engine_version

  tags = {
    Project = var.project_name
    Guide   = "5"
  }
}

# ========================================
# IAM Role for Lambda to access Aurora
# ========================================

resource "aws_iam_role" "lambda_db_role" {
  name = "${var.project_name}-lambda-db-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect    = "Allow"
        Principal = { Service = "lambda.amazonaws.com" }
        Action    = "sts:AssumeRole"
      }
    ]
  })

  tags = { Project = var.project_name }
}

resource "aws_iam_role_policy" "lambda_db_policy" {
  name = "${var.project_name}-lambda-db-policy"
  role = aws_iam_role.lambda_db_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      # CloudWatch logs
      {
        Effect = "Allow"
        Action = [
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents"
        ]
        Resource = "*"
      },
      # RDS Data API — call Aurora without persistent connection
      {
        Effect = "Allow"
        Action = [
          "rds-data:ExecuteStatement",
          "rds-data:BatchExecuteStatement",
          "rds-data:BeginTransaction",
          "rds-data:CommitTransaction",
          "rds-data:RollbackTransaction"
        ]
        Resource = aws_rds_cluster.aurora.arn
      },
      # Secrets Manager — retrieve DB credentials
      {
        Effect = "Allow"
        Action = [
          "secretsmanager:GetSecretValue"
        ]
        Resource = aws_secretsmanager_secret.aurora_credentials.arn
      }
    ]
  })
}

# ========================================
# CloudWatch Log Group
# ========================================

resource "aws_cloudwatch_log_group" "db_lambda_logs" {
  name              = "/aws/lambda/${var.project_name}-db"
  retention_in_days = 7

  tags = {
    Project = var.project_name
  }
}