import uuid
from datetime import datetime, timezone

def _id(kind): return f"{kind}--{uuid.uuid4()}"

def to_stix_bundle(cti):
    now=datetime.now(timezone.utc).isoformat().replace('+00:00','Z')
    identity={'type':'identity','spec_version':'2.1','id':_id('identity'),'created':now,'modified':now,'name':'XAITA-OT','identity_class':'system'}
    objects=[identity]
    refs=[]
    for tech in cti.get('context',[]):
        ap={'type':'attack-pattern','spec_version':'2.1','id':_id('attack-pattern'),'created':now,'modified':now,
            'name':tech.get('name','ATT&CK for ICS Technique'),
            'description':'ATT&CK contextual evidence associated by XAITA-OT; not actor identity proof.',
            'external_references':[{'source_name':'mitre-attack','external_id':tech.get('technique_id',''),'url':f"https://attack.mitre.org/techniques/ics/{tech.get('technique_id','')}"}]}
        objects.append(ap); refs.append(ap['id'])
    note={'type':'note','spec_version':'2.1','id':_id('note'),'created':now,'modified':now,
          'content':(f"XAITA-OT incident {cti['incident_id']}; risk={cti['risk']['level']}; "
                     f"attribution hypothesis={cti['attribution']['hypothesis']}; "
                     f"belief={cti['attribution']['belief']:.3f}; plausibility={cti['attribution']['plausibility']:.3f}. "
                     "Human validation required; no autonomous OT action."),
          'created_by_ref':identity['id'],'object_refs':refs}
    objects.append(note)
    return {'type':'bundle','id':_id('bundle'),'objects':objects}
