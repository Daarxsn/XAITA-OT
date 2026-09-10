from datetime import timedelta
import numpy as np
from .schemas import DetectionEvent, AttackEpisode


def event_relation(a: DetectionEvent, b: DetectionEvent, temporal_window: float) -> float:
    dt = abs((b.timestamp - a.timestamp).total_seconds())
    temporal = max(0.0, 1.0 - dt / max(temporal_window, 1e-9))
    asset = 1.0 if a.asset == b.asset else 0.35
    protocol = 1.0 if a.protocol == b.protocol else 0.40
    behavior = 1.0 if a.label == b.label else 0.55
    return 0.35 * temporal + 0.25 * asset + 0.20 * protocol + 0.20 * behavior


def relation_detail(a: DetectionEvent, b: DetectionEvent, temporal_window: float) -> dict:
    dt = abs((b.timestamp - a.timestamp).total_seconds())
    temporal = max(0.0, 1.0 - dt / max(temporal_window, 1e-9))
    asset = 1.0 if a.asset == b.asset else 0.35
    protocol = 1.0 if a.protocol == b.protocol else 0.40
    behavior = 1.0 if a.label == b.label else 0.55
    strength = 0.35 * temporal + 0.25 * asset + 0.20 * protocol + 0.20 * behavior
    return {
        "source_event": a.event_id,
        "target_event": b.event_id,
        "temporal_proximity": round(float(temporal), 4),
        "asset_continuity": round(float(asset), 4),
        "protocol_continuity": round(float(protocol), 4),
        "behavioral_similarity": round(float(behavior), 4),
        "correlation_strength": round(float(strength), 4),
    }


def reconstruct(events: list[DetectionEvent], threshold: float = 0.55, temporal_window: float = 60.0) -> list[AttackEpisode]:
    events = sorted(events, key=lambda e: e.timestamp)
    episodes = []
    current = []
    strengths = []
    edges = []
    for e in events:
        if not current:
            current = [e]
            strengths = []
            edges = []
            continue
        detail = relation_detail(current[-1], e, temporal_window)
        s = detail["correlation_strength"]
        if s >= threshold:
            current.append(e)
            strengths.append(s)
            edges.append(detail)
        else:
            if current:
                episodes.append(_episode(current, strengths, edges, len(episodes) + 1))
            current = [e]
            strengths = []
            edges = []
    if current:
        episodes.append(_episode(current, strengths, edges, len(episodes) + 1))
    return episodes


def _episode(events, strengths, edges, idx):
    corr = float(np.mean(strengths)) if strengths else 0.0
    stages = [e.label for e in events]
    return AttackEpisode(f"EP-{idx:05d}", events, corr, stages, edges)
