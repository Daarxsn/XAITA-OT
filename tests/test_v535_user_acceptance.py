import json

from scripts.v5_user_acceptance import run_acceptance


def test_independent_acceptance_contract():
    payload = run_acceptance()
    assert payload["schema_version"] == "XAITA-OT-V5-INDEPENDENT-ACCEPTANCE-1.0"
    assert payload["status"] == "pass"
    assert payload["live_validation"] is False
    live = next(item for item in payload["checks"] if item["check"] == "live operational probe")
    assert live["status"] == "skipped"


def test_acceptance_surface_is_machine_readable():
    payload = run_acceptance()
    encoded = json.dumps(payload)
    assert "verification_boundary" in encoded
    assert "disposable end-to-end smoke" in encoded
