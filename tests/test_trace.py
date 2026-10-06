import pytest

from xaita_ot.core.trace import build_analyst_trace, validate_analyst_trace
from xaita_ot.core.provenance import ProvenanceValidationError


def _manifest():
    return [{
        "evidence_id": "e1",
        "observation_id": "o1",
        "detection_id": "e1",
        "episode_id": "ep1",
        "event_id": "e1",
        "context_refs": ["T0814"],
        "secret": "must-not-leak",
        "raw_payload": {"token": "hidden"},
    }]


def test_analyst_trace_is_sanitized_and_deterministic():
    trace = build_analyst_trace(_manifest(), episode_id="ep1", event_ids=["e1"])
    assert trace == [{
        "evidence_id": "e1",
        "observation_id": "o1",
        "detection_id": "e1",
        "episode_id": "ep1",
        "event_id": "e1",
        "context_refs": ["T0814"],
    }]
    assert "secret" not in trace[0]
    assert "raw_payload" not in trace[0]
    assert validate_analyst_trace(trace, manifest=_manifest())


def test_trace_preserves_event_order():
    manifest = [
        dict(_manifest()[0]),
        {
            "evidence_id": "e2", "observation_id": "o2", "detection_id": "e2",
            "episode_id": "ep1", "event_id": "e2", "context_refs": [],
        },
    ]
    trace = build_analyst_trace(manifest, episode_id="ep1", event_ids=["e1", "e2"])
    assert [item["event_id"] for item in trace] == ["e1", "e2"]


def test_trace_rejects_tampering():
    trace = build_analyst_trace(_manifest(), episode_id="ep1", event_ids=["e1"])
    trace[0]["context_refs"] = ["T9999"]
    with pytest.raises(ValueError):
        validate_analyst_trace(trace, manifest=_manifest())


def test_trace_rejects_invalid_manifest():
    bad = dict(_manifest()[0])
    bad["event_id"] = ""
    with pytest.raises(ProvenanceValidationError):
        build_analyst_trace([bad])
