from __future__ import annotations

import math


def weighted_evidence_fusion(values: dict[str, float], reliabilities: dict[str, float]) -> dict:
    """Weighted-evidence-fusion baseline used as a point-estimate comparator."""
    if not isinstance(values, dict) or not values:
        raise ValueError("WEF evidence values must be a non-empty mapping")
    if not isinstance(reliabilities, dict):
        raise ValueError("WEF reliabilities must be a mapping")
    pairs = []
    for key, raw_value in values.items():
        value = float(raw_value)
        reliability = float(reliabilities.get(key, 0.5))
        if not math.isfinite(value) or not 0.0 <= value <= 1.0:
            raise ValueError(f"WEF evidence '{key}' must be finite and in [0, 1]")
        if not math.isfinite(reliability) or not 0.0 <= reliability <= 1.0:
            raise ValueError(f"WEF reliability '{key}' must be finite and in [0, 1]")
        pairs.append((value, reliability))
    total = sum(reliability for _, reliability in pairs)
    if total <= 0.0:
        raise ValueError("WEF total reliability must be positive")
    score = sum(value * reliability for value, reliability in pairs) / total
    return {
        "method": "WEF",
        "score": float(score),
        "belief": float(score),
        "plausibility": float(score),
        "interval_width": 0.0,
        "is_interval": False,
    }
