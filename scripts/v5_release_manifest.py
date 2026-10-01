#!/usr/bin/env python3
"""Build a deterministic XAITA-OT V5 release handover manifest.

The manifest records release-facing repository files by SHA-256. It does not
claim that the repository has been externally deployed or independently
security-certified.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RELEASE_FILES = [
    "README.md",
    "CHANGELOG.md",
    "pyproject.toml",
    "Dockerfile",
    "docker-compose.yml",
    ".env.example",
    "docs/V5_ROADMAP.md",
    "docs/V5.1_RELEASE_GATE.md",
    "docs/V5_DAY8_DEPLOYMENT_INTEGRATION_LOCK.md",
    "docs/V5_DAY9_EVIDENCE_PROVENANCE_LOCK.md",
    "docs/V5_DAY10_ATTRIBUTION_QUALITY_LOCK.md",
    "docs/V5_DAY11_OPERATIONAL_ROBUSTNESS_LOCK.md",
    "docs/V5_DAY12_RELEASE_READINESS_LOCK.md",
    "scripts/v5_preflight.py",
    "scripts/v5_operational_check.py",
    "scripts/v5_e2e_smoke.py",
    "scripts/v5_release_check.py",
    "scripts/v5_release_manifest.py",
]


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def build_manifest() -> dict:
    missing = [path for path in RELEASE_FILES if not (ROOT / path).is_file()]
    if missing:
        raise FileNotFoundError("missing release files: " + ", ".join(missing))

    pyproject = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    version = next(
        (line.split("=", 1)[1].strip().strip('"') for line in pyproject.splitlines()
         if line.startswith("version = ")),
        None,
    )
    return {
        "schema_version": "XAITA-OT-V5-RELEASE-MANIFEST-1.0",
        "package": "xaita-ot",
        "version": version,
        "verification_boundary": (
            "Repository release-handover evidence only; no claim of external "
            "deployment, independent security certification, or customer OT acceptance."
        ),
        "files": [
            {"path": path, "sha256": sha256(ROOT / path)}
            for path in RELEASE_FILES
        ],
    }


def main() -> int:
    manifest = build_manifest()
    print(json.dumps(manifest, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
