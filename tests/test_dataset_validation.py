from pathlib import Path

from xaita_ot.io.dataset_validation import (
    DatasetValidationError,
    build_manifest,
    canonical_dataset,
    validate_csv,
)


def _write(path: Path, content: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return path


def test_canonical_dataset_aliases():
    assert canonical_dataset("swat") == "SWaT"
    assert canonical_dataset("TON_IoT") == "TON-IoT"
    assert canonical_dataset("batadal") == "BATADAL"


def test_validate_swat_attack_state(tmp_path):
    path = _write(
        tmp_path / "swat.csv",
        "Timestamp,Attack State,flow\n"
        "2026-01-01 00:00:00,Normal,1.0\n"
        "2026-01-01 00:00:01,Attack,2.0\n"
        "2026-01-01 00:00:02,Normal,1.2\n",
    )
    result = validate_csv(path, "SWaT", tmp_path, chunksize=2)
    assert result.validation_status == "pass"
    assert result.timestamp_column == "Timestamp"
    assert result.label_column == "Attack State"
    assert result.attack_rows == 1
    assert result.normal_rows == 2
    assert len(result.sha256) == 64


def test_validate_batadal_day_first_timestamps(tmp_path):
    path = _write(
        tmp_path / "batadal.csv",
        "DATETIME,ATT_FLAG,SENSOR_A\n"
        "01/01/2026 00:00,0,1.0\n"
        "01/01/2026 01:00,1,1.2\n"
        "01/01/2026 02:00,0,1.1\n",
    )
    result = validate_csv(path, "BATADAL", tmp_path)
    assert result.validation_status == "pass"
    assert result.timestamp_column == "DATETIME"
    assert result.label_column == "ATT_FLAG"
    assert result.attack_rows == 1


def test_validate_toniot_date_time_pair(tmp_path):
    path = _write(
        tmp_path / "Train_Test_Network.csv",
        "date,time,label,feature\n"
        "01-Jan-26,00:00:00,0,1.0\n"
        "01-Jan-26,00:00:01,1,2.0\n"
        "01-Jan-26,00:00:02,0,1.1\n",
    )
    result = validate_csv(path, "TON-IoT", tmp_path)
    assert result.validation_status == "pass"
    assert result.timestamp_column == "date + time"
    assert result.label_column == "label"
    assert result.start_timestamp is not None
    assert result.end_timestamp is not None


def test_manifest_contains_file_identity_and_digest(tmp_path):
    _write(
        tmp_path / "a.csv",
        "timestamp,label,x\n2026-01-01T00:00:00Z,0,1\n2026-01-01T00:00:01Z,1,2\n",
    )
    _write(
        tmp_path / "nested" / "b.csv",
        "timestamp,label,x\n2026-01-01T00:00:02Z,0,3\n2026-01-01T00:00:03Z,0,4\n",
    )
    first = build_manifest("SWaT", tmp_path)
    second = build_manifest("SWaT", tmp_path)
    assert first["benchmark_validation_ready"] is True
    assert first["file_count"] == 2
    assert first["validated_files"] == 2
    assert first["review_files"] == 0
    assert len(first["manifest_sha256"]) == 64
    assert first["manifest_sha256"] == second["manifest_sha256"]
    assert [item["path"] for item in first["files"]] == ["a.csv", "nested/b.csv"]
    assert all(len(item["sha256"]) == 64 for item in first["files"])


def test_invalid_or_missing_data_is_reviewed_not_silent(tmp_path):
    path = _write(
        tmp_path / "bad.csv",
        "Timestamp,Attack State,flow\n"
        "2026-01-01 00:00:02,Normal,\n"
        "not-a-time,Attack,2.0\n"
        "2026-01-01 00:00:01,Normal,1.0\n",
    )
    result = validate_csv(path, "SWaT", tmp_path)
    assert result.validation_status == "review"
    assert result.invalid_timestamps == 1
    assert result.missing_cells == 1
    assert result.monotonic_timestamp_order is False


def test_missing_dataset_root_has_actionable_error(tmp_path):
    try:
        validate_csv(tmp_path / "missing.csv", "SWaT")
    except DatasetValidationError as exc:
        assert "CSV file not found" in str(exc)
    else:  # pragma: no cover
        raise AssertionError("expected DatasetValidationError")
