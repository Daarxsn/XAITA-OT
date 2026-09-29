from xaita_ot.core.attribution import AttributionValidationError, assess, validate_assessments


def _evidence():
    return {
        "H1": {"DC": 0.92, "BSS": 0.55, "ECS": 0.20},
        "H2": {"DC": 0.70, "BSS": 0.80, "ECS": 0.55},
    }


def _reliability():
    return {"DC": 0.70, "BSS": 0.80, "ECS": 0.85}


def test_competing_hypotheses_are_deterministic():
    a = assess(["H2", "H1"], _evidence(), _reliability())
    b = assess(["H1", "H2"], _evidence(), _reliability())
    assert [x.hypothesis for x in a] == [x.hypothesis for x in b]
    assert [(x.belief, x.plausibility) for x in a] == [(x.belief, x.plausibility) for x in b]
    assert validate_assessments(a) is True


def test_unresolved_evidence_preserves_interval_semantics():
    out = assess(["H1"], {"H1": {"DC": 0.92, "ECS": 0.55}}, _reliability())
    assert out[0].unresolved
    assert 0 <= out[0].belief <= out[0].plausibility <= 1
    assert out[0].interval_width > 0


def test_source_cannot_be_multiple_evidence_states():
    out = assess(["H1"], {"H1": {"DC": 0.92}}, _reliability())
    out[0].conflicting.append({"source": "DC", "value": 0.1, "reliability": 0.7})
    try:
        validate_assessments(out)
    except AttributionValidationError:
        return
    raise AssertionError("expected duplicate evidence state to be rejected")


def test_duplicate_hypotheses_are_rejected():
    try:
        assess(["H1", "H1"], _evidence(), _reliability())
    except AttributionValidationError:
        return
    raise AssertionError("expected duplicate hypothesis to be rejected")
