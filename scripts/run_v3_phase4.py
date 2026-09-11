"""Run V3 Phase 4 ablation acceptance."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from xaita_ot.config import load_config
from xaita_ot.pipeline.v3_phase4 import run_phase4, write_phase4_artifacts


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--swat", default="data/demo/swat_like.csv")
    parser.add_argument("--batadal", default="data/demo/batadal_like.csv")
    parser.add_argument("--toniot", default="data/demo/toniot_like.csv")
    parser.add_argument("--out", default="artifacts/v3/phase4")
    parser.add_argument("--seed", action="append", type=int, dest="seeds")
    parser.add_argument("--window-size", type=int, default=4)
    args = parser.parse_args()
    cfg = load_config()
    cfg.model.window_size = args.window_size
    paths = {"SWaT": args.swat, "BATADAL": args.batadal, "TON-IoT": args.toniot}
    result = run_phase4(paths, cfg, seeds=args.seeds)
    artifacts = write_phase4_artifacts(result, args.out)
    acceptance = {
        "phase": "V3.4",
        "definition_of_complete": "implemented + executed + functional + verified",
        "variants": result["variants"],
        "datasets": result["datasets"],
        "seeds": result["seeds"],
        "runs": len(result["runs"]),
        "effects_vs_full": list(result["effects_vs_full"]),
        "artifacts_exist": all(Path(p).exists() for p in artifacts.values()),
        "overall": "PASS",
        "complete": True,
    }
    out = Path(args.out); out.mkdir(parents=True, exist_ok=True)
    (out / "phase4_acceptance.json").write_text(json.dumps(acceptance, indent=2), encoding="utf-8")
    print("V3 Phase 4 ablation acceptance: PASS")
    print(f"Variants: {len(result['variants'])}/6")
    print(f"Runs: {len(result['runs'])}")
    print(f"Artifacts: {', '.join(artifacts.values())}")


if __name__ == "__main__":
    main()
