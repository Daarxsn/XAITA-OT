"""V3 directed cross-environment evaluation runner.

Runs all six directed transfers among SWaT, BATADAL and TON-IoT. The source
environment is used for training and the target environment is held out for
evaluation. Use --smoke for a fast structural execution with one seed and RF;
use the default configuration for the paper protocol once authorized real data
are available.
"""
from __future__ import annotations

import argparse
from pathlib import Path

from xaita_ot.config import load_config
from xaita_ot.pipeline.v3_evaluation import cross_environment_matrix


DATASETS = ("SWaT", "BATADAL", "TON-IoT")


def main():
    p = argparse.ArgumentParser(description="XAITA-OT V3 cross-environment evaluation")
    p.add_argument("--swat", required=True)
    p.add_argument("--batadal", required=True)
    p.add_argument("--toniot", required=True)
    p.add_argument("--config", default="configs/default.yaml")
    p.add_argument("--out", default="artifacts/v3/cross_environment.json")
    p.add_argument("--smoke", action="store_true", help="Use one seed and RF only for a fast execution check")
    args = p.parse_args()

    paths = {"SWaT": args.swat, "BATADAL": args.batadal, "TON-IoT": args.toniot}
    missing = [name for name, path in paths.items() if not Path(path).exists()]
    if missing:
        p.error("Missing dataset files: " + ", ".join(missing))

    cfg = load_config(args.config)
    seeds = [cfg.experiment.seeds[0]] if args.smoke else cfg.experiment.seeds
    detectors = ("random_forest",) if args.smoke else ("random_forest", "cnn", "lstm", "cnn_lstm")
    result = cross_environment_matrix(paths, cfg, seeds=seeds, detectors=detectors)
    result["mode"] = "smoke" if args.smoke else "paper"
    result["data_mode"] = "real_dataset_paths_supplied"
    result["warning"] = "Do not treat smoke/demo execution as benchmark evidence."

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    import json
    out.write_text(json.dumps(result, indent=2, allow_nan=False, default=str), encoding="utf-8")
    print(out)


if __name__ == "__main__":
    main()
