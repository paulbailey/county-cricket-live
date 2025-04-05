variable "github_token" {
  description = "GitHub Personal Access Token with workflow permissions"
  type        = string
  sensitive   = true
}

variable "poll_youtube_schedule" {
  description = "EventBridge scheduler cron expression for poll-youtube workflow"
  type        = string
  default     = "cron(0/5 8-20 * * ? *)" # Every 5 minutes between 8 AM and 8:59 PM UTC
}

variable "deploy_schedule" {
  description = "EventBridge scheduler cron expression for deploy workflow"
  type        = string
  default     = "cron(* 8-20 * * ? *)" # Every minute between 8 AM and 8:59 PM UTC
}
