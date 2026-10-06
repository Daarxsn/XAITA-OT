from __future__ import annotations

import math


_REQUIRED_WEIGHTS = {"severity", "operational_impact", "criticality", "attribution"}


def _finite_unit(value: float, name: str) -> float:
    value = float(value)
    if not math.isfinite(value):
        raise ValueError(f"{name} must be finite")
    if not 0.0 <= value <= 1.0:
        raise ValueError(f"{name} must be in [0, 1]")
    return value


def _validate_weights(weights) -> dict[str, float]:
    if not isinstance(weights, dict) or set(weights) != _REQUIRED_WEIGHTS:
        raise ValueError(f"risk weights must contain exactly {sorted(_REQUIRED_WEIGHTS)}")
    normalized = {key: _finite_unit(value, f"weight {key}") for key, value in weights.items()}
    if abs(sum(normalized.values()) - 1.0) > 1e-6:
        raise ValueError("risk weights must sum to 1.0")
    return normalized


def score_risk(severity, operational_impact, criticality, attribution_evidence, weights):
    vals = {
        "severity": _finite_unit(severity, "severity"),
        "operational_impact": _finite_unit(operational_impact, "operational_impact"),
        "criticality": _finite_unit(criticality, "criticality"),
        "attribution": _finite_unit(attribution_evidence, "attribution_evidence"),
    }
    normalized_weights = _validate_weights(weights)
    score = sum(vals[key] * normalized_weights[key] for key in vals)
    level = "LOW" if score < 0.35 else "MEDIUM" if score < 0.65 else "HIGH" if score < 0.85 else "CRITICAL"
    return {"score": float(score), "level": level, "factors": vals, "weights": normalized_weights}
