import json
from pathlib import Path

import pytest

from xaita_ot.governance import SCHEMA_VERSION, evaluate_deployment, load_policy, validate_policy
from xaita_ot.cli import main

ROOT = Path(__file__).resolve().parents[1]
POLICY = ROOT / "configs" / "governance.yaml.json"


def test_governance_policy_is_versioned_and_fail_closed():
    policy = load_policy(POLICY)
    assert policy["schema_version"] == SCHEMA_VERSION
    assert set(policy["datasets"]) == {"SWaT", "BATADAL", "TON-IoT"}
    assert policy["deployment"]["autonomous_ot_control"] == "prohibited"


def test_governance_requires_all_deployment_evidence():
    policy = load_policy(POLICY)
    result = evaluate_deployment(policy, {})
    assert result["status"] == "review_required"
    assert result["missing_evidence"]


def test_governance_approves_only_when_every_required_control_is_present():
    policy = load_policy(POLICY)
    evidence = {key: True for key in policy["deployment"]["required_evidence"]}
    result = evaluate_deployment(policy, evidence)
    assert result["status"] == "approved"
    assert result["missing_evidence"] == []


def test_invalid_governance_policy_fails_closed():
    policy = json.loads(POLICY.read_text(encoding="utf-8"))
    policy["deployment"]["autonomous_ot_control"] = "allowed"
    with pytest.raises(ValueError):
        validate_policy(policy)


def test_governance_cli_returns_review_required_until_evidence_exists(tmp_path):
    output = tmp_path / "governance.json"
    assert main(["governance-check", "--policy", str(POLICY), "--out", str(output)]) == 2
    result = json.loads(output.read_text(encoding="utf-8"))
    assert result["status"] == "review_required"
