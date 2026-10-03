from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path

import yaml

PACKAGE_SCHEMA = "XAITA-OT-CTI-PACKAGE-1.0"
PINNED_FRAMEWORK_VERSION = "19.2"


def _root() -> Path:
    return Path(os.environ.get("XAITA_OT_ROOT", Path.cwd()))


def load_cti_package(path: str | Path | None = None) -> dict:
    package_path = Path(path) if path else _root() / "configs" / "cti_package.yaml"
    data = yaml.safe_load(package_path.read_text(encoding="utf-8")) or {}
    return validate_cti_package(data)


def validate_cti_package(package: dict) -> dict:
    if package.get("schema_version") != PACKAGE_SCHEMA:
        raise ValueError(f"Unsupported CTI package schema: {package.get('schema_version')!r}")
    if package.get("framework") != "MITRE ATT&CK for ICS":
        raise ValueError("CTI package framework must be MITRE ATT&CK for ICS")
    if str(package.get("framework_version")) != PINNED_FRAMEWORK_VERSION:
        raise ValueError(f"CTI package must pin MITRE ATT&CK version {PINNED_FRAMEWORK_VERSION}")
    if package.get("review_status") != "reviewed":
        raise ValueError("CTI package must be reviewed before use")
    mappings = package.get("mappings") or {}
    required = {"reconnaissance", "protocol", "unauthorized_command", "process_deviation"}
    if set(mappings) != required:
        raise ValueError("CTI package mapping keys do not match the reviewed contract")
    for key, item in mappings.items():
        if not item.get("technique_id") or not item.get("name") or not item.get("source_url"):
            raise ValueError(f"Incomplete ATT&CK mapping metadata for {key}")
    return package


def cti_package_digest(package: dict | None = None) -> str:
    package = validate_cti_package(package or load_cti_package())
    canonical = json.dumps(package, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def cti_package_metadata(package: dict | None = None) -> dict:
    package = validate_cti_package(package or load_cti_package())
    return {
        "package_id": package["package_id"],
        "schema_version": package["schema_version"],
        "framework": package["framework"],
        "framework_version": str(package["framework_version"]),
        "review_status": package["review_status"],
        "reviewed_on": package["reviewed_on"],
        "digest_sha256": cti_package_digest(package),
    }
