output "api_endpoint" {
  description = "API Gateway endpoint URL — add to .env as ALEX_API_ENDPOINT"
  value       = "${aws_api_gateway_stage.api.invoke_url}/ingest"
}

output "api_key_id" {
  description = "API key ID — use to retrieve the actual key value"
  value       = aws_api_gateway_api_key.api_key.id
}

output "vector_bucket_name" {
  description = "S3 bucket name for vectors"
  value       = aws_s3_bucket.vectors.id
}

output "lambda_function_name" {
  description = "Lambda function name"
  value       = aws_lambda_function.ingest.function_name
}