import pandas as pd
from .taxonomy import harmonize_columns


def normalize_labels(df: pd.DataFrame, candidates=('label','Label','Normal/Attack','attack','Attack','Attack State','attack_label')):
    """Normalize heterogeneous dataset labels to the canonical binary ``label``."""
    out = df.copy()
    source = next((c for c in candidates if c in out.columns), None)
    if source is None:
        raise ValueError(
            "No explicit binary ground-truth label column found; refusing to assume all rows are benign"
        )
    vals = out[source]
    if pd.api.types.is_numeric_dtype(vals):
        numeric = pd.to_numeric(vals, errors="coerce")
        if numeric.isna().any():
            raise ValueError(f"Label column '{source}' contains non-numeric values that cannot be normalized")
        if (numeric < 0).any():
            unknown = sorted(float(value) for value in numeric[numeric < 0].unique())
            raise ValueError(
                f"Label column '{source}' contains negative/unknown sentinel values: {unknown[:8]}; "
                "resolve dataset-specific unknown labels before binary normalization"
            )
        out['label'] = (numeric > 0).astype(int)
        return out
    text = vals.astype(str).str.strip().str.lower()
    benign = {'normal', 'benign', '0', '0.0', 'false', 'no'}
    attack = {'attack', 'anomaly', 'malicious', '1', '1.0', 'true', 'yes'}
    unknown = sorted(set(text) - benign - attack)
    if unknown:
        preview = ", ".join(repr(value) for value in unknown[:8])
        raise ValueError(
            f"Label column '{source}' contains unknown/non-binary values: {preview}"
        )
    out['label'] = text.isin(attack).astype(int)
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
    # SWaT exports may use Attack State with boolean or numeric attack states.
    return _adapt(df, ('Timestamp',), ('label','Label','Normal/Attack','attack','Attack','Attack State'), 'SWaT', 'industrial')


def adapt_batadal(df):
    return _adapt(df, ('DATETIME',), ('label','Label','attack','Attack','attack_label'), 'BATADAL', 'water-process')


def adapt_toniot(df):
    out = _adapt(df, ('ts',), ('label','Label','attack','Attack','attack_label'), 'TON-IoT', 'iiot')
    if {'date', 'time'}.issubset(out.columns):
        out['timestamp'] = pd.to_datetime(
            out['date'].astype(str).str.strip() + ' ' + out['time'].astype(str).str.strip(),
            format='%d-%b-%y %H:%M:%S',
            errors='coerce',
        )
    elif 'timestamp' not in out.columns:
        out['timestamp'] = pd.date_range(start='1970-01-01', periods=len(out), freq='s')
        out.attrs['timestamp_semantics'] = 'synthetic_event_order'
    return out


def adapt_dataset(df, dataset: str):
    key = dataset.strip().lower().replace('_', '-').replace(' ', '-')
    if key == 'swat': return adapt_swat(df)
    if key in {'batadal', 'batadal-water'}: return adapt_batadal(df)
    if key in {'ton-iot', 'toniot', 'toniot-iot'}: return adapt_toniot(df)
    raise ValueError(f'Unsupported V2 dataset: {dataset}')
