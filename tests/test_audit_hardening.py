import json
import tarfile
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from xaita_ot.config import AppConfig

from xaita_ot.core.attribution import AttributionValidationError, assess
from xaita_ot.core.risk import score_risk
from xaita_ot.pipeline.evaluation import (
    _binary_episode_ids,
    binary_metrics,
    chronological_split,
    expected_calibration_error,
    select_threshold,
)
from xaita_ot.pipeline.preprocess import OTPreprocessor
from xaita_ot.operations.lifecycle import create_backup, prune_backups, restore_backup, verify_backup
from xaita_ot.cti.stix import to_stix_bundle


def test_episode_ids_do_not_leak_into_normal_rows():
    assert _binary_episode_ids([0, 1, 1, 0, 0, 1, 0]).tolist() == [0, 1, 1, 0, 0, 2, 0]


def test_chronological_episode_split_keeps_positive_episodes_whole():
    frame = pd.DataFrame({"timestamp": pd.date_range("2026-01-01", periods=20, freq="s"), "label": [0,0,0,0,1,1,0,0,0,1,1,1,0,0,0,0,1,1,0,0]})
    train, val, test = chronological_split(frame, 0.6, 0.2, "label", True)
    assert train.index.max() < val.index.min() < test.index.min()
    positive_episodes = _binary_episode_ids(frame["label"])
    for episode in np.unique(positive_episodes):
        if episode == 0:
            continue
        owners = [
            frame.index.intersection(part.index)[positive_episodes[frame.index.intersection(part.index)] == episode].size
            for part in (train, val, test)
        ]
        assert sum(x > 0 for x in owners) <= 1


def test_preprocessor_drops_alternate_numeric_label_aliases():
    df = pd.DataFrame({
        "label": [0, 1, 0, 1],
        "ATT_FLAG": [0, 1, 0, 1],
        "sensor_a": [1.0, 2.0, 1.1, 2.1],
        "asset": ["PLC-1"] * 4,
        "protocol": ["modbus"] * 4,
    })
    prep = OTPreprocessor(window_size=2)
    result = prep.fit_transform_train(df, "label")
    assert "ATT_FLAG" not in prep.numeric_features
    assert "sensor_a" in prep.numeric_features
    assert result.X.shape[-1] == len(prep.feature_names)


def test_metrics_reject_misaligned_or_non_finite_probabilities():
    with pytest.raises(ValueError):
        binary_metrics([0, 1], [0.5])
    with pytest.raises(ValueError):
        binary_metrics([0, 1], [0.2, float("nan")])
    with pytest.raises(ValueError):
        expected_calibration_error([0, 1], [0.2, 1.2])
    with pytest.raises(ValueError):
        select_threshold([0, 1], [0.2, float("inf")])


def test_invalid_attribution_evidence_fails_closed():
    with pytest.raises(AttributionValidationError):
        assess(["H1"], {"H1": {"DC": float("nan")}}, {"DC": 0.7})
    with pytest.raises(AttributionValidationError):
        assess([], {}, {})


def test_invalid_risk_inputs_fail_closed():
    weights = {"severity": 0.3, "operational_impact": 0.3, "criticality": 0.25, "attribution": 0.15}
    assert score_risk(0.2, 0.3, 0.4, 0.5, weights)["level"] == "LOW"
    with pytest.raises(ValueError):
        score_risk(float("nan"), 0.3, 0.4, 0.5, weights)
    with pytest.raises(ValueError):
        score_risk(0.2, 0.3, 0.4, 0.5, {**weights, "severity": 0.2})


def test_lifecycle_restore_rejects_path_traversal(tmp_path):
    root = tmp_path / "root"
    root.mkdir()
    (root / "safe.txt").write_text("safe", encoding="utf-8")
    backup = create_backup(root, tmp_path / "good.tar.gz")

    malicious = tmp_path / "bad.tar.gz"
    with tarfile.open(malicious, "w:gz") as archive:
        info = tarfile.TarInfo("xaita-backup/../../outside.txt")
        payload = b"evil"
        info.size = len(payload)
        import io
        archive.addfile(info, io.BytesIO(payload))
    with pytest.raises(ValueError):
        verify_backup(malicious)
    with pytest.raises(ValueError):
        restore_backup(malicious, tmp_path / "restore")


def test_lifecycle_restore_rejects_unexpected_archive_member(tmp_path):
    root = tmp_path / "root"
    root.mkdir()
    (root / "safe.txt").write_text("safe", encoding="utf-8")
    backup = create_backup(root, tmp_path / "good.tar.gz")
    tampered = tmp_path / "tampered.tar.gz"
    with tarfile.open(backup, "r:gz") as source, tarfile.open(tampered, "w:gz") as target:
        for member in source.getmembers():
            extracted = source.extractfile(member) if member.isfile() else None
            target.addfile(member, extracted)
        info = tarfile.TarInfo("xaita-backup/unexpected.txt")
        payload = b"unexpected"
        info.size = len(payload)
        import io
        target.addfile(info, io.BytesIO(payload))
    with pytest.raises(ValueError):
        verify_backup(tampered)


def test_stix_bundle_is_deterministic_for_fixed_cti():
    cti = {
        "incident_id": "INC-1",
        "generated_at": "2026-10-05T08:00:00Z",
        "context": [{"technique_id": "T0855", "name": "Unauthorized Command Message"}],
        "risk": {"level": "HIGH"},
        "attribution": {"hypothesis": "H1", "belief": 0.7, "plausibility": 0.9},
    }
    first = to_stix_bundle(cti)
    second = to_stix_bundle(cti)
    assert first == second
    assert first["id"].startswith("bundle--")


def test_create_backup_excludes_its_output_directory(tmp_path):
    root = tmp_path / "root"
    backup_dir = root / "artifacts" / "backups"
    backup_dir.mkdir(parents=True)
    (root / "safe.txt").write_text("safe", encoding="utf-8")
    (backup_dir / "old.tar.gz").write_bytes(b"old")
    backup = backup_dir / "new.tar.gz"
    create_backup(root, backup)
    manifest = json.loads(
        next(
            item.read_bytes().decode("utf-8")
            for item in [backup]
            if item.exists()
        ).split("xaita-backup/manifest.json", 1)[0]
    ) if False else None
    with tarfile.open(backup, "r:gz") as archive:
        names = archive.getnames()
    assert "xaita-backup/safe.txt" in names
    assert not any("artifacts/backups/" in name and name != "xaita-backup/" for name in names)


def test_phase7_attribution_preserves_hypothesis_identity():
    from pathlib import Path
    from xaita_ot.config import AppConfig
    from xaita_ot.pipeline.v3_phase7 import build_case
    root = Path(__file__).resolve().parents[1]
    cfg = AppConfig()
    cfg.model.window_size = 4
    result = build_case(root / "data/demo/swat_like.csv", "SWaT", cfg, seed=42, top_n=1)
    case = result["cases"][0]
    hypothesis_ids = {item["hypothesis"] for item in case["attribution_hypotheses"]}
    assert hypothesis_ids == {"H1", "H2", "H3"}
    assert case["acfm"]["best_hypothesis"]["hypothesis"] in hypothesis_ids


def test_config_rejects_invalid_weight_and_fraction_inputs():
    with pytest.raises(ValueError):
        AppConfig.model_validate({"risk": {"weights": {"severity": 0.4, "operational_impact": 0.3, "criticality": 0.2, "attribution": 0.2}}})
    with pytest.raises(ValueError):
        AppConfig.model_validate({"experiment": {"train_fraction": 0.9, "validation_fraction": 0.2}})



def test_assessment_validator_rejects_tampered_evidence_payload():
    from xaita_ot.core.attribution import validate_assessments

    assessments = assess(["H1"], {"H1": {"DC": 0.9}}, {"DC": 0.8})
    assessments[0].supporting[0]["value"] = 1.5
    with pytest.raises(AttributionValidationError, match="invalid attribution evidence"):
        validate_assessments(assessments)


def test_detector_rejects_unknown_architecture():
    from xaita_ot.models.trainer import Detector

    with pytest.raises(ValueError, match="unsupported detector architecture"):
        Detector(3, AppConfig().model, architecture="cnn_ltsm")


def test_detector_load_uses_weights_only_checkpoint(tmp_path):
    from xaita_ot.models.trainer import Detector

    config = AppConfig().model
    config.lstm_hidden = 4
    config.dropout = 0.0
    original = Detector(3, config, architecture="lstm")
    original.threshold = 0.37
    checkpoint = tmp_path / "weights.pt"
    original.save(checkpoint)

    restored = Detector(3, config, architecture="lstm").load(checkpoint)
    assert restored.threshold == pytest.approx(0.37)


def test_neural_trainer_copies_read_only_window_arrays():
    import warnings
    from xaita_ot.models.trainer import Detector

    config = AppConfig().model
    config.lstm_hidden = 4
    config.dropout = 0.0
    values = np.arange(4 * 3 * 2, dtype=np.float32).reshape(4, 3, 2)
    values.setflags(write=False)
    labels = np.array([0, 1, 0, 1], dtype=np.float32)
    model = Detector(2, config, architecture="lstm")

    with warnings.catch_warnings(record=True) as captured:
        warnings.simplefilter("always")
        model.fit(values, labels, epochs=1, batch_size=2, lr=1e-3)
    assert not any("NumPy array is not writable" in str(item.message) for item in captured)
    probabilities = model.predict_proba(values)
    assert probabilities.shape == (4,)
    assert np.isfinite(probabilities).all()


def test_run_started_at_reflects_start_not_completion(tmp_path, monkeypatch):
    import time
    from datetime import datetime
    from xaita_ot.pipeline import experiments

    count = 240
    labels = [(i // 20) % 2 for i in range(count)]
    path = tmp_path / "timing.csv"
    pd.DataFrame({
        "timestamp": pd.date_range("2026-01-01", periods=count, freq="s"),
        "label": labels,
        "sensor": np.linspace(0.0, 1.0, count),
    }).to_csv(path, index=False)

    config = AppConfig()
    config.model.window_size = 4

    def slow_fake_training(*args, **kwargs):
        time.sleep(0.12)
        return {"random_forest": {"f1": 0.5}}

    monkeypatch.setattr(experiments, "train_baselines", slow_fake_training)
    run = experiments.run_detection(path, "SWaT", config, seed=42, detector="random_forest")
    completed_at = time.time()
    started_at = datetime.fromisoformat(run.started_at).timestamp()
    assert started_at < completed_at - 0.08
    assert run.duration_seconds >= 0.12



def test_prune_refuses_all_deletions_when_any_backup_is_invalid(tmp_path):
    root = tmp_path / "source"
    root.mkdir()
    (root / "source.txt").write_text("recoverable source", encoding="utf-8")
    backup_dir = tmp_path / "backups"
    backup_dir.mkdir()
    older_valid = backup_dir / "xaita-backup-older.tar.gz"
    newer_invalid = backup_dir / "xaita-backup-newer.tar.gz"

    create_backup(root, older_valid)
    newer_invalid.write_bytes(b"this is not a valid gzip tar archive")
    import os
    os.utime(older_valid, (100, 100))
    os.utime(newer_invalid, (200, 200))

    with pytest.raises(ValueError, match="refusing to prune backups"):
        prune_backups(backup_dir, keep=1)

    assert older_valid.is_file(), "older verified recovery point must be preserved"
    assert newer_invalid.is_file(), "invalid candidate must never be silently deleted"


def test_prune_missing_directory_is_a_noop_and_keep_must_be_positive(tmp_path):
    assert prune_backups(tmp_path / "missing-backups", keep=3) == []
    with pytest.raises(ValueError, match="positive integer"):
        prune_backups(tmp_path, keep=0)
