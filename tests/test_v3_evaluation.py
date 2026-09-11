import numpy as np
import pandas as pd

from xaita_ot.config import AppConfig
from xaita_ot.pipeline.v3_evaluation import (
    audit_split_and_leakage,
    confidence_bins,
    mean_std_ci,
    paired_effect,
    evidence_ablation,
)


def _df():
    labels = [0] * 20 + [1] * 5 + [0] * 20 + [1] * 5 + [0] * 20
    return pd.DataFrame({"timestamp": pd.date_range("2026-01-01", periods=len(labels), freq="s"), "label": labels})


def test_v3_leakage_audit_passes():
    audit = audit_split_and_leakage(_df(), AppConfig())
    assert audit["status"] == "PASS"
    assert audit["chronological"] is True
    assert audit["overlap_rows"] == 0
    assert audit["preprocessing_fit_on_train_only"] is True
    assert audit["threshold_fit_on_train_only"] is True
    assert audit["bss_reference_fit_on_train_only"] is True


def test_confidence_bins_cover_predictions():
    bins = confidence_bins([0, 1, 1, 0], [0.1, 0.7, 0.8, 0.2], bins=4)
    assert sum(x["count"] for x in bins) == 4
    assert all(0 <= x["lower"] <= x["upper"] <= 1 for x in bins)


def test_statistics_ci_and_paired_effect():
    summary = mean_std_ci([0.8, 0.82, 0.78, 0.81, 0.79])
    assert summary["n"] == 5
    assert summary["ci95_low"] < summary["mean"] < summary["ci95_high"]
    effect = paired_effect([0.9, 0.8, 0.85], [0.7, 0.75, 0.8])
    assert effect["n"] == 3
    assert effect["mean_difference"] > 0


def test_six_v3_ablation_variants_execute():
    evidence = {
        "H1": {"DC": .9, "BSS": .8, "ECS": .7, "EC": .8, "MAS": .6},
        "H2": {"DC": .4, "BSS": .5, "ECS": .5, "EC": .4, "MAS": .4},
        "H3": {"DC": .3, "BSS": .4, "ECS": .4, "EC": .3, "MAS": .2},
    }
    rel = {"DC": .7, "BSS": .8, "ECS": .85, "EC": .8, "MAS": .65}
    out = evidence_ablation(evidence, ["H1", "H2", "H3"], rel)
    assert list(out) == ["Full XAITA-OT", "-BTAE", "-BSS", "-ATT&CK", "-ACFM", "Detection-only"]
    assert all(out.values())
