"""Prepare private runtime datasets for a Render deployment.

Raw benchmark files must not be committed to this public repository. The
service may instead receive a mounted persistent disk or download a private
archive at startup when XAITA_BATADAL_ARCHIVE_URL is configured.
"""
from __future__ import annotations

import hashlib
import os
import shutil
import sys
import tempfile
import urllib.request
import zipfile
from pathlib import Path


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def safe_extract(archive: Path, destination: Path) -> None:
    destination = destination.resolve()
    with zipfile.ZipFile(archive) as bundle:
        for member in bundle.infolist():
            target = (destination / member.filename).resolve()
            if target != destination and destination not in target.parents:
                raise RuntimeError(f"Unsafe archive member: {member.filename}")
        bundle.extractall(destination)


def main() -> int:
    root = Path(os.environ.get("XAITA_BATADAL_PATH", "/app/data/raw/batadal"))
    root.mkdir(parents=True, exist_ok=True)
    archive_url = os.environ.get("XAITA_BATADAL_ARCHIVE_URL")
    expected_sha = os.environ.get("XAITA_BATADAL_ARCHIVE_SHA256", "").strip().lower()

    if not archive_url:
        print(f"Runtime dataset preparation: using mounted path {root}")
        return 0

    with tempfile.TemporaryDirectory(prefix="xaita-batadal-") as temp_dir:
        archive = Path(temp_dir) / "batadal.zip"
        print("Runtime dataset preparation: downloading private BATADAL archive")
        request = urllib.request.Request(archive_url, headers={"User-Agent": "XAITA-OT-runtime/1.0"})
        with urllib.request.urlopen(request, timeout=120) as response, archive.open("wb") as output:
            shutil.copyfileobj(response, output)
        if expected_sha and sha256(archive) != expected_sha:
            raise RuntimeError("BATADAL archive SHA-256 does not match XAITA_BATADAL_ARCHIVE_SHA256")
        safe_extract(archive, root)
    print(f"Runtime dataset preparation: archive extracted to {root}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:  # fail closed: never start with silently partial data
        print(f"Runtime dataset preparation failed: {exc}", file=sys.stderr)
        raise
