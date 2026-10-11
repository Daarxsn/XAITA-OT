"""Run the agreed Phase 4 C1-C6 attribution evaluation."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from xaita_ot.config import load_config
from xaita_ot.pipeline.attribution_evaluation import (
    PHASE4_CONFIGURATIONS,
    run_phase4_attribution,
    write_phase4_attribution_artifacts,
)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--swat", default="data/demo/swat_like.csv")
    parser.add_argument("--batadal", default="data/demo/batadal_like.csv")
    parser.add_argument("--toniot", default="data/demo/toniot_like.csv")
    parser.add_argument("--out", default="artifacts/phase4-attribution")
    parser.add_argument("--seed", action="append", type=int, dest="seeds")
    parser.add_argument("--window-size", type=int, default=4)
    parser.add_argument(
        "--source-kind",
        choices=("real_benchmark", "synthetic_fixture", "unverified"),
        default="unverified",
        help="Provenance declaration only; it does not independently authenticate data.",
    )
    args = parser.parse_args()
    if args.window_size < 2:
        parser.error("--window-size must be at least 2")

    config = load_config()
    config.model.window_size = args.window_size
    paths = {"SWaT": args.swat, "BATADAL": args.batadal, "TON-IoT": args.toniot}
    result = run_phase4_attribution(
        paths, config, seeds=args.seeds, source_kind=args.source_kind
    )
    outputs = write_phase4_attribution_artifacts(result, args.out)
    acceptance = {
        "schema_version": "XAITA-OT-PHASE4-ATTRIBUTION-ACCEPTANCE-1.0",
        "phase": result["phase"],
        "status": "PASS" if (
            result["status"] == "EXECUTED"
            and result["configurations"] == list(PHASE4_CONFIGURATIONS)
            and all(
                set(run["configurations"]) == set(PHASE4_CONFIGURATIONS)
                for run in result["runs"]
            )
        ) else "FAIL",
        "source_kind": result["source_kind"],
        "benchmark_claims_allowed": result["benchmark_claims_allowed"],
        "benchmark_claims_candidate": result["benchmark_claims_candidate"],
        "configurations": result["configurations"],
        "datasets": result["datasets"],
        "seeds": result["seeds"],
        "run_count": len(result["runs"]),
        "fingerprint": result["fingerprint"],
        "artifacts": {key: Path(value).name for key, value in outputs.items()},
    }
    acceptance_path = Path(args.out) / "phase4_attribution_acceptance.json"
    acceptance_path.write_text(
        json.dumps(acceptance, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    if acceptance["status"] != "PASS":
        raise SystemExit("Phase 4 C1-C6 attribution evaluation: FAIL")
    print("Phase 4 C1-C6 attribution evaluation: PASS (execution/structure only)")
    print(f"Configurations: {len(result['configurations'])}/6")
    print(f"Dataset/seed runs: {len(result['runs'])}")
    print(f"Benchmark claims allowed: {result['benchmark_claims_allowed']}")
    print(f"Artifacts: {', '.join(outputs.values())}, {acceptance_path}")


if __name__ == "__main__":
    main()
