output "research_queue_url" {
  description = "SQS research queue URL"
  value       = aws_sqs_queue.research_queue.url
}

output "results_queue_url" {
  description = "SQS results queue URL"
  value       = aws_sqs_queue.results_queue.url
}

output "dlq_url" {
  description = "Dead letter queue URL"
  value       = aws_sqs_queue.dlq.url
}

output "planner_function_name" {
  description = "Planner Lambda function name"
  value       = aws_lambda_function.planner.function_name
}

output "scheduler_function_name" {
  description = "Scheduler Lambda function name"
  value       = aws_lambda_function.scheduler.function_name
}

output "tagger_function_name" {
  description = "Tagger Lambda function name"
  value       = aws_lambda_function.tagger.function_name
}

output "reporter_function_name" {
  description = "Reporter Lambda function name"
  value       = aws_lambda_function.reporter.function_name
}