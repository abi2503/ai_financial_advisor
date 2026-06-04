output "cluster_arn" {
  description = "Aurora cluster ARN — needed for RDS Data API calls"
  value       = aws_rds_cluster.aurora.arn
}

output "cluster_endpoint" {
  description = "Aurora cluster endpoint"
  value       = aws_rds_cluster.aurora.endpoint
}

output "secret_arn" {
  description = "Secrets Manager ARN for DB credentials"
  value       = aws_secretsmanager_secret.aurora_credentials.arn
}

output "database_name" {
  description = "Database name"
  value       = var.db_name
}