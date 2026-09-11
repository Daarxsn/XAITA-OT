"""Run V3 Phase 2: six directed cross-environment transfers."""
from __future__ import annotations

import argparse
from pathlib import Path

from xaita_ot.config import load_config
from xaita_ot.pipeline.v3_phase2 import cross_environment_phase2, write_phase2_artifacts


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--swat", default="data/demo/swat_like.csv")
    parser.add_argument("--batadal", default="data/demo/batadal_like.csv")
    parser.add_argument("--toniot", default="data/demo/toniot_like.csv")
    parser.add_argument("--out", default="artifacts/v3/phase2")
    parser.add_argument("--seed", action="append", type=int, dest="seeds")
    parser.add_argument("--detector", action="append", dest="detectors")
    parser.add_argument("--window-size", type=int, default=8)
    parser.add_argument("--epochs", type=int, default=None)
    args = parser.parse_args()

    cfg = load_config()
    cfg.model.window_size = args.window_size
    if args.epochs is not None:
        cfg.model.epochs = args.epochs
    paths = {"SWaT": args.swat, "BATADAL": args.batadal, "TON-IoT": args.toniot}
    detectors = tuple(args.detectors) if args.detectors else ("random_forest", "cnn", "lstm", "cnn_lstm")
    result = cross_environment_phase2(paths, cfg, seeds=args.seeds, detectors=detectors)
    write_phase2_artifacts(result, args.out)
    print("V3 Phase 2 cross-environment acceptance: PASS")
    print(f"Transfers: {result['pair_count']}/6")
    print(f"Detectors: {', '.join(detectors)}")


if __name__ == "__main__":
    main()
