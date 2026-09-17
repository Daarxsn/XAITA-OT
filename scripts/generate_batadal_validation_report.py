#!/usr/bin/env python3
"""Generate a local BATADAL provenance and validation report.

Raw BATADAL files are intentionally not committed. Run this script only after
placing the authorized datasets under data/raw/batadal/train_1, train_2, test.

Usage:
    PYTHONPATH=src python scripts/generate_batadal_validation_report.py
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

from xaita_ot.datasets.batadal import BATADALDatasetAdapter, BATADALValidationError


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DATA_ROOT = ROOT / "data/raw/batadal"
DEFAULT_MANIFEST = ROOT / "experiments/manifests/batadal.json"
DEFAULT_REPORT = ROOT / "experiments/reports/batadal_validation_report.json"


def build_report(data_root: Path) -> dict:
    adapter = BATADALDatasetAdapter(data_root)
    report = {
        "report": "BATADAL validation",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "data_root": str(data_root),
        "status": "PASS",
        "benchmark_gate": "CLOSED",
        "checks": [],
    }

    try:
        manifest = adapter.manifest()
        report["manifest"] = manifest
        report["checks"].append({"name": "raw_files_load_and_validate", "status": "PASS"})
    except (FileNotFoundError, BATADALValidationError, OSError) as exc:
        report["status"] = "FAIL"
        report["checks"].append(
            {
                "name": "raw_files_load_and_validate",
                "status": "FAIL",
                "error": str(exc),
            }
        )
        return report

    metadata_status = "PASS"
    metadata_error = None
    try:
        train_intervals = adapter.load_attack_metadata("train_2")
        test_intervals = adapter.load_attack_metadata("test")
        if {item.attack_id for item in train_intervals} != set(range(1, 8)):
            raise BATADALValidationError("training attack metadata must contain IDs 1–7")
        if {item.attack_id for item in test_intervals} != set(range(8, 15)):
            raise BATADALValidationError(
                "test metadata currently covers IDs 8–14 only; official completeness is unconfirmed"
            )
    except (FileNotFoundError, BATADALValidationError, OSError) as exc:
        metadata_status = "FAIL"
        metadata_error = str(exc)
        report["status"] = "FAIL"

    report["checks"].append(
        {
            "name": "attack_metadata_coverage",
            "status": metadata_status,
            **({"error": metadata_error} if metadata_error else {}),
        }
    )
    report["checks"].append(
        {
            "name": "official_test_list_completeness",
            "status": "BLOCKED",
            "reason": "The repository currently records screenshot coverage for IDs 8–14; completeness must be confirmed from the official source.",
        }
    )
    report["benchmark_gate"] = "CLOSED"
    return report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-root", type=Path, default=DEFAULT_DATA_ROOT)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    args = parser.parse_args()

    report = build_report(args.data_root)
    args.manifest.parent.mkdir(parents=True, exist_ok=True)
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.manifest.write_text(json.dumps(report.get("manifest", {}), indent=2) + "\n", encoding="utf-8")
    args.report.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(f"BATADAL report: {report['status']}")
    print(f"Manifest: {args.manifest}")
    print(f"Report: {args.report}")
    print(f"Benchmark gate: {report['benchmark_gate']}")
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
