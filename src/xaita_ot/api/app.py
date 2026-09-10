from pathlib import Path
from fastapi import FastAPI
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from datetime import datetime
from ..config import load_config
from ..core.schemas import DetectionEvent
from ..pipeline.engine import XAITAEngine

ROOT=Path(__file__).resolve().parents[3]
app=FastAPI(title='XAITA-OT API',version='0.3.0',description='Evidence-continuous OT/ICS security analytics API')
engine=XAITAEngine(load_config())

class EventIn(BaseModel):
    event_id: str
    timestamp: datetime
    asset: str='unknown'
    protocol: str='unknown'
    label: str='unknown'
    detection_confidence: float=Field(ge=0,le=1)
    features: dict[str,float]={}

@app.get('/health')
def health(): return {'status':'ok','service':'xaita-ot','version':'0.3.0'}

@app.get('/')
def dashboard(): return FileResponse(ROOT/'web'/'index.html')

@app.post('/v1/analyze')
def analyze(events:list[EventIn]):
    ev=[DetectionEvent(**e.model_dump()) for e in events]
    return {'incidents':engine.analyze_events(ev)}
