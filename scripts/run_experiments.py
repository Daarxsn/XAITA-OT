import argparse
from pathlib import Path

from xaita_ot.config import load_config
from xaita_ot.pipeline.experiments import aggregate_runs, run_detection, write_results


def main():
    parser = argparse.ArgumentParser(description="Run XAITA-OT multi-seed detection experiments")
    parser.add_argument('--dataset', required=True, help='Dataset/environment name, e.g. SWaT')
    parser.add_argument('--csv', required=True)
    parser.add_argument('--config', default='configs/default.yaml')
    parser.add_argument('--out', default=None)
    args = parser.parse_args()
    cfg = load_config(args.config)
    runs = [run_detection(args.csv, args.dataset, cfg, seed) for seed in cfg.experiment.seeds]
    result = aggregate_runs(runs)
    out = args.out or str(Path(cfg.output_dir) / f'{args.dataset.lower()}_multi_seed.json')
    write_results(result, out)
    print(out)


if __name__ == '__main__':
    main()
