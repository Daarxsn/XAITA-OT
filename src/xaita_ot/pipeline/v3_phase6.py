"""V3 Phase 6 statistical evaluation.

Aggregates repeated experimental observations and computes mean, sample
standard deviation, confidence intervals, and paired effect/statistical tests
when paired observations exist.  The implementation is intentionally generic
so it can consume detector, attribution, ablation, or other metric tables.
"""
from __future__ import annotations

from pathlib import Path
import json

import numpy as np
import pandas as pd
from scipy import stats

METRICS = ("precision", "recall", "f1", "fpr", "auroc")


def mean_std_ci(values, confidence: float = 0.95) -> dict:
    """Return mean, sample SD, and Student-t CI for repeated observations."""
    x = np.asarray(values, dtype=float)
    x = x[np.isfinite(x)]
    if len(x) == 0:
        return {"n": 0, "mean": None, "std": None, "ci_low": None, "ci_high": None, "ci_level": confidence}
    mean = float(np.mean(x))
    std = float(np.std(x, ddof=1)) if len(x) > 1 else 0.0
    if len(x) > 1:
        half = float(stats.t.ppf((1 + confidence) / 2, len(x) - 1) * std / np.sqrt(len(x)))
    else:
        half = 0.0
    return {"n": int(len(x)), "mean": mean, "std": std, "ci_low": mean - half, "ci_high": mean + half, "ci_level": confidence}


def summarize(frame: pd.DataFrame, group_cols, metrics=METRICS, confidence: float = 0.95) -> list[dict]:
    """Aggregate metrics by experiment identity, preserving repeat counts."""
    rows = []
    for keys, group in frame.groupby(list(group_cols), dropna=False):
        if not isinstance(keys, tuple): keys = (keys,)
        base = dict(zip(group_cols, keys))
        for metric in metrics:
            if metric not in group: continue
            s = mean_std_ci(group[metric].to_numpy(), confidence)
            rows.append({**base, "metric": metric, **s})
    return rows


def paired_comparison(frame: pd.DataFrame, condition_col: str, baseline: str, comparisons: list[str], pair_cols, metrics=METRICS, confidence: float = 0.95) -> list[dict]:
    """Compare conditions on matched experiment keys using paired t-tests and Cohen's dz."""
    rows = []
    base = frame[frame[condition_col] == baseline].set_index(list(pair_cols))
    for condition in comparisons:
        other = frame[frame[condition_col] == condition].set_index(list(pair_cols))
        for metric in metrics:
            if metric not in base.columns or metric not in other.columns: continue
            a, b = base[metric].align(other[metric], join="inner")
            x, y = a.to_numpy(float), b.to_numpy(float)
            finite = np.isfinite(x) & np.isfinite(y)
            x, y = x[finite], y[finite]
            d = x - y
            n = len(d)
            sd = float(np.std(d, ddof=1)) if n > 1 else 0.0
            dz = float(np.mean(d) / sd) if sd > 0 else 0.0
            if n > 1 and np.any(d != 0):
                test = stats.ttest_rel(x, y)
                p_value = float(test.pvalue)
                t_stat = float(test.statistic)
                half = float(stats.t.ppf((1 + confidence) / 2, n - 1) * sd / np.sqrt(n))
            else:
                p_value = None; t_stat = None; half = 0.0
            rows.append({"baseline": baseline, "condition": condition, "metric": metric, "n": int(n), "baseline_minus_condition_mean": float(np.mean(d)) if n else None, "difference_std": sd, "cohens_dz": dz, "t_statistic": t_stat, "p_value": p_value, "difference_ci_low": float(np.mean(d) - half) if n else None, "difference_ci_high": float(np.mean(d) + half) if n else None})
    return rows


def evaluate_ablation_statistics(ablation_result: dict, confidence: float = 0.95) -> dict:
    """Statistically evaluate a V3 Phase 4-style repeated ablation result."""
    rows = []
    for run in ablation_result["runs"]:
        for variant, metric_values in run["variants"].items():
            rows.append({"dataset": run["dataset"], "seed": run["seed"], "variant": variant, **{m: metric_values.get(m) for m in METRICS}})
    frame = pd.DataFrame(rows)
    summary = summarize(frame, ["variant"], METRICS, confidence)
    dataset_summary = summarize(frame, ["dataset", "variant"], METRICS, confidence)
    variants = [v for v in frame["variant"].unique() if v != "Full XAITA-OT"]
    effects = paired_comparison(frame, "variant", "Full XAITA-OT", variants, ["dataset", "seed"], METRICS, confidence)
    return {"confidence": confidence, "repeat_count": int(frame["seed"].nunique()), "observations": int(len(frame)), "summary": summary, "dataset_summary": dataset_summary, "paired_effects": effects}


def run_phase6_from_phase4(phase4_runner, paths: dict[str, str], cfg, seeds=None, confidence: float = 0.95) -> dict:
    """Execute repeated Phase 4 experiments and attach statistical summaries."""
    seeds = list(cfg.experiment.seeds if seeds is None else seeds)
    if len(seeds) < 2:
        raise ValueError("Phase 6 requires at least two seeds")
    result = phase4_runner(paths, cfg, seeds=seeds)
    statistics_result = evaluate_ablation_statistics(result, confidence)
    return {"phase": "V3.6", "status": "PASS", "datasets": result["datasets"], "seeds": seeds, "confidence": confidence, "source": "V3 Phase 4 ablation execution", "statistics": statistics_result, "source_runs": result["runs"]}


def write_phase6_artifacts(result: dict, out_dir: str | Path) -> dict[str, str]:
    out = Path(out_dir); out.mkdir(parents=True, exist_ok=True)
    json_path = out / "phase6_statistics.json"
    json_path.write_text(json.dumps(result, indent=2, default=str), encoding="utf-8")
    summary_path = out / "statistical_summary.csv"
    pd.DataFrame(result["statistics"]["summary"]).to_csv(summary_path, index=False)
    dataset_path = out / "statistical_dataset_summary.csv"
    pd.DataFrame(result["statistics"]["dataset_summary"]).to_csv(dataset_path, index=False)
    effects_path = out / "statistical_effects.csv"
    pd.DataFrame(result["statistics"]["paired_effects"]).to_csv(effects_path, index=False)
    return {"json": str(json_path), "summary": str(summary_path), "dataset_summary": str(dataset_path), "effects": str(effects_path)}
