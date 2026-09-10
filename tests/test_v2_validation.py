from datetime import datetime, timedelta, timezone

import pandas as pd

from xaita_ot.config import AppConfig
from xaita_ot.core.btae import event_relation, reconstruct
from xaita_ot.core.schemas import DetectionEvent, AttributionHypothesis, OTEvent, ProvenanceRecord
from xaita_ot.pipeline.evaluation import chronological_split, expected_calibration_error, attribution_ablation
from xaita_ot.pipeline.experiments import attribution_configurations, experiment_contract, aggregate_runs, ExperimentRun


def _events():
    t = datetime.now(timezone.utc)
    return [DetectionEvent(f"e{i}", t + timedelta(seconds=i * 5), "PLC1", "modbus", "HMI-01", "PLC1", "attack", 0.8) for i in range(4)]


def test_configurable_btae_weights_sum_to_one():
    cfg = AppConfig()
    assert abs(sum(cfg.correlation.weights.values()) - 1.0) < 1e-9
    assert set(cfg.correlation.weights) == {"temporal", "asset", "protocol", "communication", "sequence", "behavior"}
    assert 0.0 <= event_relation(_events()[0], _events()[1], 60, cfg.correlation.weights) <= 1.0


def test_sequence_continuity_is_explicit_in_edges():
    episode = reconstruct(_events(), threshold=.5, temporal_window=60)[0]
    assert len(episode.correlation_edges) == 3
    assert "sequence_continuity" in episode.correlation_edges[0]


def test_episode_preserves_correlation_edges():
    episode = reconstruct(_events(), threshold=.5, temporal_window=60)[0]
    assert episode.correlation_edges[0]["source_event"] == "e0"
    assert episode.correlation_edges[0]["target_event"] == "e1"
    assert "communication_relationship" in episode.correlation_edges[0]


def test_canonical_evidence_objects_exist():
    now = datetime.now(timezone.utc)
    observation = OTEvent("obs-1", now, provenance=["sensor-1"])
    hypothesis = AttributionHypothesis("H1", "Candidate attribution", "Test hypothesis")
    provenance = ProvenanceRecord("obs-1", "telemetry", "sensor-1", now)
    assert observation.event_id == "obs-1"
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


def test_v2_contract_has_four_detectors_and_six_attribution_methods():
    contract = experiment_contract("SWaT", 42)
    assert contract["detectors"] == ["RF", "CNN", "LSTM", "CNN-LSTM"]
    assert len(contract["attribution_configurations"]) == 6


def test_attribution_ablation_executes_all_six_methods():
    evidence = {
        "H1": {"DC": .90, "BSS": .82, "ECS": .76, "EC": .70, "MAS": .68},
        "H2": {"DC": .40, "BSS": .45, "ECS": .50, "EC": .30, "MAS": .42},
        "H3": {"DC": .50, "BSS": .50, "ECS": .50, "EC": .50, "MAS": .50},
    }
    reliability = {"DC": .90, "BSS": .85, "ECS": .80, "EC": .75, "MAS": .70}
    results = attribution_ablation(evidence, ["H1", "H2", "H3"], reliability)
    assert list(results) == ["DC", "DC+BSS", "DC+BSS+ECS", "DC+BSS+ECS+MAS", "ACFM", "WEF"]
    assert all(results[name] for name in results)


def test_experiment_aggregation_returns_mean_std_and_n():
    base = dict(dataset="SWaT", seed=42, started_at="2026-01-01T00:00:00+00:00", duration_seconds=1.0, config={}, rows={}, windows={})
    a = ExperimentRun(experiment_id="a", metrics={"cnn_lstm": {"f1": .8}}, **base)
    b = ExperimentRun(experiment_id="b", metrics={"cnn_lstm": {"f1": .6}}, **{**base, "seed": 43})
    result = aggregate_runs([a, b])
    assert result["aggregate"]["cnn_lstm"]["f1"]["mean"] == .7
    assert result["aggregate"]["cnn_lstm"]["f1"]["n"] == 2
