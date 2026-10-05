"""Command-line interface for XAITA-OT."""

from __future__ import annotations

import argparse
import json
import hashlib
import subprocess
from pathlib import Path

from . import __version__
from .config import load_config
from .cti.generator import write_json
from .operations.lifecycle import build_lifecycle_plan, create_backup, prune_backups, restore_backup, verify_backup
from .governance import evaluate_deployment, load_policy
from .integrations.enterprise import (
    build_audit_event,
    build_cti_export,
    build_siem_event,
    write_json as write_integration_json,
)
from .io.dataset_validation import DatasetValidationError, build_manifest, write_manifest
from .pipeline.demo import demo_events, make_demo_csv
from .pipeline.real_experiments import (
    REAL_EXPERIMENT_DATASETS,
    REAL_EXPERIMENT_DETECTORS,
    run_real_experiment,
    run_real_experiment_matrix,
    build_statistical_research_report,
    build_experiment_manifest,
    evaluate_attribution_cases,
    run_real_experiment_statistical_matrix,
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

    real_experiment_statistics = sub.add_parser(
        "real-experiment-statistics",
        help="Repeat the real benchmark matrix across multiple seeds and compute statistical summaries.",
    )
    real_experiment_statistics.add_argument("--swat-csv", required=True)
    real_experiment_statistics.add_argument("--batadal-csv", required=True)
    real_experiment_statistics.add_argument("--toniot-csv", required=True)
    real_experiment_statistics.add_argument("--seed", action="append", type=int, dest="seeds")
    real_experiment_statistics.add_argument("--confidence", type=float, default=0.95)
    real_experiment_statistics.add_argument("--out", default=None)
    real_experiment_statistics.add_argument("--config", default="configs/default.yaml")

    attribution_evaluation = sub.add_parser(
        "attribution-evaluation",
        help="Evaluate attribution configurations on an explicit labeled case set.",
    )
    attribution_evaluation.add_argument("--cases-json", required=True)
    attribution_evaluation.add_argument("--reliabilities-json", required=True)
    attribution_evaluation.add_argument("--support-threshold", type=float, default=0.60)
    attribution_evaluation.add_argument("--conflict-threshold", type=float, default=0.35)
    attribution_evaluation.add_argument("--out", default=None)

    real_experiment_report = sub.add_parser(
        "real-experiment-report",
        help="Validate a completed statistical envelope and package a research report artifact.",
    )
    real_experiment_report.add_argument("--statistics-json", required=True)
    real_experiment_report.add_argument("--out", default=None)

    experiment_manifest = sub.add_parser(
        "experiment-manifest",
        help="Build an immutable manifest for a completed experiment result artifact.",
    )
    experiment_manifest.add_argument("--result-json", required=True)
    experiment_manifest.add_argument("--out", default=None)
    experiment_manifest.add_argument("--software-revision", default=None)

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

    siem_export = sub.add_parser(
        "siem-export",
        help="Build a vendor-neutral SIEM event from a completed CTI JSON artifact.",
    )
    siem_export.add_argument("--cti", required=True, help="Completed XAITA-OT CTI JSON path.")
    siem_export.add_argument("--out", default="artifacts/enterprise/siem_event.json")
    siem_export.add_argument("--source", default="xaita-ot")

    cti_export = sub.add_parser(
        "cti-export",
        help="Wrap a completed CTI artifact in the XAITA-OT STIX 2.1 export contract.",
    )
    cti_export.add_argument("--cti", required=True, help="Completed XAITA-OT CTI JSON path.")
    cti_export.add_argument("--out", default="artifacts/enterprise/cti_export.json")

    audit_event = sub.add_parser(
        "audit-event",
        help="Create an interoperable immutable audit-event envelope.",
    )
    audit_event.add_argument("--action", required=True)
    audit_event.add_argument("--actor", required=True)
    audit_event.add_argument("--outcome", required=True)
    audit_event.add_argument("--correlation-id", required=True)
    audit_event.add_argument("--incident-id", default=None)
    audit_event.add_argument("--timestamp", default=None)
    audit_event.add_argument("--details-json", default=None)
    audit_event.add_argument("--out", default="artifacts/enterprise/audit_event.json")

    backup = sub.add_parser("backup", help="Create a verified repository backup excluding raw research datasets.")
    backup.add_argument("--root", default=".")
    backup.add_argument("--out", default="artifacts/backups/xaita-backup.tar.gz")

    backup_verify = sub.add_parser("backup-verify", help="Verify backup manifest and file checksums.")
    backup_verify.add_argument("--backup", required=True)

    backup_restore = sub.add_parser("backup-restore", help="Restore a verified backup into an empty staging directory.")
    backup_restore.add_argument("--backup", required=True)
    backup_restore.add_argument("--staging", required=True)

    backup_prune = sub.add_parser("backup-prune", help="Retain only the newest lifecycle backups.")
    backup_prune.add_argument("--directory", default="artifacts/backups")
    backup_prune.add_argument("--keep", type=int, default=5)

    lifecycle_plan = sub.add_parser("lifecycle-plan", help="Create a deterministic upgrade/rollback plan.")
    lifecycle_plan.add_argument("--current-revision", required=True)
    lifecycle_plan.add_argument("--target-revision", required=True)
    lifecycle_plan.add_argument("--backup", required=True)
    lifecycle_plan.add_argument("--rollback-revision", default=None)
    lifecycle_plan.add_argument("--out", default="artifacts/backups/lifecycle_plan.json")

    governance = sub.add_parser("governance-check", help="Validate governance policy and deployment evidence.")
    governance.add_argument("--policy", default="configs/governance.yaml.json")
    governance.add_argument("--evidence-json", default=None, help="JSON object mapping required evidence keys to true/false.")
    governance.add_argument("--out", default=None)

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
        if args.cmd == "attribution-evaluation":
            cases_payload = json.loads(Path(args.cases_json).read_text(encoding="utf-8"))
            reliabilities = json.loads(Path(args.reliabilities_json).read_text(encoding="utf-8"))
            cases = cases_payload["cases"] if isinstance(cases_payload, dict) and "cases" in cases_payload else cases_payload
            payload = evaluate_attribution_cases(
                cases,
                reliabilities=reliabilities,
                support_threshold=args.support_threshold,
                conflict_threshold=args.conflict_threshold,
                configurations=ATTRIBUTION_CONFIGURATIONS,
            )
            output = args.out or f"artifacts/attribution/attribution_evaluation_{payload['fingerprint'][:12]}.json"
            path = write_result_envelope(payload, output)
            print(json.dumps({
                "status": payload["status"],
                "case_count": payload["case_count"],
                "configurations": payload["configurations"],
                "fingerprint": payload["fingerprint"],
                "result": str(path),
            }, sort_keys=True))
            return 0

        if args.cmd == "governance-check":
            policy = load_policy(args.policy)
            evidence = json.loads(Path(args.evidence_json).read_text(encoding="utf-8")) if args.evidence_json else {}
            result = evaluate_deployment(policy, evidence)
            if args.out:
                path = write_integration_json(result, args.out)
                result["result"] = str(path)
            print(json.dumps(result, sort_keys=True))
            return 0 if result["status"] == "approved" else 2

        if args.cmd == "backup":
            path = create_backup(args.root, args.out)
            print(json.dumps({"status": "completed", "backup": str(path)}, sort_keys=True))
            return 0

        if args.cmd == "backup-verify":
            result = verify_backup(args.backup)
            print(json.dumps(result, sort_keys=True))
            return 0 if result["verified"] else 2

        if args.cmd == "backup-restore":
            path = restore_backup(args.backup, args.staging)
            print(json.dumps({"status": "completed", "staging": str(path)}, sort_keys=True))
            return 0

        if args.cmd == "backup-prune":
            removed = prune_backups(args.directory, keep=args.keep)
            print(json.dumps({"status": "completed", "removed": [str(p) for p in removed]}, sort_keys=True))
            return 0

        if args.cmd == "lifecycle-plan":
            plan = build_lifecycle_plan(
                current_revision=args.current_revision,
                target_revision=args.target_revision,
                backup_path=args.backup,
                rollback_revision=args.rollback_revision,
            )
            path = write_integration_json(plan, args.out)
            print(json.dumps({"status": "completed", "result": str(path)}, sort_keys=True))
            return 0

        if args.cmd == "siem-export":
            payload = json.loads(Path(args.cti).read_text(encoding="utf-8"))
            payload = payload[0] if isinstance(payload, list) else payload
            event = build_siem_event(payload, source=args.source)
            path = write_integration_json(event, args.out)
            print(json.dumps({"status": "completed", "event_id": event["event_id"], "result": str(path)}, sort_keys=True))
            return 0

        if args.cmd == "cti-export":
            payload = json.loads(Path(args.cti).read_text(encoding="utf-8"))
            payload = payload[0] if isinstance(payload, list) else payload
            export = build_cti_export(payload)
            path = write_integration_json(export, args.out)
            print(json.dumps({"status": "completed", "export_sha256": export["export_sha256"], "result": str(path)}, sort_keys=True))
            return 0

        if args.cmd == "audit-event":
            details = json.loads(args.details_json) if args.details_json else {}
            event = build_audit_event(
                action=args.action,
                actor=args.actor,
                outcome=args.outcome,
                correlation_id=args.correlation_id,
                incident_id=args.incident_id,
                timestamp=args.timestamp,
                details=details,
            )
            path = write_integration_json(event, args.out)
            print(json.dumps({"status": "completed", "event_id": event["event_id"], "result": str(path)}, sort_keys=True))
            return 0

        if args.cmd == "experiment-manifest":
            source = Path(args.result_json)
            raw = source.read_bytes()
            payload = json.loads(raw.decode("utf-8"))
            digest = hashlib.sha256(raw).hexdigest()
            revision = args.software_revision
            if revision is None:
                try:
                    revision = subprocess.run(
                        ["git", "rev-parse", "HEAD"],
                        capture_output=True, text=True, check=True,
                    ).stdout.strip()
                except (OSError, subprocess.CalledProcessError):
                    revision = None
            manifest = build_experiment_manifest(
                payload,
                result_sha256=digest,
                result_path=str(source),
                software_revision=revision,
            )
            output = args.out or f"artifacts/real_experiments/manifest_{manifest['manifest_sha256'][:12]}.json"
            out_path = Path(output)
            out_path.parent.mkdir(parents=True, exist_ok=True)
            out_path.write_text(json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8")
            print(json.dumps({
                "status": "completed",
                "manifest_sha256": manifest["manifest_sha256"],
                "result_sha256": manifest["result"]["sha256"],
                "result": str(out_path),
            }, sort_keys=True))
            return 0

        if args.cmd == "real-experiment-report":
            source = Path(args.statistics_json)
            payload = json.loads(source.read_text(encoding="utf-8"))
            report = build_statistical_research_report(payload)
            output = args.out or f"artifacts/real_experiments/research_report_{report['report']['fingerprint'][:12]}.json"
            path = write_result_envelope(report, output)
            print(json.dumps({
                "status": report["report"]["status"],
                "source_statistics_fingerprint": report["report"]["source_statistics_fingerprint"],
                "fingerprint": report["report"]["fingerprint"],
                "seed_count": report["report"]["seed_count"],
                "observation_count": report["report"]["observation_count"],
                "result": str(path),
            }, sort_keys=True))
            return 0

        if args.cmd == "real-experiment-statistics":
            cfg = load_config(args.config)
            seeds = args.seeds if args.seeds is not None else [42, 43, 44]
            output = args.out or f"artifacts/real_experiments/statistics_{seeds[0]}.json"
            payload = run_real_experiment_statistical_matrix(
                csv_paths={
                    "SWaT": args.swat_csv,
                    "BATADAL": args.batadal_csv,
                    "TON-IoT": args.toniot_csv,
                },
                config=cfg,
                seeds=seeds,
                confidence=args.confidence,
            )
            path = write_result_envelope(payload, output)
            print(json.dumps({
                "seeds": payload["statistics"]["seeds"],
                "confidence": payload["statistics"]["confidence"],
                "status": payload["statistics"]["status"],
                "observation_count": payload["statistics"]["observation_count"],
                "completed_matrix_count": payload["statistics"]["completed_matrix_count"],
                "failed_matrix_count": payload["statistics"]["failed_matrix_count"],
                "fingerprint": payload["statistics"]["fingerprint"],
                "result": str(path),
            }, sort_keys=True))
            return 0 if payload["statistics"]["status"] == "completed" else 1

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
