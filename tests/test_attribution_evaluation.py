from pathlib import Path
import json

import numpy as np
import pytest

from xaita_ot.config import AppConfig
from xaita_ot.pipeline.attribution_evaluation import (
    PHASE4_CONFIGURATIONS,
    run_phase4_attribution,
    write_phase4_attribution_artifacts,
)


ROOT = Path(__file__).resolve().parents[1]


def _demo_paths():
    return {
        "SWaT": ROOT / "data" / "demo" / "swat_like.csv",
        "BATADAL": ROOT / "data" / "demo" / "batadal_like.csv",
        "TON-IoT": ROOT / "data" / "demo" / "toniot_like.csv",
    }


def test_phase4_attribution_has_agreed_c1_to_c6_order():
    assert list(PHASE4_CONFIGURATIONS) == ["C1", "C2", "C3", "C4", "C5", "C6"]
    assert PHASE4_CONFIGURATIONS["C1"]["method"] == "DC"
    assert PHASE4_CONFIGURATIONS["C5"]["method"] == "WEF"
    assert PHASE4_CONFIGURATIONS["C6"]["method"] == "ACFM"


def test_phase4_attribution_executes_same_cases_and_reports_metrics():
    config = AppConfig()
    config.model.window_size = 4
    result = run_phase4_attribution(
        _demo_paths(), config, seeds=[42], source_kind="synthetic_fixture"
    )
    assert result["status"] == "EXECUTED"
    assert result["source_kind"] == "synthetic_fixture"
    assert result["benchmark_claims_allowed"] is False
    assert result["configurations"] == ["C1", "C2", "C3", "C4", "C5", "C6"]
    assert len(result["runs"]) == 3
    for run in result["runs"]:
        assert set(run["configurations"]) == set(PHASE4_CONFIGURATIONS)
        counts = {item["sample_count"] for item in run["configurations"].values()}
        assert len(counts) == 1
        for key, item in run["configurations"].items():
            assert item["sample_count"] > 0
            for metric in ("precision", "recall", "f1", "fpr", "auroc"):
                assert np.isfinite(item["metrics"][metric])
            if key == "C1":
                assert item["hypothesis_top1_accuracy"] is None
                assert item["mean_uncertainty_width"] is None
            elif key == "C5":
                assert item["mean_uncertainty_width"] is None
            else:
                assert 0 <= item["mean_attribution_belief"] <= 1
                assert item["mean_attribution_belief"] <= item["mean_attribution_plausibility"] <= 1
                assert 0 <= item["mean_uncertainty_width"] <= 1
            if key != "C1":
                assert item["hypothesis_top1_evaluated_count"] + item["hypothesis_abstention_count"] == item["sample_count"]


def test_phase4_attribution_writes_json_and_csv(tmp_path):
    config = AppConfig()
    config.model.window_size = 4
    result = run_phase4_attribution(
        _demo_paths(), config, seeds=[42], source_kind="synthetic_fixture"
    )
    outputs = write_phase4_attribution_artifacts(result, tmp_path)
    payload = json.loads(Path(outputs["json"]).read_text(encoding="utf-8"))
    assert payload["schema_version"] == "XAITA-OT-PHASE4-ATTRIBUTION-1.0"
    assert Path(outputs["metrics_csv"]).is_file()
    assert Path(outputs["metrics_csv"]).read_text(encoding="utf-8").count("\n") == 19


def test_phase4_attribution_rejects_incomplete_dataset_matrix():
    with pytest.raises(ValueError, match="exactly"):
        run_phase4_attribution(
            {"SWaT": "missing.csv"}, AppConfig(), seeds=[42]
        )
