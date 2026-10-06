from datetime import datetime, timezone

import pytest

from xaita_ot.core.attribution import assess, validate_assessments
from xaita_ot.core.evidence import (
    EvidenceValidationError,
    validate_attribution_evidence,
    validate_evidence_groups,
)
from xaita_ot.core.schemas import AttributionAssessment


def _assessment():
    return assess(
        ["H1"],
        {"H1": {"sensor": 0.9, "network": 0.2, "operator": 0.5}},
        {"sensor": 0.8, "network": 0.7, "operator": 0.6},
    )[0]


def test_evidence_states_are_validated_and_disjoint():
    item = _assessment()
    assert validate_attribution_evidence(item)
    assert validate_evidence_groups({
        "supporting": item.supporting,
        "conflicting": item.conflicting,
        "unresolved": item.unresolved,
    })


@pytest.mark.parametrize("mutator", [
    lambda a: a.supporting[0].update(source="network"),
    lambda a: a.supporting[0].update(value=2.0),
    lambda a: a.supporting[0].update(reliability=-0.1),
])
def test_evidence_validation_rejects_tampering(mutator):
    item = _assessment()
    mutator(item)
    with pytest.raises(EvidenceValidationError):
        validate_attribution_evidence(item)


def test_evidence_validation_rejects_unknown_state():
    with pytest.raises(EvidenceValidationError):
        validate_evidence_groups({"supporting": [], "conflicting": [], "unresolved": [], "other": []})


def test_attribution_validator_and_evidence_validator_agree():
    item = _assessment()
    assert validate_assessments([item])
    assert validate_attribution_evidence(item)


def test_interval_is_not_treated_as_probability():
    item = AttributionAssessment(
        "H1",
        belief=0.4,
        plausibility=0.8,
        supporting=[{"source": "s", "value": 0.8, "reliability": 0.9}],
        conflicting=[],
        unresolved=[],
    )
    assert item.interval_width == 0.4
    assert validate_attribution_evidence(item)
