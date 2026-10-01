#!/usr/bin/env python3
"""Build and attest a reproducible XAITA-OT V5 release candidate."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import zipfile
import tarfile

ROOT = Path(__file__).resolve().parents[1]
DIST = ROOT / "dist"
MANIFEST = ROOT / "artifacts" / "v5_release_manifest.json"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def package_version() -> str:
    import re
    text = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    match = re.search(r'^version\s*=\s*"([^"]+)"', text, re.MULTILINE)
    if not match:
        raise RuntimeError("package version is missing")
    return match.group(1)


def verify_wheel(path: Path, version: str) -> None:
    with zipfile.ZipFile(path) as archive:
        metadata = [n for n in archive.namelist() if n.endswith(".dist-info/METADATA")]
        if len(metadata) != 1:
            raise RuntimeError(f"expected exactly one wheel METADATA file: {path.name}")
        content = archive.read(metadata[0]).decode("utf-8", errors="strict")
        if f"Name: xaita-ot" not in content or f"Version: {version}" not in content:
            raise RuntimeError(f"wheel metadata mismatch: {path.name}")


def verify_sdist(path: Path, version: str) -> None:
    with tarfile.open(path, "r:gz") as archive:
        names = archive.getnames()
        if not any(name.endswith("/pyproject.toml") for name in names):
            raise RuntimeError(f"sdist does not contain pyproject.toml: {path.name}")
        if not any(name.startswith(f"xaita_ot-{version}/") for name in names):
            raise RuntimeError(f"sdist root does not match version {version}: {path.name}")


def main() -> int:
    version = package_version()
    wheels = sorted(DIST.glob("*.whl"))
    sdists = sorted(DIST.glob("*.tar.gz"))
    if len(wheels) != 1 or len(sdists) != 1:
        raise RuntimeError("release candidate must contain exactly one wheel and one sdist")
    verify_wheel(wheels[0], version)
    verify_sdist(sdists[0], version)

    records = []
    for path in [sdists[0], wheels[0]]:
        records.append({
            "filename": path.name,
            "sha256": sha256(path),
            "bytes": path.stat().st_size,
        })

    MANIFEST.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "schema_version": "XAITA-OT-V5-RELEASE-MANIFEST-1.0",
        "package": "xaita-ot",
        "version": version,
        "artifacts": records,
        "verification_boundary": [
            "artifact integrity and package metadata verified in CI",
            "not a production OT safety certification",
            "not an independent penetration test",
            "not customer-specific deployment acceptance",
        ],
    }
    MANIFEST.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(payload, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
