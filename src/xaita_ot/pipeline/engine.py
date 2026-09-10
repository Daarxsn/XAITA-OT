import numpy as np

from ..config import AppConfig
from ..core.seed import set_seed
from ..core.btae import reconstruct
from ..core.context import contextualize, load_attack_map
from ..core.attribution import assess, to_dict
from ..core.risk import score_risk
from ..explain.xai import feature_importance_linearized, build_explanation
from ..cti.generator import generate_cti


class XAITAEngine:
    def __init__(self, config: AppConfig):
        self.config = config
        set_seed(config.seed)
        self.attack_mapping = load_attack_map()

    @staticmethod
    def _mas(episode):
        if not episode.events:
            return 0.0
        assets = [e.asset for e in episode.events]
        protocols = [e.protocol for e in episode.events]
        labels = [e.label for e in episode.events]
        asset_consistency = len(set(assets)) / len(assets)
        protocol_consistency = len(set(protocols)) / len(protocols)
        behavior_consistency = sum(1 for i in range(1, len(labels)) if labels[i] == labels[i - 1]) / max(1, len(labels) - 1)
        detection_consistency = float(np.mean([e.detection_confidence for e in episode.events]))
        return float(np.clip(0.30 * asset_consistency + 0.20 * protocol_consistency + 0.20 * behavior_consistency + 0.30 * detection_consistency, 0.0, 1.0))

    def _hypothesis_evidence(self, base, hypotheses):
        profiles = self.config.attribution.hypothesis_profiles
        return {
            h: {
                source: float(np.clip(value * profiles.get(h, {}).get(source, 1.0), 0.0, 1.0))
                for source, value in base.items()
            }
            for h in hypotheses
        }

    def analyze_events(self, events, hypotheses=None):
        if not events:
            return []
        episodes = reconstruct(
            events,
            self.config.correlation.threshold,
            self.config.correlation.temporal_window_seconds,
            self.config.correlation.weights,
        )
        outputs = []
        hypotheses = hypotheses or list(self.config.attribution.hypothesis_profiles.keys()) or ["H1"]
        for ep in episodes:
            ctx = contextualize(ep, self.attack_mapping)
            dc = float(np.mean([e.detection_confidence for e in ep.events]))
            bss = float(np.clip(0.45 + 0.35 * ep.correlation_strength + 0.20 * dc, 0.0, 1.0))
            coverage = len(ctx) / max(1, len(ep.events))
            ecs = float(np.clip(0.45 + 0.30 * coverage, 0.0, 0.75))
            ec = float(ep.correlation_strength)
            mas = self._mas(ep)
            base = {"DC": dc, "BSS": bss, "ECS": ecs, "EC": ec, "MAS": mas}
            evidence = self._hypothesis_evidence(base, hypotheses)
            attrs = assess(hypotheses, evidence, self.config.attribution.reliability)
            best = to_dict(attrs[0]) if attrs else None
            if best is not None:
                best["evidence_vector"] = evidence.get(best["hypothesis"], {})
                best["alternatives"] = [to_dict(a) for a in attrs[1:]]
                best["interpretation"] = (
                    "narrow interval" if best["interval_width"] <= 0.10
                    else "moderate uncertainty" if best["interval_width"] <= 0.25
                    else "substantial uncertainty"
                )
            risk = score_risk(
                severity=dc,
                operational_impact=min(1.0, 0.4 + 0.1 * len(ep.events)),
                criticality=0.7,
                attribution_evidence=best["belief"] if best else 0.0,
                weights=self.config.risk.weights,
            )
            feature_names = sorted({k for e in ep.events for k in e.features})
            if feature_names:
                matrix = np.array([[e.features.get(k, 0.0) for k in feature_names] for e in ep.events], dtype=np.float32)[None, :, :]
                fi = feature_importance_linearized(matrix, feature_names)
            else:
                fi = feature_importance_linearized(np.zeros((1, 1, 1), dtype=np.float32), ["unknown"])
            xai = build_explanation(ep.events[0], ep, ctx, risk, fi)
            detection = {"event_ids": [e.event_id for e in ep.events], "mean_detection_confidence": dc}
            outputs.append(generate_cti(ep.episode_id, detection, ep, ctx, best, xai, risk))
        return outputs
