from pathlib import Path
import json

from xaita_ot.pipeline.v3_phase8 import TABLE_SCHEMAS, generate_phase8

ROOT = Path(__file__).resolve().parents[1]


def _paths():
    return {"SWaT": str(ROOT / "data/demo/swat_like.csv"), "BATADAL": str(ROOT / "data/demo/batadal_like.csv"), "TON-IoT": str(ROOT / "data/demo/toniot_like.csv")}


def test_phase8_has_exact_requested_tables():
    assert list(TABLE_SCHEMAS) == [4, 5, 6, 7, 8, 9, 10, 17, 18]


def test_phase8_generates_all_nine_tables(tmp_path):
    artifact_root = tmp_path / "v3"
    (artifact_root / "phase3").mkdir(parents=True)
    (artifact_root / "phase4").mkdir(parents=True)
    # The generator must still produce the complete table package when upstream
    # result artifacts are unavailable; unsupported measures are explicit NA.
    result = generate_phase8(_paths(), artifact_root, tmp_path / "phase8", seed=42)
    assert result["phase"] == "V3.8"
    assert set(result["generated"]) == {"4", "5", "6", "7", "8", "9", "10", "17", "18"}
    assert all(Path(p).exists() for p in result["generated"].values())
    payload = json.loads((tmp_path / "phase8" / "paper_tables.json").read_text())
    assert set(payload) == {"4", "5", "6", "7", "8", "9", "10", "17", "18"}
    for number, cols in TABLE_SCHEMAS.items():
        assert list(__import__('pandas').read_csv(tmp_path / "phase8" / f"table_{number}.csv").columns) == cols


def test_paper_table_generator_does_not_mislabel_or_invent_unsupported_metrics():
    from xaita_ot.pipeline.v3_phase8 import _table6, _table7, _table8, _table10, _table18

    cross = {
        "pairs": {
            "SWaT->BATADAL": {
                "runs": [{"metrics": {"cnn_lstm": {"f1": 0.91}}}]
            }
        }
    }
    assert _table6(cross)[0]["Macro-F1"] == "NA"

    case_study = {
        "SWaT": {
            "cases": [{
                "btae_reconstruction": {"correlation_strength": 0.99},
                "provenance": ["id1", "id2", "id3", "id4", "id5", "id6"],
                "cti": {"provenance": ["id1", "id2", "id3", "id4", "id5", "id6"]},
            }]
        }
    }
    assert _table7(case_study, {"SWaT": "ignored"})[0]["Correlation F1"] == "NA"
    table10 = {row["Metric"]: row["Result"] for row in _table10(case_study)}
    assert table10["Traceability"] == "NA"
    assert table10["Provenance Consistency"] == "NA"

    calibration = {
        "runs": [{
            "detector": {"ece": 0.05},
            "fusion": {
                "WEF": {"ece": 0.01, "score_mean": 0.8},
                "ACFM": {"ece": 0.02, "belief_mean": 0.7, "plausibility_mean": 0.95, "interval_width_mean": 0.25},
            },
        }]
    }
    table8 = _table8(calibration)
    assert table8[0]["ECE ↓"] == 0.05
    assert all(row["ECE ↓"] == "NA" for row in table8 if row["Configuration"] != "Detection Confidence Only")
    assert all(row["Mean Belief"] == "NA" for row in table8 if row["Configuration"] != "ACFM")

    ablation = {"runs": [{"variants": {"Full XAITA-OT": {"f1": 0.9}}}]}
    table18 = _table18(ablation, None, case_study)
    assert table18[0]["Detection F1"] == "NA"
    assert table18[0]["Attribution F1"] == "NA"
