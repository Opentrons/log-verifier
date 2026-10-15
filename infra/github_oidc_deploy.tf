# GitHub Actions OIDC role for Opentrons/log-verifier desktop app deploys.
#
# Mirrors inf/release-ci/opentrons_monorepo_app_deploy_oidc.tf in robot-stack-infra,
# scoped to prefix "logviewer/" instead of "app/".
#
# Buckets: robot-stack prod website (builds.opentrons.com) + ot3 prod website
# (ot3-development.builds.opentrons.com).
#
# After apply, set GitHub Actions variable OT_LOGVERIFIER_DEPLOY_ROLE to
# terraform output -raw log_verifier_github_oidc_role_arn.
#
# Prerequisite: IAM OIDC provider for https://token.actions.githubusercontent.com
# must exist in the robotics_robot_stack_prod account.

data "aws_caller_identity" "current" {}

data "aws_iam_openid_connect_provider" "github_actions" {
  url = "https://token.actions.githubusercontent.com"
}

data "aws_s3_bucket" "builds" {
  bucket = "builds.opentrons.com"
}

data "aws_s3_bucket" "ot3_development_builds" {
  bucket = "ot3-development.builds.opentrons.com"
}

locals {
  # GitHub issues this repo's OIDC subject with immutable org/repo IDs
  # ("repo:Opentrons@<org id>/<repo name>@<repo id>:..."), which is why the plain
  # "repo:Opentrons/opentrons:*" form used by the monorepo role does not match here.
  # See: gh api /repos/Opentrons/log-verifier/actions/oidc/customization/sub
  # Name and ID forms are both allowed. The repo id stays 1332098088.
  github_sub_patterns = [
    "repo:Opentrons/log-verifier:*",
    "repo:Opentrons@6139147/log-verifier@1332098088:*",
  ]

  object_arns = [
    "${data.aws_s3_bucket.builds.arn}/logviewer/*",
    "${data.aws_s3_bucket.ot3_development_builds.arn}/logviewer/*",
  ]
  cloudfront_arn = var.builds_cloudfront_distribution_id == "" ? null : "arn:aws:cloudfront::${data.aws_caller_identity.current.account_id}:distribution/${var.builds_cloudfront_distribution_id}"
}

resource "aws_iam_role" "github_actions_log_verifier_deploy" {
  name        = "github-actions-log-verifier-deploy"
  description = "OIDC: Opentrons/log-verifier S3 deploy to robot-stack + ot3 builds buckets (logviewer/ prefix)"

  lifecycle {
    create_before_destroy = true
  }

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = "sts:AssumeRoleWithWebIdentity"
        Principal = {
          Federated = data.aws_iam_openid_connect_provider.github_actions.arn
        }
        Condition = {
          StringEquals = {
            "token.actions.githubusercontent.com:aud" = "sts.amazonaws.com"
          }
          StringLike = {
            "token.actions.githubusercontent.com:sub" = local.github_sub_patterns
          }
        }
      }
    ]
  })
}

resource "aws_iam_role_policy" "github_actions_log_verifier_deploy_s3" {
  name = "log-verifier-s3-logverifier-prefix"
  role = aws_iam_role.github_actions_log_verifier_deploy.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = concat(
      [
        {
          Sid    = "ListBucketsForSync"
          Effect = "Allow"
          Action = [
            "s3:ListBucket",
            "s3:GetBucketLocation",
          ]
          Resource = [
            data.aws_s3_bucket.builds.arn,
            data.aws_s3_bucket.ot3_development_builds.arn,
          ]
        },
        {
          Sid    = "ObjectRWInReleasePrefix"
          Effect = "Allow"
          Action = [
            "s3:GetObject",
            "s3:PutObject",
            "s3:PutObjectAcl",
            "s3:DeleteObject",
            "s3:AbortMultipartUpload",
          ]
          Resource = local.object_arns
        },
      ],
      local.cloudfront_arn == null ? [] : [
        {
          Sid      = "InvalidateProdBuildsCloudFront"
          Effect   = "Allow"
          Action   = ["cloudfront:CreateInvalidation"]
          Resource = local.cloudfront_arn
        },
      ],
    )
  })
}
