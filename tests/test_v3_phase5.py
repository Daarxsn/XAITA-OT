from pathlib import Path

from xaita_ot.config import AppConfig
from xaita_ot.pipeline.v3_phase5 import PARAMETER_VALUES, run_phase5

ROOT = Path(__file__).resolve().parents[1]


def _paths():
    return {
        "SWaT": str(ROOT / "data/demo/swat_like.csv"),
        "BATADAL": str(ROOT / "data/demo/batadal_like.csv"),
        "TON-IoT": str(ROOT / "data/demo/toniot_like.csv"),
    }


def test_phase5_has_exact_five_parameters_and_three_values_each():
    assert list(PARAMETER_VALUES) == ["correlation_threshold", "temporal_window", "bss_weighting", "evidence_reliability", "attribution_threshold"]
    assert all(len(values) == 3 for values in PARAMETER_VALUES.values())


def test_phase5_executes_full_sensitivity_matrix():
    cfg = AppConfig(); cfg.model.window_size = 4
    result = run_phase5(_paths(), cfg, seeds=[42])
    assert result["status"] == "PASS"
    assert result["run_count"] == 45
    assert len(result["summary"]) == 15
    assert set(result["parameters"]) == set(PARAMETER_VALUES)
    for row in result["rows"]:
        assert 0.0 <= row["precision"] <= 1.0
        assert 0.0 <= row["recall"] <= 1.0
        assert 0.0 <= row["f1"] <= 1.0
        assert 0.0 <= row["fpr"] <= 1.0

 

def test_parameter_score_tracks_attack_hypothesis_not_highest_sorted_hypothesis():
    import numpy as np
    from xaita_ot.pipeline.v3_phase5 import _parameter_score

    evidence = {
        "BSS": np.array([0.0]),
        "ECS": np.array([0.0]),
        "MAS": np.array([0.0]),
        "EC": np.array([0.0]),
        "temporal": np.array([0.0]),
    }
    probabilities, belief, plausibility, width = _parameter_score(
        np.array([0.0]), evidence, "attribution_threshold", 0.60, np.array([0.0])
    )
    # All inputs oppose the attack hypothesis. The benign assessment has higher
    # belief and sorts first, but its score must never be reused as attack score.
    assert probabilities[0] == 0.0
    assert belief == 0.0
    assert plausibility == 0.0
    assert width == 0.0
