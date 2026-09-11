"""V3 Phase 2 cross-environment evaluation.

Transfers are evaluated with a domain-invariant canonical telemetry representation.
The source environment owns fitting: split, feature statistics, preprocessing, and
model training are fitted only on source-train data; target-test is evaluation-only.
"""
from __future__ import annotations

from itertools import permutations
from pathlib import Path
import json

import numpy as np
import pandas as pd

from ..config import AppConfig
from ..core.seed import set_seed
from ..io.adapters import adapt_dataset
from ..io.telemetry import load_csv, semantic_harmonize
from .evaluation import binary_metrics, chronological_split
from .preprocess import OTPreprocessor
from .v3_evaluation import _train_predict

TRANSFER_PAIRS = (
    ("SWaT", "BATADAL"),
    ("BATADAL", "SWaT"),
    ("SWaT", "TON-IoT"),
    ("TON-IoT", "SWaT"),
    ("BATADAL", "TON-IoT"),
    ("TON-IoT", "BATADAL"),
)


def canonical_transfer_features(df: pd.DataFrame, label_col="label") -> pd.DataFrame:
    """Project arbitrary numeric telemetry into shared domain-invariant features."""
    numeric = df.select_dtypes(include=[np.number]).copy()
    if label_col in numeric:
        numeric = numeric.drop(columns=[label_col])
    if numeric.empty:
        raise ValueError("cross-environment evaluation requires numeric telemetry")
    numeric = numeric.replace([np.inf, -np.inf], np.nan)
    med = numeric.median().fillna(0.0)
    numeric = numeric.fillna(med)
    # Aggregates deliberately avoid dataset-specific sensor names while retaining
    # level, dispersion and range information available in every environment.
    out = pd.DataFrame(index=df.index)
    out["telemetry_mean"] = numeric.mean(axis=1)
    out["telemetry_std"] = numeric.std(axis=1, ddof=0)
    out["telemetry_min"] = numeric.min(axis=1)
    out["telemetry_max"] = numeric.max(axis=1)
    out["telemetry_l1"] = numeric.abs().mean(axis=1)
    out["asset"] = df.get("asset", pd.Series("unknown", index=df.index)).astype(str).to_numpy()
    out["protocol"] = df.get("protocol", pd.Series("unknown", index=df.index)).astype(str).to_numpy()
    out["timestamp"] = df["timestamp"].to_numpy()
    out[label_col] = df[label_col].astype(int).to_numpy()
    return out


def _prepare_pair(source_df, target_df, cfg):
    source = canonical_transfer_features(source_df, cfg.attack_label_column)
    target = canonical_transfer_features(target_df, cfg.attack_label_column)
    source_train, _, _ = chronological_split(source, cfg.experiment.train_fraction, cfg.experiment.validation_fraction, cfg.attack_label_column, cfg.experiment.episode_aware)
    _, _, target_test = chronological_split(target, cfg.experiment.train_fraction, cfg.experiment.validation_fraction, cfg.attack_label_column, cfg.experiment.episode_aware)
    prep = OTPreprocessor(cfg.model.window_size)
    train_w = prep.fit_transform_train(source_train, cfg.attack_label_column)
    target_w = prep.transform(target_test, cfg.attack_label_column)
    return train_w, target_w, {"source_train_rows": len(source_train), "target_test_rows": len(target_test), "source_features": list(prep.feature_names)}


def evaluate_transfer(source_name, target_name, source_path, target_path, cfg: AppConfig, seeds=None, detectors=("random_forest", "cnn", "lstm", "cnn_lstm")) -> dict:
    seeds = list(cfg.experiment.seeds if seeds is None else seeds)
    source = adapt_dataset(semantic_harmonize(load_csv(source_path)), source_name)
    target = adapt_dataset(semantic_harmonize(load_csv(target_path)), target_name)
    train_w, target_w, prep_meta = _prepare_pair(source, target, cfg)
    if len(train_w.X) == 0 or len(target_w.X) == 0:
        raise ValueError(f"{source_name}->{target_name}: empty source-train or target-test windows")
    if len(np.unique(train_w.y)) < 2:
        raise ValueError(f"{source_name}->{target_name}: source training windows contain one class")
    if len(np.unique(target_w.y)) < 2:
        raise ValueError(f"{source_name}->{target_name}: target test windows contain one class")

    runs = []
    for seed in seeds:
        set_seed(seed)
        metrics = {}
        for detector in detectors:
            p = _train_predict(train_w, target_w, cfg, detector, seed)
            metrics[detector] = binary_metrics(target_w.y, p)
        runs.append({"seed": int(seed), "metrics": metrics})
    return {"source": source_name, "target": target_name, "runs": runs, "preprocessing": prep_meta}


def cross_environment_phase2(paths: dict[str, str], cfg: AppConfig, seeds=None, detectors=("random_forest", "cnn", "lstm", "cnn_lstm")) -> dict:
    """Execute exactly the six planned directed transfers."""
    expected = {"SWaT", "BATADAL", "TON-IoT"}
    if set(paths) != expected:
        raise ValueError(f"paths must contain exactly {sorted(expected)}")
    pairs = {}
    for source, target in TRANSFER_PAIRS:
        pairs[f"{source}->{target}"] = evaluate_transfer(source, target, paths[source], paths[target], cfg, seeds, detectors)
    return {"phase": "V3.2", "pair_count": len(pairs), "expected_pair_count": 6, "pairs": pairs, "seeds": list(cfg.experiment.seeds if seeds is None else seeds), "detectors": list(detectors), "status": "PASS"}


def write_phase2_artifacts(result: dict, out_dir: str | Path) -> dict[str, str]:
    out = Path(out_dir); out.mkdir(parents=True, exist_ok=True)
    json_path = out / "phase2_cross_environment.json"
    json_path.write_text(json.dumps(result, indent=2, default=str), encoding="utf-8")
    rows = []
    for key, pair in result["pairs"].items():
        for run in pair["runs"]:
            for detector, metric in run["metrics"].items():
                rows.append({"transfer": key, "seed": run["seed"], "detector": detector, **metric})
    csv_path = out / "cross_environment_results.csv"
    pd.DataFrame(rows).to_csv(csv_path, index=False)
    return {"json": str(json_path), "csv": str(csv_path)}
