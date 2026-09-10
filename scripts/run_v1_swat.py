"""Execute the complete V1 SWaT path: load -> detect -> BTAE -> attribution -> XAI -> risk -> CTI."""
import argparse
import json
from pathlib import Path

import numpy as np

from xaita_ot.config import load_config
from xaita_ot.core.seed import set_seed
from xaita_ot.core.schemas import DetectionEvent
from xaita_ot.io.telemetry import load_csv, semantic_harmonize
from xaita_ot.io.adapters import adapt_swat, normalize_labels
from xaita_ot.pipeline.preprocess import OTPreprocessor
from xaita_ot.pipeline.evaluation import chronological_split, binary_metrics, expected_calibration_error
from xaita_ot.models.trainer import Detector
from xaita_ot.pipeline.engine import XAITAEngine
from xaita_ot.explain.shap_xai import shap_feature_importance


def main():
    parser = argparse.ArgumentParser(description="Run XAITA-OT V1 end-to-end on SWaT")
    parser.add_argument("--csv", required=True, help="Normalized or native SWaT CSV")
    parser.add_argument("--config", default="configs/default.yaml")
    parser.add_argument("--out", default="artifacts/v1_swat.json")
    parser.add_argument("--model-out", default="artifacts/v1_cnn_lstm.pt")
    args = parser.parse_args()

    cfg = load_config(args.config)
    set_seed(cfg.seed)
    df = normalize_labels(adapt_swat(semantic_harmonize(load_csv(args.csv))))
    train, val, test = chronological_split(
        df,
        train=cfg.experiment.train_fraction,
        val=cfg.experiment.validation_fraction,
        label_col=cfg.attack_label_column,
        episode_aware=cfg.experiment.episode_aware,
    )
    prep = OTPreprocessor(cfg.model.window_size)
    train_w = prep.fit_transform_train(train, cfg.attack_label_column)
    val_w = prep.transform(val, cfg.attack_label_column)
    test_w = prep.transform(test, cfg.attack_label_column)

    detector = Detector(train_w.X.shape[-1], cfg.model, architecture="cnn_lstm")
    detector.fit(train_w.X, train_w.y, cfg.model.epochs, cfg.model.batch_size, cfg.model.learning_rate)
    val_p = detector.predict_proba(val_w.X)
    test_p = detector.predict_proba(test_w.X)
    detector_metrics = {
        "validation": {**binary_metrics(val_w.y, val_p), "ece": expected_calibration_error(val_w.y, val_p)},
        "test": {**binary_metrics(test_w.y, test_p), "ece": expected_calibration_error(test_w.y, test_p)},
    }
    detector.save(args.model_out)

    positive = np.flatnonzero(test_p >= detector.threshold)
    events = []
    for idx in positive:
        features = {name: float(test_w.X[idx, -1, j]) for j, name in enumerate(test_w.feature_names)}
        behavior_label = "anomaly"
        if "behavior_label" in test.columns:
            # The window endpoint aligns with the last raw row in the test split.
            endpoint = min(idx + cfg.model.window_size - 1, len(test) - 1)
            behavior_label = str(test.iloc[endpoint]["behavior_label"])
        events.append(DetectionEvent(
            event_id=f"det-{idx:06d}",
            timestamp=np.datetime64(test_w.timestamps[idx]).astype("datetime64[us]").astype(object),
            asset=str(test_w.assets[idx]),
            protocol=str(test_w.protocols[idx]),
            label=behavior_label,
            detection_confidence=float(test_p[idx]),
            features=features,
            source=str(test_w.sources[idx]),
            destination=str(test_w.destinations[idx]),
        ))

    engine = XAITAEngine(cfg)
    incidents = engine.analyze_events(events)

    xai = None
    if len(test_w.X):
        sample_n = min(cfg.experiment.xai_explanation_samples, len(test_w.X))
        bg_n = min(cfg.experiment.xai_background_samples, len(train_w.X))
        sample_idx = np.argsort(test_p)[-sample_n:]
        background = train_w.X[:bg_n]
        xai = shap_feature_importance(detector.model, background, test_w.X[sample_idx], test_w.feature_names)
        for incident in incidents:
            incident["xai"]["feature_level"]["top_features"] = xai
            incident["xai"]["feature_level"]["method"] = "SHAP GradientExplainer"

    result = {
        "schema_version": "XAITA-OT-V1-1.0",
        "dataset": "SWaT",
        "seed": cfg.seed,
        "split": {
            "train_rows": len(train), "validation_rows": len(val), "test_rows": len(test),
            "episode_aware": cfg.experiment.episode_aware,
        },
        "detector": detector_metrics,
        "detected_event_count": len(events),
        "incident_count": len(incidents),
        "shap_feature_importance": xai,
        "incidents": incidents,
    }
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(json.dumps(result, indent=2, allow_nan=False, default=str), encoding="utf-8")
    print(json.dumps(result, indent=2, allow_nan=False, default=str))


if __name__ == "__main__":
    main()
