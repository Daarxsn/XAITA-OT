import pytest

from xaita_ot.core.provenance import (
    ProvenanceValidationError,
    canonical_json,
    provenance_digest,
    validate_provenance,
    validate_provenance_item,
)


def _manifest():
    return [{
        "evidence_id": "e1",
        "observation_id": "o1",
        "detection_id": "e1",
        "episode_id": "ep1",
        "event_id": "e1",
        "context_refs": ["T0814"],
    }]


def test_provenance_item_shape_is_explicit():
    assert validate_provenance_item(_manifest()[0]) is None
    assert provenance_digest(_manifest()) == provenance_digest(list(_manifest()))


@pytest.mark.parametrize("field", [
    "evidence_id", "observation_id", "detection_id", "episode_id", "event_id"
])
def test_provenance_rejects_missing_required_identity(field):
    item = _manifest()[0]
    item[field] = ""
    with pytest.raises(ProvenanceValidationError):
        validate_provenance([item])


def test_provenance_rejects_invalid_context_refs():
    item = _manifest()[0]
    item["context_refs"] = "T0814"
    with pytest.raises(ProvenanceValidationError):
        validate_provenance([item])


def test_digest_rejects_invalid_manifest():
    with pytest.raises(ProvenanceValidationError):
        provenance_digest([{"evidence_id": "e1"}])


def test_canonical_serialization_preserves_unicode_and_ordered_lists():
    value = {"z": ["é", "β"], "a": {"n": 2, "m": 1}}
    assert canonical_json(value) == '{"a":{"m":1,"n":2},"z":["é","β"]}'
