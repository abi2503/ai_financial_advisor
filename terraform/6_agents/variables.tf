variable "aws_region" {
  type    = string
  default = "us-east-1"
}

variable "project_name" {
  type    = string
  default = "alex"
}

variable "alex_api_endpoint" {
  type        = string
  description = "Guide 3 API Gateway endpoint"
}

variable "alex_api_key" {
  type      = string
  sensitive = true
}

variable "openai_api_key" {
  type      = string
  sensitive = true
}

variable "db_cluster_arn" {
  type        = string
  description = "Aurora cluster ARN from Guide 5"
}

variable "db_secret_arn" {
  type        = string
  description = "Aurora secret ARN from Guide 5"
}

variable "db_name" {
  type    = string
  default = "alex_db"
}