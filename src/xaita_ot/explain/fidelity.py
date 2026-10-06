from __future__ import annotations

import numpy as np


def perturbation_fidelity(predict_fn, X, importances, top_k=1, baseline=0.0):
    """Measure mean absolute score change after perturbing top-ranked features."""
    X = np.asarray(X, dtype=np.float32)
    if X.ndim != 3 or not len(X):
        raise ValueError("X must be non-empty with shape [N, T, F]")
    if not np.isfinite(X).all():
        raise ValueError("X must contain finite values")
    if top_k <= 0:
        raise ValueError("top_k must be positive")
    ranked = sorted(importances, key=lambda item: float(item.get("importance", 0.0)), reverse=True)
    indices = []
    for item in ranked[:top_k]:
        if "index" not in item:
            continue
        index = int(item["index"])
        if not 0 <= index < X.shape[-1]:
            raise ValueError(f"feature index out of range: {index}")
        indices.append(index)
    indices = list(dict.fromkeys(indices))
    if not indices:
        return 0.0
    baseline = float(baseline)
    if not np.isfinite(baseline):
        raise ValueError("baseline must be finite")
    original = np.asarray(predict_fn(X), dtype=float).reshape(-1)
    perturbed = X.copy()
    perturbed[:, :, indices] = baseline
    changed = np.asarray(predict_fn(perturbed), dtype=float).reshape(-1)
    if len(original) != len(X) or len(changed) != len(X):
        raise ValueError("predict_fn must return one score per sample")
    if not np.isfinite(original).all() or not np.isfinite(changed).all():
        raise ValueError("predict_fn returned non-finite scores")
    return float(np.mean(np.abs(original - changed)))


def explanation_stability(values_a, values_b):
    """Return cosine similarity between two explanation vectors."""
    a = np.asarray(values_a, dtype=float).ravel()
    b = np.asarray(values_b, dtype=float).ravel()
    if a.shape != b.shape or not a.size:
        raise ValueError("explanation vectors must be non-empty and equally shaped")
    if not np.isfinite(a).all() or not np.isfinite(b).all():
        raise ValueError("explanation vectors must be finite")
    denom = np.linalg.norm(a) * np.linalg.norm(b)
    return float(np.dot(a, b) / denom) if denom else 1.0
