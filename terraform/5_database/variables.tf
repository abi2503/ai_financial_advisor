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

variable "db_name" {
  description = "Database name"
  type        = string
  default     = "alex_db"
}

variable "db_username" {
  description = "Database master username"
  type        = string
  default     = "alex_admin"
}