"""Canonical cross-dataset OT/ICS feature taxonomy for V2."""

CANONICAL_FIELDS = {
    "timestamp": "event timestamp",
    "asset": "OT asset/device identifier",
    "protocol": "industrial/IIoT protocol family",
    "src_ip": "source endpoint",
    "dst_ip": "destination endpoint",
    "label": "binary attack label",
}

DATASET_ALIASES = {
    "Timestamp": "timestamp", "DATETIME": "timestamp", "ts": "timestamp", "time": "timestamp", "Time": "timestamp",
    "Device": "asset", "device": "asset", "host": "asset", "Host": "asset",
    "Protocol": "protocol", "protocol_name": "protocol", "proto": "protocol",
    "Source IP": "src_ip", "source_ip": "src_ip", "src": "src_ip",
    "Destination IP": "dst_ip", "destination_ip": "dst_ip", "dst": "dst_ip",
    "Label": "label", "Attack": "label", "attack": "label", "attack_label": "label",
}


def harmonize_columns(df):
    out = df.copy()
    canonical_lower = {str(column).strip().lower(): column for column in out.columns}
    for source, target in DATASET_ALIASES.items():
        if source.lower() in canonical_lower and target not in out.columns:
            out[target] = out[canonical_lower[source.lower()]]
    for field in ("asset", "protocol", "src_ip", "dst_ip"):
        if field not in out.columns:
            out[field] = "unknown"
    return out
