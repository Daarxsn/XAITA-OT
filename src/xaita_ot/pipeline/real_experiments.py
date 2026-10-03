"""Reproducible real-dataset experiment execution.

This layer binds a validated researcher-supplied CSV to a detector run and
creates an auditable result envelope containing dataset identity, validation
evidence, run configuration and an immutable reproducibility fingerprint.
"""

from __future__ import annotations

from dataclasses import asdict
import hashlib
import json
from pathlib import Path
from typing import Any

from .. import __version__
from ..config import AppConfig
from .experiments import ExperimentRun, run_detection
from ..io.dataset_validation import DatasetValidationError, validate_csv


SCHEMA_VERSION = "XAITA-OT-V5-REAL-EXPERIMENT-1.0"
SUITE_SCHEMA_VERSION = "XAITA-OT-V5-REAL-EXPERIMENT-SUITE-1.0"
REAL_EXPERIMENT_DETECTORS = ("random_forest", "cnn", "lstm", "cnn_lstm")


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


def write_result_envelope(payload: dict[str, Any], output: str | Path) -> Path:
    destination = Path(output)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(
        json.dumps(payload, indent=2, sort_keys=True, default=str) + "\n",
        encoding="utf-8",
    )
    return destination
