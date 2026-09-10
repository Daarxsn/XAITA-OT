from datetime import timedelta
import numpy as np
from .schemas import DetectionEvent, AttackEpisode

def event_relation(a: DetectionEvent, b: DetectionEvent, temporal_window: float) -> float:
    dt=abs((b.timestamp-a.timestamp).total_seconds())
    temporal=max(0.0,1.0-dt/max(temporal_window,1e-9))
    asset=1.0 if a.asset==b.asset else 0.35
    protocol=1.0 if a.protocol==b.protocol else 0.40
    behavior=1.0 if a.label==b.label else 0.55
    return 0.35*temporal+0.25*asset+0.20*protocol+0.20*behavior

def reconstruct(events: list[DetectionEvent], threshold: float=0.55, temporal_window: float=60.0) -> list[AttackEpisode]:
    events=sorted(events,key=lambda e:e.timestamp)
    episodes=[]
    current=[]
    strengths=[]
    for e in events:
        if not current:
            current=[e]; strengths=[]; continue
        s=event_relation(current[-1],e,temporal_window)
        if s>=threshold:
            current.append(e); strengths.append(s)
        else:
            if current:
                episodes.append(_episode(current,strengths,len(episodes)+1))
            current=[e]; strengths=[]
    if current: episodes.append(_episode(current,strengths,len(episodes)+1))
    return episodes

def _episode(events,strengths,idx):
    corr=float(np.mean(strengths)) if strengths else 0.0
    stages=[e.label for e in events]
    return AttackEpisode(f"EP-{idx:05d}",events,corr,stages)
