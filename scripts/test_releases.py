# /// script
# dependencies = [
#     "pytest==8.4.2",
# ]
# ///

import pytest

from releases import magic_links, mark_latest_active, revoke_latest, update_releases

BASE_URL = "https://builds.opentrons.com/logviewer"
FILENAMES = [
    "Log Verifier-v1.2.3-win-abc.msi",
    "Log Verifier-v1.2.3-mac-abc.dmg",
    "Log Verifier-v1.2.3-mac-abc.zip",
    "Log Verifier-v1.2.3-linux-abc.AppImage",
    "latest.yml",
    "Log Verifier-v1.2.3-mac-abc.dmg.blockmap",
]


def test_update_omits_active_and_revoked():
    document = update_releases(None, "1.2.3", FILENAMES, BASE_URL)
    assert document == {
        "productionV1": {
            "1.2.3": {
                "win": "https://builds.opentrons.com/logviewer/Log%20Verifier-v1.2.3-win-abc.msi",
                "mac": "https://builds.opentrons.com/logviewer/Log%20Verifier-v1.2.3-mac-abc.dmg",
                "linux": "https://builds.opentrons.com/logviewer/Log%20Verifier-v1.2.3-linux-abc.AppImage",
            }
        }
    }


def test_update_preserves_existing_flags():
    existing = {
        "productionV1": {
            "1.0.0": {
                "win": "https://builds.opentrons.com/logviewer/old.msi",
                "active": True,
            },
            "1.2.3": {
                "win": "https://builds.opentrons.com/logviewer/stale.msi",
                "revoked": True,
            },
        }
    }
    document = update_releases(existing, "1.2.3", FILENAMES, BASE_URL)
    assert document["productionV1"]["1.0.0"] == existing["productionV1"]["1.0.0"]
    assert document["productionV1"]["1.2.3"]["revoked"] is True
    assert "active" not in document["productionV1"]["1.2.3"]
    assert (
        "Log%20Verifier-v1.2.3-win-abc.msi" in document["productionV1"]["1.2.3"]["win"]
    )


@pytest.mark.parametrize(
    "filenames",
    [
        ["Log Verifier-v1.2.3-mac-abc.zip"],
        ["Log Verifier-v1.2.3-win-abc.exe"],
        ["latest.yml"],
    ],
)
def test_update_rejects_non_installers(filenames):
    with pytest.raises(ValueError, match="No installers found"):
        update_releases(None, "1.2.3", filenames, BASE_URL)


def test_activate_highest_production_version():
    document = {
        "productionV1": {
            "1.9.0": {
                "win": "https://builds.opentrons.com/logviewer/old.msi",
                "mac": "https://builds.opentrons.com/logviewer/old.dmg",
                "linux": "https://builds.opentrons.com/logviewer/old.AppImage",
                "active": True,
            },
            "1.10.0": {
                "win": "https://builds.opentrons.com/logviewer/Log%20Verifier-v1.10.0-win.msi",
                "mac": "https://builds.opentrons.com/logviewer/Log%20Verifier-v1.10.0-mac.dmg",
                "linux": "https://builds.opentrons.com/logviewer/Log%20Verifier-v1.10.0-linux.AppImage",
            },
            "2.0.0": {
                "win": "https://builds.opentrons.com/logviewer/revoked.msi",
                "revoked": True,
                "active": True,
            },
            "2.1.0-alpha.1": {
                "win": "https://builds.opentrons.com/logviewer/alpha.msi"
            },
        }
    }
    active = mark_latest_active(document)
    assert active["productionV1"]["1.10.0"]["active"] is True
    assert active["productionV1"]["1.9.0"]["active"] is False
    assert active["productionV1"]["2.0.0"]["active"] is False
    assert "active" not in active["productionV1"]["2.1.0-alpha.1"]
    assert [link["version"] for link in magic_links(active)] == [
        "1.10.0",
        "1.10.0",
        "1.10.0",
    ]


def test_revoke_moves_active_to_previous_version():
    document = {
        "productionV1": {
            "1.9.0": {
                "win": "https://builds.opentrons.com/logviewer/old.msi",
                "mac": "https://builds.opentrons.com/logviewer/old.dmg",
                "linux": "https://builds.opentrons.com/logviewer/old.AppImage",
            },
            "1.10.0": {
                "win": "https://builds.opentrons.com/logviewer/Log%20Verifier-v1.10.0-win.msi",
                "mac": "https://builds.opentrons.com/logviewer/Log%20Verifier-v1.10.0-mac.dmg",
                "linux": "https://builds.opentrons.com/logviewer/Log%20Verifier-v1.10.0-linux.AppImage",
                "active": True,
            },
        }
    }
    revoked = revoke_latest(document)
    assert revoked["productionV1"]["1.10.0"]["active"] is False
    assert revoked["productionV1"]["1.10.0"]["revoked"] is True
    assert revoked["productionV1"]["1.9.0"]["active"] is True
    assert [
        (link["filename"], link["source_key"]) for link in magic_links(revoked)
    ] == [
        ("Log Verifier.msi", "logviewer/old.msi"),
        ("Log Verifier.dmg", "logviewer/old.dmg"),
        ("Log Verifier.AppImage", "logviewer/old.AppImage"),
    ]
