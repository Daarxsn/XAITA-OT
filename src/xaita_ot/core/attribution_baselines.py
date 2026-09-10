from __future__ import annotations


def weighted_evidence_fusion(values: dict[str, float], reliabilities: dict[str, float]) -> dict:
    """Weighted-evidence-fusion baseline used as a point-estimate comparator."""
    pairs = [(float(values[k]), float(reliabilities.get(k, 0.5))) for k in values]
    total = sum(max(0.0, r) for _, r in pairs)
    score = sum(max(0.0, min(1.0, v)) * max(0.0, r) for v, r in pairs) / max(total, 1e-12)
    return {
        "method": "WEF",
        "score": float(score),
        "belief": float(score),
        "plausibility": float(score),
        "interval_width": 0.0,
        "is_interval": False,
    }
