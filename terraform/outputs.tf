output "poll_youtube_rule_name" {
  description = "Name of the EventBridge rule for poll-youtube workflow"
  value       = aws_cloudwatch_event_rule.poll_youtube_workflow.name
}

output "deploy_rule_name" {
  description = "Name of the EventBridge rule for deploy workflow"
  value       = aws_cloudwatch_event_rule.deploy_workflow.name
}

output "github_connection_name" {
  description = "Name of the EventBridge API destination connection"
  value       = aws_cloudwatch_event_connection.github.name
}

output "github_api_destination_name" {
  description = "Name of the EventBridge API destination"
  value       = aws_cloudwatch_event_api_destination.github.name
}
