from dataclasses import asdict
from .schemas import AttributionAssessment

def assess(hypotheses, evidence, reliabilities):
    # evidence: {H: {DC,BSS,ECS,EC,MAS}} with values in [0,1].
    assessments=[]
    for h, vals in evidence.items():
        support=0.0; conflict=0.0; unresolved=[]; supporting=[]; conflicting=[]
        for k,v in vals.items():
            r=float(reliabilities.get(k,0.5)); score=max(0,min(1,float(v)))
            contribution=r*score
            if score>=0.60:
                support += contribution; supporting.append({'source':k,'value':score,'reliability':r})
            elif score<=0.35:
                conflict += r*(1-score); conflicting.append({'source':k,'value':score,'reliability':r})
            else:
                unresolved.append({'source':k,'value':score,'reliability':r})
        total=max(1.0,support+conflict)
        belief=min(1.0,support/total)
        plausibility=min(1.0,(support+sum(x['reliability']*x['value'] for x in unresolved))/max(1.0,support+conflict))
        assessments.append(AttributionAssessment(h,belief,max(belief,plausibility),supporting,conflicting,unresolved))
    assessments.sort(key=lambda a:(a.belief,a.plausibility),reverse=True)
    return assessments

def to_dict(a):
    d=asdict(a); d['interval_width']=a.interval_width; return d
