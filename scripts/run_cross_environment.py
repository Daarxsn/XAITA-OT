import argparse
import json
from pathlib import Path

from xaita_ot.config import load_config
from xaita_ot.pipeline.experiments import aggregate_runs, run_detection, write_results


def main():
    p = argparse.ArgumentParser(description="Run XAITA-OT across named OT/ICS environments")
    p.add_argument('--dataset', action='append', nargs=2, metavar=('NAME', 'CSV'), required=True,
                   help='Repeat for each environment, e.g. --dataset SWaT swat.csv')
    p.add_argument('--config', default='configs/default.yaml')
    p.add_argument('--out', default='artifacts/cross_environment.json')
    args = p.parse_args()
    cfg = load_config(args.config)
    environments = {}
    for name, csv in args.dataset:
        runs = [run_detection(csv, name, cfg, seed) for seed in cfg.experiment.seeds]
        environments[name] = aggregate_runs(runs)
    result = {'environments': environments, 'dataset_count': len(environments), 'seeds': cfg.experiment.seeds}
    write_results(result, args.out)
    print(args.out)


if __name__ == '__main__':
    main()
