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


def _fake_run():
    from xaita_ot.pipeline.experiments import ExperimentRun
    return ExperimentRun(
        experiment_id="SWaT-cnn_lstm-42-test",
        dataset="SWaT",
        seed=42,
        started_at="2026-01-01T00:00:00Z",
        duration_seconds=1.25,
        config={
            "detector": "cnn_lstm",
            "split_protocol": "chronological_episode_aware",
        },
        rows={"train": 4, "validation": 1, "test": 1},
        windows={"train": 1, "validation": 1, "test": 1},
        metrics={"cnn_lstm": {"f1": 1.0}},
    )


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
    payload = build_result_envelope(_FakeValidation(), _fake_run(), config=AppConfig())
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


def test_real_experiment_suite_runs_all_four_detectors(tmp_path, monkeypatch):
    from xaita_ot.pipeline.real_experiments import run_real_experiment_suite
    path = _write_valid_swat(tmp_path / "swat.csv")
    calls = []
    def fake_run_detection(csv_path, dataset, config, seed=None, detector=None):
        from xaita_ot.pipeline.experiments import ExperimentRun
        calls.append(detector)
        return ExperimentRun(
            experiment_id=f"SWaT-{detector}-42-test", dataset=dataset, seed=seed or 42,
            started_at="2026-01-01T00:00:00+00:00", duration_seconds=0.01,
            config={"detector": detector, "split_protocol": "chronological_episode_aware"},
            rows={"train": 4, "validation": 1, "test": 1},
            windows={"train": 1, "validation": 1, "test": 1},
            metrics={detector: {"f1": 1.0}},
        )
    monkeypatch.setattr("xaita_ot.pipeline.real_experiments.run_detection", fake_run_detection)
    payload = run_real_experiment_suite(csv_path=path, dataset="SWaT", config=AppConfig(), seed=42, dataset_root=tmp_path)
    assert calls == ["random_forest", "cnn", "lstm", "cnn_lstm"]
    assert payload["suite"]["status"] == "completed"
    assert payload["suite"]["completed_count"] == 4
    assert payload["suite"]["failed_count"] == 0
    assert len(payload["suite"]["fingerprint"]) == 64


def test_real_experiment_suite_blocks_invalid_input(tmp_path):
    from xaita_ot.pipeline.real_experiments import run_real_experiment_suite
    bad = tmp_path / "bad.csv"
    bad.write_text("Timestamp,Attack State,sensor\n2026-01-01 00:00:01,Normal,\nnot-a-time,Attack,2\n", encoding="utf-8")
    with pytest.raises(DatasetValidationError, match="suite execution is blocked"):
        run_real_experiment_suite(csv_path=bad, dataset="SWaT", config=AppConfig(), seed=42, dataset_root=tmp_path)


def test_real_experiment_suite_retains_detector_failure(tmp_path, monkeypatch):
    from xaita_ot.pipeline.real_experiments import run_real_experiment_suite
    path = _write_valid_swat(tmp_path / "swat.csv")
    def fake_run_detection(csv_path, dataset, config, seed=None, detector=None):
        if detector == "lstm":
            raise RuntimeError("bounded training failure")
        return _fake_run()
    monkeypatch.setattr("xaita_ot.pipeline.real_experiments.run_detection", fake_run_detection)
    payload = run_real_experiment_suite(csv_path=path, dataset="SWaT", config=AppConfig(), seed=42, dataset_root=tmp_path)
    assert payload["suite"]["status"] == "failed"
    assert payload["suite"]["completed_count"] == 3
    assert payload["suite"]["failed_detectors"] == ["lstm"]


def test_real_experiment_matrix_runs_datasets_in_deterministic_order(tmp_path, monkeypatch):
    from xaita_ot.pipeline.real_experiments import run_real_experiment_matrix

    paths = {
        "SWaT": tmp_path / "swat.csv",
        "BATADAL": tmp_path / "batadal.csv",
        "TON-IoT": tmp_path / "toniot.csv",
    }
    calls = []

    def fake_suite(csv_path, dataset, config, seed=None, detectors=()):
        calls.append((dataset, tuple(detectors)))
        return {
            "suite": {
                "status": "completed",
                "completed_detectors": list(detectors),
                "failed_detectors": [],
            }
        }

    monkeypatch.setattr(
        "xaita_ot.pipeline.real_experiments.run_real_experiment_suite",
        fake_suite,
    )
    payload = run_real_experiment_matrix(csv_paths=paths, config=AppConfig(), seed=42)
    assert calls == [
        ("SWaT", ("random_forest", "cnn", "lstm", "cnn_lstm")),
        ("BATADAL", ("random_forest", "cnn", "lstm", "cnn_lstm")),
        ("TON-IoT", ("random_forest", "cnn", "lstm", "cnn_lstm")),
    ]
    assert payload["matrix"]["status"] == "completed"
    assert payload["matrix"]["completed_dataset_count"] == 3
    assert payload["matrix"]["failed_dataset_count"] == 0
    assert len(payload["matrix"]["fingerprint"]) == 64


def test_real_experiment_matrix_retains_dataset_failure(tmp_path, monkeypatch):
    from xaita_ot.pipeline.real_experiments import run_real_experiment_matrix

    paths = {
        "SWaT": tmp_path / "swat.csv",
        "BATADAL": tmp_path / "batadal.csv",
        "TON-IoT": tmp_path / "toniot.csv",
    }

    def fake_suite(csv_path, dataset, config, seed=None, detectors=()):
        if dataset == "BATADAL":
            raise DatasetValidationError("BATADAL validation blocked")
        return {
            "suite": {
                "status": "completed",
                "completed_detectors": list(detectors),
                "failed_detectors": [],
            }
        }

    monkeypatch.setattr(
        "xaita_ot.pipeline.real_experiments.run_real_experiment_suite",
        fake_suite,
    )
    payload = run_real_experiment_matrix(csv_paths=paths, config=AppConfig(), seed=42)
    assert payload["matrix"]["status"] == "failed"
    assert payload["matrix"]["completed_dataset_count"] == 2
    assert payload["matrix"]["failed_dataset_count"] == 1
    assert payload["datasets"][1]["dataset"] == "BATADAL"
    assert payload["datasets"][1]["error"]["type"] == "DatasetValidationError"


def test_real_experiment_statistical_matrix_requires_repeated_seeds(monkeypatch):
    from xaita_ot.pipeline.real_experiments import run_real_experiment_statistical_matrix
    with pytest.raises(ValueError, match="at least two seeds"):
        run_real_experiment_statistical_matrix(
            csv_paths={"SWaT": "a", "BATADAL": "b", "TON-IoT": "c"},
            config=AppConfig(),
            seeds=[42],
        )


def test_real_experiment_statistical_matrix_aggregates_metrics(monkeypatch):
    from xaita_ot.pipeline.real_experiments import run_real_experiment_statistical_matrix

    def fake_matrix(csv_paths, config, seed, detectors, datasets):
        runs = []
        for dataset in datasets:
            detector_runs = []
            for detector in detectors:
                detector_runs.append({
                    "status": "completed",
                    "detector": detector,
                    "result": {
                        "experiment": {
                            "metrics": {detector: {"precision": 0.8 + seed / 1000.0, "f1": 0.7 + seed / 1000.0}}
                        }
                    },
                })
            runs.append({
                "status": "completed",
                "dataset": dataset,
                "result": {"runs": detector_runs},
            })
        return {"matrix": {"status": "completed"}, "datasets": runs}

    monkeypatch.setattr(
        "xaita_ot.pipeline.real_experiments.run_real_experiment_matrix",
        fake_matrix,
    )
    result = run_real_experiment_statistical_matrix(
        csv_paths={"SWaT": "a", "BATADAL": "b", "TON-IoT": "c"},
        config=AppConfig(),
        seeds=[42, 43, 44],
        confidence=0.95,
    )
    assert result["statistics"]["status"] == "completed"
    assert result["statistics"]["repeat_count"] == 3
    assert result["statistics"]["observation_count"] == 72
    assert len(result["statistics"]["summary"]) == 24
    assert len(result["statistics"]["paired_detector_comparisons"]) == 18
    assert all(row["n"] == 3 for row in result["statistics"]["summary"])
    assert all(row["ci_low"] <= row["mean"] <= row["ci_high"] for row in result["statistics"]["summary"])


def test_build_statistical_research_report_requires_completed_evidence():
    from xaita_ot.pipeline.real_experiments import build_statistical_research_report
    with pytest.raises(ValueError, match="completed statistical evidence"):
        build_statistical_research_report({
            "schema_version": "XAITA-OT-V5-REAL-EXPERIMENT-STATISTICS-1.0",
            "statistics": {"status": "failed"},
        })


def test_build_statistical_research_report_is_provenance_bound():
    from xaita_ot.pipeline.real_experiments import build_statistical_research_report
    payload = {
        "schema_version": "XAITA-OT-V5-REAL-EXPERIMENT-STATISTICS-1.0",
        "package_version": "0.5.1",
        "statistics": {
            "status": "completed",
            "repeat_count": 3,
            "completed_matrix_count": 3,
            "failed_matrix_count": 0,
            "observation_count": 6,
            "seeds": [42, 43, 44],
            "confidence": 0.95,
            "fingerprint": "a" * 64,
            "summary": [
                {"dataset": "SWaT", "detector": "cnn", "metric": "f1", "n": 3,
                 "mean": 0.8, "std": 0.01, "ci_low": 0.79, "ci_high": 0.81, "confidence": 0.95}
            ],
            "paired_detector_comparisons": [],
        },
    }
    report = build_statistical_research_report(payload)
    assert report["schema_version"] == "XAITA-OT-V5-RESEARCH-REPORT-1.0"
    assert report["report"]["source_statistics_fingerprint"] == "a" * 64
    assert report["report"]["seed_count"] == 3
    assert len(report["report"]["fingerprint"]) == 64
    assert "benchmark evidence" in report["evidence"]["verification_boundary"][0]


def test_attribution_evaluation_is_deterministic_and_explicit():
    from xaita_ot.pipeline.real_experiments import evaluate_attribution_cases
    cases = [{
        "case_id": "case-1",
        "hypotheses": ["H1", "H2"],
        "expected_hypothesis": "H1",
        "evidence": {
            "H1": {"DC": 0.95, "BSS": 0.90, "ECS": 0.80, "MAS": 0.85},
            "H2": {"DC": 0.20, "BSS": 0.30, "ECS": 0.40, "MAS": 0.35},
        },
    }]
    reliabilities = {"DC": 0.7, "BSS": 0.8, "ECS": 0.85, "MAS": 0.65}
    first = evaluate_attribution_cases(cases, reliabilities=reliabilities)
    second = evaluate_attribution_cases(cases, reliabilities=reliabilities)
    assert first["fingerprint"] == second["fingerprint"]
    assert first["status"] == "completed"
    assert first["case_count"] == 1
    assert [x["configuration"] for x in first["summaries"]] == [
        "DC", "DC+BSS", "DC+BSS+ECS", "DC+BSS+ECS+MAS", "ACFM", "WEF"
    ]
    assert all(0.0 <= row["top1_accuracy"] <= 1.0 for row in first["summaries"])


def test_attribution_evaluation_rejects_missing_expected_hypothesis():
    from xaita_ot.pipeline.real_experiments import evaluate_attribution_cases
    with pytest.raises(ValueError, match="expected_hypothesis"):
        evaluate_attribution_cases(
            [{"hypotheses": ["H1"], "evidence": {"H1": {"DC": 0.9}}}],
            reliabilities={"DC": 0.7},
        )


def test_experiment_manifest_is_deterministic_and_binds_result_identity(tmp_path):
    from xaita_ot.pipeline.real_experiments import build_experiment_manifest
    result = {
        "schema_version": "XAITA-OT-V5-REAL-EXPERIMENT-1.0",
        "package_version": "0.5.1",
        "dataset_validation": {"sha256": "a" * 64, "validation_status": "pass"},
        "experiment": {
            "dataset": "SWaT", "seed": 42,
            "config": {"detector": "cnn", "split_protocol": "chronological_episode_aware"},
            "rows": {"train": 10, "validation": 5, "test": 5},
            "windows": {"train": 8, "validation": 3, "test": 3},
            "metrics": {"cnn": {"f1": 0.9}},
        },
        "reproducibility": {
            "fingerprint": "b" * 64,
            "detector": "cnn",
            "split_protocol": "chronological_episode_aware",
            "config_sha256": "c" * 64,
        },
    }
    first = build_experiment_manifest(result, result_sha256="d" * 64, result_path="result.json", software_revision="e" * 40)
    second = build_experiment_manifest(result, result_sha256="d" * 64, result_path="result.json", software_revision="e" * 40)
    assert first == second
    assert len(first["manifest_sha256"]) == 64
    assert first["result"]["sha256"] == "d" * 64
    assert first["dataset"]["sha256"] == "a" * 64


def test_experiment_manifest_rejects_incomplete_result():
    from xaita_ot.pipeline.real_experiments import build_experiment_manifest
    with pytest.raises(ValueError, match="reproducibility fingerprint"):
        build_experiment_manifest(
            {"dataset_validation": {"sha256": "a" * 64}, "experiment": {}},
            result_sha256="d" * 64,
        )
