from pathlib import Path
import zipfile

from xaita_ot.io.dataset_archive import preflight_archive


def test_packaged_preflight_validates_three_families(tmp_path):
    archive = tmp_path / "datasets.zip"
    with zipfile.ZipFile(archive, "w") as z:
        z.writestr("SWaT/swat.csv", "Timestamp,Attack State,x\n2026-01-01 00:00:00,Normal,1\n2026-01-01 00:00:01,Attack,2\n")
        z.writestr("BATADAL/batadal.csv", "DATETIME,ATT_FLAG,x\n01/01/2026 00:00:00,0,1\n01/01/2026 00:00:01,1,2\n")
        z.writestr("TON-IoT/ton.csv", "date,time,label,x\n2026-01-01,00:00:00,0,1\n2026-01-01,00:00:01,1,2\n")
    report = preflight_archive(archive)
    assert report["all_ready"] is True
    assert all(item["ready"] for item in report["datasets"].values())


def test_packaged_preflight_is_non_destructive(tmp_path):
    archive = tmp_path / "datasets.zip"
    with zipfile.ZipFile(archive, "w") as z:
        z.writestr("SWaT/swat.csv", "Timestamp,Attack State,x\n2026-01-01 00:00:00,Normal,1\n")
    before = sorted(p.relative_to(tmp_path).as_posix() for p in tmp_path.rglob("*"))
    report = preflight_archive(archive)
    after = sorted(p.relative_to(tmp_path).as_posix() for p in tmp_path.rglob("*"))
    assert before == after
    assert report["all_ready"] is False


def test_prepare_dataset_accepts_root_level_dataset_file(tmp_path, monkeypatch):
    archive = tmp_path / "datasets.zip"
    with zipfile.ZipFile(archive, "w") as z:
        z.writestr("SWaT.csv", "Timestamp,Attack State,x\n2026-01-01 00:00:00,Normal,1\n2026-01-01 00:00:01,Attack,2\n")
    destination = tmp_path / "swat"
    monkeypatch.setenv("XAITA_DATASET_ARCHIVE", str(archive))
    from xaita_ot.io.dataset_archive import prepare_dataset
    root, source = prepare_dataset("SWaT", root=destination)
    assert root == destination
    assert source.startswith("archive:")
    assert (destination / "SWaT.csv").is_file()


def test_prepare_dataset_rejects_missing_archive_without_mutating_root(tmp_path, monkeypatch):
    destination = tmp_path / "swat"
    monkeypatch.setenv("XAITA_DATASET_ARCHIVE", str(tmp_path / "missing.zip"))
    from xaita_ot.io.dataset_archive import prepare_dataset
    root, source = prepare_dataset("SWaT", root=destination)
    assert root == destination
    assert source == "unavailable"
    assert destination.is_dir()
    assert not any(destination.iterdir())
