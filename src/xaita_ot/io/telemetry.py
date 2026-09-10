from pathlib import Path
import pandas as pd
from .taxonomy import harmonize_columns

REQUIRED_MIN = {"timestamp"}


def semantic_harmonize(df: pd.DataFrame) -> pd.DataFrame:
    out = harmonize_columns(df)
    if "asset" not in out.columns: out["asset"] = "unknown"
    if "protocol" not in out.columns: out["protocol"] = "unknown"
    return out


def load_csv(path: str | Path) -> pd.DataFrame:
    df = pd.read_csv(path)
    df.columns = [str(c).strip() for c in df.columns]
    df = semantic_harmonize(df)
    missing = REQUIRED_MIN - set(df.columns)
    if missing:
        raise ValueError(f"Missing required columns: {sorted(missing)}")
    df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce", utc=True)
    before = len(df)
    df = df.dropna(subset=["timestamp"]).drop_duplicates().sort_values("timestamp").reset_index(drop=True)
    df.attrs["dropped_invalid_timestamps"] = before - len(df)
    return df
