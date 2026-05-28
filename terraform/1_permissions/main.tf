data "aws_caller_identity" "current" {}

resource "aws_iam_group" "alex_developers" {
  name = "${var.project_name}-developers"
}

resource "aws_iam_policy" "alex_policy" {
  name        = "${var.project_name}-policy"
  description = "Permissions required for Alex AI platform"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [

      # SageMaker — needed for embedding endpoint
      {
        Effect   = "Allow"
        Action   = [
          "sagemaker:CreateModel",
          "sagemaker:CreateEndpointConfig",
          "sagemaker:CreateEndpoint",
          "sagemaker:DeleteModel",
          "sagemaker:DeleteEndpointConfig",
          "sagemaker:DeleteEndpoint",
          "sagemaker:DescribeEndpoint",
          "sagemaker:InvokeEndpoint",
          "sagemaker:ListEndpoints"
        ]
        Resource = "*"
      },

      # S3 — needed for vector storage
      {
        Effect   = "Allow"
        Action   = [
          "s3:CreateBucket",
          "s3:DeleteBucket",
          "s3:GetObject",
          "s3:PutObject",
          "s3:DeleteObject",
          "s3:ListBucket",
          "s3:PutBucketVersioning",
          "s3:PutEncryptionConfiguration",
          "s3:PutBucketPublicAccessBlock"
        ]
        Resource = "*"
      },

      # S3 Vectors — the vector database operations
      {
        Effect   = "Allow"
        Action   = [
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
      },

      # Lambda — ingest and scheduler functions
      {
        Effect   = "Allow"
        Action   = [
          "lambda:CreateFunction",
          "lambda:UpdateFunctionCode",
          "lambda:UpdateFunctionConfiguration",
          "lambda:DeleteFunction",
          "lambda:InvokeFunction",
          "lambda:GetFunction",
          "lambda:AddPermission",
          "lambda:RemovePermission",
          "lambda:ListFunctions"
        ]
        Resource = "*"
      },

      # API Gateway — the public endpoint
      {
        Effect   = "Allow"
        Action   = [
          "apigateway:*"
        ]
        Resource = "*"
      },

      # ECR — Docker image registry
      {
        Effect = "Allow"
        Action = [
          "ecr:CreateRepository",
          "ecr:DeleteRepository",
          "ecr:GetAuthorizationToken",
          "ecr:BatchCheckLayerAvailability",
          "ecr:PutImage",
          "ecr:InitiateLayerUpload",
          "ecr:UploadLayerPart",
          "ecr:CompleteLayerUpload",
          "ecr:DescribeRepositories",
          "ecr:GetDownloadUrlForLayer",
          "ecr:BatchGetImage"
        ]
        Resource = "*"
      },

      # ECS Express — runs the researcher agent
      {
        Effect = "Allow"
        Action = [
          "ecs:CreateCluster",
          "ecs:DeleteCluster",
          "ecs:CreateService",
          "ecs:UpdateService",
          "ecs:DeleteService",
          "ecs:RegisterTaskDefinition",
          "ecs:DeregisterTaskDefinition",
          "ecs:DescribeServices",
          "ecs:DescribeClusters",
          "ecs:DescribeTaskDefinition",
          "ecs:ListClusters",
          "ecs:ListServices",
          "ecs:ListTaskDefinitions",
          "ecs:RunTask",
          "ecs:StopTask",
          "ecs:DescribeTasks"
        ]
        Resource = "*"
      },

      # VPC — needed for ECS networking
      {
        Effect = "Allow"
        Action = [
          "ec2:CreateVpc",
          "ec2:DeleteVpc",
          "ec2:CreateSubnet",
          "ec2:DeleteSubnet",
          "ec2:CreateInternetGateway",
          "ec2:DeleteInternetGateway",
          "ec2:AttachInternetGateway",
          "ec2:DetachInternetGateway",
          "ec2:CreateRouteTable",
          "ec2:DeleteRouteTable",
          "ec2:CreateRoute",
          "ec2:AssociateRouteTable",
          "ec2:CreateSecurityGroup",
          "ec2:DeleteSecurityGroup",
          "ec2:AuthorizeSecurityGroupIngress",
          "ec2:AuthorizeSecurityGroupEgress",
          "ec2:DescribeVpcs",
          "ec2:DescribeSubnets",
          "ec2:DescribeSecurityGroups",
          "ec2:DescribeInternetGateways",
          "ec2:DescribeRouteTables",
          "ec2:DescribeAvailabilityZones",
          "ec2:AllocateAddress",
          "ec2:ReleaseAddress",
          "ec2:CreateNatGateway",
          "ec2:DeleteNatGateway",
          "ec2:DescribeNatGateways",
          "ec2:DescribeAddresses"
        ]
        Resource = "*"
      },

      # ELB — load balancer for ECS public URL
      {
        Effect = "Allow"
        Action = [
          "elasticloadbalancing:CreateLoadBalancer",
          "elasticloadbalancing:DeleteLoadBalancer",
          "elasticloadbalancing:CreateTargetGroup",
          "elasticloadbalancing:DeleteTargetGroup",
          "elasticloadbalancing:CreateListener",
          "elasticloadbalancing:DeleteListener",
          "elasticloadbalancing:RegisterTargets",
          "elasticloadbalancing:DeregisterTargets",
          "elasticloadbalancing:DescribeLoadBalancers",
          "elasticloadbalancing:DescribeTargetGroups",
          "elasticloadbalancing:DescribeListeners",
          "elasticloadbalancing:ModifyTargetGroupAttributes"
        ]
        Resource = "*"
      },


      # Bedrock — the AI model
      {
        Effect   = "Allow"
        Action   = [
          "bedrock:InvokeModel",
          "bedrock:InvokeModelWithResponseStream",
          "bedrock:ListFoundationModels",
          "bedrock:GetFoundationModel"
        ]
        Resource = "*"
      },

      # IAM — needed for Terraform to create service roles
      {
        Effect   = "Allow"
        Action   = [
          "iam:CreateRole",
          "iam:DeleteRole",
          "iam:AttachRolePolicy",
          "iam:DetachRolePolicy",
          "iam:PutRolePolicy",
          "iam:DeleteRolePolicy",
          "iam:GetRole",
          "iam:PassRole",
          "iam:CreatePolicy",
          "iam:DeletePolicy",
          "iam:GetPolicy",
          "iam:GetPolicyVersion",
          "iam:ListAttachedRolePolicies",
          "iam:ListRolePolicies",
          "iam:CreateInstanceProfile",
          "iam:DeleteInstanceProfile",
          "iam:AddRoleToInstanceProfile"
        ]
        Resource = "*"
      },

      # CloudWatch — logs and monitoring
      {
        Effect   = "Allow"
        Action   = [
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents",
          "logs:DescribeLogGroups",
          "logs:DeleteLogGroup"
        ]
        Resource = "*"
      },

      # Aurora (Guide 5) — the relational database
      {
        Effect   = "Allow"
        Action   = [
          "rds:CreateDBCluster",
          "rds:DeleteDBCluster",
          "rds:DescribeDBClusters",
          "rds:ModifyDBCluster",
          "rds:CreateDBSubnetGroup",
          "rds:DeleteDBSubnetGroup",
          "rds:DescribeDBSubnetGroups"
        ]
        Resource = "*"
      },

      # SQS (Guide 6) — message queue for agent orchestration
      {
        Effect   = "Allow"
        Action   = [
          "sqs:CreateQueue",
          "sqs:DeleteQueue",
          "sqs:SendMessage",
          "sqs:ReceiveMessage",
          "sqs:DeleteMessage",
          "sqs:GetQueueAttributes",
          "sqs:SetQueueAttributes",
          "sqs:ListQueues"
        ]
        Resource = "*"
      },

      # CloudFront + S3 (Guide 7) — frontend hosting
      {
        Effect   = "Allow"
        Action   = [
          "cloudfront:CreateDistribution",
          "cloudfront:UpdateDistribution",
          "cloudfront:DeleteDistribution",
          "cloudfront:GetDistribution",
          "cloudfront:CreateInvalidation"
        ]
        Resource = "*"
      }
    ]
  })
}

resource "aws_iam_group_policy_attachment" "alex_policy_attachment" {
  group      = aws_iam_group.alex_developers.name
  policy_arn = aws_iam_policy.alex_policy.arn
}

resource "aws_iam_user" "developer" {
  name = "${var.project_name}-developer"

  tags = {
    Project = var.project_name
    Purpose = "Alex AI platform developer access"
  }
}

resource "aws_iam_user_group_membership" "developer_membership" {
  user   = aws_iam_user.developer.name
  groups = [aws_iam_group.alex_developers.name]
}