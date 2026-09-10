"""Unified V2 runner for SWaT, BATADAL and TON-IoT.

The command requires real dataset CSV paths. It never substitutes synthetic values for
missing benchmarks; unavailable datasets are reported explicitly in the manifest.
"""
import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

from xaita_ot.config import load_config
from xaita_ot.pipeline.experiments import run_detection


def main():
    p = argparse.ArgumentParser(description="Run XAITA-OT V2 controlled experiments")
    p.add_argument("--swat")
    p.add_argument("--batadal")
    p.add_argument("--toniot")
    p.add_argument("--config", default="configs/default.yaml")
    p.add_argument("--out", default="artifacts/v2/experiment_manifest.json")
    args = p.parse_args()
    cfg = load_config(args.config)
    paths = {"SWaT": args.swat, "BATADAL": args.batadal, "TON-IoT": args.toniot}
    manifest = {
        "schema_version": "XAITA-OT-V2-MANIFEST-1.0",
        "started_at": datetime.now(timezone.utc).isoformat(),
        "config": cfg.model_dump(mode="json"),
        "datasets": {},
    }
    for dataset, csv_path in paths.items():
        if not csv_path:
            manifest["datasets"][dataset] = {"status": "not_provided"}
            continue
        if not Path(csv_path).exists():
            manifest["datasets"][dataset] = {"status": "missing", "path": str(csv_path)}
            continue
        runs = []
        for seed in cfg.experiment.seeds:
            run = run_detection(csv_path, dataset, cfg, seed)
            runs.append(run.__dict__)
        manifest["datasets"][dataset] = {"status": "completed", "runs": runs}
    manifest["finished_at"] = datetime.now(timezone.utc).isoformat()
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(manifest, indent=2, allow_nan=False, default=str), encoding="utf-8")
    print(out)


if __name__ == "__main__":
    main()
