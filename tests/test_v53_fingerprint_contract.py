import pytest

from xaita_ot.explain.xai import (
    ExplanationValidationError,
    explanation_fingerprint,
)


def test_fingerprint_is_stable_for_unicode_json():
    value = {"schema_version": "XAITA-OT-XAI-1.1", "label": "é", "nested": {"b": 2, "a": 1}}
    assert explanation_fingerprint(value) == explanation_fingerprint(dict(value))


@pytest.mark.parametrize("bad", [
    {"value": object()},
    {"value": float("nan")},
    {"value": float("inf")},
    {"value": float("-inf")},
])
def test_fingerprint_rejects_non_json_native_values(bad):
    with pytest.raises(ExplanationValidationError):
        explanation_fingerprint(bad)


def test_fingerprint_requires_mapping():
    with pytest.raises(ExplanationValidationError):
        explanation_fingerprint(["not", "a", "mapping"])


def test_fingerprint_changes_when_explanation_changes():
    first = {"schema_version": "XAITA-OT-XAI-1.1", "score": 0.4}
    second = {"schema_version": "XAITA-OT-XAI-1.1", "score": 0.5}
    assert explanation_fingerprint(first) != explanation_fingerprint(second)
