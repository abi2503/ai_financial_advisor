data "aws_caller_identity" "current" {}

resource "aws_iam_role" "sagemaker_role" {
  name = "${var.project_name}-sagemaker-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { Service = "sagemaker.amazonaws.com" }
      Action    = "sts:AssumeRole"
    }]
  })

  tags = { Project = var.project_name }
}

resource "aws_iam_role_policy_attachment" "sagemaker_full_access" {
  role       = aws_iam_role.sagemaker_role.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonSageMakerFullAccess"
}

resource "aws_iam_role_policy_attachment" "sagemaker_bedrock_access" {
  role       = aws_iam_role.sagemaker_role.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonBedrockFullAccess"
}

resource "aws_iam_role_policy_attachment" "sagemaker_cloudwatch_access" {
  role       = aws_iam_role.sagemaker_role.name
  policy_arn = "arn:aws:iam::aws:policy/CloudWatchEventsFullAccess"
}

resource "aws_iam_policy" "s3_vectors_access" {
  name        = "${var.project_name}-s3-vectors-policy"
  description = "Custom policy for S3 Vectors operations"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect = "Allow"
      Action = [
        "s3vectors:CreateVectorBucket",
        "s3vectors:DeleteVectorBucket",
        "s3vectors:CreateIndex",
        "s3vectors:DeleteIndex",
        "s3vectors:PutVectors",
        "s3vectors:GetVectors",
        "s3vectors:QueryVectors",
        "s3vectors:DeleteVectors",
        "s3vectors:ListVectorBuckets",
        "s3vectors:ListIndexes"
      ]
      Resource = "*"
    }]
  })
}

resource "aws_iam_role_policy_attachment" "sagemaker_s3vectors_access" {
  role       = aws_iam_role.sagemaker_role.name
  policy_arn = aws_iam_policy.s3_vectors_access.arn
}

resource "aws_sagemaker_model" "embedding_model" {
  name               = "${var.project_name}-embedding-model"
  execution_role_arn = aws_iam_role.sagemaker_role.arn

  primary_container {
    image = "763104351884.dkr.ecr.${var.aws_region}.amazonaws.com/huggingface-pytorch-inference:2.1.0-transformers4.37.0-cpu-py310-ubuntu22.04"
    environment = {
      HF_MODEL_ID = "sentence-transformers/all-MiniLM-L6-v2"
      HF_TASK     = "feature-extraction"
    }
  }

  tags = { Project = var.project_name }
}

resource "aws_sagemaker_endpoint_configuration" "embedding_config" {
  name = "${var.project_name}-embedding-config"

  production_variants {
    variant_name = "default"
    model_name   = aws_sagemaker_model.embedding_model.name

    serverless_config {
      # Why max_concurrency=1:
      #   Reduces cost — only 1 request processed at a time
      #   Sufficient for development/demo usage
      #   Scale up to 10 for production
      max_concurrency   = 1
      memory_size_in_mb = 1024
      # Why 1024 not 2048:
      #   all-MiniLM-L6-v2 is a small model
      #   1024MB is sufficient
      #   Halves the per-inference cost
    }
  }

  tags = { Project = var.project_name }
}

resource "aws_sagemaker_endpoint" "embedding_endpoint" {
  name                 = "${var.project_name}-embedding"
  endpoint_config_name = aws_sagemaker_endpoint_configuration.embedding_config.name
  tags                 = { Project = var.project_name }
}