import argparse, json
from pathlib import Path
from xaita_ot.config import load_config
from xaita_ot.io.telemetry import load_csv, semantic_harmonize
from xaita_ot.io.adapters import normalize_labels
from xaita_ot.pipeline.preprocess import OTPreprocessor
from xaita_ot.pipeline.evaluation import chronological_split
from xaita_ot.models.trainer import Detector

p=argparse.ArgumentParser(); p.add_argument('--csv',required=True); p.add_argument('--config',default='configs/default.yaml'); p.add_argument('--out',default='artifacts/cnn_lstm.pt'); a=p.parse_args()
cfg=load_config(a.config); df=normalize_labels(semantic_harmonize(load_csv(a.csv)))
tr,va,te=chronological_split(df)
prep=OTPreprocessor(cfg.model.window_size); tw=prep.fit_transform_train(tr,cfg.attack_label_column); vw=prep.transform(va,cfg.attack_label_column); ew=prep.transform(te,cfg.attack_label_column)
det=Detector(tw.X.shape[-1],cfg.model); det.fit(tw.X,tw.y,cfg.model.epochs,cfg.model.batch_size,cfg.model.learning_rate)
metrics={'validation':det.evaluate(vw.X,vw.y),'test':det.evaluate(ew.X,ew.y),'device':str(det.device),'features':prep.feature_names,'window_size':cfg.model.window_size}
det.save(a.out); Path('artifacts/training_metrics.json').write_text(json.dumps(metrics,indent=2)); print(json.dumps(metrics,indent=2))
