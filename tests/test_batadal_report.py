import json
from pathlib import Path

from scripts.generate_batadal_validation_report import build_report


def test_report_fails_closed_when_raw_datasets_are_missing(tmp_path: Path):
    report = build_report(tmp_path / "batadal")

    assert report["status"] == "FAIL"
    assert report["benchmark_gate"] == "CLOSED"
    assert report["checks"][0]["name"] == "raw_files_load_and_validate"
    assert report["checks"][0]["status"] == "FAIL"


def test_report_is_json_serializable_for_artifact_storage(tmp_path: Path):
    report = build_report(tmp_path / "batadal")
    encoded = json.dumps(report)
    decoded = json.loads(encoded)

    assert decoded["report"] == "BATADAL validation"
    assert decoded["benchmark_gate"] == "CLOSED"
