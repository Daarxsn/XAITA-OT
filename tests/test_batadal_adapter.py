from pathlib import Path

import pandas as pd
import pytest

from xaita_ot.datasets.batadal import BATADALDatasetAdapter, BATADALValidationError


def write_csv(root: Path, subset: str, filename: str, frame: pd.DataFrame) -> None:
    folder = root / subset
    folder.mkdir(parents=True)
    frame.to_csv(folder / filename, index=False)


def test_batadal_adapter_strips_column_names_and_preserves_unknown_labels(tmp_path: Path) -> None:
    timestamps = pd.date_range("2020-01-01", periods=3, freq="h")
    train = pd.DataFrame({" DATETIME": timestamps, " L_T1": [1.0, 2.0, 3.0], " ATT_FLAG": [0, 0, 0]})
    train2 = pd.DataFrame({" DATETIME": timestamps, " L_T1": [1.0, 2.0, 3.0], " ATT_FLAG": [1, -999, 0]})
    test = pd.DataFrame({"DATETIME": timestamps, "L_T1": [1.0, 2.0, 3.0]})
    write_csv(tmp_path, "train_1", "BATADAL_dataset03.csv", train)
    write_csv(tmp_path, "train_2", "BATADAL_dataset04.csv", train2)
    write_csv(tmp_path, "test", "BATADAL_test_dataset.csv", test)

    adapter = BATADALDatasetAdapter(tmp_path)
    loaded = adapter.load_all()

    assert "DATETIME" in loaded["train_2"].frame.columns
    assert "ATT_FLAG" in loaded["train_2"].frame.columns
    assert -999 in loaded["train_2"].frame["ATT_FLAG"].tolist()
    assert loaded["test"].label_column is None
    assert adapter.manifest()["dataset"] == "BATADAL"


def test_batadal_adapter_rejects_duplicate_timestamps(tmp_path: Path) -> None:
    timestamps = ["2020-01-01 00:00:00", "2020-01-01 00:00:00"]
    frame = pd.DataFrame({"DATETIME": timestamps, "L_T1": [1.0, 2.0]})
    write_csv(tmp_path, "test", "BATADAL_test_dataset.csv", frame)

    adapter = BATADALDatasetAdapter(tmp_path)
    with pytest.raises(BATADALValidationError, match="duplicate timestamps"):
        adapter.load("test")
