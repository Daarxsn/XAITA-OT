"""Reproducible real-dataset experiment execution.

This layer binds a validated researcher-supplied CSV to a detector run and
creates an auditable result envelope containing dataset identity, validation
evidence, run configuration and an immutable reproducibility fingerprint.
"""

from __future__ import annotations

from dataclasses import asdict
import hashlib
import json
import numpy as np
import pandas as pd
from pathlib import Path
from typing import Any

from .. import __version__
from ..config import AppConfig
from .experiments import ExperimentRun, run_detection
from ..io.dataset_validation import DatasetValidationError, validate_csv


SCHEMA_VERSION = "XAITA-OT-V5-REAL-EXPERIMENT-1.0"
SUITE_SCHEMA_VERSION = "XAITA-OT-V5-REAL-EXPERIMENT-SUITE-1.0"
REAL_EXPERIMENT_DETECTORS = ("random_forest", "cnn", "lstm", "cnn_lstm")
REAL_EXPERIMENT_DATASETS = ("SWaT", "BATADAL", "TON-IoT")


def _canonical_json(payload: Any) -> bytes:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")


def reproducibility_fingerprint(
    *,
    dataset_sha256: str,
    dataset: str,
    detector: str,
    seed: int,
    split_protocol: str,
    config: dict[str, Any],
    package_version: str = __version__,
) -> str:
    payload = {
        "dataset_sha256": dataset_sha256,
        "dataset": dataset,
        "detector": detector,
        "seed": int(seed),
        "split_protocol": split_protocol,
        "config": config,
        "package_version": package_version,
    }
    return hashlib.sha256(_canonical_json(payload)).hexdigest()


def build_result_envelope(
    validation: Any,
    run: ExperimentRun,
    *,
    config: AppConfig,
) -> dict[str, Any]:
    experiment = asdict(run)
    fingerprint = reproducibility_fingerprint(
        dataset_sha256=validation.sha256,
        dataset=run.dataset,
        detector=str(run.config.get("detector", "")),
        seed=run.seed,
        split_protocol=str(run.config.get("split_protocol", "")),
        config=run.config,
    )
    return {
        "schema_version": SCHEMA_VERSION,
        "package_version": __version__,
        "dataset_validation": validation.as_dict(),
        "experiment": experiment,
        "reproducibility": {
            "fingerprint": fingerprint,
            "dataset_sha256": validation.sha256,
            "seed": int(run.seed),
            "detector": str(run.config.get("detector", "")),
            "split_protocol": str(run.config.get("split_protocol", "")),
            "config_sha256": hashlib.sha256(_canonical_json(run.config)).hexdigest(),
            "package_version": __version__,
        },
    }


def run_real_experiment(
    *,
    csv_path: str | Path,
    dataset: str,
    config: AppConfig,
    detector: str,
    seed: int | None = None,
    dataset_root: str | Path | None = None,
) -> dict[str, Any]:
    """Validate a real benchmark file, execute one detector, and return an audit envelope."""
    validation = validate_csv(csv_path, dataset, root=dataset_root)
    if validation.validation_status != "pass":
        raise DatasetValidationError(
            f"{validation.dataset}: validation status is '{validation.validation_status}'; "
            "real experiment execution is blocked until the dataset passes validation"
        )

    run = run_detection(csv_path, dataset, config, seed=seed, detector=detector)
    return build_result_envelope(validation, run, config=config)



def run_real_experiment_suite(
    *,
    csv_path: str | Path,
    dataset: str,
    config: AppConfig,
    seed: int | None = None,
    dataset_root: str | Path | None = None,
    detectors: tuple[str, ...] = REAL_EXPERIMENT_DETECTORS,
) -> dict[str, Any]:
    """Validate once, execute the detector suite, and return one auditable bundle."""
    validation = validate_csv(csv_path, dataset, root=dataset_root)
    if validation.validation_status != "pass":
        raise DatasetValidationError(
            f"{validation.dataset}: validation status is '{validation.validation_status}'; "
            "real experiment suite execution is blocked until the dataset passes validation"
        )

    requested = tuple(str(d).strip().lower().replace("-", "_") for d in detectors)
    if not requested:
        raise ValueError("detectors must contain at least one detector")
    unknown = sorted(set(requested) - set(REAL_EXPERIMENT_DETECTORS))
    if unknown:
        raise ValueError(f"Unknown detector(s): {', '.join(unknown)}")
    if len(set(requested)) != len(requested):
        raise ValueError("detectors must be unique")

    run_seed = config.seed if seed is None else seed
    runs: list[dict[str, Any]] = []
    for detector in requested:
        try:
            run = run_detection(csv_path, dataset, config, seed=run_seed, detector=detector)
            runs.append({"status": "completed", "detector": detector,
                         "result": build_result_envelope(validation, run, config=config)})
        except Exception as exc:
            runs.append({"status": "failed", "detector": detector,
                         "error": {"type": type(exc).__name__, "message": str(exc)}})

    completed = sum(item["status"] == "completed" for item in runs)
    failed = len(runs) - completed
    split_protocols = sorted({
        item["result"]["reproducibility"]["split_protocol"]
        for item in runs if item["status"] == "completed"
    })
    fingerprint_payload = {
        "dataset_sha256": validation.sha256,
        "dataset": validation.dataset,
        "detectors": list(requested),
        "seed": int(run_seed),
        "split_protocols": split_protocols,
        "config": config.model_dump(mode="json"),
        "package_version": __version__,
    }
    return {
        "schema_version": SUITE_SCHEMA_VERSION,
        "package_version": __version__,
        "dataset_validation": validation.as_dict(),
        "suite": {
            "dataset": validation.dataset,
            "seed": int(run_seed),
            "requested_detectors": list(requested),
            "completed_detectors": [x["detector"] for x in runs if x["status"] == "completed"],
            "failed_detectors": [x["detector"] for x in runs if x["status"] == "failed"],
            "detector_count": len(requested),
            "completed_count": completed,
            "failed_count": failed,
            "status": "completed" if failed == 0 else "failed",
            "split_protocols": split_protocols,
            "config_sha256": hashlib.sha256(_canonical_json(config.model_dump(mode="json"))).hexdigest(),
            "fingerprint": hashlib.sha256(_canonical_json(fingerprint_payload)).hexdigest(),
        },
        "runs": runs,
    }



def run_real_experiment_matrix(
    *,
    csv_paths: dict[str, str | Path],
    config: AppConfig,
    seed: int | None = None,
    detectors: tuple[str, ...] = REAL_EXPERIMENT_DETECTORS,
    datasets: tuple[str, ...] = REAL_EXPERIMENT_DATASETS,
) -> dict[str, Any]:
    """Execute a deterministic multi-dataset detector matrix with retained failures."""
    requested_datasets = tuple(str(d).strip() for d in datasets)
    if not requested_datasets:
        raise ValueError("datasets must contain at least one dataset")
    unknown_datasets = sorted(set(requested_datasets) - set(REAL_EXPERIMENT_DATASETS))
    if unknown_datasets:
        raise ValueError(f"Unknown dataset(s): {', '.join(unknown_datasets)}")
    if len(set(requested_datasets)) != len(requested_datasets):
        raise ValueError("datasets must be unique")

    normalized_paths = {str(k).strip(): Path(v) for k, v in csv_paths.items()}
    missing = [dataset for dataset in requested_datasets if dataset not in normalized_paths]
    if missing:
        raise ValueError(f"Missing CSV path(s) for dataset(s): {', '.join(missing)}")
    extra = sorted(set(normalized_paths) - set(requested_datasets))
    if extra:
        raise ValueError(f"Unexpected CSV path dataset(s): {', '.join(extra)}")

    run_seed = config.seed if seed is None else seed
    dataset_runs: list[dict[str, Any]] = []
    for dataset in requested_datasets:
        try:
            suite = run_real_experiment_suite(
                csv_path=normalized_paths[dataset],
                dataset=dataset,
                config=config,
                seed=run_seed,
                detectors=detectors,
            )
            dataset_runs.append({
                "status": "completed" if suite["suite"]["status"] == "completed" else "failed",
                "dataset": dataset,
                "result": suite,
            })
        except Exception as exc:
            dataset_runs.append({
                "status": "failed",
                "dataset": dataset,
                "error": {"type": type(exc).__name__, "message": str(exc)},
            })

    completed = sum(item["status"] == "completed" for item in dataset_runs)
    failed = len(dataset_runs) - completed
    dataset_status = [
        {
            "dataset": item["dataset"],
            "status": item["status"],
            "completed_detectors": (
                item["result"]["suite"]["completed_detectors"] if "result" in item else []
            ),
            "failed_detectors": (
                item["result"]["suite"]["failed_detectors"] if "result" in item else []
            ),
        }
        for item in dataset_runs
    ]
    normalized_detectors = tuple(
        str(d).strip().lower().replace("-", "_") for d in detectors
    )
    fingerprint_payload = {
        "datasets": list(requested_datasets),
        "detectors": list(normalized_detectors),
        "seed": int(run_seed),
        "dataset_status": dataset_status,
        "config": config.model_dump(mode="json"),
        "package_version": __version__,
    }
    return {
        "schema_version": "XAITA-OT-V5-REAL-EXPERIMENT-MATRIX-1.0",
        "package_version": __version__,
        "matrix": {
            "datasets": list(requested_datasets),
            "detectors": list(normalized_detectors),
            "dataset_count": len(requested_datasets),
            "completed_dataset_count": completed,
            "failed_dataset_count": failed,
            "seed": int(run_seed),
            "status": "completed" if failed == 0 else "failed",
            "fingerprint": hashlib.sha256(_canonical_json(fingerprint_payload)).hexdigest(),
        },
        "datasets": dataset_runs,
    }


def _mean_std_ci(values: list[float], confidence: float = 0.95) -> dict[str, Any]:
    import math
    from scipy import stats
    finite = [float(v) for v in values if math.isfinite(float(v))]
    n = len(finite)
    if n == 0:
        return {"n": 0, "mean": None, "std": None, "ci_low": None, "ci_high": None, "confidence": confidence}
    mean = float(sum(finite) / n)
    std = float(np.std(np.asarray(finite), ddof=1)) if n > 1 else 0.0
    half = float(stats.t.ppf((1.0 + confidence) / 2.0, n - 1) * std / np.sqrt(n)) if n > 1 else 0.0
    return {"n": n, "mean": mean, "std": std, "ci_low": mean - half, "ci_high": mean + half, "confidence": confidence}


def run_real_experiment_statistical_matrix(
    *,
    csv_paths: dict[str, str | Path],
    config: AppConfig,
    seeds: list[int],
    detectors: tuple[str, ...] = REAL_EXPERIMENT_DETECTORS,
    datasets: tuple[str, ...] = REAL_EXPERIMENT_DATASETS,
    confidence: float = 0.95,
) -> dict[str, Any]:
    """Repeat the controlled matrix across seeds and return reproducible statistics."""
    if len(seeds) < 2:
        raise ValueError("statistical matrix requires at least two seeds")
    if len(set(seeds)) != len(seeds):
        raise ValueError("statistical matrix seeds must be unique")
    if not 0.0 < confidence < 1.0:
        raise ValueError("confidence must be between 0 and 1")

    runs = []
    for seed in seeds:
        matrix = run_real_experiment_matrix(
            csv_paths=csv_paths,
            config=config,
            seed=int(seed),
            detectors=detectors,
            datasets=datasets,
        )
        runs.append({"seed": int(seed), "status": matrix["matrix"]["status"], "result": matrix})

    observations = []
    for run in runs:
        seed = run["seed"]
        for dataset_run in run["result"]["datasets"]:
            if dataset_run["status"] != "completed":
                continue
            for detector_run in dataset_run["result"]["runs"]:
                if detector_run["status"] != "completed":
                    continue
                experiment = detector_run["result"]["experiment"]
                for detector, metrics in experiment["metrics"].items():
                    if detector not in tuple(str(d).strip().lower().replace("-", "_") for d in detectors):
                        continue
                    for metric, value in metrics.items():
                        if isinstance(value, (int, float)) and np.isfinite(value):
                            observations.append({
                                "dataset": dataset_run["dataset"],
                                "detector": detector,
                                "seed": seed,
                                "metric": metric,
                                "value": float(value),
                            })

    summary = []
    if observations:
        frame = pd.DataFrame(observations)
        for keys, group in frame.groupby(["dataset", "detector", "metric"], dropna=False):
            stats_row = _mean_std_ci(group["value"].tolist(), confidence)
            summary.append({
                "dataset": keys[0],
                "detector": keys[1],
                "metric": keys[2],
                **stats_row,
            })

    paired = []
    if observations:
        frame = pd.DataFrame(observations)
        for dataset in sorted(frame["dataset"].unique()):
            for metric in sorted(frame["metric"].unique()):
                pivot = frame[frame["dataset"] == dataset].pivot_table(
                    index="seed", columns="detector", values="value", aggfunc="first"
                )
                detectors_present = [d for d in detectors if d in pivot.columns]
                if len(detectors_present) < 2:
                    continue
                from scipy import stats
                baseline = detectors_present[0]
                for detector in detectors_present[1:]:
                    pair = pivot[[baseline, detector]].dropna()
                    diff = pair[baseline].to_numpy(float) - pair[detector].to_numpy(float)
                    n = len(diff)
                    if n < 2:
                        p_value = None
                        t_stat = None
                    elif np.allclose(diff, 0.0):
                        p_value = 1.0
                        t_stat = 0.0
                    else:
                        test = stats.ttest_rel(pair[baseline], pair[detector])
                        p_value = float(test.pvalue)
                        t_stat = float(test.statistic)
                    effect = float(np.mean(diff) / np.std(diff, ddof=1)) if n > 1 and np.std(diff, ddof=1) > 0 else 0.0
                    paired.append({
                        "dataset": dataset,
                        "metric": metric,
                        "baseline": baseline,
                        "detector": detector,
                        "n": n,
                        "baseline_minus_detector_mean": float(np.mean(diff)) if n else None,
                        "cohens_dz": effect,
                        "t_statistic": t_stat,
                        "p_value": p_value,
                    })

    completed_matrices = sum(run["status"] == "completed" for run in runs)
    return {
        "schema_version": "XAITA-OT-V5-REAL-EXPERIMENT-STATISTICS-1.0",
        "package_version": __version__,
        "statistics": {
            "seeds": [int(seed) for seed in seeds],
            "repeat_count": len(seeds),
            "confidence": float(confidence),
            "completed_matrix_count": completed_matrices,
            "failed_matrix_count": len(runs) - completed_matrices,
            "status": "completed" if completed_matrices == len(runs) and observations else "failed",
            "summary": summary,
            "paired_detector_comparisons": paired,
            "observation_count": len(observations),
            "fingerprint": hashlib.sha256(_canonical_json({
                "seeds": [int(seed) for seed in seeds],
                "detectors": list(detectors),
                "datasets": list(datasets),
                "confidence": float(confidence),
                "summary": summary,
                "paired_detector_comparisons": paired,
            })).hexdigest(),
        },
        "runs": runs,
    }



ATTRIBUTION_EVALUATION_SCHEMA_VERSION = "XAITA-OT-V5-ATTRIBUTION-EVALUATION-1.0"
ATTRIBUTION_CONFIGURATIONS = (
    "DC", "DC+BSS", "DC+BSS+ECS", "DC+BSS+ECS+MAS", "ACFM", "WEF",
)

def evaluate_attribution_cases(
    cases: list[dict[str, Any]],
    *,
    reliabilities: dict[str, float],
    support_threshold: float = 0.60,
    conflict_threshold: float = 0.35,
    configurations: tuple[str, ...] = ATTRIBUTION_CONFIGURATIONS,
) -> dict[str, Any]:
    """Evaluate attribution configurations on explicitly labeled evidence cases."""
    from ..core.attribution import assess, validate_assessments
    from ..core.attribution_baselines import weighted_evidence_fusion

    if not cases:
        raise ValueError("attribution evaluation requires at least one case")
    requested = tuple(str(c).strip() for c in configurations)
    unknown = sorted(set(requested) - set(ATTRIBUTION_CONFIGURATIONS))
    if unknown:
        raise ValueError(f"Unknown attribution configuration(s): {', '.join(unknown)}")
    if len(set(requested)) != len(requested):
        raise ValueError("attribution configurations must be unique")
    if not 0.0 < conflict_threshold < support_threshold < 1.0:
        raise ValueError("thresholds must satisfy 0 < conflict < support < 1")

    case_results = {name: [] for name in requested}
    source_map = {
        "DC": ["DC"],
        "DC+BSS": ["DC", "BSS"],
        "DC+BSS+ECS": ["DC", "BSS", "ECS"],
        "DC+BSS+ECS+MAS": ["DC", "BSS", "ECS", "MAS"],
        "ACFM": ["DC", "BSS", "ECS", "EC", "MAS"],
        "WEF": None,
    }
    for index, case in enumerate(cases):
        hypotheses = list(case.get("hypotheses", []))
        evidence = case.get("evidence", {})
        expected = case.get("expected_hypothesis")
        if not hypotheses or expected not in hypotheses:
            raise ValueError(f"case {index} must contain hypotheses and a matching expected_hypothesis")
        if not isinstance(evidence, dict):
            raise ValueError(f"case {index} evidence must be a mapping")

        for name in requested:
            sources = source_map[name]
            filtered = {
                hypothesis: {
                    source: float(value)
                    for source, value in evidence.get(hypothesis, {}).items()
                    if sources is None or source in sources
                }
                for hypothesis in hypotheses
            }
            if name == "WEF":
                scored = []
                for hypothesis in hypotheses:
                    result = weighted_evidence_fusion(filtered[hypothesis], reliabilities)
                    scored.append((hypothesis, result["score"]))
                scored.sort(key=lambda row: (-row[1], row[0]))
                predicted, score = scored[0]
                case_results[name].append({
                    "case_id": str(case.get("case_id", index)),
                    "expected_hypothesis": expected,
                    "predicted_hypothesis": predicted,
                    "correct": predicted == expected,
                    "belief": float(score),
                    "plausibility": float(score),
                    "interval_width": 0.0,
                    "is_interval": False,
                })
                continue

            assessments = assess(
                hypotheses, filtered, reliabilities,
                support_threshold, conflict_threshold,
            )
            validate_assessments(assessments)
            best = assessments[0]
            case_results[name].append({
                "case_id": str(case.get("case_id", index)),
                "expected_hypothesis": expected,
                "predicted_hypothesis": best.hypothesis,
                "correct": best.hypothesis == expected,
                "belief": float(best.belief),
                "plausibility": float(best.plausibility),
                "interval_width": float(best.interval_width),
                "is_interval": True,
            })

    summaries = []
    for name in requested:
        rows = case_results[name]
        summaries.append({
            "configuration": name,
            "case_count": len(rows),
            "top1_accuracy": float(sum(row["correct"] for row in rows) / len(rows)),
            "mean_belief": float(np.mean([row["belief"] for row in rows])),
            "mean_plausibility": float(np.mean([row["plausibility"] for row in rows])),
            "mean_interval_width": float(np.mean([row["interval_width"] for row in rows])),
        })

    fingerprint_payload = {
        "cases": cases,
        "reliabilities": reliabilities,
        "support_threshold": support_threshold,
        "conflict_threshold": conflict_threshold,
        "configurations": list(requested),
        "summaries": summaries,
        "case_results": case_results,
    }
    return {
        "schema_version": ATTRIBUTION_EVALUATION_SCHEMA_VERSION,
        "status": "completed",
        "case_count": len(cases),
        "configurations": list(requested),
        "thresholds": {"support": float(support_threshold), "conflict": float(conflict_threshold)},
        "summaries": summaries,
        "cases": case_results,
        "verification_boundary": [
            "This evaluates supplied attribution cases against explicit expected hypotheses.",
            "It does not constitute SWaT, BATADAL or TON-IoT benchmark evidence.",
            "Accuracy, belief, plausibility and interval width are evaluation outputs, not calibrated probabilities or causal attribution claims.",
        ],
        "fingerprint": hashlib.sha256(_canonical_json(fingerprint_payload)).hexdigest(),
    }


def build_statistical_research_report(payload: dict[str, Any]) -> dict[str, Any]:
    """Validate a completed Day 24 envelope and package it as a research artifact."""
    if payload.get("schema_version") != "XAITA-OT-V5-REAL-EXPERIMENT-STATISTICS-1.0":
        raise ValueError("unsupported statistical result schema")
    statistics = payload.get("statistics")
    if not isinstance(statistics, dict):
        raise ValueError("statistics envelope is required")
    if statistics.get("status") != "completed":
        raise ValueError("research report requires completed statistical evidence")
    repeat_count = int(statistics.get("repeat_count", 0))
    completed = int(statistics.get("completed_matrix_count", 0))
    failed = int(statistics.get("failed_matrix_count", 0))
    observations = int(statistics.get("observation_count", 0))
    if repeat_count < 2 or completed != repeat_count or failed != 0 or observations <= 0:
        raise ValueError("research report requires complete multi-seed statistical evidence")

    summary = statistics.get("summary", [])
    paired = statistics.get("paired_detector_comparisons", [])
    if not isinstance(summary, list) or not summary:
        raise ValueError("research report requires non-empty statistical summary")
    if not isinstance(paired, list):
        raise ValueError("paired detector comparisons must be a list")

    datasets = sorted({row.get("dataset") for row in summary if row.get("dataset")})
    detectors = sorted({row.get("detector") for row in summary if row.get("detector")})
    metrics = sorted({row.get("metric") for row in summary if row.get("metric")})
    report_payload = {
        "source_schema_version": payload["schema_version"],
        "source_package_version": payload.get("package_version"),
        "source_statistics_fingerprint": statistics.get("fingerprint"),
        "seeds": statistics.get("seeds", []),
        "confidence": statistics.get("confidence"),
        "repeat_count": repeat_count,
        "observation_count": observations,
        "datasets": datasets,
        "detectors": detectors,
        "metrics": metrics,
        "summary": summary,
        "paired_detector_comparisons": paired,
        "verification_boundary": [
            "This artifact packages supplied statistical evidence; it does not create benchmark evidence.",
            "No ranking, superiority, generalization, certification, or production-acceptance claim is inferred.",
            "Real benchmark claims require authorized datasets, reproducible execution, and archival of the source statistical envelope.",
        ],
    }
    fingerprint = hashlib.sha256(_canonical_json(report_payload)).hexdigest()
    return {
        "schema_version": "XAITA-OT-V5-RESEARCH-REPORT-1.0",
        "package_version": __version__,
        "report": {
            "status": "completed",
            "source_statistics_fingerprint": statistics.get("fingerprint"),
            "fingerprint": fingerprint,
            "datasets": datasets,
            "detectors": detectors,
            "metrics": metrics,
            "seed_count": repeat_count,
            "observation_count": observations,
            "summary_count": len(summary),
            "paired_comparison_count": len(paired),
        },
        "evidence": report_payload,
    }


def write_result_envelope(payload: dict[str, Any], output: str | Path) -> Path:
    destination = Path(output)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(
        json.dumps(payload, indent=2, sort_keys=True, default=str) + "\n",
        encoding="utf-8",
    )
    return destination


EXPERIMENT_MANIFEST_SCHEMA_VERSION = "XAITA-OT-V5-EXPERIMENT-MANIFEST-1.0"


def build_experiment_manifest(
    result: dict[str, Any],
    *,
    result_sha256: str,
    result_path: str | None = None,
    software_revision: str | None = None,
) -> dict[str, Any]:
    """Build an immutable manifest for a completed experiment result artifact."""
    if not isinstance(result, dict):
        raise ValueError("experiment result must be a mapping")
    if not isinstance(result_sha256, str) or len(result_sha256) != 64:
        raise ValueError("result_sha256 must be a 64-character SHA-256 digest")
    validation = result.get("dataset_validation") or {}
    experiment = result.get("experiment") or {}
    reproducibility = result.get("reproducibility") or {}
    if not validation.get("sha256"):
        raise ValueError("result is missing dataset validation SHA-256")
    required = ("dataset", "seed", "config", "rows", "windows", "metrics")
    missing = [key for key in required if key not in experiment]
    if missing:
        raise ValueError(f"result experiment is missing required fields: {', '.join(missing)}")
    if not reproducibility.get("fingerprint"):
        raise ValueError("result is missing reproducibility fingerprint")
    split_protocol = reproducibility.get("split_protocol") or experiment["config"].get("split_protocol")
    if not split_protocol:
        raise ValueError("result is missing split protocol")
    config_sha = reproducibility.get("config_sha256") or hashlib.sha256(
        _canonical_json(experiment["config"])
    ).hexdigest()

    manifest_core = {
        "schema_version": EXPERIMENT_MANIFEST_SCHEMA_VERSION,
        "package": "xaita-ot",
        "package_version": result.get("package_version", __version__),
        "software_revision": software_revision,
        "result": {
            "path": result_path,
            "sha256": result_sha256,
            "schema_version": result.get("schema_version"),
            "reproducibility_fingerprint": reproducibility["fingerprint"],
        },
        "dataset": {
            "name": experiment["dataset"],
            "sha256": validation["sha256"],
            "validation_status": validation.get("validation_status"),
        },
        "execution": {
            "seed": int(experiment["seed"]),
            "detector": reproducibility.get("detector") or experiment["config"].get("detector"),
            "split_protocol": split_protocol,
            "config_sha256": config_sha,
        },
        "shape": {
            "rows": experiment["rows"],
            "windows": experiment["windows"],
        },
        "verification_boundary": (
            "Immutable experiment handover metadata. The manifest records artifact "
            "identity and provenance; it does not establish benchmark superiority, "
            "generalization, certification, or production OT acceptance."
        ),
    }
    manifest_core["manifest_sha256"] = hashlib.sha256(
        _canonical_json(manifest_core)
    ).hexdigest()
    return manifest_core


def write_experiment_manifest(
    result: dict[str, Any],
    *,
    result_sha256: str,
    output_path: str | Path,
    result_path: str | None = None,
    software_revision: str | None = None,
) -> Path:
    manifest = build_experiment_manifest(
        result,
        result_sha256=result_sha256,
        result_path=result_path,
        software_revision=software_revision,
    )
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(manifest, indent=2, sort_keys=True, allow_nan=False),
        encoding="utf-8",
    )
    return path
