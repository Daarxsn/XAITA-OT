import numpy as np

from ..config import AppConfig
from ..core.seed import set_seed
from ..core.btae import reconstruct
from ..core.context import contextualize, load_attack_map
from ..core.attribution import assess, to_dict, validate_assessments
from ..core.risk import score_risk
from ..explain.xai import feature_importance_linearized, build_explanation, validate_explanation, explanation_fingerprint
from ..cti.generator import generate_cti


class XAITAEngine:
    def __init__(self, config: AppConfig):
        self.config = config
        set_seed(config.seed)
        self.attack_mapping = load_attack_map()

    @staticmethod
    def _mas(context, reference_techniques=None):
        """Return Jaccard alignment with a hypothesis's ATT&CK reference profile.

        None indicates that no reference profile is configured; missing profile
        evidence must not be interpreted as evidence against a hypothesis.
        """
        if not reference_techniques:
            return None
        reference = {str(value).strip().upper() for value in reference_techniques}
        observed = {
            str(item.get("technique_id", "")).strip().upper()
            for item in (context or [])
            if item.get("technique_id")
        }
        if not reference:
            return None
        if not observed:
            return 0.0
        union = observed | reference
        return float(len(observed & reference) / len(union)) if union else 0.0

    @staticmethod
    def _jaccard_similarity(observed, reference):
        ignored = {"", "unknown", "none", "null", "n/a"}
        left = {str(item).strip().lower() for item in observed if str(item).strip().lower() not in ignored}
        right = {str(item).strip().lower() for item in reference if str(item).strip().lower() not in ignored}
        if not left or not right:
            return None
        return len(left & right) / len(left | right)

    @staticmethod
    def _sequence_similarity(observed, reference):
        left = [str(item).strip().lower() for item in observed if str(item).strip()]
        right = [str(item).strip().lower() for item in reference if str(item).strip()]
        if not left or not right:
            return None
        previous = list(range(len(right) + 1))
        for i, left_item in enumerate(left, start=1):
            current = [i]
            for j, right_item in enumerate(right, start=1):
                current.append(min(
                    current[-1] + 1,
                    previous[j] + 1,
                    previous[j - 1] + (left_item != right_item),
                ))
            previous = current
        return float(1.0 - previous[-1] / max(len(left), len(right)))

    @classmethod
    def _bss(cls, episode, profile):
        """Compute behavior similarity against a validated reference profile."""
        if not profile or not episode.events:
            return None
        observed_sequence = episode.stages or [event.label for event in episode.events]
        sequence_score = cls._sequence_similarity(observed_sequence, profile["sequence"])
        asset_score = cls._jaccard_similarity([event.asset for event in episode.events], profile["assets"])
        protocol_score = cls._jaccard_similarity([event.protocol for event in episode.events], profile["protocols"])
        observed_intervals = [
            max(0.0, (right.timestamp - left.timestamp).total_seconds())
            for left, right in zip(episode.events, episode.events[1:])
        ]
        expected_intervals = profile["inter_event_seconds"]
        temporal_score = None
        if observed_intervals and expected_intervals:
            decay = profile["temporal_decay_per_second"]
            matched = min(len(observed_intervals), len(expected_intervals))
            closeness = [
                float(np.exp(-decay * abs(observed_intervals[i] - expected_intervals[i])))
                for i in range(matched)
            ]
            temporal_score = float(np.mean(closeness) * matched / max(len(observed_intervals), len(expected_intervals)))
        reference = profile["feature_reference"]
        scales = profile["feature_scales"]
        feature_scores = []
        for name, expected in reference.items():
            values = [
                float(event.features[name])
                for event in episode.events
                if name in event.features and np.isfinite(float(event.features[name]))
            ]
            if values:
                observed = float(np.mean(values))
                feature_scores.append(float(np.exp(-abs(observed - expected) / scales[name])))
        behavior_score = float(np.mean(feature_scores)) if feature_scores else None
        components = {
            "temporal": temporal_score,
            "protocol": protocol_score,
            "asset": asset_score,
            "sequence": sequence_score,
            "behavior": behavior_score,
        }
        weights = profile["weights"]
        available_weight = sum(weights[key] for key, value in components.items() if value is not None)
        if available_weight <= 0:
            return None
        return float(sum(weights[key] * value for key, value in components.items() if value is not None) / available_weight)

    def _hypothesis_evidence(self, base, hypotheses):
        profiles = self.config.attribution.hypothesis_profiles
        return {
            h: {
                source: float(np.clip(value * profiles.get(h, {}).get(source, 1.0), 0.0, 1.0))
                for source, value in base.items()
            }
            for h in hypotheses
        }

    def analyze_events(self, events, hypotheses=None, xai_feature_importance=None):
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
            # ECS is the measured episode correlation strength. BSS and MAS are
            # supplied only when their reference profiles are explicitly configured.
            ecs = float(np.clip(ep.correlation_strength, 0.0, 1.0))
            base = {"DC": dc, "ECS": ecs}
            evidence = self._hypothesis_evidence(base, hypotheses)
            for hypothesis in hypotheses:
                behavior_profile = self.config.attribution.behavior_profiles.get(hypothesis)
                bss = self._bss(ep, behavior_profile)
                if bss is not None:
                    modifier = self.config.attribution.hypothesis_profiles.get(hypothesis, {}).get("BSS", 1.0)
                    evidence[hypothesis]["BSS"] = float(np.clip(bss * modifier, 0.0, 1.0))
                reference_techniques = self.config.attribution.attack_technique_profiles.get(hypothesis)
                mas = self._mas(ctx, reference_techniques)
                if mas is not None:
                    modifier = self.config.attribution.hypothesis_profiles.get(hypothesis, {}).get("MAS", 1.0)
                    evidence[hypothesis]["MAS"] = float(np.clip(mas * modifier, 0.0, 1.0))
            attrs = assess(hypotheses, evidence, self.config.attribution.reliability, self.config.attribution.support_threshold, self.config.attribution.conflict_threshold)
            validate_assessments(attrs)
            best = to_dict(attrs[0]) if attrs else None
            if best is not None:
                best["evidence_vector"] = evidence.get(best["hypothesis"], {})
                best["mas_status"] = (
                    "available"
                    if best["hypothesis"] in self.config.attribution.attack_technique_profiles
                    else "unavailable_missing_reference_profile"
                )
                best["bss_status"] = (
                    "available"
                    if "BSS" in evidence.get(best["hypothesis"], {})
                    else "unavailable_missing_reference_profile_or_episode_context"
                )
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
                fi = xai_feature_importance or feature_importance_linearized(matrix, feature_names)
            else:
                fi = xai_feature_importance or feature_importance_linearized(np.zeros((1, 1, 1), dtype=np.float32), ["unknown"])
            xai = build_explanation(ep.events[0], ep, ctx, risk, fi, attribution=best, detection_confidence=dc)
            validate_explanation(xai, ep, ctx, risk)
            xai["fingerprint"] = explanation_fingerprint(xai)
            detection = {"event_ids": [e.event_id for e in ep.events], "mean_detection_confidence": dc}
            outputs.append(generate_cti(ep.episode_id, detection, ep, ctx, best, xai, risk))
        return outputs
