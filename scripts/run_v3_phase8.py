"""Generate paper Tables 4-10, 17 and 18 from V3 evaluation artifacts."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from xaita_ot.pipeline.v3_phase8 import generate_phase8


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--swat", default="data/demo/swat_like.csv")
    p.add_argument("--batadal", default="data/demo/batadal_like.csv")
    p.add_argument("--toniot", default="data/demo/toniot_like.csv")
    p.add_argument("--artifact-root", default="artifacts/v3")
    p.add_argument("--out", default="artifacts/v3/phase8")
    p.add_argument("--seed", type=int, default=42)
    args = p.parse_args()
    paths = {"SWaT": args.swat, "BATADAL": args.batadal, "TON-IoT": args.toniot}
    manifest = generate_phase8(paths, args.artifact_root, args.out, args.seed)
    expected = {"4", "5", "6", "7", "8", "9", "10", "17", "18"}
    generated = set(manifest["generated"])
    acceptance = {
        "phase": "V3.8",
        "definition_of_complete": "implemented + executed + functional + verified",
        "expected_tables": sorted(expected),
        "generated_tables": sorted(generated),
        "all_nine_tables_generated": generated == expected and all(Path(v).exists() for v in manifest["generated"].values()),
        "na_policy": manifest["na_policy"],
        "overall": "PASS" if generated == expected else "FAIL",
        "complete": generated == expected and all(Path(v).exists() for v in manifest["generated"].values()),
    }
    out = Path(args.out); out.mkdir(parents=True, exist_ok=True)
    (out / "phase8_acceptance.json").write_text(json.dumps(acceptance, indent=2), encoding="utf-8")
    if not acceptance["complete"]:
        raise SystemExit("V3 Phase 8 acceptance failed")
    print("V3 Phase 8 automated result generation acceptance: PASS")
    print("Tables: 4, 5, 6, 7, 8, 9, 10, 17, 18")


if __name__ == "__main__":
    main()
