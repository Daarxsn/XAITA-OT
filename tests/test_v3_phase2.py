from pathlib import Path

from xaita_ot.config import AppConfig
from xaita_ot.pipeline.v3_phase2 import TRANSFER_PAIRS, cross_environment_phase2, canonical_transfer_features
from xaita_ot.io.adapters import adapt_dataset
from xaita_ot.io.telemetry import load_csv, semantic_harmonize

ROOT = Path(__file__).resolve().parents[1]


def _paths():
    return {
        "SWaT": str(ROOT / "data/demo/swat_like.csv"),
        "BATADAL": str(ROOT / "data/demo/batadal_like.csv"),
        "TON-IoT": str(ROOT / "data/demo/toniot_like.csv"),
    }


def test_phase2_canonical_projection_is_shared():
    for name, path in _paths().items():
        df = adapt_dataset(semantic_harmonize(load_csv(path)), name)
        out = canonical_transfer_features(df)
        assert {"telemetry_mean", "telemetry_std", "telemetry_min", "telemetry_max", "telemetry_l1"}.issubset(out.columns)
        assert "label" in out.columns
        assert len(out) == len(df)


def test_phase2_executes_all_six_directed_transfers():
    cfg = AppConfig()
    cfg.model.window_size = 4
    cfg.model.epochs = 1
    cfg.experiment.seeds = [42]
    result = cross_environment_phase2(_paths(), cfg, seeds=[42], detectors=("random_forest",))
    assert result["status"] == "PASS"
    assert result["pair_count"] == 6
    assert set(result["pairs"]) == {f"{a}->{b}" for a, b in TRANSFER_PAIRS}
    for pair in result["pairs"].values():
        assert len(pair["runs"]) == 1
        assert "random_forest" in pair["runs"][0]["metrics"]
        assert pair["preprocessing"]["source_train_rows"] > 0
        assert pair["preprocessing"]["target_test_rows"] > 0
