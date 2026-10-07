from pathlib import Path
import zipfile

from scripts.prepare_runtime_data import preflight_archive


def _zip(path: Path, members: dict[str, str]) -> None:
    with zipfile.ZipFile(path, "w") as z:
        for name, body in members.items():
            z.writestr(name, body)


def test_preflight_reports_missing_dataset_families(tmp_path):
    archive = tmp_path / "datasets.zip"
    _zip(archive, {"SWaT/swat.csv": "Timestamp,Attack State,x\n2026-01-01 00:00:00,Normal,1\n"})
    report = preflight_archive(archive)
    assert report["all_ready"] is False
    assert report["datasets"]["SWaT"]["present"] is True
    assert report["datasets"]["BATADAL"]["present"] is False
    assert report["datasets"]["TON-IoT"]["present"] is False
    assert "sha256" in report["archive"]


def test_preflight_validates_all_three_without_touching_worktree(tmp_path):
    archive = tmp_path / "datasets.zip"
    _zip(archive, {
        "SWaT/swat.csv": "Timestamp,Attack State,x\n2026-01-01 00:00:00,Normal,1\n2026-01-01 00:00:01,Attack,2\n",
        "BATADAL/batadal.csv": "DATETIME,ATT_FLAG,x\n01/01/2026 00:00:00,0,1\n01/01/2026 00:00:01,1,2\n",
        "TON-IoT/ton.csv": "date,time,label,x\n2026-01-01,00:00:00,0,1\n2026-01-01,00:00:01,1,2\n",
    })
    before = {p for p in tmp_path.rglob("*")}
    report = preflight_archive(archive)
    after = {p for p in tmp_path.rglob("*")}
    assert before == after
    assert report["all_ready"] is True
    assert all(item["ready"] for item in report["datasets"].values())


def test_preflight_report_is_deterministic_for_same_archive(tmp_path):
    archive = tmp_path / "datasets.zip"
    _zip(archive, {"SWaT/swat.csv": "Timestamp,Attack State,x\n2026-01-01 00:00:00,Normal,1\n"})
    first = preflight_archive(archive)
    second = preflight_archive(archive)
    assert first["archive"]["sha256"] == second["archive"]["sha256"]
    assert first["datasets"] == second["datasets"]
