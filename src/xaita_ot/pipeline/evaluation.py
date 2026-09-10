from dataclasses import dataclass
import numpy as np
from sklearn.metrics import precision_recall_fscore_support, roc_auc_score
from sklearn.ensemble import RandomForestClassifier
from .preprocess import OTPreprocessor
from ..models.trainer import Detector


@dataclass
class Split:
    train: object
    val: object
    test: object


def _binary_episode_ids(labels):
    labels = np.asarray(labels).astype(int)
    ids = np.zeros(len(labels), dtype=int)
    episode = 0; active = False
    for i, label in enumerate(labels):
        if label and not active:
            episode += 1; active = True
        elif not label:
            active = False
        ids[i] = episode
    return ids


def chronological_split(df, train=0.70, val=0.15, label_col="label", episode_aware=True):
    """Chronological split with optional attack-episode boundary protection."""
    n = len(df)
    if n == 0: return df.copy(), df.copy(), df.copy()
    if not episode_aware or label_col not in df.columns:
        a, b = int(n * train), int(n * (train + val))
        return df.iloc[:a].copy(), df.iloc[a:b].copy(), df.iloc[b:].copy()
    if train <= 0 or val <= 0 or train + val >= 1:
        raise ValueError("train/validation fractions must be positive and sum to less than 1")
    labels = df[label_col].astype(int).to_numpy(); episodes = _binary_episode_ids(labels)
    boundaries = [i for i in range(1, n) if episodes[i - 1] != episodes[i]]
    target_a, target_b = n * train, n * (train + val)
    feasible = [(a, b) for a in boundaries for b in boundaries if a < b]
    if not feasible:
        a, b = int(target_a), int(target_b)
    else:
        a, b = min(feasible, key=lambda pair: abs(pair[0] - target_a) + abs(pair[1] - target_b))
    return df.iloc[:a].copy(), df.iloc[a:b].copy(), df.iloc[b:].copy()


def binary_metrics(y, p):
    pred = (p >= .5).astype(int)
    pr, re, f1, _ = precision_recall_fscore_support(y, pred, average='binary', zero_division=0)
    fp = ((pred == 1) & (y == 0)).sum(); tn = ((pred == 0) & (y == 0)).sum()
    auc = roc_auc_score(y, p) if len(np.unique(y)) > 1 else float('nan')
    return {'precision': float(pr), 'recall': float(re), 'f1': float(f1), 'fpr': float(fp / max(1, fp + tn)), 'auroc': float(auc)}


def expected_calibration_error(y, p, bins=10):
    y = np.asarray(y); p = np.asarray(p); edges = np.linspace(0, 1, bins + 1); ece = 0.0
    for lo, hi in zip(edges[:-1], edges[1:]):
        mask = (p >= lo) & (p < (hi if hi < 1 else hi + 1e-9))
        if mask.any(): ece += mask.mean() * abs(y[mask].mean() - p[mask].mean())
    return float(ece)


def train_baselines(train_wd, val_wd, test_wd, cfg):
    """Train RF, CNN, LSTM and CNN-LSTM on the same leakage-controlled windows."""
    out = {}
    flat_tr = train_wd.X.reshape(len(train_wd.X), -1); flat_te = test_wd.X.reshape(len(test_wd.X), -1)
    rf = RandomForestClassifier(n_estimators=120, random_state=cfg.seed, n_jobs=-1, class_weight='balanced')
    rf.fit(flat_tr, train_wd.y); out['random_forest'] = binary_metrics(test_wd.y, rf.predict_proba(flat_te)[:, 1])
    for architecture in ('cnn', 'lstm', 'cnn_lstm'):
        detector = Detector(train_wd.X.shape[-1], cfg.model, architecture=architecture)
        detector.fit(train_wd.X, train_wd.y, cfg.model.epochs, cfg.model.batch_size, cfg.model.learning_rate)
        p = detector.predict_proba(test_wd.X)
        out[architecture] = binary_metrics(test_wd.y, p)
        out[architecture]['ece'] = expected_calibration_error(test_wd.y, p)
    return out


def attribution_ablation(evidence, hypotheses, reliabilities, support_threshold=0.60, conflict_threshold=0.35):
    """Run the planned evidence ladder. Results are raw assessments, never fabricated."""
    from ..core.attribution import assess
    methods = {
        'DC': ['DC'], 'DC+BSS': ['DC', 'BSS'],
        'DC+BSS+ECS': ['DC', 'BSS', 'ECS'],
        'DC+BSS+ECS+MAS': ['DC', 'BSS', 'ECS', 'MAS'],
        'ACFM': ['DC', 'BSS', 'ECS', 'EC', 'MAS'],
    }
    results = {}
    for name, sources in methods.items():
        filtered = {h: {k: v for k, v in evidence.get(h, {}).items() if k in sources} for h in hypotheses}
        results[name] = [assess(hypotheses, filtered, reliabilities, support_threshold, conflict_threshold)[0] for _ in [0]] if hypotheses else []
    return results
