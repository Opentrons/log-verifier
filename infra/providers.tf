provider "aws" {
  profile = "robotics_robot_stack_prod-admin"
  region  = "us-east-1"

  default_tags {
    tags = {
      ou      = "robotics"
      service = "log-verifier"
    }
  }
}
