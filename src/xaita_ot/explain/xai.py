import numpy as np

def feature_importance_linearized(X, feature_names, weights=None, top_k=8):
    if len(X)==0: return []
    x=np.mean(np.abs(X),axis=(0,1))
    if weights is not None: x=x*np.abs(weights)
    order=np.argsort(x)[::-1][:top_k]
    denom=float(x.sum()) or 1.0
    return [{'feature':feature_names[i],'importance':float(x[i]/denom)} for i in order]

def build_explanation(event, episode, context, risk, feature_importance):
    return {
      'feature_level': {'question':'Why was the activity detected?','top_features':feature_importance},
      'behavioral_level': {'question':'Why were the events correlated?','factors':['temporal proximity','affected assets','protocol/communication','event ordering']},
      'attack_stage_level': {'question':'How did the attack progress?','events':[e.event_id for e in episode.events],'context':context},
      'risk_level': {'question':'Why was the incident prioritized?','risk_score':risk['score'],'factors':risk['factors']},
    }
