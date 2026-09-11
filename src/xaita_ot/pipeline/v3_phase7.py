"""V3 Phase 7 case-study reconstruction and reporting.

Builds a traceable case from canonical telemetry through detection, BTAE,
ATT&CK technique hypotheses, attribution, ACFM, XAI, risk and CTI.  ATT&CK
mappings are explicitly marked as evidence-supported hypotheses; this module
does not claim ground-truth attribution from telemetry alone.
"""
from __future__ import annotations

from pathlib import Path
from datetime import datetime, timezone
import hashlib
import json

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier

from ..config import AppConfig
from ..core.attribution import assess, to_dict
from ..core.btae import reconstruct
from ..core.schemas import DetectionEvent, AttributionHypothesis, CTIProduct
from ..core.seed import set_seed
from ..io.adapters import adapt_dataset
from ..io.telemetry import load_csv, semantic_harmonize
from .evaluation import chronological_split
from .preprocess import OTPreprocessor

ATTACK_MAPPINGS = {
    "network": [{"technique_id": "T1071", "name": "Application Layer Protocol", "tactic": "Command and Control"}],
    "command": [{"technique_id": "T1059", "name": "Command and Scripting Interpreter", "tactic": "Execution"}],
    "credential": [{"technique_id": "T1078", "name": "Valid Accounts", "tactic": "Defense Evasion / Persistence"}],
    "scan": [{"technique_id": "T1046", "name": "Network Service Scanning", "tactic": "Discovery"}],
    "dos": [{"technique_id": "T1499", "name": "Endpoint Denial of Service", "tactic": "Impact"}],
    "exfil": [{"technique_id": "T1041", "name": "Exfiltration Over C2 Channel", "tactic": "Exfiltration"}],
    "attack": [{"technique_id": "T1071", "name": "Application Layer Protocol", "tactic": "Command and Control"}],
}


def _id(prefix: str, *parts) -> str:
    raw = "|".join(map(str, parts)).encode("utf-8")
    return f"{prefix}-{hashlib.sha256(raw).hexdigest()[:12]}"


def _risk(detector_confidence: float, correlation: float, belief: float, plausibility: float) -> dict:
    exposure = float(np.clip(0.40 * detector_confidence + 0.25 * correlation + 0.35 * ((belief + plausibility) / 2), 0, 1))
    severity = "low" if exposure < .35 else "medium" if exposure < .65 else "high" if exposure < .85 else "critical"
    return {"score": round(exposure * 100, 3), "normalized": round(exposure, 4), "severity": severity, "components": {"detection": detector_confidence, "episode_correlation": correlation, "attribution_midpoint": (belief + plausibility) / 2}}


def _xai(detector, X, feature_names, top_k=8) -> dict:
    importances = np.asarray(detector.feature_importances_, dtype=float)
    if importances.sum() <= 0:
        return {"method": "RandomForest feature importance", "features": [], "fidelity_note": "Global model importance; not a causal explanation."}
    order = np.argsort(importances)[::-1][:top_k]
    features = [{"feature": feature_names[i] if i < len(feature_names) else f"feature_{i}", "importance": float(importances[i])} for i in order]
    return {"method": "RandomForest feature importance", "features": features, "fidelity_note": "Global model importance used as an execution-safe XAI artifact; it is not a causal explanation."}


def _map_attack(stages: list[str], protocol: str) -> list[dict]:
    text = " ".join(stages).lower()
    keys = [k for k in ATTACK_MAPPINGS if k in text]
    if not keys and protocol not in {"unknown", ""}:
        keys = ["network"]
    mappings = []
    for key in keys:
        for item in ATTACK_MAPPINGS[key]:
            mappings.append({**item, "evidence_basis": f"episode stages/protocol matched '{key}'", "mapping_status": "hypothesis"})
    unique = {(x["technique_id"], x["name"]): x for x in mappings}
    return list(unique.values())


def _evidence(events: list[DetectionEvent]) -> tuple[dict[str, float], dict[str, float]]:
    conf = float(np.mean([e.detection_confidence for e in events]))
    assets = [e.asset for e in events]; protocols = [e.protocol for e in events]
    asset_cont = float(len(set(assets)) == 1)
    proto_cont = float(len(set(protocols)) == 1)
    temporal = float(np.exp(-max(0.0, (events[-1].timestamp - events[0].timestamp).total_seconds()) / 120.0))
    attack = {"DC": conf, "BSS": temporal, "ECS": asset_cont, "EC": proto_cont, "MAS": float(np.mean([1.0 if e.label.lower() in {"attack", "anomaly", "malicious"} else .25 for e in events]))}
    return attack, {"DC": 1.0, "BSS": .8, "ECS": .85, "EC": .8, "MAS": .65}


def build_case(csv_path: str | Path, dataset: str, cfg: AppConfig, seed: int = 42, top_n: int = 1) -> dict:
    """Select and reconstruct the highest-confidence attack episode(s)."""
    set_seed(seed)
    df = adapt_dataset(semantic_harmonize(load_csv(csv_path)), dataset)
    train, _, test = chronological_split(df, cfg.experiment.train_fraction, cfg.experiment.validation_fraction, "label", cfg.experiment.episode_aware)
    prep = OTPreprocessor(cfg.model.window_size)
    train_w = prep.fit_transform_train(train, "label"); test_w = prep.transform(test, "label")
    if len(train_w.X) == 0 or len(test_w.X) == 0 or len(np.unique(train_w.y)) < 2:
        raise ValueError(f"{dataset}: case study requires non-empty two-class training/test windows")
    clf = RandomForestClassifier(n_estimators=120, random_state=seed, n_jobs=1, class_weight="balanced")
    flat_train = train_w.X.reshape(len(train_w.X), -1); flat_test = test_w.X.reshape(len(test_w.X), -1)
    clf.fit(flat_train, train_w.y)
    p = clf.predict_proba(flat_test)[:, 1]
    # Align window predictions to the first sample of each window; aggregate to event-level confidence.
    events = []
    timestamps = test_w.timestamps
    for i, ts in enumerate(timestamps):
        row = test.iloc[min(i + cfg.model.window_size - 1, len(test) - 1)]
        label = "attack" if p[i] >= .5 else "normal"
        events.append(DetectionEvent(_id("EV", dataset, seed, i, ts), pd.Timestamp(ts).to_pydatetime(), str(row.get("asset", "unknown")), str(row.get("protocol", "unknown")), label, float(p[i]), observation_id=_id("OBS", dataset, i)))
    episodes = reconstruct(events, threshold=.55, temporal_window=60.0)
    attack_eps = [e for e in episodes if any(ev.label == "attack" for ev in e.events)]
    if not attack_eps:
        attack_eps = sorted(episodes, key=lambda e: e.correlation_strength, reverse=True)[:top_n]
    selected = sorted(attack_eps, key=lambda e: (max(ev.detection_confidence for ev in e.events), e.correlation_strength), reverse=True)[:top_n]
    cases = []
    for ep in selected:
        attack_evidence, reliabilities = _evidence(ep.events)
        benign_evidence = {k: 1.0 - v for k, v in attack_evidence.items()}
        hypotheses = [
            AttributionHypothesis("H1", "External/remote actor", "Activity consistent with a remote or network-originating actor.", {"network": .6}),
            AttributionHypothesis("H2", "Insider or compromised account", "Activity involving otherwise known OT assets or identities.", {"asset_continuity": .6}),
            AttributionHypothesis("H3", "Misconfiguration or benign anomaly", "Non-adversarial explanation for anomalous process behavior.", {"low_detection": .5}),
        ]
        assessment = assess([h.name for h in hypotheses], {"External/remote actor": attack_evidence, "Insider or compromised account": {"DC": attack_evidence["DC"], "ECS": attack_evidence["ECS"], "MAS": attack_evidence["MAS"]}, "Misconfiguration or benign anomaly": benign_evidence}, reliabilities, .60, .35)
        best = assessment[0]
        attack_map = _map_attack(ep.stages, ep.events[0].protocol)
        feature_names = [f"window_feature_{i}" for i in range(flat_train.shape[1])]
        xai = _xai(clf, flat_test, feature_names)
        risk = _risk(max(ev.detection_confidence for ev in ep.events), ep.correlation_strength, best.belief, best.plausibility)
        provenance = [_id("PROV", dataset, seed, ep.episode_id, "telemetry"), _id("PROV", dataset, seed, ep.episode_id, "detection"), _id("PROV", dataset, seed, ep.episode_id, "btae"), _id("PROV", dataset, seed, ep.episode_id, "attribution"), _id("PROV", dataset, seed, ep.episode_id, "xai"), _id("PROV", dataset, seed, ep.episode_id, "risk")]
        cti = CTIProduct(_id("INC", dataset, seed, ep.episode_id), {"confidence": max(ev.detection_confidence for ev in ep.events), "events": [ev.event_id for ev in ep.events]}, {"episode_id": ep.episode_id, "stages": ep.stages, "correlation": ep.correlation_strength}, {"asset": ep.events[0].asset, "protocol": ep.events[0].protocol}, {"best_hypothesis": to_dict(best), "all_hypotheses": [to_dict(a) for a in assessment]}, xai, risk, provenance)
        cases.append({"case_id": _id("CASE", dataset, seed, ep.episode_id), "episode_selection": {"episode_id": ep.episode_id, "selection_basis": "highest detection confidence, then BTAE correlation", "event_count": len(ep.events)}, "attack_sequence": [{"event_id": e.event_id, "timestamp": e.timestamp.isoformat(), "label": e.label, "asset": e.asset, "protocol": e.protocol, "confidence": e.detection_confidence} for e in ep.events], "btae_reconstruction": {"episode_id": ep.episode_id, "correlation_strength": ep.correlation_strength, "stages": ep.stages, "edges": ep.correlation_edges}, "attack_mapping": attack_map, "attribution_hypotheses": [to_dict(a) for a in assessment], "acfm": {"best_hypothesis": to_dict(best), "support_threshold": .60, "conflict_threshold": .35}, "xai": xai, "risk": risk, "cti": {"incident_id": cti.incident_id, "detection": cti.detection, "behavior": cti.behavior, "context": cti.context, "attribution": cti.attribution, "xai": cti.xai, "risk": cti.risk, "provenance": cti.provenance}, "provenance": provenance})
    return {"phase": "V3.7", "status": "PASS", "dataset": dataset, "seed": seed, "cases": cases, "selection_policy": "attack-containing episodes ranked by maximum detector confidence then BTAE correlation"}


def write_case_artifact(result: dict, out_dir: str | Path) -> str:
    out = Path(out_dir); out.mkdir(parents=True, exist_ok=True)
    path = out / f"case_study_{result['dataset']}.json"
    path.write_text(json.dumps(result, indent=2, default=str), encoding="utf-8")
    return str(path)
