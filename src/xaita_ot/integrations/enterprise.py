"""Stable enterprise interoperability contracts.

The contracts are dependency-light JSON envelopes. They are intended as
interoperability boundaries, not vendor-specific certification claims.
"""

from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ..cti.stix import to_stix_bundle

SIEM_EVENT_SCHEMA = "XAITA-OT-SIEM-EVENT-1.0"
CTI_EXPORT_SCHEMA = "XAITA-OT-CTI-EXPORT-1.0"
AUDIT_EVENT_SCHEMA = "XAITA-OT-AUDIT-EVENT-1.0"


def _canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False)


def _sha256(value: Any) -> str:
    return hashlib.sha256(_canonical(value).encode("utf-8")).hexdigest()


def _is_sha256(value: Any) -> bool:
    return isinstance(value, str) and re.fullmatch(r"[0-9a-f]{64}", value) is not None


def _aware_timestamp(value: Any, field: str = "timestamp") -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field} must be a non-empty timezone-aware ISO-8601 string")
    try:
        parsed = datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError(f"{field} must be a valid timezone-aware ISO-8601 string") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError(f"{field} must include a timezone offset")
    return parsed.isoformat().replace("+00:00", "Z")


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _require(mapping: dict[str, Any], keys: tuple[str, ...], label: str) -> None:
    missing = [key for key in keys if key not in mapping]
    if missing:
        raise ValueError(f"{label} missing required fields: {', '.join(missing)}")


def build_siem_event(cti: dict[str, Any], *, source: str = "xaita-ot") -> dict[str, Any]:
    """Build a vendor-neutral SIEM event while preserving DC/AC separation."""
    _require(cti, ("schema_version", "incident_id", "detection", "behavior", "attribution", "risk"), "CTI")
    if cti["schema_version"] != "XAITA-OT-CTI-1.0":
        raise ValueError("SIEM export requires XAITA-OT-CTI-1.0 input")

    attribution = cti["attribution"]
    risk = cti["risk"]
    detection = cti["detection"]
    behavior = cti["behavior"]
    techniques = [
        {"id": item["technique_id"], "name": item.get("name", "")}
        for item in cti.get("context", [])
        if item.get("technique_id")
    ]
    core = {
        "schema_version": SIEM_EVENT_SCHEMA,
        "source": source,
        "occurred_at": cti.get("generated_at") or _utc_now(),
        "event": {
            "kind": "alert",
            "category": ["intrusion_detection"],
            "type": ["info"],
            "action": "xaita_ot_threat_assessment",
            "outcome": "review_required",
        },
        "service": {"name": "xaita-ot"},
        "xaita_ot": {
            "incident_id": cti["incident_id"],
            "episode_id": behavior.get("episode_id"),
            "risk": {
                "score": risk.get("score"),
                "level": risk.get("level"),
            },
            "detection": {
                "confidence": detection.get("mean_detection_confidence"),
                "event_ids": list(detection.get("event_ids", [])),
            },
            "attribution": {
                "hypothesis": attribution.get("hypothesis"),
                "belief": attribution.get("belief"),
                "plausibility": attribution.get("plausibility"),
            },
            "evidence": {
                "event_ids": list(behavior.get("event_ids", [])),
                "provenance_digest": cti.get("provenance_digest"),
            },
        },
        "threat": {"techniques": techniques},
        "human_validation_required": bool(cti.get("human_validation_required", True)),
        "autonomous_ot_action": bool(cti.get("autonomous_ot_action", False)),
    }
    event_id = _sha256(core)
    return {**core, "event_id": event_id}


def validate_siem_event(event: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(event, dict):
        raise ValueError("SIEM event must be a mapping")
    _require(event, ("schema_version", "event_id", "occurred_at", "event", "xaita_ot"), "SIEM event")
    if event["schema_version"] != SIEM_EVENT_SCHEMA:
        raise ValueError("Unsupported SIEM event schema")
    _require(event["event"], ("kind", "category", "type", "action", "outcome"), "SIEM event.event")
    xaita = event["xaita_ot"]
    _require(xaita, ("incident_id", "detection", "attribution", "evidence", "risk"), "SIEM event.xaita_ot")
    if "confidence" not in xaita["detection"]:
        raise ValueError("SIEM event must preserve detection confidence")
    if not {"belief", "plausibility"} <= set(xaita["attribution"]):
        raise ValueError("SIEM event must preserve attribution belief and plausibility")
    if not _is_sha256(event["event_id"]):
        raise ValueError("SIEM event ID must be a lowercase SHA-256 digest")
    core = {key: value for key, value in event.items() if key != "event_id"}
    if _sha256(core) != event["event_id"]:
        raise ValueError("SIEM event ID does not match event content")
    return event


def build_cti_export(cti: dict[str, Any]) -> dict[str, Any]:
    """Wrap the existing STIX 2.1 export in a versioned handover contract."""
    _require(cti, ("schema_version", "incident_id"), "CTI")
    if cti["schema_version"] != "XAITA-OT-CTI-1.0":
        raise ValueError("CTI export requires XAITA-OT-CTI-1.0 input")
    source_sha256 = hashlib.sha256(_canonical(cti).encode("utf-8")).hexdigest()
    bundle = to_stix_bundle(cti)
    export = {
        "schema_version": CTI_EXPORT_SCHEMA,
        "format": "STIX-2.1",
        "producer": "xaita-ot",
        "incident_id": cti["incident_id"],
        "source_cti_sha256": source_sha256,
        "bundle": bundle,
        "human_validation_required": bool(cti.get("human_validation_required", True)),
        "autonomous_ot_action": bool(cti.get("autonomous_ot_action", False)),
    }
    export["export_sha256"] = _sha256(export)
    return export


def validate_cti_export(export: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(export, dict):
        raise ValueError("CTI export must be a mapping")
    _require(export, ("schema_version", "format", "producer", "incident_id", "source_cti_sha256", "bundle", "export_sha256"), "CTI export")
    if export["schema_version"] != CTI_EXPORT_SCHEMA:
        raise ValueError("Unsupported CTI export schema")
    if export["format"] != "STIX-2.1":
        raise ValueError("CTI export format must be STIX-2.1")
    bundle = export["bundle"]
    if not isinstance(bundle, dict) or bundle.get("type") != "bundle" or not isinstance(bundle.get("objects"), list):
        raise ValueError("CTI export must contain a valid STIX bundle envelope")
    if not _is_sha256(export["source_cti_sha256"]) or not _is_sha256(export["export_sha256"]):
        raise ValueError("CTI export digests must be lowercase SHA-256 hex strings")
    core = {key: value for key, value in export.items() if key != "export_sha256"}
    if _sha256(core) != export["export_sha256"]:
        raise ValueError("CTI export digest does not match export content")
    return export


def build_audit_event(
    *,
    action: str,
    actor: str,
    outcome: str,
    correlation_id: str,
    incident_id: str | None = None,
    timestamp: str | None = None,
    details: dict[str, Any] | None = None,
) -> dict[str, Any]:
    if not action.strip() or not actor.strip() or not outcome.strip() or not correlation_id.strip():
        raise ValueError("Audit action, actor, outcome and correlation_id are required")
    effective_timestamp = _utc_now() if timestamp is None else _aware_timestamp(timestamp)
    core = {
        "schema_version": AUDIT_EVENT_SCHEMA,
        "timestamp": effective_timestamp,
        "actor": actor,
        "action": action,
        "outcome": outcome,
        "correlation_id": correlation_id,
        "incident_id": incident_id,
        "details": details or {},
    }
    event = {**core, "event_id": _sha256(core)}
    return event


def validate_audit_event(event: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(event, dict):
        raise ValueError("Audit event must be a mapping")
    _require(event, ("schema_version", "timestamp", "actor", "action", "outcome", "correlation_id", "event_id"), "Audit event")
    if event["schema_version"] != AUDIT_EVENT_SCHEMA:
        raise ValueError("Unsupported audit event schema")
    if not all(isinstance(event[key], str) and event[key].strip() for key in ("actor", "action", "outcome", "correlation_id", "event_id")):
        raise ValueError("Audit event identity fields must be non-empty strings")
    _aware_timestamp(event["timestamp"])
    if not _is_sha256(event["event_id"]):
        raise ValueError("Audit event ID must be a lowercase SHA-256 digest")
    core = {key: value for key, value in event.items() if key != "event_id"}
    if _sha256(core) != event["event_id"]:
        raise ValueError("Audit event ID does not match event content")
    return event


def write_json(payload: dict[str, Any], path: str | Path) -> Path:
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    return destination
