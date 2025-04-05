terraform {
  required_version = ">= 1.0.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }

  cloud {
    organization = "dreamshake" # Replace with your Terraform Cloud organization name

    workspaces {
      name = "county-cricket-live"
    }
  }
}

provider "aws" {
  region = var.aws_region

  default_tags {
    tags = {
      Project     = "county-cricket-live"
      Environment = var.environment
      Terraform   = "true"
    }
  }
}
