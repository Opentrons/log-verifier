terraform {
  required_version = ">= 1.3"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 6.0"
    }
  }
  backend "s3" {
    bucket       = "core-infra-tf-state"
    encrypt      = true
    key          = "robotics/log-verifier"
    use_lockfile = true
    profile      = "terraform-state"
    region       = "us-east-2"
  }
}
