from xaita_ot.core.attribution import assess


def test_unresolved_evidence_creates_interval():
    out = assess(
        ["H1"],
        {"H1": {"DC": 0.92, "BSS": 0.88, "ECS": 0.55, "EC": 0.90, "MAS": 0.85}},
        {"DC": 0.70, "BSS": 0.80, "ECS": 0.85, "EC": 0.80, "MAS": 0.65},
    )
    assert out[0].unresolved
    assert out[0].belief < out[0].plausibility
    assert out[0].interval_width > 0


def test_conflicting_evidence_reduces_plausibility():
    out = assess(
        ["H1"],
        {"H1": {"DC": 0.90, "BSS": 0.20, "ECS": 0.55, "EC": 0.80, "MAS": 0.60}},
        {"DC": 0.70, "BSS": 0.80, "ECS": 0.85, "EC": 0.80, "MAS": 0.65},
    )
    assert out[0].conflicting
    assert out[0].plausibility < 1
