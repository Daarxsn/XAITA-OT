"""Read CSV headers before pandas can silently mangle duplicate column names."""
from __future__ import annotations

import csv
from collections import Counter
from pathlib import Path


def read_csv_header(path: str | Path) -> list[str]:
    """Read the first nonblank CSV record with Python's CSV parser."""
    source = Path(path)
    try:
        with source.open("r", encoding="utf-8-sig", newline="") as handle:
            for row in csv.reader(handle, strict=True):
                if row:
                    return [str(column).strip() for column in row]
    except csv.Error as exc:
        raise ValueError(f"malformed CSV header: {exc}") from exc
    raise ValueError("CSV is empty or has no header row")


def duplicate_column_names(columns: list[str]) -> list[str]:
    """Return repeated header names using case-insensitive, whitespace-trimmed identity."""
    normalized = [str(column).strip().casefold() for column in columns]
    counts = Counter(normalized)
    duplicates = {
        str(column).strip()
        for column, key in zip(columns, normalized)
        if counts[key] > 1
    }
    return sorted(duplicates, key=str.casefold)
