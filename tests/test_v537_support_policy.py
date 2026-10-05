import json
from pathlib import Path

import pytest

from xaita_ot.support import (
    SCHEMA_VERSION,
    classify_support_request,
    load_support_policy,
    validate_support_policy,
)
from xaita_ot.cli import main

ROOT = Path(__file__).resolve().parents[1]
POLICY = ROOT / "configs" / "support_policy.json"


def test_support_policy_is_versioned_and_complete():
    policy = load_support_policy(POLICY)
    assert policy["schema_version"] == SCHEMA_VERSION
    assert set(policy["severity"]) == {"critical", "high", "medium", "low"}
    assert policy["vulnerability_disclosure"]["public_issue_for_sensitive_vulnerability"] is False
    assert policy["deployment_boundary"]["autonomous_ot_control"] == "prohibited"


@pytest.mark.parametrize("severity", ["critical", "high", "medium", "low"])
def test_support_classification_is_deterministic(severity):
    result = classify_support_request(load_support_policy(POLICY), severity)
    assert result["severity"] == severity
    assert result["acknowledgement_target"]
    assert result["triage_target"]


def test_sensitive_disclosure_policy_fails_closed():
    policy = json.loads(POLICY.read_text(encoding="utf-8"))
    policy["vulnerability_disclosure"]["public_issue_for_sensitive_vulnerability"] = True
    with pytest.raises(ValueError):
        validate_support_policy(policy)


def test_support_cli(tmp_path):
    output = tmp_path / "support.json"
    assert main(["support-check", "--severity", "critical", "--out", str(output)]) == 0
    result = json.loads(output.read_text(encoding="utf-8"))
    assert result["schema_version"] == SCHEMA_VERSION
    assert result["severity"] == "critical"
