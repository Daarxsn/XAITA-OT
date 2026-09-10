from datetime import datetime, timezone
import json

def generate_cti(incident_id, detection, episode, context, attribution, xai, risk):
    provenance=[]
    for e in episode.events: provenance.append(e.event_id)
    return {
      'schema_version':'XAITA-OT-CTI-1.0',
      'incident_id':incident_id,
      'generated_at':datetime.now(timezone.utc).isoformat(),
      'detection':detection,
      'behavior':{'episode_id':episode.episode_id,'event_ids':provenance,'correlation_strength':episode.correlation_strength,'stages':episode.stages},
      'context':context,
      'attribution':attribution,
      'xai':xai,
      'risk':risk,
      'provenance':provenance,
      'human_validation_required':True,
      'autonomous_ot_action':False,
    }

def write_json(obj,path):
    with open(path,'w',encoding='utf-8') as f: json.dump(obj,f,indent=2,default=str)
