import argparse
import json
from pathlib import Path

from xaita_ot.config import load_config
from xaita_ot.core.seed import set_seed
from xaita_ot.io.telemetry import load_csv, semantic_harmonize
from xaita_ot.io.adapters import normalize_labels
from xaita_ot.pipeline.preprocess import OTPreprocessor
from xaita_ot.pipeline.evaluation import chronological_split
from xaita_ot.models.trainer import Detector


p = argparse.ArgumentParser(description="Train the XAITA-OT CNN-LSTM detector")
p.add_argument("--csv", required=True)
p.add_argument("--config", default="configs/default.yaml")
p.add_argument("--out", default="artifacts/cnn_lstm.pt")
p.add_argument("--metrics-out", default="artifacts/training_metrics.json")
a = p.parse_args()

cfg = load_config(a.config)
set_seed(cfg.seed)
df = normalize_labels(semantic_harmonize(load_csv(a.csv)))
tr, va, te = chronological_split(
    df,
    train=cfg.experiment.train_fraction,
    val=cfg.experiment.validation_fraction,
    label_col=cfg.attack_label_column,
    episode_aware=cfg.experiment.episode_aware,
)
prep = OTPreprocessor(cfg.model.window_size)
tw = prep.fit_transform_train(tr, cfg.attack_label_column)
vw = prep.transform(va, cfg.attack_label_column)
ew = prep.transform(te, cfg.attack_label_column)
det = Detector(tw.X.shape[-1], cfg.model, architecture="cnn_lstm")
det.fit(tw.X, tw.y, cfg.model.epochs, cfg.model.batch_size, cfg.model.learning_rate)
metrics = {
    "dataset_rows": {"train": len(tr), "validation": len(va), "test": len(te)},
    "window_counts": {"train": len(tw.X), "validation": len(vw.X), "test": len(ew.X)},
    "validation": det.evaluate(vw.X, vw.y),
    "test": det.evaluate(ew.X, ew.y),
    "device": str(det.device),
    "architecture": det.architecture,
    "features": prep.feature_names,
    "window_size": cfg.model.window_size,
    "seed": cfg.seed,
    "episode_aware": cfg.experiment.episode_aware,
    "imputation_values": prep.fill_values,
}
Path(a.out).parent.mkdir(parents=True, exist_ok=True)
det.save(a.out)
Path(a.metrics_out).parent.mkdir(parents=True, exist_ok=True)
Path(a.metrics_out).write_text(json.dumps(metrics, indent=2, allow_nan=False), encoding="utf-8")
print(json.dumps(metrics, indent=2))
