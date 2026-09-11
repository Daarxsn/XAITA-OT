from pathlib import Path

import numpy as np

from xaita_ot.config import AppConfig
from xaita_ot.pipeline.v3_phase4 import VARIANTS, run_phase4

ROOT = Path(__file__).resolve().parents[1]


def _paths():
    return {
        "SWaT": str(ROOT / "data/demo/swat_like.csv"),
        "BATADAL": str(ROOT / "data/demo/batadal_like.csv"),
        "TON-IoT": str(ROOT / "data/demo/toniot_like.csv"),
    }


def test_phase4_contains_exact_six_variants():
    assert list(VARIANTS) == ["Full XAITA-OT", "-BTAE", "-BSS", "-ATT&CK", "-ACFM", "Detection-only"]


def test_phase4_executes_all_variants_and_effects():
    cfg = AppConfig()
    cfg.model.window_size = 4
    result = run_phase4(_paths(), cfg, seeds=[42])
    assert result["status"] == "PASS"
    assert result["variants"] == list(VARIANTS)
    assert result["row_count"] == 18
    assert len(result["runs"]) == 3
    for run in result["runs"]:
        assert set(run["variants"]) == set(VARIANTS)
        for metrics in run["variants"].values():
            for key in ("precision", "recall", "f1", "fpr"):
                assert 0.0 <= metrics[key] <= 1.0
            assert np.isfinite(metrics["auroc"]) or np.isnan(metrics["auroc"])
    assert set(result["effects_vs_full"]) == set(VARIANTS) - {"Full XAITA-OT"}
    for effects in result["effects_vs_full"].values():
        assert {x["metric"] for x in effects} == {"f1", "precision", "recall", "fpr", "auroc"}
