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
