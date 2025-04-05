output "schedule_group_name" {
  description = "Name of the EventBridge scheduler group"
  value       = aws_scheduler_schedule_group.github_actions.name
}

output "poll_youtube_schedule_name" {
  description = "Name of the EventBridge schedule for poll-youtube workflow"
  value       = aws_scheduler_schedule.poll_youtube_workflow.name
}

output "deploy_schedule_name" {
  description = "Name of the EventBridge schedule for deploy workflow"
  value       = aws_scheduler_schedule.deploy_workflow.name
}

output "connection_name" {
  description = "Name of the EventBridge API destination connection"
  value       = aws_scheduler_connection.github.name
}
