import pandas as pd
from xaita_ot.io.adapters import adapt_dataset


def test_swat_adapter_harmonizes_timestamp_and_label():
    df = pd.DataFrame({"Timestamp": ["2026-01-01 00:00:00"], "Normal/Attack": ["Normal"]})
    out = adapt_dataset(df, "SWaT")
    assert "timestamp" in out and out.loc[0, "label"] == 0


def test_batadal_adapter_harmonizes_datetime():
    df = pd.DataFrame({"DATETIME": ["2026-01-01 00:00:00"], "attack": [1]})
    out = adapt_dataset(df, "BATADAL")
    assert "timestamp" in out and out.loc[0, "label"] == 1


def test_toniot_adapter_harmonizes_ts_and_attack():
    df = pd.DataFrame({"ts": ["2026-01-01 00:00:00"], "Attack": ["Normal"]})
    out = adapt_dataset(df, "TON-IoT")
    assert "timestamp" in out and out.loc[0, "label"] == 0


def test_unknown_dataset_rejected():
    try:
        adapt_dataset(pd.DataFrame({"timestamp": []}), "unknown")
    except ValueError as exc:
        assert "Unsupported V2 dataset" in str(exc)
    else:
        raise AssertionError("unknown dataset must be rejected")
