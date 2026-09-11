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
