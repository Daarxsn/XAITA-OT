from pathlib import Path

import numpy as np
import pandas as pd

from xaita_ot.config import AppConfig
from xaita_ot.pipeline.v3_phase4 import run_phase4
from xaita_ot.pipeline.v3_phase6 import METRICS, evaluate_ablation_statistics, mean_std_ci, run_phase6_from_phase4

ROOT = Path(__file__).resolve().parents[1]


def _paths():
    return {"SWaT": str(ROOT / "data/demo/swat_like.csv"), "BATADAL": str(ROOT / "data/demo/batadal_like.csv"), "TON-IoT": str(ROOT / "data/demo/toniot_like.csv")}


def test_mean_std_and_ci_requires_repeated_observations():
    out = mean_std_ci([0.8, 0.7, 0.9, 0.8, 0.75])
    assert out["n"] == 5
    assert out["std"] > 0
    assert out["ci_low"] < out["mean"] < out["ci_high"]


def test_phase6_rejects_single_seed():
    cfg = AppConfig(); cfg.model.window_size = 4
    try:
        run_phase6_from_phase4(run_phase4, _paths(), cfg, seeds=[42])
    except ValueError as exc:
        assert "at least two seeds" in str(exc)
    else:
        raise AssertionError("Phase 6 must require repeated seeds")


def test_phase6_executes_multiple_seeds_and_statistical_comparison():
    cfg = AppConfig(); cfg.model.window_size = 4
    result = run_phase6_from_phase4(run_phase4, _paths(), cfg, seeds=[42, 43, 44])
    assert result["status"] == "PASS"
    assert result["statistics"]["repeat_count"] == 3
    assert result["statistics"]["observations"] == 54
    assert len(result["statistics"]["summary"]) == 30
    assert len(result["statistics"]["dataset_summary"]) == 90
    assert len(result["statistics"]["paired_effects"]) == 25
    assert all(row["n"] == 9 for row in result["statistics"]["summary"])
    assert all(row["metric"] in METRICS for row in result["statistics"]["summary"])
