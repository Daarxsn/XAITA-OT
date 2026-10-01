import json
import subprocess
import sys


def test_release_manifest_is_deterministic_and_complete():
    first = subprocess.run(
        [sys.executable, "scripts/v5_release_manifest.py"],
        capture_output=True, text=True, check=True,
    )
    second = subprocess.run(
        [sys.executable, "scripts/v5_release_manifest.py"],
        capture_output=True, text=True, check=True,
    )
    assert first.stdout == second.stdout
    manifest = json.loads(first.stdout)
    assert manifest["schema_version"] == "XAITA-OT-V5-RELEASE-MANIFEST-1.0"
    assert manifest["package"] == "xaita-ot"
    assert manifest["version"] == "0.5.1"
    assert manifest["files"]
    assert all(len(item["sha256"]) == 64 for item in manifest["files"])
