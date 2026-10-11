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
    # Some TON-IoT files store date and clock time in separate columns.
    # Combine before taxonomy harmonization could mistake "time" alone for the
    # event timestamp and sort/deduplicate records by time-of-day.
    raw_columns = {str(column).strip().lower(): column for column in df.columns}
    explicit_timestamp_aliases = {"timestamp", "datetime", "ts", "date_time", "date time"}
    if (
        "timestamp" not in raw_columns
        and not (explicit_timestamp_aliases & set(raw_columns))
        and "date" in raw_columns
        and "time" in raw_columns
    ):
        date_column = raw_columns["date"]
        time_column = raw_columns["time"]
        df["timestamp"] = pd.to_datetime(
            df[date_column].astype(str).str.strip()
            + " "
            + df[time_column].astype(str).str.strip(),
            errors="coerce",
            utc=True,
            dayfirst=True,
        )
    if len(df.columns) != len(set(df.columns)):
        duplicates = sorted({c for c in df.columns if list(df.columns).count(c) > 1})
        raise ValueError(f"Duplicate columns: {duplicates}")
    df = semantic_harmonize(df)
    missing = REQUIRED_MIN - set(df.columns)
    if missing and require_timestamp:
        raise ValueError(f"Missing required columns: {sorted(missing)}")
    if "timestamp" not in df.columns:
        return df
    # SWaT, BATADAL, and TON-IoT include day-first timestamps as well as ISO
    # timestamps. ISO year-first values remain unambiguous with dayfirst enabled.
    parsed = pd.to_datetime(df["timestamp"], errors="coerce", utc=True, dayfirst=True)
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
