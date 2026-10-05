"""Governance policy validation and deployment-boundary checks."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

SCHEMA_VERSION = "XAITA-OT-GOVERNANCE-1.0"
ALLOWED_DATASET_STATUS = {"approved", "restricted", "prohibited", "review_required"}


def load_policy(path: str | Path) -> dict[str, Any]:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    return validate_policy(payload)


def validate_policy(policy: dict[str, Any]) -> dict[str, Any]:
    if policy.get("schema_version") != SCHEMA_VERSION:
        raise ValueError("unsupported governance schema")
    project = policy.get("project")
    datasets = policy.get("datasets")
    deployment = policy.get("deployment")
    if not isinstance(project, dict) or not isinstance(datasets, dict) or not isinstance(deployment, dict):
        raise ValueError("governance policy requires project, datasets and deployment objects")
    required_datasets = {"SWaT", "BATADAL", "TON-IoT"}
    if set(datasets) != required_datasets:
        raise ValueError("governance policy must define SWaT, BATADAL and TON-IoT")
    for name, item in datasets.items():
        if not isinstance(item, dict) or item.get("status") not in ALLOWED_DATASET_STATUS:
            raise ValueError(f"invalid governance status for {name}")
        if not item.get("license_control") or not item.get("source"):
            raise ValueError(f"dataset {name} is missing license/source controls")
    if deployment.get("autonomous_ot_control") != "prohibited":
        raise ValueError("autonomous OT control must remain prohibited")
    required = deployment.get("required_evidence")
    if not isinstance(required, list) or not required:
        raise ValueError("deployment required_evidence must be a non-empty list")
    return policy


def evaluate_deployment(policy: dict[str, Any], evidence: dict[str, bool]) -> dict[str, Any]:
    policy = validate_policy(policy)
    required = policy["deployment"]["required_evidence"]
    missing = [key for key in required if evidence.get(key) is not True]
    status = "approved" if not missing else "review_required"
    return {
        "schema_version": SCHEMA_VERSION,
        "status": status,
        "missing_evidence": missing,
        "autonomous_ot_control": policy["deployment"]["autonomous_ot_control"],
    }
