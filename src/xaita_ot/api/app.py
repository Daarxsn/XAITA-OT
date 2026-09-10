from datetime import datetime
import hmac
import os
from pathlib import Path

from fastapi import FastAPI, Header, HTTPException, Request
from fastapi.responses import FileResponse
from pydantic import BaseModel, ConfigDict, Field

from ..config import load_config
from ..core.schemas import DetectionEvent
from ..pipeline.engine import XAITAEngine

VERSION = "0.4.0"
ROOT = Path(os.environ.get("XAITA_OT_ROOT", Path.cwd()))
MAX_EVENTS = int(os.environ.get("XAITA_MAX_EVENTS", "5000"))
API_KEY = os.environ.get("XAITA_API_KEY")

app = FastAPI(
    title="XAITA-OT API",
    version=VERSION,
    description="Evidence-continuous OT/ICS security analytics API",
)
engine = XAITAEngine(load_config())


@app.middleware("http")
async def security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "no-referrer"
    response.headers["Cache-Control"] = "no-store"
    return response


class EventIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    event_id: str = Field(min_length=1, max_length=128)
    timestamp: datetime
    asset: str = Field(default="unknown", min_length=1, max_length=128)
    protocol: str = Field(default="unknown", min_length=1, max_length=64)
    source: str = Field(default="unknown", min_length=1, max_length=128)
    destination: str = Field(default="unknown", min_length=1, max_length=128)
    label: str = Field(default="unknown", min_length=1, max_length=128)
    detection_confidence: float = Field(ge=0, le=1)
    features: dict[str, float] = Field(default_factory=dict)


def _check_api_key(header_key: str | None) -> None:
    if API_KEY and not header_key:
        raise HTTPException(status_code=401, detail="API key required")
    if API_KEY and not hmac.compare_digest(header_key or "", API_KEY):
        raise HTTPException(status_code=403, detail="Invalid API key")


@app.get("/health")
def health():
    return {"status": "ok", "service": "xaita-ot", "version": VERSION}


@app.get("/ready")
def ready():
    dashboard_path = ROOT / "web" / "index.html"
    return {"status": "ready", "dashboard": dashboard_path.exists(), "max_events": MAX_EVENTS}


@app.get("/")
def dashboard():
    dashboard_path = ROOT / "web" / "index.html"
    if not dashboard_path.exists():
        raise HTTPException(status_code=503, detail="Dashboard asset unavailable")
    return FileResponse(dashboard_path)


@app.post("/v1/analyze")
def analyze(events: list[EventIn], xaita_api_key: str | None = Header(default=None)):
    _check_api_key(xaita_api_key)
    if not events:
        raise HTTPException(status_code=400, detail="At least one event is required")
    if len(events) > MAX_EVENTS:
        raise HTTPException(status_code=413, detail=f"Maximum {MAX_EVENTS} events per request")
    ev = [DetectionEvent(**e.model_dump()) for e in events]
    return {"incidents": engine.analyze_events(ev)}
