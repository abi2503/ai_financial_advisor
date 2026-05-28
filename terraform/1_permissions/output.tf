output "developer_user_name" {
  description = "IAM user name for Alex developer"
  value       = aws_iam_user.developer.name
}

output "developer_group_name" {
  description = "IAM group name"
  value       = aws_iam_group.alex_developers.name
}

output "policy_arn" {
  description = "ARN of the Alex IAM policy"
  value       = aws_iam_policy.alex_policy.arn
}