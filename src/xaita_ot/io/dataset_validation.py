"""Real-dataset validation and reproducibility manifest utilities.

The validator inspects researcher-supplied CSV files without modifying them or
requiring raw benchmark data to be committed to the repository.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
from typing import Any

import pandas as pd


DATASET_ALIASES = {
    "swat": "SWaT",
    "batadal": "BATADAL",
    "ton-iot": "TON-IoT",
    "toniot": "TON-IoT",
}

TIMESTAMP_ALIASES = {
    "SWaT": ("Timestamp", "timestamp", "time", "ts"),
    "BATADAL": ("DATETIME", "timestamp", "Timestamp", "time", "ts"),
    "TON-IoT": ("ts", "timestamp", "time", "Time"),
}

LABEL_ALIASES = {
    "SWaT": ("label", "Label", "Normal/Attack", "attack", "Attack", "Attack State"),
    "BATADAL": ("ATT_FLAG", "label", "Label", "attack", "Attack", "attack_label"),
    "TON-IoT": ("label", "Label", "attack", "Attack", "type"),
}

BENIGN_VALUES = {"normal", "benign", "0", "0.0", "false", "no", "", "nan", "none", "null"}


class DatasetValidationError(ValueError):
    """Raised when dataset validation cannot produce a trustworthy manifest."""


@dataclass(frozen=True)
class CSVValidation:
    dataset: str
    path: str
    sha256: str
    size_bytes: int
    rows: int
    columns: list[str]
    timestamp_column: str | None
    label_column: str | None
    invalid_timestamps: int
    missing_cells: int
    duplicate_timestamps: int
    monotonic_timestamp_order: bool | None
    start_timestamp: str | None
    end_timestamp: str | None
    label_values: list[str]
    attack_rows: int
    normal_rows: int
    validation_status: str

    def as_dict(self) -> dict[str, Any]:
        return {
            "dataset": self.dataset,
            "path": self.path,
            "sha256": self.sha256,
            "size_bytes": self.size_bytes,
            "rows": self.rows,
            "columns": self.columns,
            "column_count": len(self.columns),
            "timestamp_column": self.timestamp_column,
            "label_column": self.label_column,
            "invalid_timestamps": self.invalid_timestamps,
            "missing_cells": self.missing_cells,
            "duplicate_timestamps": self.duplicate_timestamps,
            "monotonic_timestamp_order": self.monotonic_timestamp_order,
            "start_timestamp": self.start_timestamp,
            "end_timestamp": self.end_timestamp,
            "label_values": self.label_values,
            "attack_rows": self.attack_rows,
            "normal_rows": self.normal_rows,
            "validation_status": self.validation_status,
        }


def canonical_dataset(name: str) -> str:
    key = name.strip().lower().replace("_", "-").replace(" ", "-")
    value = DATASET_ALIASES.get(key)
    if value is None:
        raise DatasetValidationError(f"Unsupported dataset: {name}")
    return value


def _resolve_column(columns: list[str], aliases: tuple[str, ...]) -> str | None:
    normalized = {column.strip().lower(): column for column in columns}
    for alias in aliases:
        found = normalized.get(alias.lower())
        if found is not None:
            return found
    return None


def sha256_file(path: Path, chunk_size: int = 1024 * 1024) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(chunk_size), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _resolve_case_insensitive(columns: list[str], name: str) -> str | None:
    lookup = {column.lower(): column for column in columns}
    return lookup.get(name.lower())


def _parse_timestamp(frame: pd.DataFrame, dataset: str, timestamp_column: str | None) -> tuple[pd.Series | None, str | None]:
    if dataset == "TON-IoT":
        date_column = _resolve_case_insensitive(list(frame.columns), "date")
        time_column = _resolve_case_insensitive(list(frame.columns), "time")
        if date_column and time_column:
            combined = (
                frame[date_column].astype(str).str.strip()
                + " "
                + frame[time_column].astype(str).str.strip()
            )
            return pd.to_datetime(combined, errors="coerce", utc=True), f"{date_column} + {time_column}"
    if timestamp_column is None:
        return None, None
    return (
        pd.to_datetime(
            frame[timestamp_column],
            errors="coerce",
            dayfirst=dataset == "BATADAL",
            utc=True,
        ),
        timestamp_column,
    )


def _label_is_attack(series: pd.Series) -> pd.Series:
    if pd.api.types.is_numeric_dtype(series):
        numeric = pd.to_numeric(series, errors="coerce")
        return numeric.fillna(0).astype(float) > 0
    text = series.astype(str).str.strip().str.lower()
    return ~text.isin(BENIGN_VALUES)


def validate_csv(
    path: str | Path,
    dataset: str,
    root: str | Path | None = None,
    chunksize: int = 100_000,
) -> CSVValidation:
    dataset_name = canonical_dataset(dataset)
    source = Path(path)
    if not source.is_file():
        raise DatasetValidationError(f"{dataset_name}: CSV file not found: {source}")

    root_path = Path(root).resolve() if root is not None else source.parent.resolve()
    source_resolved = source.resolve()
    try:
        display_path = source_resolved.relative_to(root_path).as_posix()
    except ValueError:
        display_path = source_resolved.as_posix()

    header = pd.read_csv(source, nrows=0)
    columns = [str(column).strip() for column in header.columns]
    if any(not column for column in columns):
        raise DatasetValidationError(f"{dataset_name}: blank column name in {source}")
    if len(columns) != len(set(columns)):
        duplicates = sorted({column for column in columns if columns.count(column) > 1})
        raise DatasetValidationError(f"{dataset_name}: duplicate columns {duplicates} in {source}")

    source_timestamp_column = _resolve_column(columns, TIMESTAMP_ALIASES[dataset_name])
    source_label_column = _resolve_column(columns, LABEL_ALIASES[dataset_name])

    rows = 0
    invalid_timestamps = 0
    missing_cells = 0
    duplicate_timestamps = 0
    monotonic = True if (source_timestamp_column or dataset_name == "TON-IoT") else None
    start_timestamp = None
    end_timestamp = None
    previous_timestamp = None
    label_values: set[str] = set()
    attack_rows = 0
    normal_rows = 0
    effective_timestamp_column = source_timestamp_column

    try:
        for frame in pd.read_csv(source, chunksize=chunksize, low_memory=False):
            frame.columns = columns
            rows += len(frame)
            missing_cells += int(frame.isna().sum().sum())

            timestamps, timestamp_display = _parse_timestamp(
                frame, dataset_name, source_timestamp_column
            )
            if timestamp_display:
                effective_timestamp_column = timestamp_display
            if timestamps is not None:
                invalid_timestamps += int(timestamps.isna().sum())
                valid = timestamps.dropna()
                if len(valid):
                    first = valid.iloc[0]
                    last = valid.iloc[-1]
                    if start_timestamp is None:
                        start_timestamp = first.isoformat()
                    end_timestamp = last.isoformat()
                    if previous_timestamp is not None:
                        if first < previous_timestamp:
                            monotonic = False
                        if first == previous_timestamp:
                            duplicate_timestamps += 1
                    diffs = valid.diff().dropna()
                    duplicate_timestamps += int((diffs == pd.Timedelta(0)).sum())
                    if bool((diffs < pd.Timedelta(0)).any()):
                        monotonic = False
                    previous_timestamp = last

            if source_label_column:
                labels = frame[source_label_column]
                label_values.update(str(value) for value in labels.dropna().unique())
                attacks = _label_is_attack(labels)
                attack_rows += int(attacks.sum())
                normal_rows += int((~attacks).sum())

    except Exception as exc:
        raise DatasetValidationError(
            f"{dataset_name}: unable to parse {source}: {type(exc).__name__}: {exc}"
        ) from exc

    if rows == 0:
        raise DatasetValidationError(f"{dataset_name}: {source} is empty")

    ready = (
        effective_timestamp_column is not None
        and source_label_column is not None
        and invalid_timestamps == 0
        and duplicate_timestamps == 0
        and bool(monotonic)
        and missing_cells == 0
    )

    return CSVValidation(
        dataset=dataset_name,
        path=display_path,
        sha256=sha256_file(source),
        size_bytes=source.stat().st_size,
        rows=rows,
        columns=columns,
        timestamp_column=effective_timestamp_column,
        label_column=source_label_column,
        invalid_timestamps=invalid_timestamps,
        missing_cells=missing_cells,
        duplicate_timestamps=duplicate_timestamps,
        monotonic_timestamp_order=monotonic,
        start_timestamp=start_timestamp,
        end_timestamp=end_timestamp,
        label_values=sorted(label_values),
        attack_rows=attack_rows,
        normal_rows=normal_rows,
        validation_status="pass" if ready else "review",
    )


def discover_csvs(root: str | Path) -> list[Path]:
    base = Path(root)
    if not base.exists():
        raise DatasetValidationError(f"Dataset root not found: {base}")
    if base.is_file():
        if base.suffix.lower() != ".csv":
            raise DatasetValidationError(f"Dataset input is not a CSV: {base}")
        return [base]
    files = sorted(
        {
            path.resolve()
            for path in base.rglob("*")
            if path.is_file() and path.suffix.lower() == ".csv"
        },
        key=lambda item: item.as_posix().lower(),
    )
    if not files:
        raise DatasetValidationError(f"No CSV benchmark files found under {base}")
    return files


def build_manifest(dataset: str, root: str | Path) -> dict[str, Any]:
    dataset_name = canonical_dataset(dataset)
    base = Path(root).resolve()
    files = discover_csvs(base)
    records = [validate_csv(path, dataset_name, base).as_dict() for path in files]
    passed = sum(item["validation_status"] == "pass" for item in records)
    payload: dict[str, Any] = {
        "schema_version": "XAITA-OT-V5-REAL-DATA-MANIFEST-1.0",
        "dataset": dataset_name,
        "root": ".",
        "file_count": len(records),
        "validated_files": passed,
        "review_files": len(records) - passed,
        "benchmark_validation_ready": passed == len(records) and len(records) > 0,
        "files": records,
    }
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    payload["manifest_sha256"] = hashlib.sha256(canonical).hexdigest()
    return payload


def build_all_manifests(dataset_roots: dict[str, str | Path]) -> dict[str, Any]:
    manifests = {
        canonical_dataset(dataset): build_manifest(dataset, root)
        for dataset, root in dataset_roots.items()
    }
    payload: dict[str, Any] = {
        "schema_version": "XAITA-OT-V5-REAL-DATA-MANIFEST-BUNDLE-1.0",
        "datasets": manifests,
        "all_validation_ready": bool(manifests) and all(
            item["benchmark_validation_ready"] for item in manifests.values()
        ),
    }
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    payload["bundle_sha256"] = hashlib.sha256(canonical).hexdigest()
    return payload


def write_manifest(payload: dict[str, Any], output: str | Path) -> Path:
    destination = Path(output)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return destination
