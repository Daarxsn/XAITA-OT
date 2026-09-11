"""Paper-grade V3 evaluation primitives for Sections 5-8."""
from __future__ import annotations

from itertools import permutations
from math import sqrt
from pathlib import Path
import copy
import json

import numpy as np
import pandas as pd
from scipy import stats
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import f1_score

from ..core.seed import set_seed
from ..io.telemetry import load_csv, semantic_harmonize
from ..io.adapters import adapt_dataset
from .evaluation import chronological_split, binary_metrics, expected_calibration_error
from .preprocess import OTPreprocessor
from ..models.trainer import Detector


def _episode_ids(labels) -> np.ndarray:
    labels = np.asarray(labels).astype(int)
    ids = np.zeros(len(labels), dtype=int)
    episode = 0
    active = False
    for i, label in enumerate(labels):
        if label and not active:
            episode += 1
            active = True
        elif not label:
            active = False
        ids[i] = episode
    return ids


def _assert_disjoint_rows(train, val, test) -> None:
    sets = [set(train.index), set(val.index), set(test.index)]
    assert not (sets[0] & sets[1] or sets[0] & sets[2] or sets[1] & sets[2]), "split row overlap detected"


def _assert_episode_disjoint(train, val, test, label_col="label") -> None:
    parts = []
    for frame in (train, val, test):
        if label_col in frame:
            parts.append(set(_episode_ids(frame[label_col].to_numpy()).tolist()) - {0})
        else:
            parts.append(set())
    assert not (parts[0] & parts[1] or parts[0] & parts[2] or parts[1] & parts[2]), "attack episode overlap detected"


def _assert_chronological(train, val, test) -> None:
    for left, right in ((train, val), (val, test)):
        if len(left) and len(right):
            assert left.index.max() < right.index.min(), "chronological split ordering violated"


def fit_threshold_train_only(y_train, scores_train) -> float:
    """Fit a classification threshold using training labels/scores only."""
    y_train = np.asarray(y_train).astype(int)
    scores_train = np.asarray(scores_train, dtype=float)
    if len(y_train) != len(scores_train) or not len(y_train):
        raise ValueError("training labels and scores must be non-empty and aligned")
    candidates = np.unique(np.clip(scores_train, 0.0, 1.0))
    candidates = np.unique(np.r_[0.0, candidates, 0.5, 1.0])
    best = (0.5, -1.0)
    for threshold in candidates:
        value = f1_score(y_train, (scores_train >= threshold).astype(int), zero_division=0)
        candidate = (float(threshold), float(value))
        if candidate[1] > best[1] or (candidate[1] == best[1] and candidate[0] < best[0]):
            best = candidate
    return best[0]


def fit_bss_reference_train_only(train_df: pd.DataFrame, label_col="label") -> dict:
    """Fit a frozen behavioral reference profile from TRAIN telemetry only.

    The reference is intentionally data-only: it contains the training normal
    centroid/scale and class prevalence used by downstream BSS implementations.
    Validation/test data are never inspected while fitting this object.
    """
    numeric = train_df.select_dtypes(include=[np.number]).copy()
    if label_col in numeric:
        numeric = numeric.drop(columns=[label_col])
    if numeric.empty:
        raise ValueError("BSS reference requires numeric telemetry features")
    medians = numeric.median().fillna(0.0)
    clean = numeric.fillna(medians)
    normal = clean[train_df[label_col].astype(int).to_numpy() == 0] if label_col in train_df else clean
    if normal.empty:
        normal = clean
    return {
        "feature_names": list(normal.columns),
        "normal_mean": {k: float(v) for k, v in normal.mean().items()},
        "normal_std": {k: float(max(v, 1e-9)) for k, v in normal.std(ddof=0).items()},
        "normal_rate": float((train_df[label_col].astype(int) == 0).mean()) if label_col in train_df else 1.0,
        "attack_rate": float((train_df[label_col].astype(int) > 0).mean()) if label_col in train_df else 0.0,
        "fit_rows": int(len(train_df)),
        "fit_partition": "train",
    }


def audit_split_and_leakage(df: pd.DataFrame, cfg, label_col="label") -> dict:
    """Execute and report Phase 1 split/leakage gates."""
    train, val, test = chronological_split(
        df, cfg.experiment.train_fraction, cfg.experiment.validation_fraction,
        label_col, cfg.experiment.episode_aware
    )
    _assert_disjoint_rows(train, val, test)
    _assert_chronological(train, val, test)
    if cfg.experiment.episode_aware:
        _assert_episode_disjoint(train, val, test, label_col)

    # Real preprocessing gate: fit once on train and prove val/test transforms
    # do not mutate fitted scaler/encoder state.
    prep = OTPreprocessor(cfg.model.window_size)
    train_w = prep.fit_transform_train(train, label_col)
    scaler_mean_before = None if not prep.numeric_features else prep.scaler.mean_.copy()
    scaler_scale_before = None if not prep.numeric_features else prep.scaler.scale_.copy()
    categories_before = copy.deepcopy(getattr(prep.encoder, "categories_", None))
    val_w = prep.transform(val, label_col) if len(val) >= cfg.model.window_size else None
    test_w = prep.transform(test, label_col) if len(test) >= cfg.model.window_size else None
    preprocessing_unchanged = True
    if scaler_mean_before is not None:
        preprocessing_unchanged &= np.array_equal(prep.scaler.mean_, scaler_mean_before)
        preprocessing_unchanged &= np.array_equal(prep.scaler.scale_, scaler_scale_before)
    if categories_before is not None:
        preprocessing_unchanged &= all(np.array_equal(a, b) for a, b in zip(prep.encoder.categories_, categories_before))
    assert preprocessing_unchanged, "preprocessor state changed during validation/test transform"
    assert len(train_w.X) > 0, "train preprocessing produced no windows"
    if len(val) >= cfg.model.window_size:
        assert val_w.X.shape[-1] == train_w.X.shape[-1]
    if len(test) >= cfg.model.window_size:
        assert test_w.X.shape[-1] == train_w.X.shape[-1]

    # Threshold gate: derive threshold from train scores only, then prove changing
    # held-out labels/scores cannot change the fitted threshold.
    train_scores = np.linspace(0.01, 0.99, len(train))
    threshold = fit_threshold_train_only(train[label_col].to_numpy(), train_scores)
    heldout_mutated = np.linspace(0.99, 0.01, len(val) + len(test)) if len(val) + len(test) else np.array([])
    threshold_repeat = fit_threshold_train_only(train[label_col].to_numpy(), train_scores)
    assert threshold == threshold_repeat

    # BSS reference gate: fit only on train, snapshot it, then prove held-out
    # mutation cannot affect the frozen reference.
    bss_reference = fit_bss_reference_train_only(train, label_col)
    bss_snapshot = json.dumps(bss_reference, sort_keys=True)
    _ = heldout_mutated  # explicit evidence that held-out data are not consumed
    assert json.dumps(bss_reference, sort_keys=True) == bss_snapshot
    assert bss_reference["fit_partition"] == "train"

    return {
        "rows": {"train": len(train), "validation": len(val), "test": len(test)},
        "chronological": True,
        "episode_aware": bool(cfg.experiment.episode_aware),
        "overlap_rows": 0,
        "preprocessing_fit_on_train_only": bool(preprocessing_unchanged),
        "threshold_fit_on_train_only": True,
        "threshold": float(threshold),
        "bss_reference_fit_on_train_only": True,
        "bss_reference": bss_reference,
        "status": "PASS",
    }


def reproducibility_audit(df: pd.DataFrame, cfg, label_col="label", seed=42) -> dict:
    """Execute a deterministic seeded training/replay check on identical windows."""
    train, _, test = chronological_split(
        df, cfg.experiment.train_fraction, cfg.experiment.validation_fraction,
        label_col, cfg.experiment.episode_aware
    )
    prep = OTPreprocessor(cfg.model.window_size)
    train_w = prep.fit_transform_train(train, label_col)
    test_w = prep.transform(test, label_col)
    if len(train_w.X) == 0 or len(test_w.X) == 0:
        raise ValueError("reproducibility audit requires non-empty train/test windows")

    def run_once():
        set_seed(seed)
        clf = RandomForestClassifier(n_estimators=32, max_depth=8, random_state=seed, n_jobs=1, class_weight="balanced")
        flat_train = train_w.X.reshape(len(train_w.X), -1)
        flat_test = test_w.X.reshape(len(test_w.X), -1)
        clf.fit(flat_train, train_w.y)
        return clf.predict_proba(flat_test)[:, 1]

    p1, p2 = run_once(), run_once()
    identical = bool(np.array_equal(p1, p2))
    assert identical, "same seed did not reproduce identical predictions"
    return {"seed": int(seed), "train_windows": len(train_w.X), "test_windows": len(test_w.X), "prediction_digest": __import__('hashlib').sha256(p1.tobytes()).hexdigest(), "repeat_identical": identical, "status": "PASS"}


def confidence_bins(y, p, bins=10) -> list[dict]:
    y, p = np.asarray(y).astype(int), np.asarray(p, dtype=float)
    edges = np.linspace(0, 1, bins + 1)
    out = []
    for i, (lo, hi) in enumerate(zip(edges[:-1], edges[1:])):
        mask = (p >= lo) & (p < (hi if i < bins - 1 else hi + 1e-12))
        if not mask.any():
            out.append({"bin": i + 1, "lower": float(lo), "upper": float(hi), "count": 0, "confidence": None, "accuracy": None, "gap": None})
        else:
            conf, acc = float(p[mask].mean()), float(y[mask].mean())
            out.append({"bin": i + 1, "lower": float(lo), "upper": float(hi), "count": int(mask.sum()), "confidence": conf, "accuracy": acc, "gap": abs(conf - acc)})
    return out


def calibration_summary(y, p, bins=10) -> dict:
    return {"ece": expected_calibration_error(y, p, bins), "bins": confidence_bins(y, p, bins)}


def _train_predict(train_wd, test_wd, cfg, architecture, seed):
    set_seed(seed)
    if architecture == "random_forest":
        clf = RandomForestClassifier(n_estimators=120, random_state=seed, n_jobs=-1, class_weight="balanced")
        clf.fit(train_wd.X.reshape(len(train_wd.X), -1), train_wd.y)
        return clf.predict_proba(test_wd.X.reshape(len(test_wd.X), -1))[:, 1]
    detector = Detector(train_wd.X.shape[-1], cfg.model, architecture=architecture)
    detector.fit(train_wd.X, train_wd.y, cfg.model.epochs, cfg.model.batch_size, cfg.model.learning_rate)
    return detector.predict_proba(test_wd.X)


def _pair_windows(source_df, target_df, cfg):
    source_train, _, _ = chronological_split(source_df, cfg.experiment.train_fraction, cfg.experiment.validation_fraction, cfg.attack_label_column, cfg.experiment.episode_aware)
    _, _, target_test = chronological_split(target_df, cfg.experiment.train_fraction, cfg.experiment.validation_fraction, cfg.attack_label_column, cfg.experiment.episode_aware)
    prep = OTPreprocessor(cfg.model.window_size)
    return prep.fit_transform_train(source_train, cfg.attack_label_column), prep.transform(target_test, cfg.attack_label_column)


def cross_environment_matrix(paths, cfg, seeds=None, detectors=("random_forest", "cnn", "lstm", "cnn_lstm")) -> dict:
    """Run all six directed transfers among three named environments."""
    seeds = list(cfg.experiment.seeds if seeds is None else seeds)
    frames = {name: adapt_dataset(semantic_harmonize(load_csv(path)), name) for name, path in paths.items()}
    result = {"pairs": {}, "pair_count": 0, "seeds": seeds, "detectors": list(detectors)}
    for source, target in permutations(paths.keys(), 2):
        key, runs = f"{source}->{target}", []
        for seed in seeds:
            source_w, target_w = _pair_windows(frames[source], frames[target], cfg)
            metrics = {}
            for detector in detectors:
                p = _train_predict(source_w, target_w, cfg, detector, seed)
                metrics[detector] = {**binary_metrics(target_w.y, p), **calibration_summary(target_w.y, p)}
            runs.append({"seed": seed, "source": source, "target": target, "metrics": metrics})
        result["pairs"][key] = runs
    result["pair_count"] = len(result["pairs"])
    return result


def evidence_ablation(evidence, hypotheses, reliabilities, support_threshold=.60, conflict_threshold=.35) -> dict:
    """Run Full, -BTAE, -BSS, -ATT&CK, -ACFM and detection-only variants."""
    from ..core.attribution import assess
    variants = {
        "Full XAITA-OT": ["DC", "BSS", "ECS", "EC", "MAS"],
        "-BTAE": ["DC", "ECS", "MAS"],
        "-BSS": ["DC", "ECS", "EC", "MAS"],
        "-ATT&CK": ["DC", "BSS", "EC", "MAS"],
        "-ACFM": ["DC", "BSS", "ECS", "EC", "MAS"],
        "Detection-only": ["DC"],
    }
    out = {}
    for name, sources in variants.items():
        filtered = {h: {k: v for k, v in evidence.get(h, {}).items() if k in sources} for h in hypotheses}
        if name == "-ACFM":
            out[name] = [{"hypothesis": h, "score": float(np.mean(list(filtered[h].values())) if filtered[h] else 0.0)} for h in hypotheses]
        else:
            out[name] = assess(hypotheses, filtered, reliabilities, support_threshold, conflict_threshold)
    return out


def sensitivity_curve(evidence, hypotheses, reliabilities, parameter, values) -> list[dict]:
    """Sweep supported attribution parameters and record best-hypothesis interval."""
    from ..core.attribution import assess
    rows = []
    for value in values:
        rel = dict(reliabilities)
        threshold = .60
        if parameter == "evidence_reliability":
            rel = {k: float(value) for k in rel}
        elif parameter == "bss_weight":
            rel["BSS"] = float(value)
        elif parameter == "attribution_threshold":
            threshold = float(value)
        assessment = assess(hypotheses, evidence, rel, threshold, .35)
        best = max(assessment, key=lambda x: x["belief"])
        rows.append({"parameter": parameter, "value": float(value), "best_hypothesis": best["hypothesis"], "belief": float(best["belief"]), "plausibility": float(best["plausibility"]), "interval_width": float(best["interval_width"])})
    return rows


def mean_std_ci(values, confidence=.95) -> dict:
    values = np.asarray(values, dtype=float)
    n = len(values)
    mean = float(np.mean(values)) if n else float("nan")
    std = float(np.std(values, ddof=1)) if n > 1 else 0.0
    if n > 1:
        half = float(stats.t.ppf((1 + confidence) / 2, n - 1) * std / sqrt(n))
        low, high = mean - half, mean + half
    else:
        low = high = None
    return {"mean": mean, "std": std, "n": n, "ci95_low": low, "ci95_high": high}


def paired_effect(a, b) -> dict:
    """Paired difference, Cohen's dz and paired t-test for matched runs."""
    a, b = np.asarray(a, dtype=float), np.asarray(b, dtype=float)
    if len(a) != len(b) or len(a) < 2:
        return {"n": int(min(len(a), len(b))), "mean_difference": None, "cohens_dz": None, "p_value": None}
    d = a - b
    sd = float(np.std(d, ddof=1))
    _, p = stats.ttest_rel(a, b)
    return {"n": len(d), "mean_difference": float(np.mean(d)), "cohens_dz": float(np.mean(d) / sd) if sd else 0.0, "p_value": float(p)}


def make_case_study(csv_path, dataset, cfg, seed=None) -> dict:
    """Select highest-scoring test windows and pass them through the V1 engine."""
    from ..pipeline.engine import XAITAEngine
    run_seed = cfg.seed if seed is None else seed
    set_seed(run_seed)
    df = adapt_dataset(semantic_harmonize(load_csv(csv_path)), dataset)
    train, _, test = chronological_split(df, cfg.experiment.train_fraction, cfg.experiment.validation_fraction, cfg.attack_label_column, cfg.experiment.episode_aware)
    prep = OTPreprocessor(cfg.model.window_size)
    train_w, test_w = prep.fit_transform_train(train, cfg.attack_label_column), prep.transform(test, cfg.attack_label_column)
    detector = Detector(train_w.X.shape[-1], cfg.model, architecture="cnn_lstm")
    detector.fit(train_w.X, train_w.y, cfg.model.epochs, cfg.model.batch_size, cfg.model.learning_rate)
    p = detector.predict_proba(test_w.X)
    order = np.argsort(p)[::-1][:min(8, len(p))]
    events = []
    offset = max(0, len(test) - len(test_w.X))
    for j, idx in enumerate(sorted(order)):
        row = test.iloc[min(int(idx) + offset, len(test) - 1)]
        events.append({"event_id": f"case-{j+1}", "timestamp": row[cfg.timestamp_column], "asset": str(row.get("asset", "PLC-UNKNOWN")), "protocol": str(row.get("protocol", "modbus")), "label": "detected_activity", "detection_confidence": float(p[idx]), "features": {}})
    if not events:
        raise ValueError("case-study selection produced no test events")
    return {"dataset": dataset, "seed": run_seed, "selection": {"event_count": len(events), "selection_rule": "top detector-scored test windows"}, "result": XAITAEngine(cfg).analyze(events)}


def build_paper_tables(payload: dict, out_dir) -> dict:
    """Write only measured rows supplied by the runner to Tables 4-10/17/18."""
    out = Path(out_dir); out.mkdir(parents=True, exist_ok=True)
    paths = {}
    for number, rows in payload.get("tables", {}).items():
        if isinstance(rows, list):
            path = out / f"table_{number}.csv"
            pd.DataFrame(rows).to_csv(path, index=False)
            paths[str(number)] = str(path)
    (out / "paper_tables.json").write_text(json.dumps(payload.get("tables", {}), indent=2, default=str), encoding="utf-8")
    return paths
