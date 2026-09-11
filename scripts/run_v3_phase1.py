"""Execute the V3 Phase 1 Leakage & Reproducibility acceptance audit.

This runner is deliberately fail-closed: a Phase 1 run is COMPLETE only when
all required gates execute successfully and every gate reports PASS.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from xaita_ot.config import load_config
from xaita_ot.io.adapters import adapt_dataset
from xaita_ot.io.telemetry import load_csv, semantic_harmonize
from xaita_ot.pipeline.v3_evaluation import audit_split_and_leakage, reproducibility_audit


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--csv", required=True)
    parser.add_argument("--dataset", default="SWaT")
    parser.add_argument("--out", default="artifacts/v3/phase1")
    args = parser.parse_args()

    cfg = load_config()
    df = adapt_dataset(semantic_harmonize(load_csv(args.csv)), args.dataset)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    checks = {}
    errors = []
    try:
        checks["split_and_leakage"] = audit_split_and_leakage(df, cfg, cfg.attack_label_column)
    except Exception as exc:
        checks["split_and_leakage"] = {"status": "FAIL", "error": f"{type(exc).__name__}: {exc}"}
        errors.append("split_and_leakage")

    for seed in cfg.experiment.seeds:
        try:
            checks[f"reproducibility_seed_{seed}"] = reproducibility_audit(df, cfg, cfg.attack_label_column, seed)
        except Exception as exc:
            checks[f"reproducibility_seed_{seed}"] = {"status": "FAIL", "seed": seed, "error": f"{type(exc).__name__}: {exc}"}
            errors.append(f"reproducibility_seed_{seed}")

    required = ["split_and_leakage"] + [f"reproducibility_seed_{s}" for s in cfg.experiment.seeds]
    all_pass = not errors and all(checks.get(k, {}).get("status") == "PASS" for k in required)
    report = {
        "phase": "V3 Phase 1 — Leakage & Reproducibility Audit",
        "definition_of_complete": ["implemented", "executed", "functional", "verified"],
        "dataset": args.dataset,
        "input": str(args.csv),
        "seeds": list(cfg.experiment.seeds),
        "required_gates": required,
        "checks": checks,
        "errors": errors,
        "overall": "PASS" if all_pass else "FAIL",
        "complete": bool(all_pass),
    }
    (out / "phase1_acceptance.json").write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")
    (out / "split_audit.json").write_text(json.dumps(checks["split_and_leakage"], indent=2, default=str), encoding="utf-8")
    repro = {k: v for k, v in checks.items() if k.startswith("reproducibility_seed_")}
    (out / "reproducibility_audit.json").write_text(json.dumps(repro, indent=2, default=str), encoding="utf-8")
    print(json.dumps(report, indent=2, default=str))
    return 0 if all_pass else 1


if __name__ == "__main__":
    raise SystemExit(main())
