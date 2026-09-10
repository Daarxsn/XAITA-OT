from datetime import datetime, timedelta, timezone
import numpy as np, pandas as pd
from pathlib import Path

def make_demo_csv(path, n=3000, seed=42):
    rng=np.random.default_rng(seed); t=pd.date_range('2026-01-01',periods=n,freq='s',tz='UTC')
    data={f'f{i}':rng.normal(0,1,n) for i in range(16)}
    labels=np.zeros(n,dtype=int)
    for start in [500,1200,2100]:
        labels[start:start+80]=1
        for i in range(16): data[f'f{i}'][start:start+80]+=rng.normal(2.0,0.4)
    df=pd.DataFrame(data); df.insert(0,'timestamp',t); df['label']=labels
    df['asset']=np.where(labels,'PLC-02','PLC-01'); df['protocol']=np.where(labels,'modbus','modbus')
    Path(path).parent.mkdir(parents=True,exist_ok=True); df.to_csv(path,index=False); return path

def demo_events(n=12):
    from ..core.schemas import DetectionEvent
    now=datetime.now(timezone.utc)
    labels=['reconnaissance','protocol','unauthorized_command','process_deviation']
    return [DetectionEvent(f'e{i+1}',now+timedelta(seconds=i*12),'PLC-02','modbus',labels[i%4],0.88+0.01*(i%5),{'f0':1+i*0.1,'f1':0.5}) for i in range(n)]
