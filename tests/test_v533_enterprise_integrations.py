import json
from pathlib import Path

import pytest

from xaita_ot.cli import main
from xaita_ot.integrations.enterprise import (
    AUDIT_EVENT_SCHEMA,
    CTI_EXPORT_SCHEMA,
    SIEM_EVENT_SCHEMA,
    build_audit_event,
    build_cti_export,
    build_siem_event,
    validate_audit_event,
    validate_cti_export,
    validate_siem_event,
)

ROOT = Path(__file__).resolve().parents[1]


def load_smoke_cti():
    payload = json.loads((ROOT / "artifacts" / "smoke_cti.json").read_text(encoding="utf-8"))
    return payload[0] if isinstance(payload, list) else payload


def test_siem_contract_preserves_detection_and_attribution_separation():
    event = build_siem_event(load_smoke_cti(), source="test-siem")
    assert event["schema_version"] == SIEM_EVENT_SCHEMA
    assert event["source"] == "test-siem"
    assert event["xaita_ot"]["detection"]["confidence"] is not None
    assert event["xaita_ot"]["attribution"]["belief"] is not None
    assert event["xaita_ot"]["attribution"]["plausibility"] is not None
    assert event["human_validation_required"] is True
    assert event["autonomous_ot_action"] is False
    assert validate_siem_event(event) == event


def test_cti_export_wraps_stix_21_and_records_source_digest():
    export = build_cti_export(load_smoke_cti())
    assert export["schema_version"] == CTI_EXPORT_SCHEMA
    assert export["format"] == "STIX-2.1"
    assert export["bundle"]["type"] == "bundle"
    assert export["bundle"]["objects"]
    assert len(export["source_cti_sha256"]) == 64
    assert len(export["export_sha256"]) == 64
    assert validate_cti_export(export) == export


def test_audit_event_is_deterministic_for_fixed_inputs():
    kwargs = {
        "action": "cti.export",
        "actor": "analyst@example",
        "outcome": "success",
        "correlation_id": "corr-001",
        "incident_id": "EP-00001",
        "timestamp": "2026-10-05T08:00:00Z",
        "details": {"format": "STIX-2.1"},
    }
    first = build_audit_event(**kwargs)
    second = build_audit_event(**kwargs)
    assert first == second
    assert first["schema_version"] == AUDIT_EVENT_SCHEMA
    assert len(first["event_id"]) == 64
    assert validate_audit_event(first) == first


def test_cli_exposes_enterprise_contracts(tmp_path):
    siem = tmp_path / "siem.json"
    cti = tmp_path / "cti.json"
    audit = tmp_path / "audit.json"
    source = ROOT / "artifacts" / "smoke_cti.json"

    assert main(["siem-export", "--cti", str(source), "--out", str(siem)]) == 0
    assert main(["cti-export", "--cti", str(source), "--out", str(cti)]) == 0
    assert main([
        "audit-event", "--action", "cti.export", "--actor", "analyst",
        "--outcome", "success", "--correlation-id", "corr-001",
        "--timestamp", "2026-10-05T08:00:00Z", "--out", str(audit),
    ]) == 0

    assert json.loads(siem.read_text())["schema_version"] == SIEM_EVENT_SCHEMA
    assert json.loads(cti.read_text())["schema_version"] == CTI_EXPORT_SCHEMA
    assert json.loads(audit.read_text())["schema_version"] == AUDIT_EVENT_SCHEMA


def test_contracts_fail_closed_on_invalid_input():
    with pytest.raises(ValueError):
        build_siem_event({"schema_version": "wrong", "incident_id": "x"})
    with pytest.raises(ValueError):
        validate_siem_event({"schema_version": SIEM_EVENT_SCHEMA})
    with pytest.raises(ValueError):
        validate_cti_export({"schema_version": CTI_EXPORT_SCHEMA})
    with pytest.raises(ValueError):
        build_audit_event(action="", actor="a", outcome="success", correlation_id="c")
