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

    def analyze_events(self, events, hypotheses=None):
        if not events:
            return []

        episodes = reconstruct(
            events,
            self.config.correlation.threshold,
            self.config.correlation.temporal_window_seconds,
        )
        outputs = []
        hypotheses = hypotheses or ["H1", "H2", "H3"]

        for ep in episodes:
            ctx = contextualize(ep, self.attack_mapping)
            dc = float(np.mean([e.detection_confidence for e in ep.events]))
            bss = min(1.0, 0.45 + 0.35 * ep.correlation_strength + 0.20 * dc)
            # Context coverage is evidence, not proof. Keep a bounded headroom
            # so complete ATT&CK mapping does not become artificial certainty.
            coverage = len(ctx) / max(1, len(ep.events))
            ecs = min(0.85, 0.55 + 0.30 * coverage)
            ec = ep.correlation_strength
            mas = 0.50 + 0.50 * bool(set(e.asset for e in ep.events))
            base = {"DC": dc, "BSS": bss, "ECS": ecs, "EC": ec, "MAS": mas}
            evidence = {
                h: {k: max(0.0, min(1.0, v * (1.0 - 0.08 * i))) for k, v in base.items()}
                for i, h in enumerate(hypotheses)
            }
            attrs = assess(hypotheses, evidence, self.config.attribution.reliability)
            best = to_dict(attrs[0]) if attrs else None

            risk = score_risk(
                severity=max(0.0, dc),
                operational_impact=min(1.0, 0.4 + 0.1 * len(ep.events)),
                criticality=0.7,
                attribution_evidence=best["belief"] if best else 0.0,
                weights=self.config.risk.weights,
            )

            feature_names = sorted({k for e in ep.events for k in e.features})
            if feature_names:
                matrix = np.array(
                    [[e.features.get(k, 0.0) for k in feature_names] for e in ep.events],
                    dtype=np.float32,
                )[None, :, :]
                fi = feature_importance_linearized(matrix, feature_names)
            else:
                fi = feature_importance_linearized(
                    np.zeros((1, 1, 1), dtype=np.float32), ["unknown"]
                )

            xai = build_explanation(ep.events[0], ep, ctx, risk, fi)
            detection = {
                "event_ids": [e.event_id for e in ep.events],
                "mean_detection_confidence": dc,
            }
            cti = generate_cti(ep.episode_id, detection, ep, ctx, best, xai, risk)
            outputs.append(cti)
        return outputs
