from pathlib import Path
import yaml

DEFAULT_TECHNIQUES = {
  "reconnaissance": {"technique_id":"T0846", "name":"Remote System Discovery"},
  "protocol": {"technique_id":"T0869", "name":"Standard Application Layer Protocol"},
  "unauthorized_command": {"technique_id":"T0855", "name":"Unauthorized Command Message"},
  "process_deviation": {"technique_id":"T0814", "name":"DoS: Network Flooding"},
}

def load_attack_map(path='configs/attack_mapping.yaml'):
    p=Path(path)
    return yaml.safe_load(p.read_text()) if p.exists() else DEFAULT_TECHNIQUES

def contextualize(episode, mapping=None):
    mapping=mapping or DEFAULT_TECHNIQUES
    out=[]
    for e in episode.events:
        key=e.label.lower().replace(' ','_')
        item=mapping.get(key)
        if item:
            out.append({'event_id':e.event_id,**item,'supporting_evidence':[e.event_id]})
    return out
