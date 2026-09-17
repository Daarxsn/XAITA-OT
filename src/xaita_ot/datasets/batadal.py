"""BATADAL dataset loading and validation."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import hashlib
import json

import pandas as pd

from .batadal_attacks import BATADALAttackInterval, apply_attack_intervals, load_attack_intervals


class BATADALValidationError(ValueError):
    """Raised when a BATADAL input violates an ingestion invariant."""


@dataclass(frozen=True)
class BATADALFrame:
    """A validated BATADAL dataframe and its source metadata."""

    subset: str
    path: Path
    frame: pd.DataFrame
    timestamp_column: str
    label_column: str | None


class BATADALDatasetAdapter:
    """Load and validate BATADAL train/test CSV files."""

    TIMESTAMP_ALIASES = ("DATETIME", "timestamp", "Timestamp", "time", "ts")
    LABEL_ALIASES = ("ATT_FLAG", "label", "Label", "attack", "Attack", "attack_label")

    def __init__(self, root: str | Path):
        self.root = Path(root)

    @staticmethod
    def sha256(path: str | Path, chunk_size: int = 1024 * 1024) -> str:
        digest = hashlib.sha256()
        with Path(path).open("rb") as handle:
            for chunk in iter(lambda: handle.read(chunk_size), b""):
                digest.update(chunk)
        return digest.hexdigest()

    @staticmethod
    def _resolve_column(columns: pd.Index, aliases: tuple[str, ...], required: bool) -> str | None:
        normalized = {str(column).strip().lower(): str(column) for column in columns}
        for alias in aliases:
            match = normalized.get(alias.lower())
            if match is not None:
                return match
        if required:
            raise BATADALValidationError(
                f"Missing required column; expected one of {', '.join(aliases)}"
            )
        return None

    @staticmethod
    def _validate_frame(frame: pd.DataFrame, path: Path, subset: str) -> tuple[str, str | None]:
        if frame.empty:
            raise BATADALValidationError(f"{subset}: {path} is empty")

        frame.columns = [str(column).strip() for column in frame.columns]
        if frame.columns.duplicated().any():
            duplicates = frame.columns[frame.columns.duplicated()].tolist()
            raise BATADALValidationError(f"{subset}: duplicate columns: {duplicates}")

        timestamp_column = BATADALDatasetAdapter._resolve_column(
            frame.columns, BATADALDatasetAdapter.TIMESTAMP_ALIASES, required=True
        )
        label_column = BATADALDatasetAdapter._resolve_column(
            frame.columns, BATADALDatasetAdapter.LABEL_ALIASES, required=False
        )

        # BATADAL publishes dates as dd/mm/yy HH; day-first parsing is required.
        timestamps = pd.to_datetime(frame[timestamp_column], errors="coerce", dayfirst=True)
        if timestamps.isna().any():
            count = int(timestamps.isna().sum())
            raise BATADALValidationError(f"{subset}: {count} invalid timestamps")
        if timestamps.duplicated().any():
            raise BATADALValidationError(f"{subset}: duplicate timestamps detected")
        if not timestamps.is_monotonic_increasing:
            raise BATADALValidationError(f"{subset}: timestamps are not sorted")

        if frame.isna().any().any():
            missing = int(frame.isna().sum().sum())
            raise BATADALValidationError(f"{subset}: {missing} missing cells")

        frame[timestamp_column] = timestamps
        if label_column is not None:
            frame[label_column] = pd.to_numeric(frame[label_column], errors="raise")

        return timestamp_column, label_column

    def load(self, subset: str, path: str | Path | None = None) -> BATADALFrame:
        """Load one subset: ``train_1``, ``train_2`` or ``test``."""
        if path is None:
            filenames = {
                "train_1": "BATADAL_dataset03.csv",
                "train_2": "BATADAL_dataset04.csv",
                "test": "BATADAL_test_dataset.csv",
            }
            try:
                path = self.root / subset / filenames[subset]
            except KeyError as exc:
                raise BATADALValidationError(f"Unsupported subset: {subset}") from exc
        source = Path(path)
        if not source.exists():
            raise FileNotFoundError(source)
        frame = pd.read_csv(source)
        timestamp_column, label_column = self._validate_frame(frame, source, subset)
        return BATADALFrame(subset, source, frame, timestamp_column, label_column)

    def load_attack_metadata(self, subset: str) -> list[BATADALAttackInterval]:
        metadata_files = {
            "train_2": self.root / "attack_lists" / "training_dataset_2_attacks.csv",
            "test": self.root / "attack_lists" / "test_dataset_attacks.csv",
        }
        try:
            metadata_path = metadata_files[subset]
        except KeyError as exc:
            raise BATADALValidationError(
                f"Attack interval metadata is not defined for subset: {subset}"
            ) from exc
        return load_attack_intervals(metadata_path)

    def load_aligned(self, subset: str) -> BATADALFrame:
        item = self.load(subset)
        intervals = self.load_attack_metadata(subset)
        aligned = apply_attack_intervals(item.frame, intervals, item.timestamp_column)
        return BATADALFrame(item.subset, item.path, aligned, item.timestamp_column, item.label_column)

    def load_all(self) -> dict[str, BATADALFrame]:
        return {subset: self.load(subset) for subset in ("train_1", "train_2", "test")}

    def manifest(self) -> dict[str, Any]:
        records: list[dict[str, Any]] = []
        for subset in ("train_1", "train_2", "test"):
            item = self.load(subset)
            timestamps = item.frame[item.timestamp_column]
            labels = item.frame[item.label_column] if item.label_column else None
            record: dict[str, Any] = {
                "dataset": "BATADAL",
                "subset": subset,
                "filename": item.path.name,
                "relative_path": str(item.path),
                "sha256": self.sha256(item.path),
                "size_bytes": item.path.stat().st_size,
                "rows": len(item.frame),
                "columns": len(item.frame.columns),
                "timestamp_column": item.timestamp_column,
                "label_column": item.label_column,
                "start_timestamp": timestamps.iloc[0].isoformat(),
                "end_timestamp": timestamps.iloc[-1].isoformat(),
                "sampling_frequency": "hourly" if timestamps.diff().dropna().eq(pd.Timedelta(hours=1)).all() else "non-hourly",
            }
            if labels is not None:
                values = {float(value) for value in labels.unique()}
                record["label_values"] = sorted(values)
                record["unknown_label_values"] = sorted(value for value in values if value < 0)
            records.append(record)
        return {"dataset": "BATADAL", "files": records}

    def write_manifest(self, output: str | Path) -> Path:
        destination = Path(output)
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(json.dumps(self.manifest(), indent=2) + "\n", encoding="utf-8")
        return destination
