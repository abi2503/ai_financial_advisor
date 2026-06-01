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

variable "openai_api_key" {
  description = "OpenAI API key for agent tracing"
  type        = string
  sensitive   = true
}

variable "alex_api_endpoint" {
  description = "Guide 3 ingest API endpoint"
  type        = string
}

variable "alex_api_key" {
  description = "API key for ALEX researcher"
  type= string
}