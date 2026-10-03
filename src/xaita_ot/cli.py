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
from .pipeline.real_experiments import (
    REAL_EXPERIMENT_DATASETS,
    REAL_EXPERIMENT_DETECTORS,
    run_real_experiment,
    run_real_experiment_matrix,
    run_real_experiment_suite,
    write_result_envelope,
)
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

    real_experiment_suite = sub.add_parser(
        "real-experiment-suite",
        help="Validate a real benchmark CSV, execute the four-detector suite, and write an auditable bundle.",
    )
    real_experiment_suite.add_argument("--dataset", required=True, choices=["SWaT", "BATADAL", "TON-IoT"])
    real_experiment_suite.add_argument("--csv", required=True)
    real_experiment_suite.add_argument("--seed", type=int, default=42)
    real_experiment_suite.add_argument("--root", default=None)
    real_experiment_suite.add_argument("--out", default=None)
    real_experiment_suite.add_argument("--config", default="configs/default.yaml")

    real_experiment_matrix = sub.add_parser(
        "real-experiment-matrix",
        help="Validate and execute the four-detector suite across SWaT, BATADAL and TON-IoT.",
    )
    real_experiment_matrix.add_argument("--swat-csv", required=True, help="CSV path for SWaT.")
    real_experiment_matrix.add_argument("--batadal-csv", required=True, help="CSV path for BATADAL.")
    real_experiment_matrix.add_argument("--toniot-csv", required=True, help="CSV path for TON-IoT.")
    real_experiment_matrix.add_argument("--seed", type=int, default=42)
    real_experiment_matrix.add_argument("--out", default=None)
    real_experiment_matrix.add_argument("--config", default="configs/default.yaml")

    real_experiment = sub.add_parser(
        "real-experiment",
        help="Validate a real benchmark CSV, execute one detector, and write an auditable result envelope.",
    )
    real_experiment.add_argument(
        "--dataset",
        required=True,
        choices=["SWaT", "BATADAL", "TON-IoT"],
        help="Benchmark dataset family.",
    )
    real_experiment.add_argument(
        "--csv",
        required=True,
        help="Path to the specific benchmark CSV to execute.",
    )
    real_experiment.add_argument(
        "--detector",
        required=True,
        choices=["random_forest", "cnn", "lstm", "cnn_lstm"],
        help="Detector architecture to execute.",
    )
    real_experiment.add_argument(
        "--seed",
        type=int,
        default=42,
        help="Deterministic experiment seed.",
    )
    real_experiment.add_argument(
        "--root",
        default=None,
        help="Optional dataset root used for manifest-relative file identity.",
    )
    real_experiment.add_argument(
        "--out",
        default=None,
        help="Result JSON path. Defaults to artifacts/real_experiments/<dataset>_<detector>_<seed>.json.",
    )
    real_experiment.add_argument(
        "--config",
        default="configs/default.yaml",
        help="Experiment configuration YAML path.",
    )

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.cmd == "synthetic-data" and args.rows <= 0:
        parser.error("--rows must be a positive integer")
    if args.cmd == "validate-data" and args.chunksize <= 0:
        parser.error("--chunksize must be a positive integer")
    if args.cmd in {"real-experiment", "real-experiment-suite", "real-experiment-matrix"} and args.seed < 0:
        parser.error("--seed must be non-negative")

    try:
        if args.cmd == "real-experiment-matrix":
            cfg = load_config(args.config)
            output = args.out or f"artifacts/real_experiments/matrix_{args.seed}.json"
            payload = run_real_experiment_matrix(
                csv_paths={
                    "SWaT": args.swat_csv,
                    "BATADAL": args.batadal_csv,
                    "TON-IoT": args.toniot_csv,
                },
                config=cfg,
                seed=args.seed,
                detectors=REAL_EXPERIMENT_DETECTORS,
                datasets=REAL_EXPERIMENT_DATASETS,
            )
            path = write_result_envelope(payload, output)
            print(json.dumps({
                "datasets": payload["matrix"]["datasets"],
                "detectors": payload["matrix"]["detectors"],
                "seed": payload["matrix"]["seed"],
                "status": payload["matrix"]["status"],
                "completed_dataset_count": payload["matrix"]["completed_dataset_count"],
                "failed_dataset_count": payload["matrix"]["failed_dataset_count"],
                "fingerprint": payload["matrix"]["fingerprint"],
                "result": str(path),
            }, sort_keys=True))
            return 0 if payload["matrix"]["status"] == "completed" else 1

        if args.cmd == "real-experiment-suite":
            cfg = load_config(args.config)
            output = args.out or f"artifacts/real_experiments/{args.dataset}_suite_{args.seed}.json"
            payload = run_real_experiment_suite(
                csv_path=args.csv, dataset=args.dataset, config=cfg, seed=args.seed,
                dataset_root=args.root, detectors=REAL_EXPERIMENT_DETECTORS,
            )
            path = write_result_envelope(payload, output)
            print(json.dumps({
                "dataset": payload["suite"]["dataset"],
                "seed": payload["suite"]["seed"],
                "requested_detectors": payload["suite"]["requested_detectors"],
                "completed_detectors": payload["suite"]["completed_detectors"],
                "failed_detectors": payload["suite"]["failed_detectors"],
                "status": payload["suite"]["status"],
                "fingerprint": payload["suite"]["fingerprint"],
                "result": str(path),
            }, sort_keys=True))
            return 0 if payload["suite"]["status"] == "completed" else 1

        if args.cmd == "real-experiment":
            cfg = load_config(args.config)
            output = args.out or (
                f"artifacts/real_experiments/"
                f"{args.dataset}_{args.detector}_{args.seed}.json"
            )
            payload = run_real_experiment(
                csv_path=args.csv,
                dataset=args.dataset,
                config=cfg,
                detector=args.detector,
                seed=args.seed,
                dataset_root=args.root,
            )
            path = write_result_envelope(payload, output)
            print(json.dumps({
                "experiment_id": payload["experiment"]["experiment_id"],
                "dataset": payload["experiment"]["dataset"],
                "detector": payload["reproducibility"]["detector"],
                "seed": payload["reproducibility"]["seed"],
                "split_protocol": payload["reproducibility"]["split_protocol"],
                "fingerprint": payload["reproducibility"]["fingerprint"],
                "result": str(path),
            }, sort_keys=True))
            return 0

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
    except (OSError, ValueError, TypeError, json.JSONDecodeError, DatasetValidationError, FileNotFoundError) as exc:
        parser.exit(1, f"xaita: error: {exc}\n")

    return 1


if __name__ == "__main__":
    raise SystemExit(main())
