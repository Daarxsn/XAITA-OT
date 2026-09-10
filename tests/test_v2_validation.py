from datetime import datetime, timedelta, timezone

import pandas as pd

from xaita_ot.config import AppConfig
from xaita_ot.core.btae import event_relation, reconstruct
from xaita_ot.core.schemas import DetectionEvent, AttributionHypothesis, OTEvent, ProvenanceRecord
from xaita_ot.pipeline.evaluation import chronological_split, expected_calibration_error


def _events():
    t = datetime.now(timezone.utc)
    return [DetectionEvent(f"e{i}", t + timedelta(seconds=i * 5), "PLC1", "modbus", "attack", 0.8) for i in range(4)]


def test_configurable_btae_weights_sum_to_one():
    cfg = AppConfig()
    assert abs(sum(cfg.correlation.weights.values()) - 1.0) < 1e-9
    expected = 0.30 * (1.0 - 5.0 / 60.0) + 0.20 + 0.15 + 0.15 * 0.50 + 0.20
    assert abs(event_relation(_events()[0], _events()[1], 60, cfg.correlation.weights) - expected) < 1e-6


def test_episode_preserves_correlation_edges():
    episode = reconstruct(_events(), threshold=.5, temporal_window=60)[0]
    assert len(episode.correlation_edges) == 3
    assert episode.correlation_edges[0]["source_event"] == "e0"
    assert episode.correlation_edges[0]["target_event"] == "e1"
    assert "communication_relationship" in episode.correlation_edges[0]


def test_canonical_evidence_objects_exist():
    now = datetime.now(timezone.utc)
    observation = OTEvent("obs-1", now, provenance=["sensor-1"])
    hypothesis = AttributionHypothesis("H1", "Candidate attribution", "Test hypothesis")
    provenance = ProvenanceRecord("obs-1", "telemetry", "sensor-1", now)
    assert observation.event_id == hypothesis.hypothesis_id.replace("H1", "obs-1") or observation.event_id == "obs-1"
    assert hypothesis.status == "candidate"
    assert provenance.parent_ids == []


def test_episode_aware_split_keeps_attack_runs_together():
    labels = [0] * 10 + [1] * 5 + [0] * 10 + [1] * 5 + [0] * 10
    df = pd.DataFrame({"timestamp": pd.date_range("2026-01-01", periods=len(labels), freq="s"), "label": labels})
    tr, va, te = chronological_split(df, .70, .15, "label", episode_aware=True)
    for left, right in ((tr, va), (va, te)):
        if len(left) and len(right):
            assert not (int(left.iloc[-1].label) == 1 and int(right.iloc[0].label) == 1)


def test_ece_is_bounded():
    value = expected_calibration_error([0, 0, 1, 1], [0.1, 0.2, 0.8, 0.9])
    assert 0.0 <= value <= 1.0
