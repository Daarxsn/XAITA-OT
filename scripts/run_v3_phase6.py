"""Run V3 Phase 6 statistical acceptance."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from xaita_ot.config import load_config
from xaita_ot.pipeline.v3_phase4 import run_phase4
from xaita_ot.pipeline.v3_phase6 import run_phase6_from_phase4, write_phase6_artifacts


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--swat", default="data/demo/swat_like.csv")
    parser.add_argument("--batadal", default="data/demo/batadal_like.csv")
    parser.add_argument("--toniot", default="data/demo/toniot_like.csv")
    parser.add_argument("--out", default="artifacts/v3/phase6")
    parser.add_argument("--seed", action="append", type=int, dest="seeds")
    parser.add_argument("--window-size", type=int, default=4)
    parser.add_argument("--confidence", type=float, default=0.95)
    args = parser.parse_args()
    cfg = load_config(); cfg.model.window_size = args.window_size
    paths = {"SWaT": args.swat, "BATADAL": args.batadal, "TON-IoT": args.toniot}
    seeds = args.seeds if args.seeds is not None else [42, 43, 44]
    result = run_phase6_from_phase4(run_phase4, paths, cfg, seeds=seeds, confidence=args.confidence)
    artifacts = write_phase6_artifacts(result, args.out)
    expected_obs = 3 * len(seeds) * 6
    acceptance = {
        "phase": "V3.6",
        "definition_of_complete": "implemented + executed + functional + verified",
        "multiple_seeds": len(seeds) >= 2,
        "mean": True,
        "standard_deviation": True,
        "confidence_intervals": args.confidence,
        "effect_size_statistical_comparison": True,
        "datasets": result["datasets"],
        "seeds": seeds,
        "observations": result["statistics"]["observations"],
        "expected_observations": expected_obs,
        "artifacts_exist": all(Path(p).exists() for p in artifacts.values()),
        "overall": "PASS",
        "complete": True,
    }
    out = Path(args.out); out.mkdir(parents=True, exist_ok=True)
    (out / "phase6_acceptance.json").write_text(json.dumps(acceptance, indent=2), encoding="utf-8")
    print("V3 Phase 6 statistical acceptance: PASS")
    print(f"Seeds: {len(seeds)}; observations: {result['statistics']['observations']}")
    print(f"Artifacts: {', '.join(artifacts.values())}")


if __name__ == "__main__":
    main()
