import pandas as pd
from xaita_ot.io.adapters import adapt_dataset
from xaita_ot.io.telemetry import load_csv


def test_all_v2_adapters_harmonize_native_timestamp_and_labels(tmp_path):
    fixtures = {
        "SWaT": {"Timestamp": ["2026-01-01T00:00:00Z", "2026-01-01T00:00:01Z"], "Label": ["Normal", "Attack"]},
        "BATADAL": {"DATETIME": ["2026-01-01T00:00:00Z", "2026-01-01T00:00:01Z"], "attack": [0, 1]},
        "TON-IoT": {"ts": ["2026-01-01T00:00:00Z", "2026-01-01T00:00:01Z"], "type": ["normal", "attack"], "label": [0, 1]},
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


def test_swat_attack_state_boolean_and_numeric_values_are_attacks():
    df = pd.DataFrame({
        "Timestamp": ["2026-01-01T00:00:00Z"] * 5,
        "Attack State": ["False", "True", "5.0", "7.0", ""],
    })
    out = adapt_dataset(df, "SWaT")
    assert out["label"].tolist() == [0, 1, 1, 1, 0]


def test_unknown_dataset_rejected():
    try:
        adapt_dataset(pd.DataFrame({"timestamp": []}), "unknown")
    except ValueError as exc:
        assert "Unsupported V2 dataset" in str(exc)
    else:
        raise AssertionError("unknown dataset must be rejected")



def test_toniot_categorical_type_is_not_used_as_binary_ground_truth():
    import pytest

    df = pd.DataFrame({
        "ts": ["2026-01-01T00:00:00Z", "2026-01-01T00:00:01Z"],
        "type": ["normal", "backdoor"],
    })
    with pytest.raises(ValueError, match="No explicit binary ground-truth label column"):
        adapt_dataset(df, "TON-IoT")


def test_adapter_fails_closed_when_no_dataset_label_exists():
    import pytest

    df = pd.DataFrame({
        "Timestamp": ["2026-01-01T00:00:00Z"],
        "sensor": [1.25],
    })
    with pytest.raises(ValueError, match="No explicit binary ground-truth label column"):
        adapt_dataset(df, "SWaT")



def test_adapter_rejects_unknown_categorical_label_values():
    import pytest

    df = pd.DataFrame({
        "Timestamp": ["2026-01-01T00:00:00Z", "2026-01-01T00:00:01Z"],
        "Label": ["Normal", "backdoor"],
    })
    with pytest.raises(ValueError, match="unknown/non-binary values"):
        adapt_dataset(df, "SWaT")



def test_batadal_unknown_negative_label_sentinel_is_not_normalized_as_benign():
    import pytest

    df = pd.DataFrame({
        "DATETIME": ["2026-01-01T00:00:00Z", "2026-01-01T01:00:00Z"],
        "ATT_FLAG": [0, -999],
    })
    with pytest.raises(ValueError, match="negative/unknown sentinel values"):
        adapt_dataset(df, "BATADAL")
