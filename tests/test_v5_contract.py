from xaita_ot.v5 import V5_CONTRACT, V5Contract


def test_v5_contract_identity_and_pipeline():
    assert isinstance(V5_CONTRACT, V5Contract)
    assert V5_CONTRACT.version == "5.1"
    assert V5_CONTRACT.pipeline == (
        "observation",
        "detection",
        "episode",
        "context",
        "attribution",
        "explanation",
        "risk",
        "cti",
    )


def test_v5_contract_preserves_safety_invariants():
    capabilities = V5_CONTRACT.as_dict()
    assert capabilities["preserves_confidence_separation"] is True
    assert capabilities["preserves_provenance"] is True
    assert capabilities["analyst_support_only"] is True
    assert capabilities["pipeline"] == list(V5_CONTRACT.pipeline)


def test_v5_developer_contract_is_explicit():
    assert V5_CONTRACT.contract_id == "XAITA-OT-V5-DEV-1.0"
    assert V5_CONTRACT.supported_python == ("3.10", "3.11", "3.12", "3.13")
    assert V5_CONTRACT.cli_commands == ("demo", "synthetic-data", "validate-data")
    assert V5_CONTRACT.api_routes == (
        "GET /health",
        "GET /ready",
        "GET /",
        "GET /v2/system",
        "GET /v2/capabilities",
        "GET /v2/ops/summary",
        "GET /v2/datasets",
        "GET /v2/benchmark",
        "POST /v2/experiment",
        "POST /v1/analyze",
    )


def test_v5_contract_serialization_is_stable():
    document = V5_CONTRACT.as_dict()
    assert document["contract_id"] == "XAITA-OT-V5-DEV-1.0"
    assert document["supported_python"] == ["3.10", "3.11", "3.12", "3.13"]
    assert document["cli_commands"] == ["demo", "synthetic-data"]
    assert document["api_routes"][0] == "GET /health"
