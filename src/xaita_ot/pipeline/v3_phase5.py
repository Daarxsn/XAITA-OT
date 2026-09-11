"""V3 Phase 5 sensitivity analysis for key XAITA-OT parameters."""
from __future__ import annotations

from pathlib import Path
import json

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import precision_recall_fscore_support, roc_auc_score

from ..config import AppConfig
from ..core.attribution import assess
from ..core.seed import set_seed
from ..io.adapters import adapt_dataset
from ..io.telemetry import load_csv, semantic_harmonize
from .evaluation import chronological_split
from .preprocess import OTPreprocessor

PARAMETER_VALUES = {
    "correlation_threshold": [0.45, 0.55, 0.65],
    "temporal_window": [30.0, 60.0, 120.0],
    "bss_weighting": [0.50, 0.80, 1.10],
    "evidence_reliability": [0.60, 0.80, 1.00],
    "attribution_threshold": [0.50, 0.60, 0.70],
}
BASE_RELIABILITY = {"DC": 1.0, "BSS": 0.80, "ECS": 0.85, "EC": 0.80, "MAS": 0.65}


def _metrics(y, p):
    y = np.asarray(y).astype(int); p = np.clip(np.asarray(p, dtype=float), 0, 1)
    pred = (p >= 0.5).astype(int)
    pr, re, f1, _ = precision_recall_fscore_support(y, pred, average="binary", zero_division=0)
    fp = ((pred == 1) & (y == 0)).sum(); tn = ((pred == 0) & (y == 0)).sum()
    return {
        "precision": float(pr), "recall": float(re), "f1": float(f1),
        "fpr": float(fp / max(1, fp + tn)),
        "auroc": float(roc_auc_score(y, p)) if len(np.unique(y)) > 1 else float("nan"),
    }


def _base_evidence(train, test, window_size):
    numeric_train = train.select_dtypes(include=[np.number]).drop(columns=["label"], errors="ignore")
    numeric_test = test.select_dtypes(include=[np.number]).drop(columns=["label"], errors="ignore")
    common = [c for c in numeric_train.columns if c in numeric_test.columns]
    if not common: raise ValueError("sensitivity requires shared numeric telemetry")
    a, b = numeric_train[common].copy(), numeric_test[common].copy()
    med = a.median().fillna(0); a = a.fillna(med); b = b.fillna(med)
    mu, sd = a.mean(), a.std(ddof=0).replace(0, 1.0)
    z = ((b - mu) / sd).abs()
    anomaly = np.clip(z.mean(axis=1).to_numpy() / 4.0, 0, 1)
    dispersion = np.clip(z.std(axis=1, ddof=0).to_numpy() / 4.0, 0, 1)
    change = np.clip((b.diff().abs().fillna(0) / sd).mean(axis=1).to_numpy() / 4.0, 0, 1)
    range_score = np.clip(z.max(axis=1).to_numpy() / 6.0, 0, 1)
    ts = pd.to_datetime(test["timestamp"], utc=True).astype("int64").to_numpy() / 1e9
    delta = np.r_[np.nan, np.diff(ts)]
    temporal = np.clip(np.exp(-np.nan_to_num(delta, nan=0.0) / 60.0), 0, 1)
    def roll(v, w=window_size):
        return np.convolve(v, np.ones(w) / w, mode="valid") if len(v) >= w else np.array([])
    return {"BSS": roll(anomaly), "ECS": roll(dispersion), "MAS": roll(0.5 * change + 0.5 * anomaly), "EC": roll(range_score), "temporal": roll(temporal)}


def _detector(train_w, test_w, seed):
    set_seed(seed)
    clf = RandomForestClassifier(n_estimators=120, random_state=seed, n_jobs=1, class_weight="balanced")
    clf.fit(train_w.X.reshape(len(train_w.X), -1), train_w.y)
    return clf.predict_proba(test_w.X.reshape(len(test_w.X), -1))[:, 1]


def _parameter_score(detector_p, evidence, parameter, value, timestamps):
    e = {k: np.asarray(v, dtype=float).copy() for k, v in evidence.items() if k != "temporal"}
    temporal = evidence["temporal"].copy()
    if parameter == "correlation_threshold":
        e["EC"] = np.clip((e["EC"] - value) / max(1e-9, 1.0 - value), 0, 1)
    elif parameter == "temporal_window":
        e["temporal"] = np.clip(temporal * (1.0 - np.exp(-float(value) / 60.0)), 0, 1)
    elif parameter == "bss_weighting":
        e["BSS"] = np.clip(e["BSS"] * float(value), 0, 1)
    elif parameter == "evidence_reliability":
        e = {k: np.clip(v * float(value), 0, 1) for k, v in e.items()}
    elif parameter == "attribution_threshold":
        pass
    else:
        raise ValueError(f"unsupported parameter: {parameter}")
    rel = dict(BASE_RELIABILITY)
    if "temporal" in e: rel["EC"] = rel["EC"]
    if parameter == "bss_weighting": rel["BSS"] = float(np.clip(value, 0, 1))
    if parameter == "evidence_reliability": rel = {k: float(np.clip(v * value, 0, 1)) for k, v in rel.items()}
    threshold = float(value) if parameter == "attribution_threshold" else 0.60
    n = len(detector_p)
    p = np.empty(n)
    belief = np.empty(n); plausibility = np.empty(n)
    for i in range(n):
        attack = {"DC": float(detector_p[i]), **{k: float(v[i]) for k, v in e.items()}}
        benign = {k: 1.0 - v for k, v in attack.items()}
        a = assess(["attack", "benign"], {"attack": attack, "benign": benign}, rel, threshold, 0.35)[0]
        belief[i], plausibility[i] = a.belief, a.plausibility
        p[i] = (belief[i] + plausibility[i]) / 2.0
    return p, float(np.mean(belief)), float(np.mean(plausibility)), float(np.mean(plausibility - belief))


def evaluate_dataset(csv_path, dataset, cfg: AppConfig, seed=42):
    df = adapt_dataset(semantic_harmonize(load_csv(csv_path)), dataset)
    train, _, test = chronological_split(df, cfg.experiment.train_fraction, cfg.experiment.validation_fraction, "label", cfg.experiment.episode_aware)
    prep = OTPreprocessor(cfg.model.window_size)
    train_w = prep.fit_transform_train(train, "label"); test_w = prep.transform(test, "label")
    if len(np.unique(train_w.y)) < 2 or len(np.unique(test_w.y)) < 2:
        raise ValueError(f"{dataset}: sensitivity requires two-class train/test windows")
    detector_p = _detector(train_w, test_w, seed)
    evidence = _base_evidence(train, test, cfg.model.window_size)
    evidence = {k: v[:len(test_w.y)] for k, v in evidence.items()}
    rows = []
    for parameter, values in PARAMETER_VALUES.items():
        for value in values:
            p, belief, plausibility, width = _parameter_score(detector_p, evidence, parameter, value, test_w.timestamps)
            rows.append({"dataset": dataset, "seed": int(seed), "parameter": parameter, "value": float(value), **_metrics(test_w.y, p), "belief_mean": belief, "plausibility_mean": plausibility, "interval_width_mean": width})
    return rows


def run_phase5(paths: dict[str, str], cfg: AppConfig, seeds=None):
    seeds = list(cfg.experiment.seeds if seeds is None else seeds)
    expected = {"SWaT", "BATADAL", "TON-IoT"}
    if set(paths) != expected: raise ValueError(f"paths must contain exactly {sorted(expected)}")
    rows = [row for dataset, path in paths.items() for seed in seeds for row in evaluate_dataset(path, dataset, cfg, seed)]
    frame = pd.DataFrame(rows)
    summary = frame.groupby(["parameter", "value"], as_index=False).agg(
        f1_mean=("f1", "mean"), f1_std=("f1", "std"), precision_mean=("precision", "mean"), recall_mean=("recall", "mean"), fpr_mean=("fpr", "mean"), auroc_mean=("auroc", "mean"), interval_width_mean=("interval_width_mean", "mean"), n=("f1", "size")
    )
    return {"phase": "V3.5", "status": "PASS", "datasets": list(paths), "seeds": seeds, "parameters": PARAMETER_VALUES, "rows": rows, "summary": summary.to_dict(orient="records"), "run_count": len(rows)}


def write_phase5_artifacts(result: dict, out_dir: str | Path):
    out = Path(out_dir); out.mkdir(parents=True, exist_ok=True)
    json_path = out / "phase5_sensitivity.json"
    json_path.write_text(json.dumps(result, indent=2, default=str), encoding="utf-8")
    csv_path = out / "sensitivity_results.csv"
    pd.DataFrame(result["rows"]).to_csv(csv_path, index=False)
    summary_path = out / "sensitivity_summary.csv"
    pd.DataFrame(result["summary"]).to_csv(summary_path, index=False)
    return {"json": str(json_path), "results": str(csv_path), "summary": str(summary_path)}
