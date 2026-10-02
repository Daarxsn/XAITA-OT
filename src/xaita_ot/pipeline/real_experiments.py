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


def write_result_envelope(payload: dict[str, Any], output: str | Path) -> Path:
    destination = Path(output)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(
        json.dumps(payload, indent=2, sort_keys=True, default=str) + "\n",
        encoding="utf-8",
    )
    return destination
