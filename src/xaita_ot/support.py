"""Validation helpers for the XAITA-OT support and vulnerability-disclosure policy."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

SCHEMA_VERSION = "XAITA-OT-SUPPORT-1.0"
SEVERITIES = ("critical", "high", "medium", "low")


def load_support_policy(path: str | Path) -> dict[str, Any]:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    return validate_support_policy(payload)


def validate_support_policy(policy: dict[str, Any]) -> dict[str, Any]:
    if policy.get("schema_version") != SCHEMA_VERSION:
        raise ValueError("unsupported support policy schema")
    support = policy.get("support")
    severity = policy.get("severity")
    disclosure = policy.get("vulnerability_disclosure")
    boundary = policy.get("deployment_boundary")
    if not all(isinstance(item, dict) for item in (support, severity, disclosure, boundary)):
        raise ValueError("support policy requires support, severity, vulnerability_disclosure and deployment_boundary")
    if set(severity) != set(SEVERITIES):
        raise ValueError("support policy must define all four severity levels")
    for level in SEVERITIES:
        item = severity[level]
        if not item.get("definition") or not item.get("acknowledgement_target") or not item.get("triage_target"):
            raise ValueError(f"severity {level} is incomplete")
    if disclosure.get("public_issue_for_sensitive_vulnerability") is not False:
        raise ValueError("sensitive vulnerabilities must not be directed to public issues")
    if disclosure.get("coordinated_disclosure") is not True:
        raise ValueError("coordinated disclosure must be enabled")
    if boundary.get("autonomous_ot_control") != "prohibited":
        raise ValueError("autonomous OT control must remain prohibited")
    return policy


def classify_support_request(policy: dict[str, Any], severity: str) -> dict[str, Any]:
    policy = validate_support_policy(policy)
    if severity not in SEVERITIES:
        raise ValueError(f"unsupported severity: {severity}")
    level = policy["severity"][severity]
    return {
        "schema_version": SCHEMA_VERSION,
        "severity": severity,
        "acknowledgement_target": level["acknowledgement_target"],
        "triage_target": level["triage_target"],
        "channel": policy["support"]["channel"],
        "public_issue_for_sensitive_vulnerability": policy["vulnerability_disclosure"]["public_issue_for_sensitive_vulnerability"],
    }
