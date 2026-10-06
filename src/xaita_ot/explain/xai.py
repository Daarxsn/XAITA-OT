import hashlib
import json

import numpy as np


EXPLANATION_SCHEMA_VERSION = "XAITA-OT-XAI-1.1"


class ExplanationValidationError(ValueError):
    """Raised when an explanation is inconsistent with its source evidence."""


def feature_importance_linearized(X, feature_names, weights=None, top_k=8):
    X = np.asarray(X, dtype=float)
    if X.ndim != 3:
        raise ValueError("X must have shape [N, T, F]")
    if len(X) == 0:
        return []
    if X.shape[-1] != len(feature_names):
        raise ValueError("feature_names length must match the feature dimension")
    if top_k <= 0:
        raise ValueError("top_k must be positive")
    if not np.isfinite(X).all():
        raise ValueError("X must contain finite values")
    x = np.mean(np.abs(X), axis=(0, 1))
    if weights is not None:
        weights = np.asarray(weights, dtype=float)
        if weights.shape != x.shape or not np.isfinite(weights).all():
            raise ValueError("weights must be finite and match the feature dimension")
        x = x * np.abs(weights)
    order = np.argsort(x)[::-1][:top_k]
    denom = float(x.sum())
    if not np.isfinite(denom) or denom <= 0.0:
        return []
    return [{"feature": feature_names[i], "importance": float(x[i] / denom)} for i in order]


def build_explanation(event, episode, context, risk, feature_importance, attribution=None, detection_confidence=None):
    return {
      'schema_version': EXPLANATION_SCHEMA_VERSION,
      'feature_level': {'question':'Why was the activity detected?','top_features':feature_importance},
      'behavioral_level': {'question':'Why were the events correlated?','factors':['temporal proximity','affected assets','protocol/communication','event ordering']},
      'attack_stage_level': {'question':'How did the attack progress?','events':[e.event_id for e in episode.events],'context':context},
      'risk_level': {'question':'Why was the incident prioritized?','risk_score':risk['score'],'factors':risk['factors']},
      'attribution_level': {
          'question': 'What attribution does the evidence support?',
          'hypothesis': attribution.get('hypothesis') if attribution else None,
          'belief': attribution.get('belief') if attribution else None,
          'plausibility': attribution.get('plausibility') if attribution else None,
          'interval_width': attribution.get('interval_width') if attribution else None,
          'interpretation': attribution.get('interpretation') if attribution else None,
          'alternatives': attribution.get('alternatives', []) if attribution else [],
      },
      'confidence_semantics': {
          'detection_confidence': detection_confidence,
          'attribution_is_evidence_interval': True,
          'attribution_is_not_calibrated_probability': True,
      },
    }


def validate_explanation(explanation, episode, context, risk):
    """Validate explanation claims against the exact objects used to generate them."""
    if not isinstance(explanation, dict):
        raise ExplanationValidationError("explanation must be a mapping")
    required = {"schema_version", "feature_level", "behavioral_level", "attack_stage_level", "risk_level", "attribution_level", "confidence_semantics"}
    missing = sorted(required - set(explanation))
    if missing:
        raise ExplanationValidationError(f"missing explanation sections: {', '.join(missing)}")

    features = explanation["feature_level"].get("top_features")
    if not isinstance(features, list):
        raise ExplanationValidationError("feature_level.top_features must be a list")
    names = [item.get("feature") for item in features if isinstance(item, dict)]
    if len(names) != len(features) or len(names) != len(set(names)):
        raise ExplanationValidationError("feature explanations must have unique feature names")
    importances = [float(item.get("importance", -1.0)) for item in features]
    if any(not np.isfinite(value) or value < 0.0 or value > 1.0 for value in importances):
        raise ExplanationValidationError("feature importance must be within [0, 1]")
    if features and sum(importances) > 1.0 + 1e-6:
        raise ExplanationValidationError("feature importances must not exceed 1 in aggregate")

    episode_ids = [event.event_id for event in episode.events]
    explained_ids = explanation["attack_stage_level"].get("events")
    if explained_ids != episode_ids:
        raise ExplanationValidationError("attack-stage explanation event IDs do not match episode evidence")
    if explanation["attack_stage_level"].get("context") != context:
        raise ExplanationValidationError("attack-stage explanation context does not match source context")

    attribution_level = explanation["attribution_level"]
    if not isinstance(attribution_level, dict):
        raise ExplanationValidationError("attribution_level must be a mapping")
    belief = attribution_level.get("belief")
    plausibility = attribution_level.get("plausibility")
    width = attribution_level.get("interval_width")
    if belief is not None or plausibility is not None or width is not None:
        try:
            belief = float(belief)
            plausibility = float(plausibility)
            width = float(width)
        except (TypeError, ValueError) as exc:
            raise ExplanationValidationError("attribution interval values must be numeric") from exc
        if not all(np.isfinite(v) for v in (belief, plausibility, width)):
            raise ExplanationValidationError("attribution interval values must be finite")
        if not 0.0 <= belief <= plausibility <= 1.0:
            raise ExplanationValidationError("attribution interval must satisfy 0 <= belief <= plausibility <= 1")
        if abs(width - (plausibility - belief)) > 1e-12:
            raise ExplanationValidationError("attribution interval width is inconsistent")
    semantics = explanation["confidence_semantics"]
    if semantics.get("attribution_is_evidence_interval") is not True:
        raise ExplanationValidationError("attribution must remain an evidence interval")
    if semantics.get("attribution_is_not_calibrated_probability") is not True:
        raise ExplanationValidationError("attribution must not be represented as calibrated probability")
    dc = semantics.get("detection_confidence")
    if dc is not None and (not np.isfinite(float(dc)) or not 0.0 <= float(dc) <= 1.0):
        raise ExplanationValidationError("detection confidence must be within [0, 1]")

    risk_level = explanation["risk_level"]
    if not np.isfinite(float(risk_level.get("risk_score", -1.0))):
        raise ExplanationValidationError("risk explanation score must be finite")
    if float(risk_level.get("risk_score", -1.0)) != float(risk["score"]):
        raise ExplanationValidationError("risk explanation score does not match risk evidence")
    if risk_level.get("factors") != risk["factors"]:
        raise ExplanationValidationError("risk explanation factors do not match risk evidence")

    expected_factors = ['temporal proximity','affected assets','protocol/communication','event ordering']
    if explanation["behavioral_level"].get("factors") != expected_factors:
        raise ExplanationValidationError("behavioral explanation factors changed unexpectedly")

    return True


def explanation_fingerprint(explanation):
    """Return a stable digest of an already-validated explanation."""
    try:
        payload = json.dumps(explanation, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise ExplanationValidationError("explanation is not deterministically serializable") from exc
    return hashlib.sha256(payload).hexdigest()
