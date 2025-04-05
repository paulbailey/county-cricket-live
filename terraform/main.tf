resource "aws_scheduler_schedule_group" "github_actions" {
  name = "github-actions"
}

resource "aws_scheduler_connection" "github" {
  name = "github-connection"

  auth_parameters {
    api_key {
      key   = "Authorization"
      value = "Bearer ${var.github_token}"
    }
  }
}

# API Destination for GitHub
resource "aws_scheduler_destination" "github" {
  name = "github-api"

  api_destination {
    api_id              = aws_scheduler_connection.github.id
    method              = "POST"
    invocation_endpoint = "https://api.github.com/repos/PBailey/county-cricket-live/dispatches"
    header_parameters = {
      "Accept"       = "application/vnd.github.v3+json"
      "Content-Type" = "application/json"
    }
  }
}

# Poll YouTube workflow schedule
resource "aws_scheduler_schedule" "poll_youtube_workflow" {
  name                = "trigger-poll-youtube-workflow"
  group_name          = aws_scheduler_schedule_group.github_actions.name
  schedule_expression = var.poll_youtube_schedule
  state               = "ENABLED"

  flexible_time_window {
    mode = "OFF"
  }

  target {
    arn      = aws_scheduler_destination.github.arn
    role_arn = aws_iam_role.scheduler_role.arn

    input = jsonencode({
      event_type = "poll-youtube"
      client_payload = {
        triggered_by = "eventbridge"
      }
    })

    retry_policy {
      maximum_retry_attempts = 3
    }
  }
}

# Deploy workflow schedule
resource "aws_scheduler_schedule" "deploy_workflow" {
  name                = "trigger-deploy-workflow"
  group_name          = aws_scheduler_schedule_group.github_actions.name
  schedule_expression = var.deploy_schedule
  state               = "ENABLED"

  flexible_time_window {
    mode = "OFF"
  }

  target {
    arn      = aws_scheduler_destination.github.arn
    role_arn = aws_iam_role.scheduler_role.arn

    input = jsonencode({
      event_type = "deploy"
      client_payload = {
        triggered_by = "eventbridge"
      }
    })

    retry_policy {
      maximum_retry_attempts = 3
    }
  }
}

resource "aws_iam_role" "scheduler_role" {
  name = "eventbridge-scheduler-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "scheduler.amazonaws.com"
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
          "scheduler:InvokeApiDestination"
        ]
        Resource = aws_scheduler_destination.github.arn
      }
    ]
  })
}
