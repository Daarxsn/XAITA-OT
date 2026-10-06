import pytest
from datetime import datetime, timezone

from xaita_ot.core.schemas import AttackEpisode, DetectionEvent
from xaita_ot.explain.xai import build_explanation, validate_explanation, ExplanationValidationError


def _episode():
    e = DetectionEvent("e1", datetime(2026, 1, 1, tzinfo=timezone.utc), "PLC1", "modbus", "attack", 0.9)
    return AttackEpisode("ep1", [e], 0.8)


def _risk():
    return {"score": 0.5, "factors": {"severity": 0.9}}


def _attribution():
    return {
        "hypothesis": "H1", "belief": 0.4, "plausibility": 0.8,
        "interval_width": 0.4, "interpretation": "substantial uncertainty",
        "alternatives": [{"hypothesis": "H2", "belief": 0.2, "plausibility": 0.7}],
    }


def test_explanation_preserves_attribution_and_dc_semantics():
    ep = _episode()
    context = []
    explanation = build_explanation(
        ep.events[0], ep, context, _risk(), [{"feature": "pressure", "importance": 1.0}],
        attribution=_attribution(), detection_confidence=0.9,
    )
    assert validate_explanation(explanation, ep, context, _risk())
    assert explanation["confidence_semantics"]["detection_confidence"] == 0.9
    assert explanation["confidence_semantics"]["attribution_is_evidence_interval"] is True
    assert explanation["confidence_semantics"]["attribution_is_not_calibrated_probability"] is True


@pytest.mark.parametrize("mutation", [
    lambda x: x["confidence_semantics"].update(attribution_is_evidence_interval=False),
    lambda x: x["confidence_semantics"].update(attribution_is_not_calibrated_probability=False),
    lambda x: x["attribution_level"].update(interval_width=0.2),
])
def test_explanation_rejects_confidence_semantic_tampering(mutation):
    ep = _episode()
    explanation = build_explanation(
        ep.events[0], ep, [], _risk(), [{"feature": "pressure", "importance": 1.0}],
        attribution=_attribution(), detection_confidence=0.9,
    )
    mutation(explanation)
    with pytest.raises(ExplanationValidationError):
        validate_explanation(explanation, ep, [], _risk())
