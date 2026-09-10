from pathlib import Path

import yaml

DEFAULT_TECHNIQUES = {
    "reconnaissance": {"technique_id": "T0846", "name": "Remote System Discovery"},
    "protocol": {"technique_id": "T0869", "name": "Standard Application Layer Protocol"},
    "unauthorized_command": {"technique_id": "T0855", "name": "Unauthorized Command Message"},
    "process_deviation": {"technique_id": "T0814", "name": "DoS: Network Flooding"},
}


def load_attack_map(path="configs/attack_mapping.yaml"):
    p = Path(path)
    if not p.exists():
        return DEFAULT_TECHNIQUES
    loaded = yaml.safe_load(p.read_text(encoding="utf-8")) or {}
    return loaded or DEFAULT_TECHNIQUES


def contextualize(episode, mapping=None):
    mapping = mapping or DEFAULT_TECHNIQUES
    out = []
    for event in episode.events:
        key = event.label.lower().replace(" ", "_")
        item = mapping.get(key)
        if item:
            out.append(
                {
                    "event_id": event.event_id,
                    **item,
                    "supporting_evidence": [event.event_id],
                }
            )
    return out
