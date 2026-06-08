output "dashboard_url" {
  value = "https://console.aws.amazon.com/cloudwatch/home?region=us-east-1#dashboards:name=Alex-AI-Platform"
}

output "sns_topic_arn" {
  value = aws_sns_topic.alex_alarms.arn
}