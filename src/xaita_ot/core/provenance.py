"""Deterministic provenance and evidence-lineage utilities for XAITA-OT V5.2."""

from __future__ import annotations

from datetime import datetime
import hashlib
import json
from typing import Any


class ProvenanceValidationError(ValueError):
    """Raised when an evidence/provenance contract is internally inconsistent."""


def canonical_json(value: Any) -> str:
    """Serialize JSON deterministically for hashing and reproducible artifacts."""
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        default=_json_default,
    )


def _json_default(value: Any) -> str:
    if isinstance(value, datetime):
        return value.isoformat()
    raise TypeError(f"Object of type {type(value).__name__} is not JSON serializable")


def provenance_digest(manifest: list[dict[str, Any]]) -> str:
    """Return a stable SHA-256 digest for an ordered provenance manifest."""
    validate_provenance(manifest)
    return hashlib.sha256(canonical_json(manifest).encode("utf-8")).hexdigest()


def _require_text(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ProvenanceValidationError(f"{field} must be a non-empty string")
    return value.strip()


def validate_provenance_item(item: dict[str, Any]) -> None:
    """Validate the complete shape of one provenance lineage item."""
    if not isinstance(item, dict):
        raise ProvenanceValidationError("provenance items must be mappings")
    required = ("evidence_id", "observation_id", "detection_id", "episode_id", "event_id")
    for field in required:
        _require_text(item.get(field), field)
    refs = item.get("context_refs", [])
    if not isinstance(refs, list):
        raise ProvenanceValidationError("context_refs must be a list")
    for ref in refs:
        _require_text(ref, "context_refs entry")


def build_provenance_manifest(episode, context) -> list[dict[str, Any]]:
    """Build an explicit observation → detection → episode → context lineage."""
    episode_id = episode.episode_id
    context_by_event: dict[str, list[dict[str, Any]]] = {}
    for item in context:
        event_id = item.get("event_id")
        if event_id:
            context_by_event.setdefault(str(event_id), []).append(item)

    manifest: list[dict[str, Any]] = []
    for event in episode.events:
        event_id = str(event.event_id)
        observation_id = event.observation_id or event_id
        manifest.append(
            {
                "evidence_id": event_id,
                "observation_id": observation_id,
                "detection_id": event_id,
                "episode_id": episode_id,
                "event_id": event_id,
                "context_refs": [
                    str(item["technique_id"])
                    for item in context_by_event.get(event_id, [])
                    if item.get("technique_id")
                ],
            }
        )
    return manifest


def validate_provenance(
    manifest: list[dict[str, Any]],
    *,
    episode_id: str | None = None,
    event_ids: list[str] | None = None,
    context: list[dict[str, Any]] | None = None,
) -> None:
    """Validate lineage identifiers, uniqueness and backward references."""
    if not isinstance(manifest, list):
        raise ProvenanceValidationError("provenance manifest must be a list")

    evidence_ids = [item.get("evidence_id") for item in manifest]
    if any(not isinstance(value, str) or not value for value in evidence_ids):
        raise ProvenanceValidationError("every provenance item requires a non-empty evidence_id")
    if len(evidence_ids) != len(set(evidence_ids)):
        raise ProvenanceValidationError("evidence_id values must be unique")

    expected = [str(value) for value in event_ids] if event_ids is not None else None
    actual = [str(item.get("event_id")) for item in manifest]
    if expected is not None and actual != expected:
        raise ProvenanceValidationError("provenance event order does not match episode event order")

    for item in manifest:
        validate_provenance_item(item)
        if not item.get("observation_id") or not item.get("detection_id") or not item.get("episode_id"):
            raise ProvenanceValidationError("provenance items require observation, detection and episode references")
        if episode_id is not None and item["episode_id"] != episode_id:
            raise ProvenanceValidationError("provenance item references the wrong episode")
        if item["detection_id"] != item["event_id"]:
            raise ProvenanceValidationError("detection_id must point backward to the event evidence")

    if context is not None:
        known = {
            str(item.get("technique_id"))
            for item in context
            if item.get("technique_id")
        }
        for item in manifest:
            unknown = set(item.get("context_refs", [])) - known
            if unknown:
                raise ProvenanceValidationError(
                    f"provenance references unknown context evidence: {sorted(unknown)}"
                )


def validate_cti_provenance(cti: dict[str, Any]) -> None:
    """Validate the evidence lineage embedded in a generated CTI product."""
    behavior = cti.get("behavior") or {}
    event_ids = [str(value) for value in behavior.get("event_ids", [])]
    manifest = cti.get("provenance_manifest")
    if not isinstance(manifest, list):
        raise ProvenanceValidationError("CTI product is missing provenance_manifest")

    validate_provenance(
        manifest,
        episode_id=behavior.get("episode_id"),
        event_ids=event_ids,
        context=cti.get("context") or [],
    )

    digest = cti.get("provenance_digest")
    if not isinstance(digest, str) or digest != provenance_digest(manifest):
        raise ProvenanceValidationError("provenance_digest does not match provenance_manifest")

    linked = cti.get("provenance_links") or {}
    if [str(x) for x in linked.get("detections", [])] != event_ids:
        raise ProvenanceValidationError("provenance detection links do not match behavior event_ids")
    if linked.get("episodes", []) != [behavior.get("episode_id")]:
        raise ProvenanceValidationError("provenance episode link is inconsistent")
