# /// script
# dependencies = [
#     "boto3==1.40.61",
#     "semver==3.0.4",
#     "yarl==1.22.0",
# ]
# ///

import argparse
import copy
import json
import os
import uuid
from pathlib import Path

import boto3
import semver
from botocore.exceptions import ClientError
from yarl import URL

INSTALLERS = {"win": ".msi", "mac": ".dmg", "linux": ".AppImage"}
STABLE_NAMES = {
    "win": "Log Verifier.msi",
    "mac": "Log Verifier.dmg",
    "linux": "Log Verifier.AppImage",
}
PUBLIC = {"ACL": "public-read", "CacheControl": "max-age=60"}


def select_installers(filenames):
    chosen = {}
    for platform, extension in INSTALLERS.items():
        matches = [name for name in filenames if name.endswith(extension)]
        if len(matches) > 1:
            raise ValueError(f"Multiple {platform} installers: {', '.join(matches)}")
        if matches:
            chosen[platform] = matches[0]
    return chosen


def artifact_url(base_url, filename):
    return str(URL(base_url) / filename)


def update_releases(existing, version, filenames, base_url):
    if not version:
        raise ValueError("version is required")
    document = {"productionV1": {}} if existing is None else copy.deepcopy(existing)
    releases = document.get("productionV1")
    if not isinstance(releases, dict):
        releases = {}
        document["productionV1"] = releases
    installers = select_installers(filenames)
    if not installers:
        raise ValueError(f"No installers found for {version}")
    previous = releases.get(version) or {}
    releases[version] = {
        platform: artifact_url(base_url, name) for platform, name in installers.items()
    }
    for flag in ("active", "revoked"):
        if isinstance(previous.get(flag), bool):
            releases[version][flag] = previous[flag]
    return document


def _releases_of(document):
    releases = document.get("productionV1") if isinstance(document, dict) else None
    if not isinstance(releases, dict):
        raise ValueError("releases.json is missing productionV1")
    return releases


def _stable(version):
    try:
        parsed = semver.Version.parse(version)
    except ValueError:
        return None
    return parsed if parsed == parsed.finalize_version() else None


def latest_version(releases):
    versions = [
        parsed
        for version, release in releases.items()
        if release.get("revoked") is not True and (parsed := _stable(version))
    ]
    if not versions:
        raise ValueError("No production release")
    return str(max(versions))


def _flag_active(releases, chosen):
    for version, release in releases.items():
        if version == chosen or release.get("active") is True:
            release["active"] = version == chosen


def mark_latest_active(document):
    document = copy.deepcopy(document)
    releases = _releases_of(document)
    _flag_active(releases, latest_version(releases))
    return document


def revoke_latest(document):
    document = copy.deepcopy(document)
    releases = _releases_of(document)
    current = latest_version(releases)
    releases[current].update(revoked=True, active=False)
    try:
        chosen = latest_version(releases)
    except ValueError:
        chosen = None
    _flag_active(releases, chosen)
    return document


def active_release(document):
    releases = _releases_of(document)
    versions = [
        version
        for version, release in releases.items()
        if release.get("active") is True
    ]
    if len(versions) > 1:
        raise ValueError(f"Multiple active releases: {', '.join(versions)}")
    if not versions:
        return None
    return versions[0], releases[versions[0]]


def magic_links(document):
    active = active_release(document)
    if active is None:
        return []
    version, release = active
    return [
        {
            "platform": platform,
            "filename": filename,
            "version": version,
            "source_key": URL(release[platform]).path.lstrip("/"),
        }
        for platform, filename in STABLE_NAMES.items()
        if isinstance(release.get(platform), str) and release[platform]
    ]


def fetch_releases(bucket, prefix, s3):
    try:
        payload = s3.get_object(
            Bucket=bucket, Key=f"{prefix.strip('/')}/releases.json"
        )["Body"].read()
    except ClientError as error:
        if error.response["Error"]["Code"] not in {"NoSuchKey", "404"}:
            raise
        return {"productionV1": {}}
    return json.loads(payload)


def publish(document, bucket, prefix, distribution_id=None, s3=None, cloudfront=None):
    client = s3 or boto3.client("s3")
    prefix = prefix.strip("/")
    client.put_object(
        Bucket=bucket,
        Key=f"{prefix}/releases.json",
        Body=json.dumps(document, indent=2).encode() + b"\n",
        ContentType="application/json",
        **PUBLIC,
    )
    for link in magic_links(document):
        destination = f"{prefix}/{link['filename']}"
        source = client.head_object(Bucket=bucket, Key=link["source_key"])
        print(f"Stable link s3://{bucket}/{destination} -> {link['source_key']}")
        client.copy_object(
            Bucket=bucket,
            Key=destination,
            CopySource={"Bucket": bucket, "Key": link["source_key"]},
            ContentType=source["ContentType"],
            MetadataDirective="REPLACE",
            **PUBLIC,
        )
    if not magic_links(document):
        print("No active release. Stable links were left unchanged.")
    if distribution_id:
        (cloudfront or boto3.client("cloudfront")).create_invalidation(
            DistributionId=distribution_id,
            InvalidationBatch={
                "Paths": {"Quantity": 1, "Items": [f"/{prefix}/*"]},
                "CallerReference": str(uuid.uuid4()),
            },
        )


def _filenames(artifact_dir):
    return [path.name for path in Path(artifact_dir).iterdir() if path.is_file()]


def _active_version(document):
    active = active_release(document)
    return None if active is None else active[0]


def write_latest_summary(before, after):
    path = os.environ.get("GITHUB_STEP_SUMMARY")
    if not path:
        return
    with open(path, "a", encoding="utf-8") as summary:
        summary.write("## Latest release\n\n")
        summary.write(f"- Before: `{before or 'none'}`\n")
        summary.write(f"- After: `{after or 'none'}`\n")


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=["update", "activate", "revoke"])
    parser.add_argument("--bucket", required=True)
    parser.add_argument("--prefix", required=True)
    parser.add_argument("--distribution-id", default="")
    parser.add_argument("--version")
    parser.add_argument("--artifact-dir")
    args = parser.parse_args(argv)

    s3 = boto3.client("s3")
    document = fetch_releases(args.bucket, args.prefix, s3)
    if args.command == "update":
        document = update_releases(
            document,
            args.version,
            _filenames(args.artifact_dir),
            f"https://{args.bucket}/{args.prefix.strip('/')}",
        )
    else:
        before = _active_version(document)
        document = {"activate": mark_latest_active, "revoke": revoke_latest}[
            args.command
        ](document)
        after = _active_version(document)
        print("No active release" if after is None else f"Active release {after}")
        write_latest_summary(before, after)
    publish(document, args.bucket, args.prefix, args.distribution_id or None, s3=s3)


if __name__ == "__main__":
    main()
