output "log_verifier_github_oidc_role_arn" {
  description = <<-EOT
    IAM role ARN for GitHub Actions OIDC from repo Opentrons/log-verifier to deploy
    artifacts to s3://builds.opentrons.com/logviewer/ and
    s3://ot3-development.builds.opentrons.com/logviewer/.
    Set GitHub variable OT_LOGVERIFIER_DEPLOY_ROLE to this value.
  EOT
  value       = aws_iam_role.github_actions_log_verifier_deploy.arn
}

output "log_verifier_deploy_folders" {
  description = "S3 destinations used by .github/workflows/build-deploy.yaml"
  value = {
    release          = "s3://${data.aws_s3_bucket.builds.id}/logviewer/"
    internal_release = "s3://${data.aws_s3_bucket.ot3_development_builds.id}/logviewer/"
  }
}
