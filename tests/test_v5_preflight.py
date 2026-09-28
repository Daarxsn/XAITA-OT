from pathlib import Path

from scripts.v5_preflight import run_preflight


def test_preflight_finds_repository_assets(monkeypatch):
    monkeypatch.delenv("XAITA_ENV", raising=False)
    checks = run_preflight()
    by_name = {item["check"]: item for item in checks}
    assert by_name["package_import"]["status"] == "pass"
    assert by_name["dataset configuration"]["status"] == "pass"
    assert by_name["dashboard asset"]["status"] == "pass"
    assert by_name["artifact_write"]["status"] == "pass"


def test_preflight_can_require_datasets(tmp_path, monkeypatch):
    for name in ("swat", "batadal", "ton_iot"):
        (tmp_path / name).mkdir()
        (tmp_path / name / "sample.csv").write_text("timestamp,label\n2026-01-01T00:00:00Z,0\n", encoding="utf-8")
    monkeypatch.setenv("XAITA_SWAT_PATH", str(tmp_path / "swat"))
    monkeypatch.setenv("XAITA_BATADAL_PATH", str(tmp_path / "batadal"))
    monkeypatch.setenv("XAITA_TONIOT_PATH", str(tmp_path / "ton_iot"))
    checks = run_preflight(require_datasets=True)
    dataset_checks = [item for item in checks if item["check"].startswith("dataset:")]
    assert len(dataset_checks) == 3
    assert all(item["status"] == "pass" for item in dataset_checks)
