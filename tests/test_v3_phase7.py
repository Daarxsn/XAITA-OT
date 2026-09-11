from pathlib import Path

from xaita_ot.config import AppConfig
from xaita_ot.pipeline.v3_phase7 import build_case

ROOT = Path(__file__).resolve().parents[1]
PATHS = {
    "SWaT": ROOT / "data/demo/swat_like.csv",
    "BATADAL": ROOT / "data/demo/batadal_like.csv",
    "TON-IoT": ROOT / "data/demo/toniot_like.csv",
}
REQUIRED = {"episode_selection", "attack_sequence", "btae_reconstruction", "attack_mapping", "attribution_hypotheses", "acfm", "xai", "risk", "cti", "provenance"}


def test_phase7_case_schema_and_traceability():
    cfg = AppConfig(); cfg.model.window_size = 4
    for dataset, path in PATHS.items():
        result = build_case(path, dataset, cfg, seed=42, top_n=1)
        assert result["status"] == "PASS"
        assert result["cases"]
        case = result["cases"][0]
        assert REQUIRED <= set(case)
        assert case["attack_sequence"]
        assert case["btae_reconstruction"]["episode_id"] == case["episode_selection"]["episode_id"]
        assert case["provenance"]
        assert case["cti"]["provenance"] == case["provenance"]
        assert 0 <= case["risk"]["normalized"] <= 1
        assert 0 <= case["acfm"]["best_hypothesis"]["belief"] <= 1
        assert 0 <= case["acfm"]["best_hypothesis"]["plausibility"] <= 1
        assert case["xai"]["features"] or case["xai"]["method"]
        for mapping in case["attack_mapping"]:
            assert mapping["mapping_status"] == "hypothesis"
            assert mapping["technique_id"].startswith("T")
