"""Run V3 Phase 7 case-study acceptance."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from xaita_ot.config import load_config
from xaita_ot.pipeline.v3_phase7 import build_case, write_case_artifact


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--swat", default="data/demo/swat_like.csv")
    parser.add_argument("--batadal", default="data/demo/batadal_like.csv")
    parser.add_argument("--toniot", default="data/demo/toniot_like.csv")
    parser.add_argument("--out", default="artifacts/v3/phase7")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--window-size", type=int, default=4)
    parser.add_argument("--top-n", type=int, default=1)
    args = parser.parse_args()
    cfg = load_config(); cfg.model.window_size = args.window_size
    paths = {"SWaT": args.swat, "BATADAL": args.batadal, "TON-IoT": args.toniot}
    outputs = []
    for dataset, path in paths.items():
        result = build_case(path, dataset, cfg, args.seed, args.top_n)
        outputs.append(result)
    artifact_paths = [write_case_artifact(r, args.out) for r in outputs]
    required = ("episode_selection", "attack_sequence", "btae_reconstruction", "attack_mapping", "attribution_hypotheses", "acfm", "xai", "risk", "cti", "provenance")
    complete = all(r["status"] == "PASS" and r["cases"] and all(all(k in c for k in required) for c in r["cases"]) for r in outputs)
    acceptance = {
        "phase": "V3.7",
        "definition_of_complete": "implemented + executed + functional + verified",
        "datasets": list(paths),
        "seed": args.seed,
        "required_components": list(required),
        "cases_per_dataset": [len(r["cases"]) for r in outputs],
        "artifacts_exist": all(Path(p).exists() for p in artifact_paths),
        "overall": "PASS" if complete else "FAIL",
        "complete": bool(complete),
        "mapping_boundary": "ATT&CK mappings are evidence-supported hypotheses, not ground-truth attribution claims.",
    }
    out = Path(args.out); out.mkdir(parents=True, exist_ok=True)
    (out / "phase7_acceptance.json").write_text(json.dumps(acceptance, indent=2), encoding="utf-8")
    if not complete: raise SystemExit("V3 Phase 7 case-study acceptance: FAIL")
    print("V3 Phase 7 case-study acceptance: PASS")
    print(f"Datasets: {len(outputs)}/3; cases: {sum(len(r['cases']) for r in outputs)}")
    print(f"Artifacts: {', '.join(artifact_paths)}")


if __name__ == "__main__":
    main()
