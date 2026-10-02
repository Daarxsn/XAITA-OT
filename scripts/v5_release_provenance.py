#!/usr/bin/env python3
"""XAITA-OT V5.10 release provenance and artifact inventory gate."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import zipfile
import tarfile

ROOT = Path(__file__).resolve().parents[1]
DIST = ROOT / "dist"
OUT = ROOT / "artifacts"
OUT.mkdir(exist_ok=True)


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def git_value(*args: str) -> str:
    try:
        return subprocess.check_output(["git", *args], cwd=ROOT, text=True).strip()
    except Exception:
        return ""


def wheel_version(path: Path) -> str:
    with zipfile.ZipFile(path) as z:
        metadata = next(n for n in z.namelist() if n.endswith(".dist-info/METADATA"))
        text = z.read(metadata).decode("utf-8", "replace")
    for line in text.splitlines():
        if line.startswith("Version: "):
            return line.split(": ", 1)[1].strip()
    raise RuntimeError("wheel metadata has no Version field")


def main() -> int:
    artifacts = sorted([*DIST.glob("*.whl"), *DIST.glob("*.tar.gz")])
    if not artifacts:
        print("Release provenance: FAIL — no release artifacts found")
        return 1

    manifest = ROOT / "artifacts" / "v5_release_manifest.json"
    if not manifest.exists():
        print("Release provenance: FAIL — release manifest missing")
        return 1

    entries = []
    for path in artifacts:
        entries.append({
            "name": path.name,
            "size_bytes": path.stat().st_size,
            "sha256": sha256(path),
        })

    versions = {wheel_version(p) for p in DIST.glob("*.whl")}
    if len(versions) != 1:
        print("Release provenance: FAIL — inconsistent wheel versions")
        return 1

    provenance = {
        "schema_version": "XAITA-OT-V5.10-RELEASE-PROVENANCE-1.0",
        "project": "xaita-ot",
        "version": sorted(versions)[0],
        "git_commit": os.environ.get("GITHUB_SHA") or git_value("rev-parse", "HEAD"),
        "git_ref": os.environ.get("GITHUB_REF", ""),
        "python": sys.version.split()[0],
        "artifacts": entries,
        "release_manifest_sha256": sha256(manifest),
        "provenance_boundary": (
            "Integrity and build provenance for generated release artifacts; "
            "not a signature, attestation, penetration test, or production acceptance."
        ),
    }
    out = OUT / "v5_release_provenance.json"
    out.write_text(json.dumps(provenance, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"Release provenance: PASS — {len(entries)} artifacts, version {provenance['version']}")
    print(f"Wrote {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
