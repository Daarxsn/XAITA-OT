from pathlib import Path

import pandas as pd
import pytest

from xaita_ot.config import AppConfig
from xaita_ot.io.dataset_validation import DatasetValidationError, validate_csv
from xaita_ot.pipeline.real_experiments import (
    SCHEMA_VERSION,
    build_result_envelope,
    reproducibility_fingerprint,
    run_real_experiment,
)


def _write_valid_swat(path: Path) -> Path:
    rows = [
        "Timestamp,Attack State,sensor_a,sensor_b,asset,protocol\n",
        "2026-01-01 00:00:00,Normal,1,2,PLC-1,modbus\n",
        "2026-01-01 00:00:01,Normal,1.1,2.1,PLC-1,modbus\n",
        "2026-01-01 00:00:02,Attack,4,6,PLC-1,modbus\n",
        "2026-01-01 00:00:03,Attack,4.5,6.5,PLC-1,modbus\n",
        "2026-01-01 00:00:04,Normal,1.2,2.2,PLC-1,modbus\n",
        "2026-01-01 00:00:05,Normal,1.3,2.3,PLC-1,modbus\n",
    ]
    path.write_text("".join(rows), encoding="utf-8")
    return path


class _FakeValidation:
    sha256 = "a" * 64

    def as_dict(self):
        return {"dataset": "SWaT", "sha256": self.sha256, "validation_status": "pass"}


class _FakeRun:
    dataset = "SWaT"
    seed = 42
    experiment_id = "SWaT-cnn_lstm-42-test"
    started_at = "2026-01-01T00:00:00Z"
    duration_seconds = 1.25
    config = {
        "detector": "cnn_lstm",
        "split_protocol": "chronological_episode_aware",
    }
    rows = {"train": 4, "validation": 1, "test": 1}
    windows = {"train": 1, "validation": 1, "test": 1}
    metrics = {"cnn_lstm": {"f1": 1.0}}


def test_reproducibility_fingerprint_is_deterministic():
    kwargs = {
        "dataset_sha256": "b" * 64,
        "dataset": "SWaT",
        "detector": "cnn_lstm",
        "seed": 42,
        "split_protocol": "chronological_episode_aware",
        "config": {"window": 32, "epochs": 1},
    }
    first = reproducibility_fingerprint(**kwargs)
    second = reproducibility_fingerprint(**kwargs)
    changed = reproducibility_fingerprint(**{**kwargs, "seed": 43})
    assert first == second
    assert first != changed
    assert len(first) == 64


def test_result_envelope_contains_audit_identity():
    payload = build_result_envelope(_FakeValidation(), _FakeRun(), config=AppConfig())
    assert payload["schema_version"] == SCHEMA_VERSION
    assert payload["dataset_validation"]["sha256"] == "a" * 64
    assert payload["experiment"]["experiment_id"] == "SWaT-cnn_lstm-42-test"
    assert payload["reproducibility"]["seed"] == 42
    assert payload["reproducibility"]["detector"] == "cnn_lstm"
    assert payload["reproducibility"]["split_protocol"] == "chronological_episode_aware"
    assert len(payload["reproducibility"]["fingerprint"]) == 64


def test_real_experiment_blocks_unvalidated_input(tmp_path, monkeypatch):
    bad = tmp_path / "bad.csv"
    bad.write_text(
        "Timestamp,Attack State,sensor\n"
        "2026-01-01 00:00:01,Normal,\n"
        "not-a-time,Attack,2\n",
        encoding="utf-8",
    )
    with pytest.raises(DatasetValidationError, match="blocked until the dataset passes validation"):
        run_real_experiment(
            csv_path=bad,
            dataset="SWaT",
            config=AppConfig(),
            detector="random_forest",
            seed=42,
            dataset_root=tmp_path,
        )


def test_real_experiment_acceptance_path_persists_validation_then_runs(tmp_path, monkeypatch):
    path = _write_valid_swat(tmp_path / "swat.csv")
    validation = validate_csv(path, "SWaT", tmp_path)
    assert validation.validation_status == "pass"

    def fake_run_detection(csv_path, dataset, config, seed=None, detector=None):
        from xaita_ot.pipeline.experiments import ExperimentRun
        return ExperimentRun(
            experiment_id="SWaT-random_forest-42-test",
            dataset=dataset,
            seed=seed or 42,
            started_at="2026-01-01T00:00:00+00:00",
            duration_seconds=0.01,
            config={
                "detector": detector,
                "split_protocol": "chronological_episode_aware",
            },
            rows={"train": 4, "validation": 1, "test": 1},
            windows={"train": 1, "validation": 1, "test": 1},
            metrics={detector: {"f1": 1.0}},
        )

    monkeypatch.setattr(
        "xaita_ot.pipeline.real_experiments.run_detection",
        fake_run_detection,
    )
    payload = run_real_experiment(
        csv_path=path,
        dataset="SWaT",
        config=AppConfig(),
        detector="random_forest",
        seed=42,
        dataset_root=tmp_path,
    )
    assert payload["dataset_validation"]["validation_status"] == "pass"
    assert payload["experiment"]["dataset"] == "SWaT"
    assert payload["experiment"]["seed"] == 42
    assert payload["reproducibility"]["detector"] == "random_forest"
