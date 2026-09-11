"""V3 Phase 3 calibration evaluation.

Evaluates detector confidence and the WEF/ACFM attribution outputs without
refitting calibration or preprocessing on evaluation data.  ACFM remains an
interval-valued evidence assessment; its midpoint is used only as a comparable
binary confidence point for calibration analysis.
"""
from __future__ import annotations

from pathlib import Path
import json

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import brier_score_loss

from ..config import AppConfig
from ..core.attribution import assess
from ..core.attribution_baselines import weighted_evidence_fusion
from ..core.seed import set_seed
from ..io.adapters import adapt_dataset
from ..io.telemetry import load_csv, semantic_harmonize
from .evaluation import chronological_split, expected_calibration_error
from .preprocess import OTPreprocessor


def confidence_bins(y, p, bins: int = 10) -> list[dict]:
    """Return empirical confidence/accuracy statistics for fixed probability bins."""
    y = np.asarray(y).astype(int)
    p = np.asarray(p, dtype=float)
    if len(y) != len(p) or len(y) == 0:
        raise ValueError("labels and probabilities must be non-empty and aligned")
    if not 1 <= bins <= 100:
        raise ValueError("bins must be between 1 and 100")
    edges = np.linspace(0.0, 1.0, bins + 1)
    rows = []
    for i, (lo, hi) in enumerate(zip(edges[:-1], edges[1:])):
        mask = (p >= lo) & (p < (hi if i < bins - 1 else hi + 1e-12))
        if mask.any():
            confidence = float(p[mask].mean())
            accuracy = float(y[mask].mean())
            rows.append({"bin": i + 1, "lower": float(lo), "upper": float(hi), "count": int(mask.sum()), "confidence": confidence, "accuracy": accuracy, "gap": abs(confidence - accuracy)})
        else:
            rows.append({"bin": i + 1, "lower": float(lo), "upper": float(hi), "count": 0, "confidence": None, "accuracy": None, "gap": None})
    return rows


def reliability_summary(y, p, bins: int = 10) -> dict:
    """Compute ECE, Brier score and confidence-bin data."""
    y = np.asarray(y).astype(int)
    p = np.clip(np.asarray(p, dtype=float), 0.0, 1.0)
    return {
        "ece": float(expected_calibration_error(y, p, bins)),
        "brier": float(brier_score_loss(y, p)),
        "bins": confidence_bins(y, p, bins),
    }


def reliability_diagram(y, probabilities: dict[str, np.ndarray], out_path: str | Path, bins: int = 10) -> dict:
    """Write a reliability diagram and return the measured summaries."""
    summaries = {name: reliability_summary(y, p, bins) for name, p in probabilities.items()}
    fig, ax = plt.subplots(figsize=(7, 6))
    ax.plot([0, 1], [0, 1], linestyle="--", label="Perfect calibration")
    for name, summary in summaries.items():
        populated = [row for row in summary["bins"] if row["count"]]
        x = [row["confidence"] for row in populated]
        z = [row["accuracy"] for row in populated]
        ax.plot(x, z, marker="o", label=name)
    ax.set_xlabel("Mean predicted confidence")
    ax.set_ylabel("Empirical accuracy")
    ax.set_title("XAITA-OT Reliability Diagram")
    ax.set_xlim(0, 1); ax.set_ylim(0, 1)
    ax.grid(True, alpha=0.25)
    ax.legend()
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.tight_layout()
    fig.savefig(out_path, dpi=160)
    plt.close(fig)
    return summaries


def _window_context_scores(train_df: pd.DataFrame, test_df: pd.DataFrame, train_w, window_size: int, label_col="label") -> dict[str, np.ndarray]:
    """Build deterministic contextual evidence from train-fitted numeric baselines."""
    train_num = train_df.select_dtypes(include=[np.number]).drop(columns=[label_col], errors="ignore")
    test_num = test_df.select_dtypes(include=[np.number]).drop(columns=[label_col], errors="ignore")
    if train_num.empty or test_num.empty:
        raise ValueError("calibration evidence requires numeric telemetry")
    common = [c for c in train_num.columns if c in test_num.columns]
    if not common:
        raise ValueError("calibration evidence has no shared numeric telemetry")
    train_num, test_num = train_num[common], test_num[common]
    med = train_num.median().fillna(0.0)
    train_num, test_num = train_num.fillna(med), test_num.fillna(med)
    mean = train_num.mean()
    std = train_num.std(ddof=0).replace(0, 1.0)
    z = ((test_num - mean) / std).abs()
    row_anomaly = np.clip(z.mean(axis=1).to_numpy() / 4.0, 0.0, 1.0)
    row_dispersion = np.clip(z.std(axis=1, ddof=0).to_numpy() / 4.0, 0.0, 1.0)
    row_range = np.clip((z.max(axis=1).to_numpy()) / 6.0, 0.0, 1.0)
    diffs = test_num.diff().abs().fillna(0.0)
    row_change = np.clip((diffs / std).mean(axis=1).to_numpy() / 4.0, 0.0, 1.0)

    def roll(values):
        out = np.convolve(values, np.ones(window_size) / window_size, mode="valid")
        return out[:len(train_w.X)] if len(out) >= len(train_w.X) else np.pad(out, (0, len(train_w.X) - len(out)), mode="edge")

    return {"BSS": roll(row_anomaly), "ECS": roll(row_dispersion), "EC": roll(row_range), "MAS": roll(row_change)}


def fuse_wef_acfm(y, detector_p, contextual: dict[str, np.ndarray], reliabilities=None, support_threshold=.60, conflict_threshold=.35) -> dict:
    """Compare WEF point confidence with ACFM interval-midpoint confidence."""
    y = np.asarray(y).astype(int)
    detector_p = np.clip(np.asarray(detector_p, dtype=float), 0.0, 1.0)
    n = len(y)
    if len(detector_p) != n or any(len(v) != n for v in contextual.values()):
        raise ValueError("fusion evidence arrays must align with labels")
    reliabilities = dict(reliabilities or {"DC": 1.0, "BSS": .7, "ECS": .6, "EC": .5, "MAS": .6})
    hypotheses = ["attack", "benign"]
    wef = np.empty(n, dtype=float)
    acfm = np.empty(n, dtype=float)
    belief = np.empty(n, dtype=float)
    plausibility = np.empty(n, dtype=float)
    for i in range(n):
        attack = {"DC": float(detector_p[i]), **{k: float(v[i]) for k, v in contextual.items()}}
        result = weighted_evidence_fusion(attack, reliabilities)
        wef[i] = result["score"]
        evidence = {"attack": attack, "benign": {k: 1.0 - v for k, v in attack.items()}}
        assessments = assess(hypotheses, evidence, reliabilities, support_threshold, conflict_threshold)
        a = next(item for item in assessments if item.hypothesis == "attack")
        belief[i], plausibility[i] = float(a.belief), float(a.plausibility)
        acfm[i] = float(np.clip((a.belief + a.plausibility) / 2.0, 0.0, 1.0))
    return {
        "WEF": {"probabilities": wef, **reliability_summary(y, wef)},
        "ACFM": {"probabilities": acfm, "belief": belief, "plausibility": plausibility, **reliability_summary(y, acfm)},
        "reliabilities": reliabilities,
        "acfm_point_estimate": "midpoint of belief/plausibility interval; used only for calibration comparison",
    }


def evaluate_dataset(csv_path: str | Path, dataset: str, cfg: AppConfig, seed: int = 42, bins: int = 10) -> dict:
    """Run calibration evaluation on one environment with train-only preprocessing."""
    set_seed(seed)
    df = adapt_dataset(semantic_harmonize(load_csv(csv_path)), dataset)
    train, _, test = chronological_split(df, cfg.experiment.train_fraction, cfg.experiment.validation_fraction, cfg.attack_label_column, cfg.experiment.episode_aware)
    prep = OTPreprocessor(cfg.model.window_size)
    train_w = prep.fit_transform_train(train, cfg.attack_label_column)
    test_w = prep.transform(test, cfg.attack_label_column)
    if len(train_w.X) == 0 or len(test_w.X) == 0:
        raise ValueError(f"{dataset}: calibration evaluation produced empty windows")
    if len(np.unique(train_w.y)) < 2 or len(np.unique(test_w.y)) < 2:
        raise ValueError(f"{dataset}: calibration evaluation requires both classes in train and test windows")
    rf = RandomForestClassifier(n_estimators=120, random_state=seed, n_jobs=1, class_weight="balanced")
    rf.fit(train_w.X.reshape(len(train_w.X), -1), train_w.y)
    detector_p = rf.predict_proba(test_w.X.reshape(len(test_w.X), -1))[:, 1]
    contextual = _window_context_scores(train, test, train_w, cfg.model.window_size, cfg.attack_label_column)
    contextual = {k: v[:len(test_w.y)] for k, v in contextual.items()}
    detector = reliability_summary(test_w.y, detector_p, bins)
    fusion = fuse_wef_acfm(test_w.y, detector_p, contextual)
    return {
        "dataset": dataset,
        "seed": int(seed),
        "window_size": int(cfg.model.window_size),
        "train_windows": int(len(train_w.X)),
        "test_windows": int(len(test_w.X)),
        "detector": detector,
        "fusion": {"WEF": {k: v for k, v in fusion["WEF"].items() if k != "probabilities"}, "ACFM": {k: v for k, v in fusion["ACFM"].items() if k not in {"probabilities", "belief", "plausibility"}}, "reliabilities": fusion["reliabilities"], "acfm_point_estimate": fusion["acfm_point_estimate"]},
        "_plot_data": {"y": test_w.y.tolist(), "detector": detector_p.tolist(), "WEF": fusion["WEF"]["probabilities"].tolist(), "ACFM": fusion["ACFM"]["probabilities"].tolist()},
    }


def run_phase3(paths: dict[str, str], cfg: AppConfig, seeds=None, bins: int = 10) -> dict:
    """Execute calibration evaluation across configured environments and seeds."""
    seeds = list(cfg.experiment.seeds if seeds is None else seeds)
    expected = {"SWaT", "BATADAL", "TON-IoT"}
    if set(paths) != expected:
        raise ValueError(f"paths must contain exactly {sorted(expected)}")
    results = []
    for dataset, path in paths.items():
        for seed in seeds:
            results.append(evaluate_dataset(path, dataset, cfg, seed, bins))
    by_method = {"detector": [], "WEF": [], "ACFM": []}
    for item in results:
        by_method["detector"].append(item["detector"]["ece"])
        by_method["WEF"].append(item["fusion"]["WEF"]["ece"])
        by_method["ACFM"].append(item["fusion"]["ACFM"]["ece"])
    def agg(values):
        a = np.asarray(values, dtype=float)
        return {"mean": float(a.mean()), "std": float(a.std(ddof=1)) if len(a) > 1 else 0.0, "n": int(len(a))}
    return {"phase": "V3.3", "status": "PASS", "datasets": list(paths), "seeds": seeds, "bins": bins, "runs": results, "ece_summary": {k: agg(v) for k, v in by_method.items()}}


def write_phase3_artifacts(result: dict, out_dir: str | Path) -> dict[str, str]:
    """Write JSON/CSV confidence bins and reliability diagrams."""
    out = Path(out_dir); out.mkdir(parents=True, exist_ok=True)
    json_path = out / "phase3_calibration.json"
    json_path.write_text(json.dumps(result, indent=2, default=str), encoding="utf-8")
    rows = []
    for run in result["runs"]:
        for method, summary in (("detector", run["detector"]), ("WEF", run["fusion"]["WEF"]), ("ACFM", run["fusion"]["ACFM"])):
            for row in summary["bins"]:
                rows.append({"dataset": run["dataset"], "seed": run["seed"], "method": method, **row})
    bins_path = out / "confidence_bins.csv"
    pd.DataFrame(rows).to_csv(bins_path, index=False)
    first = result["runs"][0]
    y = np.asarray(first["_plot_data"]["y"], dtype=int)
    probs = {k: np.asarray(first["_plot_data"][k], dtype=float) for k in ("detector", "WEF", "ACFM")}
    plot_path = out / "reliability_diagram.png"
    reliability_diagram(y, probs, plot_path, result["bins"])
    # Remove private plot payload from persisted JSON to keep artifacts compact.
    persisted = dict(result)
    persisted["runs"] = [{k: v for k, v in run.items() if k != "_plot_data"} for run in result["runs"]]
    json_path.write_text(json.dumps(persisted, indent=2, default=str), encoding="utf-8")
    return {"json": str(json_path), "bins": str(bins_path), "reliability_diagram": str(plot_path)}
