output "endpoint_name" {
  description = "SageMaker endpoint name — used by Lambda in Guide 3"
  value       = aws_sagemaker_endpoint.embedding_endpoint.name
}

output "endpoint_arn" {
  description = "SageMaker endpoint ARN"
  value       = aws_sagemaker_endpoint.embedding_endpoint.arn
}