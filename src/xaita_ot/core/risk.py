def score_risk(severity, operational_impact, criticality, attribution_evidence, weights):
    vals={'severity':max(0,min(1,severity)),'operational_impact':max(0,min(1,operational_impact)),'criticality':max(0,min(1,criticality)),'attribution':max(0,min(1,attribution_evidence))}
    score=sum(vals[k]*weights.get(k,0) for k in vals)
    level='LOW' if score<0.35 else 'MEDIUM' if score<0.65 else 'HIGH' if score<0.85 else 'CRITICAL'
    return {'score':float(score),'level':level,'factors':vals,'weights':weights}
