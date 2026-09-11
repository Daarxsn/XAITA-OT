"""V3 Phase 4 ablation framework.

The framework evaluates the six planned configurations on leakage-controlled
train/test windows.  BTAE is represented by the behavioral/contextual evidence
channels BSS, ECS and MAS; ATT&CK is an explicit context-coverage evidence
channel; ACFM is the interval-valued fusion method and WEF is its point-estimate
baseline.  The mapping is explicit so an ablation cannot silently remove the
wrong component.
"""
from __future__ import annotations

from pathlib import Path
import json

import numpy as np
import pandas as pd
from scipy import stats
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import precision_recall_fscore_support, roc_auc_score

from ..config import AppConfig
from ..core.attribution import assess
from ..core.attribution_baselines import weighted_evidence_fusion
from ..core.seed import set_seed
from ..io.adapters import adapt_dataset
from ..io.telemetry import load_csv, semantic_harmonize
from .evaluation import chronological_split
from .preprocess import OTPreprocessor

VARIANTS = {
    "Full XAITA-OT": ("ACFM", ("DC", "BSS", "ECS", "ATT&CK", "MAS")),
    "-BTAE": ("ACFM", ("DC", "ATT&CK")),
    "-BSS": ("ACFM", ("DC", "ECS", "ATT&CK", "MAS")),
    "-ATT&CK": ("ACFM", ("DC", "BSS", "ECS", "MAS")),
    "-ACFM": ("WEF", ("DC", "BSS", "ECS", "ATT&CK", "MAS")),
    "Detection-only": ("DC", ("DC",)),
}

RELIABILITIES = {"DC": 1.0, "BSS": .80, "ECS": .85, "ATT&CK": .75, "MAS": .65}


def _metrics(y, p):
    y = np.asarray(y).astype(int); p = np.clip(np.asarray(p, dtype=float), 0, 1)
    pred = (p >= .5).astype(int)
    pr, re, f1, _ = precision_recall_fscore_support(y, pred, average="binary", zero_division=0)
    fp = int(((pred == 1) & (y == 0)).sum()); tn = int(((pred == 0) & (y == 0)).sum())
    auc = roc_auc_score(y, p) if len(np.unique(y)) > 1 else float("nan")
    return {"precision": float(pr), "recall": float(re), "f1": float(f1), "fpr": float(fp / max(1, fp + tn)), "auroc": float(auc)}


def _window_evidence(train_df, test_df, window_size, label_col="label"):
    """Generate frozen train-referenced evidence vectors for test windows."""
    numeric_train = train_df.select_dtypes(include=[np.number]).drop(columns=[label_col], errors="ignore")
    numeric_test = test_df.select_dtypes(include=[np.number]).drop(columns=[label_col], errors="ignore")
    common = [c for c in numeric_train.columns if c in numeric_test.columns]
    if not common:
        raise ValueError("ablation requires shared numeric telemetry")
    a, b = numeric_train[common].copy(), numeric_test[common].copy()
    med = a.median().fillna(0); a = a.fillna(med); b = b.fillna(med)
    mu = a.mean(); sd = a.std(ddof=0).replace(0, 1.0)
    z = ((b - mu) / sd).abs()
    row_anomaly = np.clip(z.mean(axis=1).to_numpy() / 4.0, 0, 1)
    row_dispersion = np.clip(z.std(axis=1, ddof=0).to_numpy() / 4.0, 0, 1)
    row_range = np.clip(z.max(axis=1).to_numpy() / 6.0, 0, 1)
    changes = b.diff().abs().fillna(0)
    row_change = np.clip((changes / sd).mean(axis=1).to_numpy() / 4.0, 0, 1)

    assets = test_df.get("asset", pd.Series("unknown", index=test_df.index)).astype(str).to_numpy()
    protocols = test_df.get("protocol", pd.Series("unknown", index=test_df.index)).astype(str).to_numpy()
    known_asset = set(train_df.get("asset", pd.Series("unknown", index=train_df.index)).astype(str))
    known_protocol = set(train_df.get("protocol", pd.Series("unknown", index=train_df.index)).astype(str))
    attack_map = np.array([1.0 if (x in known_asset and y in known_protocol) else .55 for x, y in zip(assets, protocols)])

    def roll(v):
        if len(v) < window_size: return np.array([])
        return np.convolve(v, np.ones(window_size) / window_size, mode="valid")
    return {
        "BSS": roll(row_anomaly),
        "ECS": roll(row_dispersion),
        "MAS": roll(np.clip(.5 * row_change + .5 * row_anomaly, 0, 1)),
        "ATT&CK": roll(attack_map),
        "EC": roll(row_range),
    }


def _window_detector(train_w, test_w, seed):
    set_seed(seed)
    clf = RandomForestClassifier(n_estimators=120, random_state=seed, n_jobs=1, class_weight="balanced")
    clf.fit(train_w.X.reshape(len(train_w.X), -1), train_w.y)
    return clf.predict_proba(test_w.X.reshape(len(test_w.X), -1))[:, 1]


def _fuse(y, detector_p, evidence, variant):
    method, sources = VARIANTS[variant]
    n = len(y)
    if variant == "Detection-only":
        p = np.asarray(detector_p, dtype=float)
        return p, np.zeros(n), np.ones(n), {"method": "DC", "interval_width_mean": 0.0}
    full = {"DC": detector_p, **evidence}
    filtered = {k: np.asarray(full[k], dtype=float) for k in sources}
    if method == "WEF":
        p = np.array([weighted_evidence_fusion({k: float(v[i]) for k, v in filtered.items()}, RELIABILITIES)["score"] for i in range(n)])
        return p, p.copy(), p.copy(), {"method": "WEF", "interval_width_mean": 0.0}
    hypotheses = ["attack", "benign"]
    p, belief, plausibility = np.empty(n), np.empty(n), np.empty(n)
    for i in range(n):
        attack = {k: float(v[i]) for k, v in filtered.items()}
        ev = {"attack": attack, "benign": {k: 1.0 - value for k, value in attack.items()}}
        ass = assess(hypotheses, ev, RELIABILITIES, .60, .35)
        a = next(x for x in ass if x.hypothesis == "attack")
        belief[i] = float(a.belief); plausibility[i] = float(a.plausibility)
        p[i] = (belief[i] + plausibility[i]) / 2.0
    return p, belief, plausibility, {"method": "ACFM", "interval_width_mean": float(np.mean(plausibility - belief))}


def evaluate_dataset(csv_path, dataset, cfg: AppConfig, seed=42):
    df = adapt_dataset(semantic_harmonize(load_csv(csv_path)), dataset)
    train, _, test = chronological_split(df, cfg.experiment.train_fraction, cfg.experiment.validation_fraction, cfg.attack_label_column, cfg.experiment.episode_aware)
    prep = OTPreprocessor(cfg.model.window_size)
    train_w = prep.fit_transform_train(train, cfg.attack_label_column)
    test_w = prep.transform(test, cfg.attack_label_column)
    if len(train_w.X) == 0 or len(test_w.X) == 0 or len(np.unique(train_w.y)) < 2 or len(np.unique(test_w.y)) < 2:
        raise ValueError(f"{dataset}: ablation requires two-class non-empty train/test windows")
    detector_p = _window_detector(train_w, test_w, seed)
    evidence = _window_evidence(train, test, cfg.model.window_size, cfg.attack_label_column)
    evidence = {k: v[:len(test_w.y)] for k, v in evidence.items()}
    results = {}
    for variant in VARIANTS:
        p, belief, plausibility, meta = _fuse(test_w.y, detector_p, evidence, variant)
        results[variant] = {**_metrics(test_w.y, p), "belief_mean": float(np.mean(belief)), "plausibility_mean": float(np.mean(plausibility)), "interval_width_mean": float(meta["interval_width_mean"]), "method": meta["method"]}
    return {"dataset": dataset, "seed": int(seed), "train_windows": len(train_w.X), "test_windows": len(test_w.X), "variants": results}


def run_phase4(paths: dict[str, str], cfg: AppConfig, seeds=None) -> dict:
    seeds = list(cfg.experiment.seeds if seeds is None else seeds)
    expected = {"SWaT", "BATADAL", "TON-IoT"}
    if set(paths) != expected: raise ValueError(f"paths must contain exactly {sorted(expected)}")
    runs = [evaluate_dataset(path, dataset, cfg, seed) for dataset, path in paths.items() for seed in seeds]
    rows = []
    for run in runs:
        for variant, metrics in run["variants"].items():
            rows.append({"dataset": run["dataset"], "seed": run["seed"], "variant": variant, **metrics})
    frame = pd.DataFrame(rows)
    full = frame[frame.variant == "Full XAITA-OT"].set_index(["dataset", "seed"])
    effects = {}
    for variant in VARIANTS:
        if variant == "Full XAITA-OT": continue
        other = frame[frame.variant == variant].set_index(["dataset", "seed"])
        paired = []
        for metric in ("f1", "precision", "recall", "fpr", "auroc"):
            a, b = full[metric].align(other[metric], join="inner")
            a, b = a.to_numpy(float), b.to_numpy(float)
            d = a - b
            sd = float(np.std(d, ddof=1)) if len(d) > 1 else 0.0
            p = float(stats.ttest_rel(a, b).pvalue) if len(d) > 1 else None
            paired.append({"metric": metric, "n": int(len(d)), "full_minus_variant_mean": float(np.nanmean(d)) if len(d) else None, "cohens_dz": float(np.nanmean(d) / sd) if sd > 0 else 0.0, "p_value": p})
        effects[variant] = paired
    return {"phase": "V3.4", "status": "PASS", "datasets": list(paths), "seeds": seeds, "variants": list(VARIANTS), "runs": runs, "effects_vs_full": effects, "row_count": len(rows)}


def write_phase4_artifacts(result: dict, out_dir: str | Path):
    out = Path(out_dir); out.mkdir(parents=True, exist_ok=True)
    (out / "phase4_ablation.json").write_text(json.dumps(result, indent=2, default=str), encoding="utf-8")
    rows = []
    for run in result["runs"]:
        for variant, metrics in run["variants"].items():
            rows.append({"dataset": run["dataset"], "seed": run["seed"], "variant": variant, **metrics})
    csv = out / "ablation_results.csv"; pd.DataFrame(rows).to_csv(csv, index=False)
    effect_rows = []
    for variant, metrics in result["effects_vs_full"].items():
        for item in metrics: effect_rows.append({"variant": variant, **item})
    effects = out / "ablation_effects.csv"; pd.DataFrame(effect_rows).to_csv(effects, index=False)
    return {"json": str(out / "phase4_ablation.json"), "results": str(csv), "effects": str(effects)}
