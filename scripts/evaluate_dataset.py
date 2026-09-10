import argparse
import json
from pathlib import Path

from xaita_ot.config import load_config
from xaita_ot.core.seed import set_seed
from xaita_ot.io.telemetry import load_csv, semantic_harmonize
from xaita_ot.pipeline.preprocess import OTPreprocessor
from xaita_ot.pipeline.evaluation import chronological_split, train_baselines


def main():
    p = argparse.ArgumentParser(description="Run a leakage-aware XAITA-OT detection evaluation")
    p.add_argument('--csv', required=True)
    p.add_argument('--config', default='configs/default.yaml')
    p.add_argument('--out', default='artifacts/evaluation.json')
    args = p.parse_args()

    cfg = load_config(args.config)
    set_seed(cfg.seed)
    df = semantic_harmonize(load_csv(args.csv))
    tr, va, te = chronological_split(
        df,
        train=cfg.experiment.train_fraction,
        val=cfg.experiment.validation_fraction,
        label_col=cfg.attack_label_column,
        episode_aware=cfg.experiment.episode_aware,
    )
    prep = OTPreprocessor(cfg.model.window_size)
    train_wd = prep.fit_transform_train(tr, cfg.attack_label_column)
    val_wd = prep.transform(va, cfg.attack_label_column)
    test_wd = prep.transform(te, cfg.attack_label_column)
    result = {
        'dataset_rows': {'train': len(tr), 'validation': len(va), 'test': len(te)},
        'window_counts': {'train': len(train_wd.X), 'validation': len(val_wd.X), 'test': len(test_wd.X)},
        'episode_aware': cfg.experiment.episode_aware,
        'seed': cfg.seed,
        'metrics': train_baselines(train_wd, val_wd, test_wd, cfg),
    }
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(json.dumps(result, indent=2, allow_nan=False), encoding='utf-8')
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
