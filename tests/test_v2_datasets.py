import pandas as pd
from xaita_ot.io.adapters import adapt_dataset
from xaita_ot.io.telemetry import load_csv


def test_all_v2_adapters_harmonize_native_timestamp_and_labels(tmp_path):
    fixtures = {
        "SWaT": {"Timestamp": ["2026-01-01T00:00:00Z", "2026-01-01T00:00:01Z"], "Label": ["Normal", "Attack"]},
        "BATADAL": {"DATETIME": ["2026-01-01T00:00:00Z", "2026-01-01T00:00:01Z"], "attack": [0, 1]},
        "TON-IoT": {"ts": ["2026-01-01T00:00:00Z", "2026-01-01T00:00:01Z"], "type": ["normal", "attack"]},
    }
    for dataset, values in fixtures.items():
        path = tmp_path / f"{dataset}.csv"
        pd.DataFrame(values).to_csv(path, index=False)
        loaded = load_csv(path)
        out = adapt_dataset(loaded, dataset)
        assert "timestamp" in out.columns
        assert out["timestamp"].notna().all()
        assert out["label"].tolist() == [0, 1]
        for field in ("asset", "protocol", "src_ip", "dst_ip"):
            assert field in out.columns


def test_unknown_dataset_rejected():
    try:
        adapt_dataset(pd.DataFrame({"timestamp": []}), "unknown")
    except ValueError as exc:
        assert "Unsupported V2 dataset" in str(exc)
    else:
        raise AssertionError("unknown dataset must be rejected")
