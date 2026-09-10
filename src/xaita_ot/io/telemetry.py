from pathlib import Path
import pandas as pd

REQUIRED_MIN = {"timestamp"}

def load_csv(path: str | Path) -> pd.DataFrame:
    df = pd.read_csv(path)
    missing = REQUIRED_MIN - set(df.columns)
    if missing:
        raise ValueError(f"Missing required columns: {sorted(missing)}")
    df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce", utc=True)
    df = df.dropna(subset=["timestamp"]).sort_values("timestamp").reset_index(drop=True)
    return df

def semantic_harmonize(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    aliases = {
        "time": "timestamp", "Time": "timestamp", "Timestamp": "timestamp",
        "src_ip": "src_ip", "source_ip": "src_ip", "Source IP": "src_ip",
        "dst_ip": "dst_ip", "destination_ip": "dst_ip", "Destination IP": "dst_ip",
        "device": "asset", "Device": "asset", "host": "asset",
        "protocol_name": "protocol", "Protocol": "protocol",
    }
    for a, b in aliases.items():
        if a in out.columns and b not in out.columns:
            out[b] = out[a]
    if "asset" not in out.columns:
        out["asset"] = "unknown"
    if "protocol" not in out.columns:
        out["protocol"] = "unknown"
    return out
