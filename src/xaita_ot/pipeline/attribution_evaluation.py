"""Phase 4 C1-C6 attribution evaluation.

This is separate from the V3 Phase 4 ablation experiment. It compares the
agreed evidence configurations using identical chronological test windows.
The attribution interval is an evidence interval, not a calibrated probability.
"""
from __future__ import annotations

from pathlib import Path
import json
from typing import Any

import numpy as np
import pandas as pd

from ..config import AppConfig
from ..core.attribution import assess
from ..core.attribution_baselines import weighted_evidence_fusion
from ..core.seed import set_seed
from ..io.adapters import adapt_dataset
from ..io.dataset_validation import DatasetValidationError, validate_csv
from ..io.telemetry import load_csv, semantic_harmonize
from .evaluation import chronological_split
from .preprocess import OTPreprocessor
from .v3_phase4 import RELIABILITIES, _metrics, _window_detector, _window_evidence


PHASE4_CONFIGURATIONS = {
    "C1": {"name": "Detection only", "method": "DC", "sources": ()},
    "C2": {"name": "DC + BSS", "method": "ACFM", "sources": ("DC", "BSS")},
    "C3": {"name": "DC + BSS + ECS", "method": "ACFM", "sources": ("DC", "BSS", "ECS")},
    "C4": {"name": "DC + BSS + ECS + MAS", "method": "ACFM", "sources": ("DC", "BSS", "ECS", "MAS")},
    "C5": {"name": "Weighted Evidence Fusion", "method": "WEF", "sources": ("DC", "BSS", "ECS", "MAS")},
    "C6": {"name": "ACFM", "method": "ACFM", "sources": ("DC", "BSS", "ECS", "MAS")},
}
PHASE4_SCHEMA_VERSION = "XAITA-OT-PHASE4-ATTRIBUTION-1.0"
DATASETS = ("SWaT", "BATADAL", "TON-IoT")


def _fuse_configuration(
    configuration_id: str,
    labels: np.ndarray,
    detector_scores: np.ndarray,
    evidence: dict[str, np.ndarray],
) -> dict[str, Any]:
    definition = PHASE4_CONFIGURATIONS[configuration_id]
    n = len(labels)
    if len(detector_scores) != n:
        raise ValueError("detector score count does not match test labels")

    if configuration_id == "C1":
        scores = np.asarray(detector_scores, dtype=float)
        metrics = _metrics(labels, scores)
        return {
            "configuration": configuration_id,
            "name": definition["name"],
            "method": definition["method"],
            "sources": list(definition["sources"]),
            "sample_count": int(n),
            "metrics": metrics,
            "hypothesis_top1_accuracy": None,
            "hypothesis_top1_evaluated_count": 0,
            "hypothesis_abstention_count": None,
            "detector": "random_forest",
            "mean_detection_confidence": float(np.mean(detector_scores)),
            "mean_attribution_belief": None,
            "mean_attribution_plausibility": None,
            "mean_uncertainty_width": None,
            "attribution_metrics_status": "not_applicable_detection_only",
        }

    scores_by_source = {"DC": np.asarray(detector_scores, dtype=float), **evidence}
    selected = {
        source: np.asarray(scores_by_source[source], dtype=float)
        for source in definition["sources"]
    }
    if any(len(values) != n for values in selected.values()):
        raise ValueError(f"{configuration_id}: evidence length does not match test labels")
    if any(not np.isfinite(values).all() or np.any((values < 0) | (values > 1)) for values in selected.values()):
        raise ValueError(f"{configuration_id}: evidence must be finite and in [0, 1]")

    scores = np.empty(n, dtype=float)
    beliefs = np.empty(n, dtype=float)
    plausibilities = np.empty(n, dtype=float)
    top1_attack = np.full(n, np.nan, dtype=float)
    interval_available = definition["method"] == "ACFM"

    for index in range(n):
        values = {source: float(series[index]) for source, series in selected.items()}
        if definition["method"] == "WEF":
            fused = weighted_evidence_fusion(values, RELIABILITIES)
            scores[index] = fused["score"]
            beliefs[index] = np.nan
            plausibilities[index] = np.nan
            if scores[index] > 0.5:
                top1_attack[index] = 1.0
            elif scores[index] < 0.5:
                top1_attack[index] = 0.0
            continue

        competing_evidence = {
            "attack": values,
            "benign": {source: 1.0 - score for source, score in values.items()},
        }
        assessments = assess(
            ["attack", "benign"],
            competing_evidence,
            RELIABILITIES,
            support_threshold=0.60,
            conflict_threshold=0.35,
        )
        by_hypothesis = {item.hypothesis: item for item in assessments}
        attack = by_hypothesis["attack"]
        scores[index] = (attack.belief + attack.plausibility) / 2.0
        beliefs[index] = attack.belief
        plausibilities[index] = attack.plausibility
        benign = by_hypothesis["benign"]
        attack_rank = (attack.belief, attack.plausibility)
        benign_rank = (benign.belief, benign.plausibility)
        if attack_rank != benign_rank:
            top1_attack[index] = 1.0 if attack_rank > benign_rank else 0.0

    result_metrics = _metrics(labels, scores)
    ranked = np.isfinite(top1_attack)
    ranking_count = int(ranked.sum())
    ranking_accuracy = (
        float(np.mean(top1_attack[ranked].astype(int) == labels[ranked].astype(int)))
        if ranking_count else None
    )
    return {
        "configuration": configuration_id,
        "name": definition["name"],
        "method": definition["method"],
        "sources": list(definition["sources"]),
        "sample_count": int(n),
        "metrics": result_metrics,
        "hypothesis_top1_accuracy": ranking_accuracy,
        "hypothesis_top1_evaluated_count": ranking_count,
        "hypothesis_abstention_count": int(n - ranking_count),
        "detector": "random_forest",
        "mean_detection_confidence": float(np.mean(detector_scores)),
        "mean_attribution_belief": float(np.mean(beliefs)) if interval_available else None,
        "mean_attribution_plausibility": float(np.mean(plausibilities)) if interval_available else None,
        "mean_uncertainty_width": float(np.mean(plausibilities - beliefs)) if interval_available else None,
        "attribution_metrics_status": "evaluated",
    }


def evaluate_dataset_attribution(
    csv_path: str | Path,
    dataset: str,
    config: AppConfig,
    seed: int = 42,
) -> dict[str, Any]:
    """Evaluate C1-C6 on the same validated chronological test windows."""
    source = Path(csv_path)
    validation = validate_csv(source, dataset, root=source.parent)
    if validation.validation_status != "pass":
        raise DatasetValidationError(
            f"{validation.dataset}: Phase 4 attribution evaluation is blocked until validation passes"
        )

    set_seed(seed)
    frame = adapt_dataset(
        semantic_harmonize(
            load_csv(source, strict_timestamps=True, sort_and_deduplicate=False)
        ),
        dataset,
    )
    train, _, test = chronological_split(
        frame,
        config.experiment.train_fraction,
        config.experiment.validation_fraction,
        config.attack_label_column,
        config.experiment.episode_aware,
    )
    preprocessor = OTPreprocessor(config.model.window_size)
    train_windows = preprocessor.fit_transform_train(train, config.attack_label_column)
    test_windows = preprocessor.transform(test, config.attack_label_column)
    if (
        len(train_windows.X) == 0
        or len(test_windows.X) == 0
        or np.unique(train_windows.y).size < 2
        or np.unique(test_windows.y).size < 2
    ):
        raise ValueError(
            f"{dataset}: Phase 4 requires non-empty train/test windows and both classes in each"
        )

    detector_scores = _window_detector(train_windows, test_windows, seed)
    evidence_windows = _window_evidence(
        train, test, config.model.window_size, config.attack_label_column
    )
    evidence_windows = {
        key: values[: len(test_windows.y)]
        for key, values in evidence_windows.items()
    }
    results = {
        key: _fuse_configuration(
            key, test_windows.y, detector_scores, evidence_windows
        )
        for key in PHASE4_CONFIGURATIONS
    }
    return {
        "dataset": dataset,
        "seed": int(seed),
        "dataset_validation": validation.as_dict(),
        "split_protocol": "chronological_episode_aware",
        "train_rows": int(len(train)),
        "test_rows": int(len(test)),
        "train_windows": int(len(train_windows.X)),
        "test_windows": int(len(test_windows.X)),
        "configurations": results,
    }


def run_phase4_attribution(
    paths: dict[str, str | Path],
    config: AppConfig,
    seeds: list[int] | None = None,
    source_kind: str = "unverified",
) -> dict[str, Any]:
    """Run C1-C6 for each dataset/seed; source kind is provenance, not certification."""
    if set(paths) != set(DATASETS):
        raise ValueError(f"paths must contain exactly {list(DATASETS)}")
    if source_kind not in {"real_benchmark", "synthetic_fixture", "unverified"}:
        raise ValueError("source_kind must be real_benchmark, synthetic_fixture or unverified")
    selected_seeds = list(config.experiment.seeds if seeds is None else seeds)
    if not selected_seeds or any(int(seed) < 0 for seed in selected_seeds):
        raise ValueError("at least one non-negative seed is required")

    runs = [
        evaluate_dataset_attribution(paths[dataset], dataset, config, int(seed))
        for dataset in DATASETS
        for seed in selected_seeds
    ]
    return {
        "schema_version": PHASE4_SCHEMA_VERSION,
        "phase": "Phase 4 Attribution Evaluation",
        "status": "EXECUTED",
        "source_kind": source_kind,
        "benchmark_claims_allowed": source_kind == "real_benchmark",
        "benchmark_claims_note": (
            "Source-kind metadata is user-declared and does not independently verify provenance, "
            "licensing, ground truth or benchmark authenticity."
        ),
        "configurations": list(PHASE4_CONFIGURATIONS),
        "datasets": list(DATASETS),
        "seeds": [int(seed) for seed in selected_seeds],
        "runs": runs,
    }


def write_phase4_attribution_artifacts(
    result: dict[str, Any], out_dir: str | Path
) -> dict[str, str]:
    output = Path(out_dir)
    output.mkdir(parents=True, exist_ok=True)
    json_path = output / "phase4_attribution.json"
    csv_path = output / "phase4_attribution_metrics.csv"
    json_path.write_text(
        json.dumps(result, indent=2, sort_keys=True, allow_nan=False, default=str) + "\n",
        encoding="utf-8",
    )
    rows = []
    for run in result["runs"]:
        for key, configuration in run["configurations"].items():
            rows.append({
                "dataset": run["dataset"],
                "seed": run["seed"],
                "configuration": key,
                "name": configuration["name"],
                "method": configuration["method"],
                "sample_count": configuration["sample_count"],
                "precision": configuration["metrics"]["precision"],
                "recall": configuration["metrics"]["recall"],
                "f1": configuration["metrics"]["f1"],
                "fpr": configuration["metrics"]["fpr"],
                "auroc": configuration["metrics"]["auroc"],
                "hypothesis_top1_accuracy": configuration["hypothesis_top1_accuracy"],
                "hypothesis_top1_evaluated_count": configuration["hypothesis_top1_evaluated_count"],
                "hypothesis_abstention_count": configuration["hypothesis_abstention_count"],
                "detector": configuration["detector"],
                "mean_detection_confidence": configuration["mean_detection_confidence"],
                "mean_attribution_belief": configuration["mean_attribution_belief"],
                "mean_attribution_plausibility": configuration["mean_attribution_plausibility"],
                "mean_uncertainty_width": configuration["mean_uncertainty_width"],
                "attribution_metrics_status": configuration["attribution_metrics_status"],
            })
    pd.DataFrame(rows).to_csv(csv_path, index=False)
    return {"json": str(json_path), "metrics_csv": str(csv_path)}
