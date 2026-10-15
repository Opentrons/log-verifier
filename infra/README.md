# Log Verifier release hosting

GitHub Actions for Opentrons/log-verifier uploads signed installers to the existing
builds website buckets, under `logviewer/` — the same pattern as the desktop app's `app/` prefix.

| Channel  | URL                                                    |
| -------- | ------------------------------------------------------ |
| Release  | https://builds.opentrons.com/logviewer                 |
| Internal | https://ot3-development.builds.opentrons.com/logviewer |

This stack does **not** create those buckets. It creates an IAM role that GitHub
Actions assumes via OIDC, with object access limited to the `logviewer/` prefix.

## Apply

Requires the same AWS profiles as `robot-stack-infra` (`terraform-state` and
`robotics_robot_stack_prod-admin`).

```sh
cd infra
terraform init
terraform apply
# optional: pass the builds.opentrons.com CloudFront ID so the role can invalidate
# terraform apply -var='builds_cloudfront_distribution_id=<id from release-ci>'
```

## GitHub Actions variables

After apply:

1. Set `OT_LOGVERIFIER_DEPLOY_ROLE` to `terraform output -raw log_verifier_github_oidc_role_arn`.
2. Optionally set `OT_LOGVERIFIER_BUILDS_CLOUDFRONT_DISTRIBUTION_ID` to the
   `builds.opentrons.com` distribution ID (same value as
   `OT_APP_BUILDS_CLOUDFRONT_DISTRIBUTION_ID` in Opentrons/opentrons).
