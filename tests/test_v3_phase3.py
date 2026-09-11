from pathlib import Path

import numpy as np

from xaita_ot.config import AppConfig
from xaita_ot.pipeline.v3_phase3 import confidence_bins, reliability_summary, run_phase3

ROOT = Path(__file__).resolve().parents[1]


def _paths():
    return {
        "SWaT": str(ROOT / "data/demo/swat_like.csv"),
        "BATADAL": str(ROOT / "data/demo/batadal_like.csv"),
        "TON-IoT": str(ROOT / "data/demo/toniot_like.csv"),
    }


def test_confidence_bins_cover_all_samples():
    y = np.array([0, 0, 1, 1, 1, 0])
    p = np.array([.05, .15, .55, .65, .85, .95])
    rows = confidence_bins(y, p, bins=10)
    assert len(rows) == 10
    assert sum(r["count"] for r in rows) == len(y)
    assert all(r["gap"] is None or 0.0 <= r["gap"] <= 1.0 for r in rows)


def test_reliability_summary_reports_ece_and_brier():
    y = np.array([0, 0, 1, 1])
    p = np.array([.1, .2, .8, .9])
    summary = reliability_summary(y, p, bins=4)
    assert 0.0 <= summary["ece"] <= 1.0
    assert 0.0 <= summary["brier"] <= 1.0
    assert len(summary["bins"]) == 4


def test_phase3_runs_all_datasets_and_compares_wef_acfm():
    cfg = AppConfig()
    cfg.model.window_size = 4
    result = run_phase3(_paths(), cfg, seeds=[42], bins=5)
    assert result["status"] == "PASS"
    assert result["datasets"] == ["SWaT", "BATADAL", "TON-IoT"]
    assert len(result["runs"]) == 3
    assert set(result["ece_summary"]) == {"detector", "WEF", "ACFM"}
    for run in result["runs"]:
        assert "ece" in run["detector"]
        assert "brier" in run["detector"]
        assert "ece" in run["fusion"]["WEF"]
        assert "brier" in run["fusion"]["WEF"]
        assert "ece" in run["fusion"]["ACFM"]
        assert "brier" in run["fusion"]["ACFM"]
        assert run["fusion"]["acfm_point_estimate"].startswith("midpoint")
