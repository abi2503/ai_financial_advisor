variable "aws_region" {
  description = "AWS region"
  type        = string
  default     = "us-east-1"
}

variable "project_name" {
  description = "Project name"
  type        = string
  default     = "alex"
}

variable "sagemaker_endpoint_name" {
  description = "SageMaker embedding endpoint name from Guide 2"
  type        = string
}