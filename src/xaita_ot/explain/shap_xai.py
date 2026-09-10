from __future__ import annotations

import numpy as np


def shap_feature_importance(model, background, samples, feature_names, top_k=8):
    """Compute model-faithful SHAP feature importance for a trained torch detector."""
    try:
        import shap
        import torch
    except ImportError as exc:
        raise RuntimeError("SHAP explanation requires the optional shap dependency") from exc
    if background.ndim != 3 or samples.ndim != 3:
        raise ValueError("background and samples must have shape [N, T, F]")
    if background.shape[-1] != len(feature_names):
        raise ValueError("feature_names length must match the feature dimension")
    device = next(model.parameters()).device
    model.eval()
    background_t = torch.as_tensor(background, dtype=torch.float32, device=device)
    samples_t = torch.as_tensor(samples, dtype=torch.float32, device=device)
    explainer = shap.GradientExplainer(model, background_t)
    values = explainer.shap_values(samples_t)
    if isinstance(values, list): values = values[0]
    values = np.asarray(values)
    if values.ndim == 4 and values.shape[-1] == 1: values = values[..., 0]
    if values.ndim != 3: raise RuntimeError(f"Unexpected SHAP output shape: {values.shape}")
    importance = np.mean(np.abs(values), axis=(0, 1)); total = float(importance.sum()) or 1.0
    order = np.argsort(importance)[::-1][:top_k]
    return [{"feature": feature_names[i], "index": int(i), "importance": float(importance[i] / total), "mean_abs_shap": float(importance[i])} for i in order]
