#!/usr/bin/env python3
"""Validate BATADAL attack-list metadata without requiring raw datasets.

Usage:
    python scripts/validate_batadal_attack_metadata.py
"""

from __future__ import annotations

from pathlib import Path

from xaita_ot.datasets.batadal_attacks import (
    BATADALAttackMetadataError,
    load_attack_intervals,
)


ROOT = Path(__file__).resolve().parents[1]
METADATA_ROOT = ROOT / "data/raw/batadal/attack_lists"


def validate_file(path: Path, expected_ids: set[int], name: str) -> None:
    intervals = load_attack_intervals(path)
    actual_ids = {item.attack_id for item in intervals}
    missing = expected_ids - actual_ids
    unexpected = actual_ids - expected_ids
    if missing or unexpected:
        raise BATADALAttackMetadataError(
            f"{name}: expected IDs {sorted(expected_ids)}, "
            f"found {sorted(actual_ids)}; missing={sorted(missing)}, "
            f"unexpected={sorted(unexpected)}"
        )
    for interval in intervals:
        if not interval.source_reference:
            raise BATADALAttackMetadataError(
                f"{name}: attack {interval.attack_id} has no source_reference"
            )


def main() -> int:
    validate_file(
        METADATA_ROOT / "training_dataset_2_attacks.csv",
        set(range(1, 8)),
        "training_dataset_2_attacks.csv",
    )

    test_path = METADATA_ROOT / "test_dataset_attacks.csv"
    test_intervals = load_attack_intervals(test_path)
    test_ids = {item.attack_id for item in test_intervals}
    if test_ids != set(range(8, 15)):
        raise BATADALAttackMetadataError(
            "test_dataset_attacks.csv: visible screenshot coverage currently "
            f"requires IDs 8–14; found {sorted(test_ids)}. Confirm official "
            "test-list completeness before enabling benchmark evaluation."
        )
    for interval in test_intervals:
        if not interval.source_reference:
            raise BATADALAttackMetadataError(
                f"test_dataset_attacks.csv: attack {interval.attack_id} has no source_reference"
            )

    print("BATADAL attack metadata: PASS")
    print("Training metadata: IDs 1–7 validated")
    print("Test metadata: IDs 8–14 validated as screenshot coverage only")
    print("Benchmark gate: CLOSED until official test-list completeness is confirmed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
