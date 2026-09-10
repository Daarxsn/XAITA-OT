from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import json
from pathlib import Path
import time

import numpy as np

from ..config import AppConfig
from ..core.seed import set_seed
from ..io.telemetry import load_csv, semantic_harmonize
from ..io.adapters import adapt_dataset
from .evaluation import chronological_split, train_baselines
from .preprocess import OTPreprocessor


@dataclass
class ExperimentRun:
    experiment_id: str
    dataset: str
    seed: int
    started_at: str
    duration_seconds: float
    config: dict
    rows: dict
    windows: dict
    metrics: dict


def run_detection(csv_path: str | Path, dataset: str, config: AppConfig, seed: int | None = None) -> ExperimentRun:
    started = time.perf_counter()
    run_seed = config.seed if seed is None else seed
    set_seed(run_seed)
    df = adapt_dataset(semantic_harmonize(load_csv(csv_path)), dataset)
    train, val, test = chronological_split(
        df, train=config.experiment.train_fraction, val=config.experiment.validation_fraction,
        label_col=config.attack_label_column, episode_aware=config.experiment.episode_aware,
    )
    prep = OTPreprocessor(config.model.window_size)
    train_w = prep.fit_transform_train(train, config.attack_label_column)
    val_w = prep.transform(val, config.attack_label_column)
    test_w = prep.transform(test, config.attack_label_column)
    metrics = train_baselines(train_w, val_w, test_w, config, seed=run_seed)
    duration = time.perf_counter() - started
    now = datetime.now(timezone.utc)
    return ExperimentRun(
        experiment_id=f"{dataset}-{run_seed}-{now.strftime('%Y%m%dT%H%M%SZ')}",
        dataset=dataset, seed=run_seed, started_at=now.isoformat(),
        duration_seconds=float(duration), config=config.model_dump(mode='json'),
        rows={'train': len(train), 'validation': len(val), 'test': len(test)},
        windows={'train': len(train_w.X), 'validation': len(val_w.X), 'test': len(test_w.X)}, metrics=metrics,
    )


def aggregate_runs(runs: list[ExperimentRun]) -> dict:
    if not runs:
        return {'schema_version': 'XAITA-OT-V2-EXPERIMENT-1.0', 'runs': [], 'aggregate': {}}
    metric_values = {}
    for run in runs:
        for model, metrics in run.metrics.items():
            for metric, value in metrics.items():
                if isinstance(value, (int, float)) and np.isfinite(value):
                    metric_values.setdefault(model, {}).setdefault(metric, []).append(float(value))
    aggregate = {
        model: {
            metric: {
                'mean': float(np.mean(values)),
                'std': float(np.std(values, ddof=1)) if len(values) > 1 else 0.0,
                'n': len(values),
            }
            for metric, values in metrics.items()
        }
        for model, metrics in metric_values.items()
    }
    return {
        'schema_version': 'XAITA-OT-V2-EXPERIMENT-1.0',
        'runs': [asdict(r) for r in runs],
        'aggregate': aggregate,
    }


def write_results(result: dict, path: str | Path):
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(result, indent=2, allow_nan=False, default=str), encoding='utf-8')
