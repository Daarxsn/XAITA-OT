from dataclasses import dataclass
import hashlib

import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import precision_recall_fscore_support, roc_auc_score
from sklearn.model_selection import train_test_split

from .preprocess import WindowedData
from ..models.trainer import Detector
from ..core.seed import set_seed


@dataclass
class Split:
    train: object
    val: object
    test: object


def _binary_episode_ids(labels):
    labels = np.asarray(labels).astype(int)
    ids = np.zeros(len(labels), dtype=int)
    episode = 0
    active = False
    for i, label in enumerate(labels):
        if label and not active:
            episode += 1
            active = True
        elif not label:
            active = False
        ids[i] = episode
    return ids


def _validate_fractions(train, val):
    if train <= 0 or val <= 0 or train + val >= 1:
        raise ValueError("train/validation fractions must be positive and sum to less than 1")


def stratified_split(df, train=0.70, val=0.15, label_col="label", seed=42):
    """Stratified row split for non-temporal data.

    This preserves class proportions but does not prevent duplicate feature
    patterns from crossing partitions. Prefer group_stratified_split when
    duplicate/correlated flow records are present.
    """
    if len(df) == 0:
        return df.copy(), df.copy(), df.copy()
    _validate_fractions(train, val)
    if label_col not in df.columns:
        raise ValueError(f"Cannot stratify without label column '{label_col}'")
    labels = df[label_col].astype(int)
    if labels.nunique() < 2:
        raise ValueError("Stratified split requires at least two classes")
    train_df, remainder = train_test_split(
        df, train_size=train, random_state=seed, stratify=labels
    )
    val_share = val / (1.0 - train)
    val_df, test_df = train_test_split(
        remainder, train_size=val_share, random_state=seed,
        stratify=remainder[label_col].astype(int)
    )
    return train_df.sort_index().copy(), val_df.sort_index().copy(), test_df.sort_index().copy()


def _feature_group_ids(df, label_col):
    excluded = {label_col, "type", "timestamp", "date", "time"}
    columns = [c for c in df.columns if c not in excluded]
    if not columns:
        raise ValueError("Cannot create feature groups: no feature columns remain")
    groups = []
    for row in df[columns].itertuples(index=False, name=None):
        payload = "\x1f".join("" if value is None else repr(value) for value in row)
        groups.append(hashlib.sha256(payload.encode("utf-8")).hexdigest())
    return np.asarray(groups)


def group_stratified_split(df, train=0.70, val=0.15, label_col="label", seed=42):
    """Split identical model-feature patterns as indivisible groups.

    This is the default non-temporal protocol for TON-IoT Network. It prevents
    exact duplicate feature patterns from appearing in multiple partitions.
    Groups with conflicting labels are rejected.
    """
    if len(df) == 0:
        return df.copy(), df.copy(), df.copy()
    _validate_fractions(train, val)
    if label_col not in df.columns:
        raise ValueError(f"Cannot group-split without label column '{label_col}'")

    groups = _feature_group_ids(df, label_col)
    group_labels = {}
    for group, label in zip(groups, df[label_col].astype(int).to_numpy()):
        label = int(label)
        if group in group_labels and group_labels[group] != label:
            raise ValueError("A feature group contains conflicting labels; refusing to split")
        group_labels[group] = label

    unique_groups = np.asarray(list(group_labels))
    unique_labels = np.asarray([group_labels[g] for g in unique_groups])
    if np.unique(unique_labels).size < 2:
        raise ValueError("Group-stratified split requires at least two classes")

    train_groups, remainder_groups = train_test_split(
        unique_groups, train_size=train, random_state=seed, stratify=unique_labels
    )
    remainder_labels = np.asarray([group_labels[g] for g in remainder_groups])
    val_share = val / (1.0 - train)
    val_groups, test_groups = train_test_split(
        remainder_groups, train_size=val_share, random_state=seed,
        stratify=remainder_labels
    )

    train_set, val_set, test_set = map(set, (train_groups, val_groups, test_groups))
    train_mask = np.fromiter((g in train_set for g in groups), dtype=bool, count=len(groups))
    val_mask = np.fromiter((g in val_set for g in groups), dtype=bool, count=len(groups))
    test_mask = np.fromiter((g in test_set for g in groups), dtype=bool, count=len(groups))

    return (
        df.loc[train_mask].sort_index().copy(),
        df.loc[val_mask].sort_index().copy(),
        df.loc[test_mask].sort_index().copy(),
    )


def chronological_split(df, train=0.70, val=0.15, label_col="label", episode_aware=True):
    """Chronological split with optional attack-episode boundary protection."""
    n = len(df)
    if n == 0:
        return df.copy(), df.copy(), df.copy()
    _validate_fractions(train, val)
    if not episode_aware or label_col not in df.columns:
        a, b = int(n * train), int(n * (train + val))
        return df.iloc[:a].copy(), df.iloc[a:b].copy(), df.iloc[b:].copy()

    labels = df[label_col].astype(int).to_numpy()
    episodes = _binary_episode_ids(labels)
    boundaries = [i for i in range(1, n) if episodes[i - 1] != episodes[i]]
    target_a, target_b = n * train, n * (train + val)
    feasible = [(a, b) for a in boundaries for b in boundaries if a < b]
    if not feasible:
        a, b = int(target_a), int(target_b)
    else:
        a, b = min(feasible, key=lambda pair: abs(pair[0] - target_a) + abs(pair[1] - target_b))
    return df.iloc[:a].copy(), df.iloc[a:b].copy(), df.iloc[b:].copy()


def select_threshold(y, p, metric="f1"):
    """Select a decision threshold on validation predictions only."""
    y = np.asarray(y).astype(int)
    p = np.asarray(p, dtype=float)
    if len(y) == 0 or np.unique(y).size < 2:
        return 0.5

    thresholds = np.unique(np.concatenate(([0.0], p, [1.0])))
    best_threshold, best_score = 0.5, -np.inf
    for threshold in thresholds:
        pred = (p >= threshold).astype(int)
        pr, re, f1, _ = precision_recall_fscore_support(
            y, pred, average="binary", zero_division=0
        )
        if metric == "f1":
            score = f1
        elif metric == "balanced_accuracy":
            tn = ((pred == 0) & (y == 0)).sum()
            fp = ((pred == 1) & (y == 0)).sum()
            specificity = tn / max(1, tn + fp)
            score = (re + specificity) / 2.0
        else:
            raise ValueError("threshold_metric must be 'f1' or 'balanced_accuracy'")
        if score > best_score or (np.isclose(score, best_score) and threshold < best_threshold):
            best_threshold, best_score = float(threshold), float(score)
    return best_threshold


def binary_metrics(y, p, threshold=0.5):
    y = np.asarray(y).astype(int)
    p = np.asarray(p, dtype=float)
    pred = (p >= threshold).astype(int)
    pr, re, f1, _ = precision_recall_fscore_support(
        y, pred, average="binary", zero_division=0
    )
    fp = ((pred == 1) & (y == 0)).sum()
    tn = ((pred == 0) & (y == 0)).sum()
    auc = roc_auc_score(y, p) if len(np.unique(y)) > 1 else float("nan")
    return {
        "precision": float(pr),
        "recall": float(re),
        "f1": float(f1),
        "fpr": float(fp / max(1, fp + tn)),
        "auroc": float(auc),
        "threshold": float(threshold),
    }


def expected_calibration_error(y, p, bins=10):
    y = np.asarray(y)
    p = np.asarray(p)
    edges = np.linspace(0, 1, bins + 1)
    ece = 0.0
    for lo, hi in zip(edges[:-1], edges[1:]):
        mask = (p >= lo) & (p < (hi if hi < 1 else hi + 1e-9))
        if mask.any():
            ece += mask.mean() * abs(y[mask].mean() - p[mask].mean())
    return float(ece)


def _sample_windowed(wd: WindowedData, max_windows, seed):
    if not max_windows or len(wd.X) <= max_windows:
        return wd
    rng = np.random.default_rng(seed)
    indices = np.sort(rng.choice(len(wd.X), size=max_windows, replace=False))
    return WindowedData(
        X=np.asarray(wd.X[indices]),
        y=wd.y[indices],
        timestamps=wd.timestamps[indices],
        feature_names=wd.feature_names,
        assets=wd.assets[indices],
        protocols=wd.protocols[indices],
        sources=wd.sources[indices],
        destinations=wd.destinations[indices],
    )


def train_baselines(train_wd, val_wd, test_wd, cfg, seed=None):
    """Train detectors, select thresholds on validation, then evaluate test."""
    if seed is not None:
        set_seed(seed)
    run_seed = cfg.seed if seed is None else seed
    out = {}

    rf_train = _sample_windowed(train_wd, cfg.experiment.max_rf_train_windows, run_seed)
    neural_train = _sample_windowed(train_wd, cfg.experiment.max_neural_train_windows, run_seed)

    flat_tr = rf_train.X.reshape(len(rf_train.X), -1)
    flat_val = val_wd.X.reshape(len(val_wd.X), -1)
    flat_te = test_wd.X.reshape(len(test_wd.X), -1)

    rf = RandomForestClassifier(
        n_estimators=120,
        random_state=run_seed,
        n_jobs=cfg.experiment.rf_n_jobs,
        class_weight="balanced",
    )
    rf.fit(flat_tr, rf_train.y)
    rf_val_p = rf.predict_proba(flat_val)[:, 1]
    rf_threshold = select_threshold(val_wd.y, rf_val_p, cfg.experiment.threshold_metric)
    out["random_forest"] = binary_metrics(
        test_wd.y, rf.predict_proba(flat_te)[:, 1], rf_threshold
    )

    for architecture in ("cnn", "lstm", "cnn_lstm"):
        detector = Detector(neural_train.X.shape[-1], cfg.model, architecture=architecture)
        detector.fit(
            neural_train.X, neural_train.y,
            cfg.model.epochs, cfg.model.batch_size, cfg.model.learning_rate
        )
        val_p = detector.predict_proba(val_wd.X)
        detector.threshold = select_threshold(
            val_wd.y, val_p, cfg.experiment.threshold_metric
        )
        p = detector.predict_proba(test_wd.X)
        out[architecture] = binary_metrics(test_wd.y, p, detector.threshold)
        out[architecture]["ece"] = expected_calibration_error(test_wd.y, p)
    return out


def attribution_ablation(evidence, hypotheses, reliabilities, support_threshold=0.60, conflict_threshold=0.35):
    """Run the planned evidence ladder plus WEF point-estimate baseline."""
    from ..core.attribution import assess
    from ..core.attribution_baselines import weighted_evidence_fusion

    methods = {
        "DC": ["DC"],
        "DC+BSS": ["DC", "BSS"],
        "DC+BSS+ECS": ["DC", "BSS", "ECS"],
        "DC+BSS+ECS+MAS": ["DC", "BSS", "ECS", "EC", "MAS"],
        "ACFM": ["DC", "BSS", "ECS", "EC", "MAS"],
    }
    results = {}
    for name, sources in methods.items():
        filtered = {h: {k: v for k, v in evidence.get(h, {}).items() if k in sources} for h in hypotheses}
        results[name] = assess(hypotheses, filtered, reliabilities, support_threshold, conflict_threshold)
    results["WEF"] = [
        {"hypothesis": h, **weighted_evidence_fusion(evidence.get(h, {}), reliabilities)}
        for h in hypotheses
    ]
    return results
