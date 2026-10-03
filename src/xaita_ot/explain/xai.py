import hashlib
import json

import numpy as np


EXPLANATION_SCHEMA_VERSION = "XAITA-OT-XAI-1.1"


class ExplanationValidationError(ValueError):
    """Raised when an explanation is inconsistent with its source evidence."""


def feature_importance_linearized(X, feature_names, weights=None, top_k=8):
    if len(X)==0: return []
    x=np.mean(np.abs(X),axis=(0,1))
    if weights is not None: x=x*np.abs(weights)
    order=np.argsort(x)[::-1][:top_k]
    denom=float(x.sum()) or 1.0
    return [{'feature':feature_names[i],'importance':float(x[i]/denom)} for i in order]


def build_explanation(event, episode, context, risk, feature_importance):
    return {
      'schema_version': EXPLANATION_SCHEMA_VERSION,
      'feature_level': {'question':'Why was the activity detected?','top_features':feature_importance},
      'behavioral_level': {'question':'Why were the events correlated?','factors':['temporal proximity','affected assets','protocol/communication','event ordering']},
      'attack_stage_level': {'question':'How did the attack progress?','events':[e.event_id for e in episode.events],'context':context},
      'risk_level': {'question':'Why was the incident prioritized?','risk_score':risk['score'],'factors':risk['factors']},
    }


def validate_explanation(explanation, episode, context, risk):
    """Validate explanation claims against the exact objects used to generate them."""
    if not isinstance(explanation, dict):
        raise ExplanationValidationError("explanation must be a mapping")
    required = {"schema_version", "feature_level", "behavioral_level", "attack_stage_level", "risk_level"}
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
    if any(value < 0.0 or value > 1.0 for value in importances):
        raise ExplanationValidationError("feature importance must be within [0, 1]")
    if features and abs(sum(importances) - 1.0) > 1e-6:
        raise ExplanationValidationError("feature importances must sum to 1")

    episode_ids = [event.event_id for event in episode.events]
    explained_ids = explanation["attack_stage_level"].get("events")
    if explained_ids != episode_ids:
        raise ExplanationValidationError("attack-stage explanation event IDs do not match episode evidence")
    if explanation["attack_stage_level"].get("context") != context:
        raise ExplanationValidationError("attack-stage explanation context does not match source context")

    risk_level = explanation["risk_level"]
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
