import pandas as pd
from .taxonomy import harmonize_columns


def normalize_labels(df: pd.DataFrame, candidates=('label','Label','Normal/Attack','attack','Attack','attack_label','type')):
    out = df.copy()
    source = next((c for c in candidates if c in out.columns), None)
    if source is None:
        out['label'] = 0
        return out
    vals = out[source]
    if pd.api.types.is_numeric_dtype(vals):
        out['label'] = (vals.astype(float) > 0).astype(int)
        return out
    text = vals.astype(str).str.strip().str.lower()
    benign = {'normal', 'benign', '0', 'false', 'no', 'nan'}
    out['label'] = (~text.isin(benign)).astype(int)
    return out


def _adapt(df, timestamp_aliases, label_candidates, asset, protocol):
    out = harmonize_columns(df)
    out.columns = [str(c).strip() for c in out.columns]
    for alias in timestamp_aliases:
        if alias in out.columns and 'timestamp' not in out.columns:
            out['timestamp'] = out[alias]
            break
    out = normalize_labels(out, label_candidates)
    if 'asset' not in out or out['asset'].isna().all(): out['asset'] = asset
    if 'protocol' not in out or out['protocol'].isna().all(): out['protocol'] = protocol
    return out


def adapt_swat(df):
    return _adapt(df, ('Timestamp',), ('label','Label','Normal/Attack','attack','Attack'), 'SWaT', 'industrial')


def adapt_batadal(df):
    return _adapt(df, ('DATETIME',), ('label','Label','attack','Attack','attack_label'), 'BATADAL', 'water-process')


def adapt_toniot(df):
    return _adapt(df, ('ts',), ('label','Label','attack','Attack','type'), 'TON-IoT', 'iiot')


def adapt_dataset(df, dataset: str):
    key = dataset.strip().lower().replace('_', '-').replace(' ', '-')
    if key == 'swat': return adapt_swat(df)
    if key in {'batadal', 'batadal-water'}: return adapt_batadal(df)
    if key in {'ton-iot', 'toniot', 'toniot-iot'}: return adapt_toniot(df)
    raise ValueError(f'Unsupported V2 dataset: {dataset}')
