"""Command-line interface for XAITA-OT."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from . import __version__
from .config import load_config
from .cti.generator import write_json
from .io.dataset_validation import DatasetValidationError, build_manifest, write_manifest
from .pipeline.demo import demo_events, make_demo_csv
from .pipeline.engine import XAITAEngine


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="xaita",
        description="XAITA-OT evidence-continuous OT/ICS threat analysis.",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
    )
    sub = parser.add_subparsers(dest="cmd", required=True)

    demo = sub.add_parser("demo", help="Run the built-in analysis demo.")
    demo.add_argument(
        "--out",
        default="artifacts/demo_cti.json",
        help="Output JSON path (default: artifacts/demo_cti.json).",
    )

    synthetic = sub.add_parser(
        "synthetic-data",
        help="Generate a deterministic synthetic OT dataset.",
    )
    synthetic.add_argument(
        "--out",
        default="data/demo/swat_like.csv",
        help="Output CSV path (default: data/demo/swat_like.csv).",
    )
    synthetic.add_argument(
        "--rows",
        type=int,
        default=3000,
        help="Number of rows to generate (must be positive).",
    )

    validate = sub.add_parser(
        "validate-data",
        help="Validate researcher-supplied real benchmark CSVs and write a reproducibility manifest.",
    )
    validate.add_argument(
        "--dataset",
        required=True,
        choices=["SWaT", "BATADAL", "TON-IoT"],
        help="Benchmark dataset family.",
    )
    validate.add_argument(
        "--root",
        required=True,
        help="Dataset root directory or a single CSV file.",
    )
    validate.add_argument(
        "--out",
        default=None,
        help="Manifest JSON path. Defaults to artifacts/<dataset>_real_data_manifest.json.",
    )
    validate.add_argument(
        "--chunksize",
        type=int,
        default=100000,
        help="CSV rows processed per chunk (must be positive).",
    )

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.cmd == "synthetic-data" and args.rows <= 0:
        parser.error("--rows must be a positive integer")
    if args.cmd == "validate-data" and args.chunksize <= 0:
        parser.error("--chunksize must be a positive integer")

    try:
        if args.cmd == "validate-data":
            output = args.out or f"artifacts/{args.dataset}_real_data_manifest.json"
            payload = build_manifest(args.dataset, args.root)
            path = write_manifest(payload, output)
            print(json.dumps({
                "dataset": payload["dataset"],
                "files": payload["file_count"],
                "validated_files": payload["validated_files"],
                "review_files": payload["review_files"],
                "benchmark_validation_ready": payload["benchmark_validation_ready"],
                "manifest_sha256": payload["manifest_sha256"],
                "manifest": str(path),
            }, sort_keys=True))
            return 0 if payload["benchmark_validation_ready"] else 2

        cfg = load_config()
        engine = XAITAEngine(cfg)

        if args.cmd == "synthetic-data":
            output = Path(make_demo_csv(args.out, args.rows, cfg.seed))
            print(output)
            return 0

        if args.cmd == "demo":
            output = Path(args.out)
            write_json(engine.analyze_events(demo_events()), output)
            print(output)
            return 0

        parser.error(f"unsupported command: {args.cmd}")
    except (OSError, ValueError, TypeError, json.JSONDecodeError, DatasetValidationError) as exc:
        parser.exit(1, f"xaita: error: {exc}\n")

    return 1


if __name__ == "__main__":
    raise SystemExit(main())
