"""Regression tests for correctness and safety gaps found in the repository audit."""
import asyncio
import tarfile
import zipfile
from pathlib import Path
from unittest.mock import patch

import numpy as np
import pandas as pd
import pytest

from xaita_ot.config import ModelConfig
from xaita_ot.io.dataset_archive import _download_archive, _safe_extract_selected
from xaita_ot.io.dataset_validation import _parse_timestamp, validate_csv
from xaita_ot.operations.lifecycle import create_backup, verify_backup
from xaita_ot.pipeline.swat_unlabeled import _top_deviations, analyze_swat_unlabeled


def test_swat_ambiguous_timestamp_uses_day_first():
    frame = pd.DataFrame({"Timestamp": ["02/07/2021 10:07:42 AM"]})
    parsed, _ = _parse_timestamp(frame, "SWaT", "Timestamp")
    assert parsed is not None
    assert parsed.iloc[0] == pd.Timestamp("2021-07-02 10:07:42", tz="UTC")


def test_toniot_missing_timestamp_column_is_reviewed(tmp_path):
    csv = tmp_path / "no-time.csv"
    csv.write_text("label,feature\nnormal,1\nattack,2\n", encoding="utf-8")
    result = validate_csv(csv, "TON-IoT", root=tmp_path)
    assert result.timestamp_column is None
    assert result.validation_status == "review"


def test_unknown_string_labels_are_not_counted_as_attacks(tmp_path):
    csv = tmp_path / "unknown-labels.csv"
    csv.write_text(
        "timestamp,label,feature\n"
        "2026-01-01T00:00:00Z,normal,1\n"
        "2026-01-01T00:00:01Z,unlabeled,2\n"
        "2026-01-01T00:00:02Z,attack,3\n",
        encoding="utf-8",
    )
    result = validate_csv(csv, "SWaT", root=tmp_path)
    assert result.validation_status == "review"
    assert result.normal_rows == 1
    assert result.attack_rows == 1
    assert result.unknown_label_rows == 1


def test_top_deviation_score_uses_matching_row_and_feature():
    values = np.array([[100.0, 3.0], [4.0, 9.0]])
    names, scores = _top_deviations(
        values, ["A", "B"], np.array([0.0, 0.0]), np.array([1.0, 1.0]), top_n=1
    )
    assert names == ["A", "B"]
    assert scores == [100.0, 9.0]


def test_swat_boolean_telemetry_is_supported(tmp_path):
    source = tmp_path / "input"
    source.mkdir()
    frame = pd.DataFrame({
        "Timestamp": pd.date_range("2021-07-01", periods=300, freq="s").astype(str),
        "binary_a": [bool(i % 2) for i in range(300)],
        "binary_b": [bool((i // 2) % 2) for i in range(300)],
        "sensor": [float(i % 17) for i in range(300)],
    })
    frame.to_csv(source / "telemetry.csv", index=False)
    result = analyze_swat_unlabeled(
        source, tmp_path / "output", seed=42, train_fraction=0.7,
        max_train_rows=256, n_estimators=10, top_n=2,
    )
    assert result["unique_csv_count"] == 1
    assert result["files"][0]["status"] == "completed"
    assert (tmp_path / "output" / "telemetry_scored.csv").is_file()


def test_swat_unlabeled_output_inside_input_root_is_rejected(tmp_path):
    source = tmp_path / "input"
    source.mkdir()
    (source / "telemetry.csv").write_text(
        "Timestamp,A,B\n2021-07-01T00:00:00Z,1,2\n",
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="outside the input root"):
        analyze_swat_unlabeled(source, source / "derived")


def test_backup_at_root_does_not_exclude_all_files(tmp_path):
    root = tmp_path / "root"
    root.mkdir()
    (root / "safe.txt").write_text("preserve-me", encoding="utf-8")
    backup = create_backup(root, root / "xaita-backup-root.tar.gz")
    assert verify_backup(backup)["verified"] is True
    with tarfile.open(backup, "r:gz") as archive:
        names = archive.getnames()
    assert "xaita-backup/safe.txt" in names


def test_backup_skips_symlink_files(tmp_path):
    root = tmp_path / "root"
    root.mkdir()
    secret = tmp_path / "outside-secret.txt"
    secret.write_text("secret", encoding="utf-8")
    link = root / "external.txt"
    try:
        link.symlink_to(secret)
    except (OSError, NotImplementedError):
        pytest.skip("symlink creation is unavailable")
    backup = create_backup(root, tmp_path / "xaita-backup.tar.gz")
    with tarfile.open(backup, "r:gz") as archive:
        names = archive.getnames()
    assert "xaita-backup/external.txt" not in names


def test_model_config_rejects_invalid_training_parameters():
    with pytest.raises(ValueError, match="dropout"):
        ModelConfig(dropout=1.0)
    with pytest.raises(ValueError, match="learning_rate"):
        ModelConfig(learning_rate=0.0)
    with pytest.raises(ValueError, match="window_size"):
        ModelConfig(window_size=0)


def test_archive_download_enforces_limit_while_streaming(monkeypatch):
    import xaita_ot.io.dataset_archive as archive_module

    class Response:
        headers = {}

        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def read(self, _size=-1):
            if not hasattr(self, "_sent"):
                self._sent = True
                return b"x" * 11
            return b""

    monkeypatch.setattr(archive_module, "MAX_ARCHIVE_BYTES", 10)
    with patch("xaita_ot.io.dataset_archive.urllib.request.urlopen", return_value=Response()):
        with pytest.raises(RuntimeError, match="exceeds"):
            _download_archive("https://example.invalid/dataset.zip")


def test_archive_extract_rejects_duplicate_destinations(tmp_path):
    archive = tmp_path / "duplicate.zip"
    with zipfile.ZipFile(archive, "w") as bundle:
        bundle.writestr("SWaT/a.csv", "first")
        bundle.writestr("SWaT/a.csv", "second")
    with zipfile.ZipFile(archive) as bundle:
        with pytest.raises(RuntimeError, match="Duplicate archive destination"):
            _safe_extract_selected(bundle, bundle.infolist(), tmp_path / "output")


def test_request_body_limit_middleware_rejects_streamed_oversize_body():
    from xaita_ot.api.app import RequestBodyLimitMiddleware

    chunks = iter([
        {"type": "http.request", "body": b"a" * 700, "more_body": True},
        {"type": "http.request", "body": b"b" * 400, "more_body": True},
    ])
    sent = []

    async def receive():
        return next(chunks)

    async def send(message):
        sent.append(message)

    async def app(_scope, _receive, _send):
        raise AssertionError("oversize request must not reach the app")

    middleware = RequestBodyLimitMiddleware(app, max_bytes_getter=lambda: 1024)
    scope = {
        "type": "http", "method": "POST", "headers": [],
        "path": "/v1/analyze", "query_string": b"", "scheme": "http",
        "http_version": "1.1", "server": ("localhost", 80),
        "client": ("127.0.0.1", 12345),
    }
    asyncio.run(middleware(scope, receive, send))
    assert sent[0]["type"] == "http.response.start"
    assert sent[0]["status"] == 413



def test_mas_matches_attack_technique_profile_jaccard():
    from xaita_ot.pipeline.engine import XAITAEngine

    context = [
        {"technique_id": "T0846"},
        {"technique_id": "T0855"},
        {"technique_id": "T0831"},
    ]
    # Intersection={T0846,T0855}; union={T0846,T0855,T0831,T0869}.
    score = XAITAEngine._mas(context, ["T0846", "T0855", "T0869"])
    assert score == pytest.approx(2 / 4)


def test_mas_is_unavailable_without_reference_profile():
    from xaita_ot.pipeline.engine import XAITAEngine

    assert XAITAEngine._mas([{"technique_id": "T0869"}], None) is None



def test_api_rejects_naive_event_timestamp_and_nonfinite_features():
    from xaita_ot.api.app import EventIn

    naive = {
        "event_id": "evt-naive",
        "timestamp": "2026-10-11T10:00:00",
        "detection_confidence": 0.8,
        "features": {"flow": 1.0},
    }
    with pytest.raises(ValueError, match="timezone offset"):
        EventIn.model_validate(naive)

    nonfinite = {
        **naive,
        "timestamp": "2026-10-11T10:00:00Z",
        "features": {"flow": float("nan")},
    }
    with pytest.raises(ValueError, match="finite"):
        EventIn.model_validate(nonfinite)



def test_toniot_ambiguous_date_time_pair_uses_day_first(tmp_path):
    from xaita_ot.io.adapters import adapt_dataset

    csv = tmp_path / "toniot-date-time.csv"
    csv.write_text(
        "date,time,type,feature\n"
        "02/07/2021,10:00:00,normal,1\n"
        "03/07/2021,10:00:01,attack,2\n",
        encoding="utf-8",
    )
    frame = pd.read_csv(csv)
    adapted = adapt_dataset(frame, "TON-IoT")
    assert adapted["timestamp"].iloc[0] == pd.Timestamp("2021-07-02 10:00:00", tz="UTC")
    validation = validate_csv(csv, "TON-IoT", root=tmp_path)
    assert validation.start_timestamp == "2021-07-02T10:00:00+00:00"
    assert validation.validation_status == "pass"



def test_toniot_duplicate_timestamps_do_not_pass_preflight(tmp_path):
    csv = tmp_path / "duplicate-toniot.csv"
    csv.write_text(
        "date,time,label,feature\n"
        "02/07/2021,10:00:00,0,1\n"
        "02/07/2021,10:00:00,1,2\n",
        encoding="utf-8",
    )
    result = validate_csv(csv, "TON-IoT", root=tmp_path)
    assert result.duplicate_timestamps == 1
    assert result.validation_status == "review"



def test_stix_bundle_deduplicates_repeated_attack_patterns():
    from xaita_ot.cti.stix import to_stix_bundle

    cti = {
        "incident_id": "INC-DUPLICATE-TECH",
        "generated_at": "2026-10-11T10:00:00Z",
        "context": [
            {"technique_id": "T0855", "name": "Unauthorized Command Message"},
            {"technique_id": "T0855", "name": "Unauthorized Command Message"},
        ],
        "risk": {"level": "HIGH"},
        "attribution": {"hypothesis": "H1", "belief": 0.7, "plausibility": 0.9},
    }
    bundle = to_stix_bundle(cti)
    ids = [item["id"] for item in bundle["objects"]]
    assert len(ids) == len(set(ids))
    assert sum(item["type"] == "attack-pattern" for item in bundle["objects"]) == 1


def test_stix_export_rejects_naive_generated_timestamp():
    from xaita_ot.cti.stix import to_stix_bundle

    cti = {
        "incident_id": "INC-NAIVE-TIME",
        "generated_at": "2026-10-11T10:00:00",
        "context": [],
        "risk": {"level": "HIGH"},
        "attribution": {"hypothesis": "H1", "belief": 0.7, "plausibility": 0.9},
    }
    with pytest.raises(ValueError, match="timezone-aware"):
        to_stix_bundle(cti)


def test_provenance_malformed_item_raises_domain_error():
    from xaita_ot.core.provenance import ProvenanceValidationError, validate_provenance

    with pytest.raises(ProvenanceValidationError, match="mappings"):
        validate_provenance([["not", "a", "mapping"]])


def test_explicit_empty_correlation_weights_are_rejected():
    from xaita_ot.core.btae import _validated_weights

    with pytest.raises(ValueError, match="exactly"):
        _validated_weights({})



def test_reproducibility_fingerprint_binds_implementation_hash():
    from xaita_ot.pipeline.real_experiments import (
        reproducibility_fingerprint, source_code_fingerprint,
    )

    common = {
        "dataset_sha256": "a" * 64,
        "dataset": "SWaT",
        "detector": "cnn_lstm",
        "seed": 42,
        "split_protocol": "chronological_episode_aware",
        "config": {"window_size": 8},
    }
    implementation = source_code_fingerprint()
    assert len(implementation) == 64
    assert implementation == source_code_fingerprint()
    current = reproducibility_fingerprint(**common, implementation_sha256=implementation)
    other_build = reproducibility_fingerprint(**common, implementation_sha256="b" * 64)
    assert current != other_build


def test_api_dataset_selector_rejects_ambiguous_directory(tmp_path):
    from fastapi import HTTPException
    from xaita_ot.api.app import _find_dataset_csv

    (tmp_path / "part-a.csv").write_text("timestamp,label,x\n2026-01-01T00:00:00Z,0,1\n", encoding="utf-8")
    (tmp_path / "part-b.csv").write_text("timestamp,label,x\n2026-01-01T00:00:01Z,1,2\n", encoding="utf-8")
    with pytest.raises(HTTPException) as exc:
        _find_dataset_csv(tmp_path, "SWaT")
    assert exc.value.status_code == 409
    assert "Ambiguous SWaT dataset directory" in str(exc.value.detail)


def test_api_dataset_selector_prefers_canonical_toniot_network_file(tmp_path):
    from xaita_ot.api.app import _find_dataset_csv

    preferred = tmp_path / "train_test_network.csv"
    preferred.write_text("ts,type,x\n2026-01-01T00:00:00Z,normal,1\n", encoding="utf-8")
    (tmp_path / "other.csv").write_text("ts,type,x\n2026-01-01T00:00:00Z,normal,1\n", encoding="utf-8")
    assert _find_dataset_csv(tmp_path, "TON-IoT") == preferred


def test_shared_csv_loader_parses_ambiguous_swat_timestamp_day_first(tmp_path):
    from xaita_ot.io.telemetry import load_csv

    csv = tmp_path / "ambiguous-swat-time.csv"
    csv.write_text(
        "Timestamp,Attack State,sensor\n"
        "02/07/2021 10:00:00 AM,Normal,1\n"
        "03/07/2021 10:00:01 AM,Attack,2\n",
        encoding="utf-8",
    )
    frame = load_csv(csv, sort_and_deduplicate=False)
    assert frame["timestamp"].iloc[0] == pd.Timestamp("2021-07-02 10:00:00", tz="UTC")
    assert frame["timestamp"].iloc[1] == pd.Timestamp("2021-07-03 10:00:01", tz="UTC")



def test_shared_csv_loader_combines_toniot_date_and_time_before_sorting(tmp_path):
    from xaita_ot.io.telemetry import load_csv

    csv = tmp_path / "toniot-time-pair.csv"
    csv.write_text(
        "date,time,type,feature\n"
        "02/07/2021,10:00:00,normal,1\n"
        "02/07/2021,10:00:01,attack,2\n"
        "03/07/2021,09:59:59,normal,3\n",
        encoding="utf-8",
    )
    frame = load_csv(csv)
    assert frame["timestamp"].tolist() == [
        pd.Timestamp("2021-07-02 10:00:00", tz="UTC"),
        pd.Timestamp("2021-07-02 10:00:01", tz="UTC"),
        pd.Timestamp("2021-07-03 09:59:59", tz="UTC"),
    ]


def test_archive_discovery_matches_dotted_swat_a8_root():
    from xaita_ot.io.dataset_archive import _matches_name

    assert _matches_name(
        "SWaT.A8_June 2021/_20210622_093704/20210622_093704.csv",
        "SWaT",
    )
    assert not _matches_name("not-swatting/data.csv", "SWaT")


def test_stix_attack_pattern_uses_canonical_mitre_url():
    from xaita_ot.cti.stix import to_stix_bundle

    cti = {
        "incident_id": "INC-URL",
        "generated_at": "2026-10-11T10:00:00Z",
        "context": [{"technique_id": "T0855", "name": "Unauthorized Command Message"}],
        "risk": {"level": "HIGH"},
        "attribution": {"hypothesis": "H1", "belief": 0.7, "plausibility": 0.9},
    }
    bundle = to_stix_bundle(cti)
    attack_pattern = next(item for item in bundle["objects"] if item["type"] == "attack-pattern")
    assert attack_pattern["external_references"][0]["url"] == "https://attack.mitre.org/techniques/T0855/"


def test_stix_rejects_invalid_attack_pattern_id():
    from xaita_ot.cti.stix import to_stix_bundle

    cti = {
        "incident_id": "INC-BAD-ID",
        "generated_at": "2026-10-11T10:00:00Z",
        "context": [{"technique_id": "", "name": "Unknown technique"}],
        "risk": {"level": "HIGH"},
        "attribution": {"hypothesis": "H1", "belief": 0.7, "plausibility": 0.9},
    }
    with pytest.raises(ValueError, match="Invalid ATT&CK technique ID"):
        to_stix_bundle(cti)



def test_reproducibility_fingerprint_rejects_nonfinite_config():
    from xaita_ot.pipeline.real_experiments import reproducibility_fingerprint

    with pytest.raises(ValueError):
        reproducibility_fingerprint(
            dataset_sha256="a" * 64,
            dataset="SWaT",
            detector="cnn_lstm",
            seed=42,
            split_protocol="chronological_episode_aware",
            config={"invalid_threshold": float("nan")},
            implementation_sha256="b" * 64,
        )


def test_backup_verification_rejects_duplicate_normalized_paths(tmp_path):
    import io
    import tarfile
    from xaita_ot.operations.lifecycle import _validate_archive_members

    archive_path = tmp_path / "case-collision.tar.gz"
    payload = b"sample"
    manifest = {"files": [{"path": "a.txt", "sha256": "0" * 64, "size": len(payload)}]}
    with tarfile.open(archive_path, "w:gz") as archive:
        root = tarfile.TarInfo("xaita-backup")
        root.type = tarfile.DIRTYPE
        archive.addfile(root)
        data = b"{}"
        item = tarfile.TarInfo("xaita-backup/manifest.json")
        item.size = len(data)
        archive.addfile(item, io.BytesIO(data))
        for name in ("xaita-backup/a.txt", "xaita-backup/A.TXT"):
            item = tarfile.TarInfo(name)
            item.size = len(payload)
            archive.addfile(item, io.BytesIO(payload))
    with tarfile.open(archive_path, "r:gz") as archive:
        with pytest.raises(ValueError, match="duplicate normalized archive path"):
            _validate_archive_members(archive, manifest)


def test_attack_technique_profiles_require_unique_valid_ids():
    from xaita_ot.config import AttributionConfig

    config = AttributionConfig(attack_technique_profiles={
        "H1": ["T0846", "T0855.001"],
    })
    assert config.attack_technique_profiles["H1"] == ["T0846", "T0855.001"]
    with pytest.raises(ValueError, match="invalid ATT&CK technique ID"):
        AttributionConfig(attack_technique_profiles={"H1": ["not-a-technique"]})
    with pytest.raises(ValueError, match="duplicate technique IDs"):
        AttributionConfig(attack_technique_profiles={"H1": ["T0846", "T0846"]})


def test_legacy_ec_attribution_reliability_is_migrated_to_eCS_only():
    from xaita_ot.config import AttributionConfig

    cfg = AttributionConfig(reliability={
        "DC": 0.7, "BSS": 0.8, "ECS": 0.85, "EC": 0.8, "MAS": 0.65
    })
    assert set(cfg.reliability) == {"DC", "BSS", "ECS", "MAS"}
