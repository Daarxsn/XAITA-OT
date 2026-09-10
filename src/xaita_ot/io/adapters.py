import pandas as pd


def normalize_labels(df: pd.DataFrame, candidates=('label','Label','Normal/Attack','Normal/Attack','attack','Attack')):
    out=df.copy()
    source=next((c for c in candidates if c in out.columns),None)
    if source is None:
        out['label']=0; return out
    vals=out[source]
    if pd.api.types.is_numeric_dtype(vals):
        out['label']=(vals.astype(float)>0).astype(int); return out
    text=vals.astype(str).str.strip().str.lower()
    benign={'normal','benign','0','false','no','nan'}
    out['label']=(~text.isin(benign)).astype(int)
    return out


def adapt_swat(df):
    out=df.copy(); out.columns=[str(c).strip() for c in out.columns]
    if 'Timestamp' in out: out['timestamp']=out['Timestamp']
    out=normalize_labels(out)
    if 'asset' not in out: out['asset']='SWaT'
    if 'protocol' not in out: out['protocol']='industrial'
    return out


def adapt_batadal(df):
    out=df.copy(); out.columns=[str(c).strip() for c in out.columns]
    if 'DATETIME' in out: out['timestamp']=out['DATETIME']
    out=normalize_labels(out,('label','Label','attack','Attack','attack_label'))
    if 'asset' not in out: out['asset']='BATADAL'
    if 'protocol' not in out: out['protocol']='water-process'
    return out


def adapt_toniot(df):
    out=df.copy(); out.columns=[str(c).strip() for c in out.columns]
    if 'ts' in out: out['timestamp']=out['ts']
    out=normalize_labels(out,('label','Label','attack','Attack','type'))
    if 'asset' not in out: out['asset']='TON-IoT'
    if 'protocol' not in out: out['protocol']='iiot'
    return out
