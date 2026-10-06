from pathlib import Path
import pandas as pd
from .taxonomy import harmonize_columns

REQUIRED_MIN = {"timestamp"}


def semantic_harmonize(df: pd.DataFrame) -> pd.DataFrame:
    out = harmonize_columns(df)
    if "asset" not in out.columns: out["asset"] = "unknown"
    if "protocol" not in out.columns: out["protocol"] = "unknown"
    return out


def load_csv(
    path: str | Path,
    require_timestamp: bool = True,
    *,
    strict_timestamps: bool = False,
    sort_and_deduplicate: bool = True,
) -> pd.DataFrame:
    """Load and normalize a CSV with optional strict timestamp semantics."""
    source = Path(path)
    if not source.is_file():
        raise FileNotFoundError(source)
    df = pd.read_csv(source)
    df.columns = [str(c).strip() for c in df.columns]
    if len(df.columns) != len(set(df.columns)):
        duplicates = sorted({c for c in df.columns if list(df.columns).count(c) > 1})
        raise ValueError(f"Duplicate columns: {duplicates}")
    df = semantic_harmonize(df)
    missing = REQUIRED_MIN - set(df.columns)
    if missing and require_timestamp:
        raise ValueError(f"Missing required columns: {sorted(missing)}")
    if "timestamp" not in df.columns:
        return df
    parsed = pd.to_datetime(df["timestamp"], errors="coerce", utc=True)
    invalid = int(parsed.isna().sum())
    duplicate_timestamps = int(parsed.dropna().duplicated().sum())
    out_of_order = bool(not parsed.dropna().is_monotonic_increasing)
    if strict_timestamps and invalid:
        raise ValueError(f"Invalid timestamps detected: {invalid}")
    if strict_timestamps and duplicate_timestamps:
        raise ValueError(f"Duplicate timestamps detected: {duplicate_timestamps}")
    if strict_timestamps and out_of_order:
        raise ValueError("Timestamps are not monotonically increasing")
    df["timestamp"] = parsed
    if sort_and_deduplicate:
        before = len(df)
        df = df.dropna(subset=["timestamp"]).drop_duplicates().sort_values("timestamp").reset_index(drop=True)
        df.attrs["dropped_invalid_timestamps"] = before - len(df)
    else:
        df.attrs["dropped_invalid_timestamps"] = invalid
    df.attrs["duplicate_timestamps"] = duplicate_timestamps
    df.attrs["timestamps_sorted"] = not out_of_order
    return df
