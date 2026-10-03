import os
from pathlib import Path

import yaml

from ..cti.package import load_cti_package, validate_cti_package, cti_package_metadata

DEFAULT_TECHNIQUES = {
    "reconnaissance": {"technique_id": "T0846", "name": "Remote System Discovery"},
    "protocol": {"technique_id": "T0869", "name": "Standard Application Layer Protocol"},
    "unauthorized_command": {"technique_id": "T0855", "name": "Unauthorized Command Message"},
    "process_deviation": {"technique_id": "T0831", "name": "Manipulation of Control"},
}


def load_attack_map(path=None):
    if path is None:
        root = Path(os.environ.get("XAITA_OT_ROOT", Path.cwd()))
        p = root / "configs" / "attack_mapping.yaml"
    else:
        p = Path(path)
    if not p.exists():
        return DEFAULT_TECHNIQUES
    loaded = yaml.safe_load(p.read_text(encoding="utf-8")) or {}
    return loaded or DEFAULT_TECHNIQUES


def contextualize(episode, mapping=None):
    mapping = mapping or DEFAULT_TECHNIQUES
    out = []
    for event in episode.events:
        key = event.label.strip().lower().replace(" ", "_")
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


def load_reviewed_attack_map(path=None):
    """Return the pinned, reviewed ATT&CK-for-ICS package mapping only."""
    package = load_cti_package(path)
    validate_cti_package(package)
    return package["mappings"]


def reviewed_attack_package_metadata(path=None):
    package = load_cti_package(path)
    return cti_package_metadata(package)
