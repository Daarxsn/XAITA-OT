"""BATADAL attack-interval metadata and timestamp alignment utilities."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import csv

import pandas as pd


class BATADALAttackMetadataError(ValueError):
    """Raised when attack metadata is incomplete or inconsistent."""


@dataclass(frozen=True)
class BATADALAttackInterval:
    """One inclusive BATADAL attack interval."""

    attack_id: int
    start_time: pd.Timestamp
    end_time: pd.Timestamp
    duration_hours: int
    description: str
    scada_concealment: str
    labelled_hours: int | None = None
    source_reference: str = ""

    def __post_init__(self) -> None:
        if self.end_time < self.start_time:
            raise BATADALAttackMetadataError(
                f"attack {self.attack_id}: end_time precedes start_time"
            )
        if self.duration_hours <= 0:
            raise BATADALAttackMetadataError(
                f"attack {self.attack_id}: duration_hours must be positive"
            )


def load_attack_intervals(path: str | Path) -> list[BATADALAttackInterval]:
    """Load and validate attack intervals from a structured CSV file."""
    source = Path(path)
    if not source.exists():
        raise FileNotFoundError(source)

    intervals: list[BATADALAttackInterval] = []
    with source.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        required = {
            "attack_id",
            "start_time",
            "end_time",
            "duration_hours",
            "description",
            "scada_concealment",
            "labelled_hours",
            "source_reference",
        }
        if reader.fieldnames is None or not required.issubset(reader.fieldnames):
            raise BATADALAttackMetadataError(
                f"{source}: required columns missing; expected {sorted(required)}"
            )

        seen_ids: set[int] = set()
        for row_number, row in enumerate(reader, start=2):
            if not any((value or "").strip() for value in row.values()):
                continue
            try:
                attack_id = int(row["attack_id"])
                start_time = pd.Timestamp(row["start_time"])
                end_time = pd.Timestamp(row["end_time"])
                duration_hours = int(row["duration_hours"])
                labelled_raw = (row.get("labelled_hours") or "").strip()
                labelled_hours = int(labelled_raw) if labelled_raw else None
            except (TypeError, ValueError) as exc:
                raise BATADALAttackMetadataError(
                    f"{source}:{row_number}: invalid typed value"
                ) from exc
            if attack_id in seen_ids:
                raise BATADALAttackMetadataError(
                    f"{source}:{row_number}: duplicate attack_id {attack_id}"
                )
            seen_ids.add(attack_id)
            intervals.append(
                BATADALAttackInterval(
                    attack_id=attack_id,
                    start_time=start_time,
                    end_time=end_time,
                    duration_hours=duration_hours,
                    description=(row.get("description") or "").strip(),
                    scada_concealment=(row.get("scada_concealment") or "").strip(),
                    labelled_hours=labelled_hours,
                    source_reference=(row.get("source_reference") or "").strip(),
                )
            )

    return sorted(intervals, key=lambda item: (item.start_time, item.attack_id))


def apply_attack_intervals(
    frame: pd.DataFrame,
    intervals: list[BATADALAttackInterval],
    timestamp_column: str,
    *,
    output_column: str = "interval_attack_label",
    attack_id_column: str = "interval_attack_id",
) -> pd.DataFrame:
    """Return a copy with inclusive interval-derived labels.

    Existing native labels, including BATADAL's ``-999`` unknown value, are
    never overwritten. A timestamp matching multiple intervals receives the
    first matching attack ID in deterministic start-time/ID order and the
    overlap is reported through ``interval_attack_overlap``.
    """
    if timestamp_column not in frame.columns:
        raise BATADALAttackMetadataError(f"missing timestamp column: {timestamp_column}")

    result = frame.copy()
    timestamps = pd.to_datetime(result[timestamp_column], errors="coerce")
    if timestamps.isna().any():
        raise BATADALAttackMetadataError("timestamp column contains invalid values")

    result[output_column] = 0
    result[attack_id_column] = pd.NA
    result["interval_attack_overlap"] = False

    matches: list[list[int]] = []
    for timestamp in timestamps:
        matched = [
            interval.attack_id
            for interval in intervals
            if interval.start_time <= timestamp <= interval.end_time
        ]
        matches.append(matched)

    for index, matched in enumerate(matches):
        if matched:
            result.iat[index, result.columns.get_loc(output_column)] = 1
            result.iat[index, result.columns.get_loc(attack_id_column)] = matched[0]
            result.iat[index, result.columns.get_loc("interval_attack_overlap")] = len(matched) > 1

    return result
