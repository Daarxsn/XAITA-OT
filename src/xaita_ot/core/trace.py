"""Sanitized analyst-facing provenance trace utilities for XAITA-OT V5.2."""

from __future__ import annotations

from typing import Any

from .provenance import validate_provenance


TRACE_FIELDS = (
    "evidence_id",
    "observation_id",
    "detection_id",
    "episode_id",
    "event_id",
    "context_refs",
)


def build_analyst_trace(
    manifest: list[dict[str, Any]],
    *,
    episode_id: str | None = None,
    event_ids: list[str] | None = None,
    context: list[dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    """Build a deterministic, sanitized lineage view for analysts.

    Only validated provenance identifiers and context references are emitted.
    Arbitrary fields from the source manifest are intentionally excluded.
    """
    validate_provenance(
        manifest,
        episode_id=episode_id,
        event_ids=event_ids,
        context=context,
    )
    return [
        {
            "evidence_id": item["evidence_id"],
            "observation_id": item["observation_id"],
            "detection_id": item["detection_id"],
            "episode_id": item["episode_id"],
            "event_id": item["event_id"],
            "context_refs": list(item.get("context_refs", [])),
        }
        for item in manifest
    ]


def validate_analyst_trace(
    trace: list[dict[str, Any]],
    *,
    manifest: list[dict[str, Any]],
) -> bool:
    """Confirm that a trace is an exact sanitized projection of a manifest."""
    if not isinstance(trace, list):
        raise ValueError("analyst trace must be a list")
    expected = build_analyst_trace(manifest)
    if trace != expected:
        raise ValueError("analyst trace does not match validated provenance")
    if any(set(item) != set(TRACE_FIELDS) for item in trace):
        raise ValueError("analyst trace contains unexpected or missing fields")
    return True
