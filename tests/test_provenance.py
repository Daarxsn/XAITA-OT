from datetime import datetime, timezone

import pytest

from xaita_ot.core.provenance import (
    ProvenanceValidationError,
    build_provenance_manifest,
    canonical_json,
    provenance_digest,
    validate_provenance,
    validate_cti_provenance,
)
from xaita_ot.core.schemas import AttackEpisode, DetectionEvent
from xaita_ot.cti.generator import generate_cti


def _episode():
    t = datetime(2026, 1, 1, tzinfo=timezone.utc)
    events = [
        DetectionEvent("e1", t, "PLC1", "modbus", "attack", 0.9, observation_id="obs-1"),
        DetectionEvent("e2", t, "PLC1", "modbus", "attack", 0.8, observation_id="obs-2"),
    ]
    return AttackEpisode(
        "ep-1",
        events,
        0.85,
        stages=["initial_access"],
        correlation_edges=[{"from": "e1", "to": "e2"}],
    )


def _context():
    return [
        {"event_id": "e1", "technique_id": "T0814", "name": "Denial of Service"},
        {"event_id": "e2", "technique_id": "T0814", "name": "Denial of Service"},
    ]


def test_provenance_manifest_is_complete_and_deterministic():
    episode = _episode()
    manifest = build_provenance_manifest(episode, _context())
    validate_provenance(manifest, episode_id="ep-1", event_ids=["e1", "e2"], context=_context())

    assert manifest[0]["observation_id"] == "obs-1"
    assert manifest[1]["detection_id"] == "e2"
    assert provenance_digest(manifest) == provenance_digest(list(manifest))
    assert canonical_json({"b": 2, "a": 1}) == '{"a":1,"b":2}'


def test_provenance_rejects_unknown_context_and_wrong_episode():
    manifest = build_provenance_manifest(_episode(), _context())
    with pytest.raises(ProvenanceValidationError):
        validate_provenance(manifest, episode_id="wrong")
    bad = [dict(item) for item in manifest]
    bad[0]["context_refs"] = ["UNKNOWN"]
    with pytest.raises(ProvenanceValidationError):
        validate_provenance(bad, episode_id="ep-1", event_ids=["e1", "e2"], context=_context())


def test_generated_cti_contains_verifiable_provenance():
    cti = generate_cti(
        "inc-1",
        {"event_ids": ["e1", "e2"]},
        _episode(),
        _context(),
        {"hypothesis": "H1"},
        {"summary": "test"},
        {"risk_score": 0.5},
    )
    validate_cti_provenance(cti)
    assert cti["provenance_digest"] == provenance_digest(cti["provenance_manifest"])


def test_provenance_rejects_duplicate_evidence_ids():
    manifest = build_provenance_manifest(_episode(), _context())
    manifest[1]["evidence_id"] = manifest[0]["evidence_id"]
    with pytest.raises(ProvenanceValidationError):
        validate_provenance(manifest)
