from pathlib import Path
import zipfile

import pytest

from scripts.prepare_runtime_data import (
    _archive_contains_dataset,
    _has_csv,
    _prepare_from_archive,
    safe_extract,
)


def _write_zip(path: Path, members: dict[str, str]) -> None:
    with zipfile.ZipFile(path, "w") as archive:
        for name, content in members.items():
            archive.writestr(name, content)


def test_project_archive_contains_all_dataset_families(tmp_path):
    archive = tmp_path / "datasets.zip"
    _write_zip(archive, {
        "SWaT/swat.csv": "Timestamp,Label,x\n2026-01-01,Normal,1\n",
        "BATADAL/batadal.csv": "DATETIME,ATT_FLAG,x\n01/01/2026,0,1\n",
        "TON-IoT/train_test_network.csv": "ts,label,x\n2026-01-01,0,1\n",
    })
    with zipfile.ZipFile(archive) as bundle:
        names = [item.filename for item in bundle.infolist()]
    assert _archive_contains_dataset(names, "SWaT")
    assert _archive_contains_dataset(names, "BATADAL")
    assert _archive_contains_dataset(names, "TON-IoT")


def test_dataset_specific_archive_extracts_safely(tmp_path):
    archive = tmp_path / "swat.zip"
    _write_zip(archive, {"swat.csv": "Timestamp,Label,x\n2026-01-01,Normal,1\n"})
    destination = tmp_path / "swat"
    assert _prepare_from_archive(
        archive, "SWaT", destination, expected_sha="", dataset_specific=True
    )
    assert _has_csv(destination)


def test_generic_project_archive_extracts_only_selected_dataset(tmp_path):
    archive = tmp_path / "datasets.zip"
    _write_zip(archive, {
        "SWaT/swat.csv": "Timestamp,Label,x\n2026-01-01,Normal,1\n",
        "TON-IoT/ton.csv": "ts,label,x\n2026-01-01,0,1\n",
    })
    destination = tmp_path / "swat"
    assert _prepare_from_archive(
        archive, "SWaT", destination, expected_sha="", dataset_specific=False
    )
    assert (destination / "SWaT" / "swat.csv").is_file()
    assert not (destination / "TON-IoT").exists()


def test_safe_extract_rejects_path_traversal(tmp_path):
    archive = tmp_path / "evil.zip"
    _write_zip(archive, {"../../escape.csv": "bad"})
    with pytest.raises(RuntimeError, match="Unsafe archive member"):
        safe_extract(archive, tmp_path / "out")
