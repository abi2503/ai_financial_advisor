output "api_endpoint" {
  description = "API Gateway endpoint URL"
  value       = "${aws_api_gateway_stage.api.invoke_url}/ingest"
}

output "api_key_id" {
  description = "API key ID"
  value       = aws_api_gateway_api_key.api_key.id
}

output "lambda_function_name" {
  description = "Lambda function name"
  value       = aws_lambda_function.ingest.function_name
}

output "vector_backend" {
  description = "Current vector storage backend"
  value       = "pgvector (Aurora Serverless)"
}