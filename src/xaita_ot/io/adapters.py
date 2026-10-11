import pandas as pd
from .taxonomy import harmonize_columns


def normalize_labels(df: pd.DataFrame, candidates=('label','Label','Normal/Attack','attack','Attack','Attack State','attack_label','type')):
    """Normalize heterogeneous dataset labels to the canonical binary ``label``."""
    out = df.copy()
    source = next((c for c in candidates if c in out.columns), None)
    if source is None:
        raise ValueError(
            "Missing required attack-label column; refusing to manufacture an all-benign label vector"
        )
    vals = out[source]
    unknown = {'', 'nan', 'none', 'null', 'unknown', 'unlabeled', 'unlabelled', 'n/a', 'na', 'not available', 'not_available', '-999', '-999.0'}
    if pd.api.types.is_numeric_dtype(vals):
        numeric = pd.to_numeric(vals, errors="coerce")
        invalid = numeric.isna() | (numeric < 0)
        if invalid.any():
            raise ValueError(
                f"Label column '{source}' contains {int(invalid.sum())} missing/unknown label values"
            )
        out['label'] = (numeric > 0).astype(int)
        return out
    text = vals.astype(str).str.strip().str.lower()
    numeric_text = pd.to_numeric(text, errors="coerce")
    invalid = text.isin(unknown) | (numeric_text.notna() & (numeric_text < 0))
    if invalid.any():
        raise ValueError(
            f"Label column '{source}' contains {int(invalid.sum())} missing/unknown label values"
        )
    benign = {'normal', 'benign', '0', '0.0', 'false', 'no'}
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
    # SWaT exports may use Attack State with boolean or numeric attack states.
    return _adapt(df, ('Timestamp',), ('label','Label','Normal/Attack','attack','Attack','Attack State'), 'SWaT', 'industrial')


def adapt_batadal(df):
    return _adapt(df, ('DATETIME',), ('label','Label','attack','Attack','attack_label'), 'BATADAL', 'water-process')


def adapt_toniot(df):
    out = _adapt(df, ('ts',), ('label','Label','attack','Attack','type'), 'TON-IoT', 'iiot')
    if {'date', 'time'}.issubset(out.columns):
        # TON-IoT distributions use more than one date spelling. Parse the
        # combined source fields with day-first semantics instead of forcing a
        # single format that can silently turn every timestamp into NaT.
        combined = (
            out['date'].astype(str).str.strip()
            + ' '
            + out['time'].astype(str).str.strip()
        )
        out['timestamp'] = pd.to_datetime(
            combined, errors='coerce', dayfirst=True, utc=True
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
