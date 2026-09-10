from __future__ import annotations

import numpy as np


def perturbation_fidelity(predict_fn, X, importances, top_k=1, baseline=0.0):
    """Measure prediction change after replacing the most important features.

    Returns the mean absolute change in model score. This is a model-faithfulness
    diagnostic for explanations; it is not an accuracy metric.
    """
    X = np.asarray(X, dtype=np.float32)
    if X.ndim != 3:
        raise ValueError("X must have shape [N, T, F]")
    ranked = sorted(importances, key=lambda x: x.get("importance", 0.0), reverse=True)
    indices = [int(item["index"]) for item in ranked[:top_k] if "index" in item]
    if not indices:
        return 0.0
    original = np.asarray(predict_fn(X), dtype=float)
    perturbed = X.copy()
    perturbed[:, :, indices] = baseline
    changed = np.asarray(predict_fn(perturbed), dtype=float)
    return float(np.mean(np.abs(original - changed)))


def explanation_stability(values_a, values_b):
    """Return cosine similarity between two explanation vectors."""
    a = np.asarray(values_a, dtype=float).ravel()
    b = np.asarray(values_b, dtype=float).ravel()
    if a.shape != b.shape:
        raise ValueError("explanation vectors must have the same shape")
    denom = np.linalg.norm(a) * np.linalg.norm(b)
    return float(np.dot(a, b) / denom) if denom else 1.0
