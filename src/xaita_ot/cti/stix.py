from __future__ import annotations

import uuid
from datetime import datetime, timezone


def _id(kind: str, key: str) -> str:
    return f"{kind}--{uuid.uuid5(uuid.NAMESPACE_URL, 'xaita-ot:' + kind + ':' + key)}"


def _timestamp(cti: dict) -> str:
    raw = cti.get("generated_at")
    if raw:
        try:
            return datetime.fromisoformat(str(raw).replace("Z", "+00:00")).astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
        except ValueError as exc:
            raise ValueError("CTI generated_at must be a valid ISO-8601 timestamp") from exc
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def to_stix_bundle(cti):
    now = _timestamp(cti)
    incident_id = str(cti.get("incident_id", "unknown"))
    identity = {
        "type": "identity",
        "spec_version": "2.1",
        "id": _id("identity", "xaita-ot"),
        "created": now,
        "modified": now,
        "name": "XAITA-OT",
        "identity_class": "system",
    }
    objects = [identity]
    refs = []
    seen = set()
    for index, tech in enumerate(cti.get("context", [])):
        technique_id = str(tech.get("technique_id", ""))
        technique_name = str(tech.get("name", "ATT&CK for ICS Technique"))
        key = f"{incident_id}:technique:{technique_id or index}:{technique_name}"
        ap = {
            "type": "attack-pattern",
            "spec_version": "2.1",
            "id": _id("attack-pattern", key),
            "created": now,
            "modified": now,
            "name": technique_name,
            "description": "ATT&CK contextual evidence associated by XAITA-OT; not actor identity proof.",
            "external_references": [{
                "source_name": "mitre-attack",
                "external_id": technique_id,
                "url": f"https://attack.mitre.org/techniques/ics/{technique_id}",
            }],
        }
        objects.append(ap)
        if ap["id"] not in seen:
            refs.append(ap["id"])
            seen.add(ap["id"])
    note = {
        "type": "note",
        "spec_version": "2.1",
        "id": _id("note", incident_id),
        "created": now,
        "modified": now,
        "content": (
            f"XAITA-OT incident {incident_id}; risk={cti['risk']['level']}; "
            f"attribution hypothesis={cti['attribution']['hypothesis']}; "
            f"belief={cti['attribution']['belief']:.3f}; plausibility={cti['attribution']['plausibility']:.3f}. "
            "Human validation required; no autonomous OT action."
        ),
        "created_by_ref": identity["id"],
        "object_refs": refs,
    }
    objects.append(note)
    return {
        "type": "bundle",
        "id": _id("bundle", incident_id),
        "objects": objects,
    }
