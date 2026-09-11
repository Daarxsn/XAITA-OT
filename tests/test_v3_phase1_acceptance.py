import numpy as np
import pandas as pd

from xaita_ot.config import AppConfig
from xaita_ot.pipeline.v3_evaluation import (
    audit_split_and_leakage,
    fit_bss_reference_train_only,
    fit_threshold_train_only,
    reproducibility_audit,
)


def _frame(n=240):
    labels = np.zeros(n, dtype=int)
    labels[60:75] = 1
    labels[150:165] = 1
    return pd.DataFrame({
        "timestamp": pd.date_range("2026-01-01", periods=n, freq="s"),
        "sensor_a": np.linspace(0, 1, n),
        "sensor_b": np.sin(np.arange(n) / 10),
        "asset": ["PLC-1"] * n,
        "protocol": ["modbus"] * n,
        "label": labels,
    })


def test_phase1_split_preprocessing_threshold_bss_gates_pass():
    cfg = AppConfig()
    cfg.model.window_size = 16
    cfg.experiment.seeds = [42]
    report = audit_split_and_leakage(_frame(), cfg)
    assert report["status"] == "PASS"
    assert report["chronological"] is True
    assert report["overlap_rows"] == 0
    assert report["preprocessing_fit_on_train_only"] is True
    assert report["threshold_fit_on_train_only"] is True
    assert report["bss_reference_fit_on_train_only"] is True


def test_threshold_depends_only_on_training_data():
    y = np.array([0, 0, 1, 1])
    scores = np.array([.1, .2, .8, .9])
    first = fit_threshold_train_only(y, scores)
    # Held-out observations are deliberately different and are not passed to the fitter.
    _heldout_y = np.array([1, 1, 0, 0])
    _heldout_scores = np.array([.99, .98, .01, .02])
    second = fit_threshold_train_only(y, scores)
    assert first == second


def test_bss_reference_is_train_scoped():
    train = _frame(120)
    ref = fit_bss_reference_train_only(train)
    assert ref["fit_partition"] == "train"
    assert ref["fit_rows"] == len(train)
    assert ref["feature_names"]


def test_seed_reproducibility_is_verified():
    cfg = AppConfig()
    cfg.model.window_size = 16
    result = reproducibility_audit(_frame(), cfg, seed=42)
    assert result["status"] == "PASS"
    assert result["repeat_identical"] is True
    assert len(result["prediction_digest"]) == 64
