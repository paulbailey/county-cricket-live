resource "aws_cloudwatch_event_rule" "poll_youtube_workflow" {
  name                = "trigger-poll-youtube-workflow"
  description         = "Trigger the poll-youtube workflow on GitHub Actions"
  schedule_expression = var.poll_youtube_schedule
  state               = "ENABLED"
}

resource "aws_cloudwatch_event_rule" "deploy_workflow" {
  name                = "trigger-deploy-workflow"
  description         = "Trigger the deploy workflow on GitHub Actions"
  schedule_expression = var.deploy_schedule
  state               = "ENABLED"
}

resource "aws_cloudwatch_event_target" "poll_youtube_workflow" {
  rule      = aws_cloudwatch_event_rule.poll_youtube_workflow.name
  target_id = "GitHubDispatch"
  arn       = aws_cloudwatch_event_api_destination.github.arn
  role_arn  = aws_iam_role.scheduler_role.arn

  input = jsonencode({
    ref = "main"
  })

  retry_policy {
    maximum_retry_attempts = 3
    maximum_event_age_in_seconds = 60  }
}

resource "aws_cloudwatch_event_target" "deploy_workflow" {
  rule      = aws_cloudwatch_event_rule.deploy_workflow.name
  target_id = "GitHubDispatch"
  arn       = aws_cloudwatch_event_api_destination.github_deploy.arn
  role_arn  = aws_iam_role.scheduler_role.arn

  input = jsonencode({
    ref = "main"
  })

  retry_policy {
    maximum_retry_attempts = 3
    maximum_event_age_in_seconds = 60  }
}

resource "aws_cloudwatch_event_connection" "github" {
  name               = "github-connection"
  authorization_type = "API_KEY"

  auth_parameters {
    api_key {
      key   = "Authorization"
      value = "Bearer ${var.github_token}"
    }
  }
}

resource "aws_cloudwatch_event_api_destination" "github" {
  name                = "github-api"
  connection_arn      = aws_cloudwatch_event_connection.github.arn
  invocation_endpoint = "https://api.github.com/repos/paulbailey/county-cricket-live/actions/workflows/poll-youtube.yml/dispatches"
  http_method         = "POST"
}

# Create a second API destination for the deploy workflow
resource "aws_cloudwatch_event_api_destination" "github_deploy" {
  name                = "github-api-deploy"
  connection_arn      = aws_cloudwatch_event_connection.github.arn
  invocation_endpoint = "https://api.github.com/repos/paulbailey/county-cricket-live/actions/workflows/deploy.yml/dispatches"
  http_method         = "POST"
}

# Get current AWS account ID
data "aws_caller_identity" "current" {}

resource "aws_iam_role" "scheduler_role" {
  name = "eventbridge-scheduler-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "events.amazonaws.com"
        }
      }
    ]
  })
}

resource "aws_iam_role_policy" "scheduler_policy" {
  name = "eventbridge-scheduler-policy"
  role = aws_iam_role.scheduler_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "events:InvokeApiDestination"
        ]
        Resource = [
          aws_cloudwatch_event_api_destination.github.arn,
          "${aws_cloudwatch_event_api_destination.github.arn}/*"
        ]
      }
    ]
  })
}
