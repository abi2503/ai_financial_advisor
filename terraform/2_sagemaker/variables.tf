variable "aws_region" {
  description = "AWS region to deploy resources"
  type        = string
  default     = "us-east-1"
}

variable "project_name" {
  description = "Project name used for resource naming"
  type        = string
  default     = "alex"
}

variable "sagemaker_instance_type" {
  description = "Instance type for SageMaker serverless endpoint"
  type        = string
  default     = "ml.serverless"
}