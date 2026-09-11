"""Run the V3 Phase-1 leakage/reproducibility audit.

Usage:
  python scripts/audit_v3.py --dataset SWaT --csv path/to/data.csv

The command performs structural split checks and a deterministic preprocessing
fit audit. It never tunes a threshold or BSS reference on validation/test data.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from xaita_ot.config import AppConfig
from xaita_ot.io.adapters import adapt_dataset
from xaita_ot.io.telemetry import load_csv
from xaita_ot.pipeline.v3_evaluation import audit_split_and_leakage


def main():
    parser = argparse.ArgumentParser(description="XAITA-OT V3 Phase-1 leakage audit")
    parser.add_argument("--dataset", required=True, choices=["SWaT", "BATADAL", "TON-IoT"])
    parser.add_argument("--csv", required=True)
    parser.add_argument("--output", default="artifacts/v3/leakage_audit.json")
    args = parser.parse_args()

    cfg = AppConfig()
    df = adapt_dataset(load_csv(args.csv), args.dataset)
    report = audit_split_and_leakage(df, cfg, cfg.attack_label_column)
    report.update({"dataset": args.dataset, "csv": str(Path(args.csv)), "tool": "v3_phase1_leakage_audit"})

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))
    raise SystemExit(0 if report["status"] == "PASS" else 1)


if __name__ == "__main__":
    main()
