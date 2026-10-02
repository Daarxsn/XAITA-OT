#!/usr/bin/env python3
"""Validate all locally configured real benchmark datasets.

Raw benchmark files stay outside source control. This script writes only
metadata (schema, row counts, hashes and validation status) to the selected
manifest path.
"""

from __future__ import annotations

import argparse
import os
from pathlib import Path

from xaita_ot.io.dataset_validation import build_all_manifests, write_manifest


ROOT = Path(__file__).resolve().parents[1]
DEFAULTS = {
    "SWaT": ROOT / "data" / "raw" / "swat",
    "BATADAL": ROOT / "data" / "raw" / "batadal",
    "TON-IoT": ROOT / "data" / "raw" / "ton_iot",
}
ENV_NAMES = {
    "SWaT": "XAITA_SWAT_PATH",
    "BATADAL": "XAITA_BATADAL_PATH",
    "TON-IoT": "XAITA_TONIOT_PATH",
}


def configured_roots() -> dict[str, Path]:
    return {
        dataset: Path(os.environ.get(env_name, str(DEFAULTS[dataset])))
        for dataset, env_name in ENV_NAMES.items()
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Validate all locally configured XAITA-OT real benchmark datasets."
    )
    parser.add_argument(
        "--out",
        default="artifacts/real_data_manifest_bundle.json",
        help="Output metadata manifest (default: artifacts/real_data_manifest_bundle.json).",
    )
    args = parser.parse_args(argv)

    roots = configured_roots()
    payload = build_all_manifests(roots)
    path = write_manifest(payload, args.out)

    print(f"Manifest: {path}")
    for dataset, item in payload["datasets"].items():
        print(
            f"{dataset}: files={item['file_count']} "
            f"validated={item['validated_files']} "
            f"review={item['review_files']} "
            f"ready={item['benchmark_validation_ready']}"
        )
    print(f"All validation ready: {payload['all_validation_ready']}")
    print(f"Bundle SHA-256: {payload['bundle_sha256']}")
    return 0 if payload["all_validation_ready"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
