#!/usr/bin/env python3
"""Validate local BATADAL files and write a provenance manifest.

Usage:
    python scripts/validate_batadal.py
    python scripts/validate_batadal.py --root data/raw/batadal --output experiments/manifests/batadal.json
"""

from __future__ import annotations

import argparse
from pathlib import Path

from xaita_ot.datasets.batadal import BATADALDatasetAdapter


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path("data/raw/batadal"))
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("experiments/manifests/batadal.json"),
    )
    args = parser.parse_args()

    adapter = BATADALDatasetAdapter(args.root)
    manifest = adapter.manifest()
    output = adapter.write_manifest(args.output)

    print("BATADAL validation: PASS")
    for item in manifest["files"]:
        print(
            f"- {item['subset']}: rows={item['rows']} "
            f"columns={item['columns']} "
            f"sampling={item['sampling_frequency']}"
        )
    print(f"Manifest: {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
