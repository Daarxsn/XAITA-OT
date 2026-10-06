import math
import numpy as np
from .schemas import DetectionEvent, AttackEpisode

DEFAULT_WEIGHTS = {
    "temporal": 0.25,
    "asset": 0.15,
    "protocol": 0.10,
    "communication": 0.10,
    "sequence": 0.20,
    "behavior": 0.20,
}


def _components(a: DetectionEvent, b: DetectionEvent, temporal_window: float) -> dict:
    dt = abs((b.timestamp - a.timestamp).total_seconds())
    temporal = max(0.0, 1.0 - dt / max(temporal_window, 1e-9))
    communication = 0.50
    if any(value != "unknown" for value in (a.source, a.destination, b.source, b.destination)):
        communication = 1.0 if (a.source, a.destination) == (b.source, b.destination) else 0.35
    # Sequence continuity captures ordered behavioral progression separately from
    # label similarity. Consecutive events with a changed behavior are treated as
    # a coherent transition; repeated behavior is maximally sequence-consistent.
    sequence = 1.0 if a.label == b.label else 0.80
    return {
        "temporal": temporal,
        "asset": 1.0 if a.asset == b.asset else 0.35,
        "protocol": 1.0 if a.protocol == b.protocol else 0.40,
        "communication": communication,
        "sequence": sequence,
        "behavior": 1.0 if a.label == b.label else 0.55,
    }


def _validated_weights(weights=None) -> dict[str, float]:
    value = dict(weights or DEFAULT_WEIGHTS)
    required = set(DEFAULT_WEIGHTS)
    if set(value) != required:
        raise ValueError(f"correlation weights must contain exactly {sorted(required)}")
    if any(not math.isfinite(float(v)) or float(v) < 0.0 for v in value.values()):
        raise ValueError("correlation weights must be finite and non-negative")
    if abs(sum(float(v) for v in value.values()) - 1.0) > 1e-6:
        raise ValueError("correlation weights must sum to 1.0")
    return {key: float(value[key]) for key in sorted(required)}


def event_relation(a: DetectionEvent, b: DetectionEvent, temporal_window: float, weights=None) -> float:
    if not math.isfinite(float(temporal_window)) or float(temporal_window) <= 0.0:
        raise ValueError("temporal_window must be finite and positive")
    components = _components(a, b, temporal_window)
    weights = _validated_weights(weights)
    return sum(weights[k] * components[k] for k in components)


def relation_detail(a: DetectionEvent, b: DetectionEvent, temporal_window: float, weights=None) -> dict:
    if not math.isfinite(float(temporal_window)) or float(temporal_window) <= 0.0:
        raise ValueError("temporal_window must be finite and positive")
    components = _components(a, b, temporal_window)
    weights = _validated_weights(weights)
    strength = sum(weights[k] * components[k] for k in components)
    return {
        "source_event": a.event_id,
        "target_event": b.event_id,
        "temporal_proximity": round(float(components["temporal"]), 4),
        "asset_continuity": round(float(components["asset"]), 4),
        "protocol_continuity": round(float(components["protocol"]), 4),
        "communication_relationship": round(float(components["communication"]), 4),
        "sequence_continuity": round(float(components["sequence"]), 4),
        "behavioral_similarity": round(float(components["behavior"]), 4),
        "correlation_strength": round(float(strength), 4),
    }


def reconstruct(events: list[DetectionEvent], threshold: float = 0.55, temporal_window: float = 60.0, weights=None) -> list[AttackEpisode]:
    if not 0.0 <= float(threshold) <= 1.0:
        raise ValueError("correlation threshold must be in [0, 1]")
    if not math.isfinite(float(temporal_window)) or float(temporal_window) <= 0.0:
        raise ValueError("temporal_window must be finite and positive")
    events = sorted(events, key=lambda e: e.timestamp)
    episodes = []
    current, strengths, edges = [], [], []
    for event in events:
        if not current:
            current, strengths, edges = [event], [], []
            continue
        detail = relation_detail(current[-1], event, temporal_window, weights)
        strength = detail["correlation_strength"]
        if strength >= threshold:
            current.append(event)
            strengths.append(strength)
            edges.append(detail)
        else:
            episodes.append(_episode(current, strengths, edges, len(episodes) + 1))
            current, strengths, edges = [event], [], []
    if current:
        episodes.append(_episode(current, strengths, edges, len(episodes) + 1))
    return episodes


def _episode(events, strengths, edges, idx):
    correlation = float(np.mean(strengths)) if strengths else 0.0
    stages = [e.label for e in events]
    return AttackEpisode(f"EP-{idx:05d}", events, correlation, stages, edges)
