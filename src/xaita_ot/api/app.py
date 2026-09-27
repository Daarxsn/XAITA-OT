from datetime import datetime
import hmac
import os
import json
from pathlib import Path

from fastapi import FastAPI, Header, HTTPException, Request
from fastapi.responses import FileResponse, HTMLResponse
from pydantic import BaseModel, ConfigDict, Field

from .. import __version__
from ..config import load_config
from ..core.schemas import DetectionEvent
from ..pipeline.engine import XAITAEngine
from ..pipeline.experiments import run_detection

VERSION = __version__
_PROJECT_ROOT = Path(__file__).resolve().parents[3]
_CONFIGURED_ROOT = os.environ.get("XAITA_OT_ROOT")
ROOT = Path(_CONFIGURED_ROOT) if _CONFIGURED_ROOT else _PROJECT_ROOT
_DEFAULT_ROOT = ROOT
MAX_EVENTS = int(os.environ.get("XAITA_MAX_EVENTS", "5000"))
API_KEY = os.environ.get("XAITA_API_KEY")


def _dataset_path(env_name: str, default_relative: str) -> str | None:
    """Resolve an explicit deployment path, then a conventional mounted path."""
    configured = os.environ.get(env_name)
    if configured:
        return configured
    candidates = [ROOT / default_relative, Path("/app") / default_relative]
    for candidate in candidates:
        if candidate.exists():
            return str(candidate)
    return str(candidates[0])


def _dataset_status(path: str | None) -> dict:
    """Return dataset presence without requiring benchmark data in the repo."""
    exists = bool(path and Path(path).exists())
    csv_count = 0
    sample = None
    if exists:
        root = Path(path)
        if root.is_file() and root.suffix.lower() == ".csv":
            csv_count = 1
            sample = root.name
        elif root.is_dir():
            csvs = list(root.rglob("*.csv")) + list(root.rglob("*.CSV"))
            csv_count = len(csvs)
            if csvs:
                sample = sorted(csvs)[0].name
    return {
        "configured": bool(path),
        "exists": exists,
        "ready": exists and csv_count > 0,
        "csv_count": csv_count,
        "sample_file": sample,
        "path": path,
    }


def _experiment_detector_name(name: str) -> str:
    aliases = {
        "rf": "random_forest", "random forest": "random_forest",
        "random_forest": "random_forest", "cnn": "cnn", "lstm": "lstm",
        "cnn-lstm": "cnn_lstm", "cnn_lstm": "cnn_lstm",
    }
    key = name.strip().lower()
    return aliases.get(key, name.strip())


def _find_dataset_csv(path: str | Path, dataset: str) -> Path:
    root = Path(path)
    if root.is_file():
        return root
    if not root.is_dir():
        raise HTTPException(status_code=409, detail=f"{dataset} dataset path is configured but unavailable")
    patterns = {
        "TON-IoT": ["**/train_test_network.csv", "**/Train_Test_IoT_*.csv", "**/*.csv"],
        "SWaT": ["**/*.csv", "**/*.CSV"],
        "BATADAL": ["**/*.csv", "**/*.CSV"],
    }.get(dataset, ["**/*.csv"])
    candidates = []
    for pattern in patterns:
        candidates.extend(p for p in root.glob(pattern) if p.is_file())
        if candidates:
            break
    if not candidates:
        raise HTTPException(status_code=409, detail=f"No CSV benchmark file found under {dataset} dataset path")
    if dataset == "TON-IoT":
        network = [p for p in candidates if p.name.lower() == "train_test_network.csv"]
        if network:
            return network[0]
        iot = [p for p in candidates if "train_test_iot_modbus" in p.name.lower()]
        if iot:
            return iot[0]
    return sorted(candidates)[0]


DATASET_PATHS = {
    "SWaT": _dataset_path("XAITA_SWAT_PATH", "data/raw/swat"),
    "BATADAL": _dataset_path("XAITA_BATADAL_PATH", "data/raw/batadal"),
    "TON-IoT": _dataset_path("XAITA_TONIOT_PATH", "data/raw/ton_iot"),
}

app = FastAPI(title="XAITA-OT API", version=VERSION, description="Evidence-continuous OT/ICS security analytics API")
engine = XAITAEngine(load_config())


def _dashboard_candidates() -> list[Path]:
    if _CONFIGURED_ROOT:
        candidates = [Path(_CONFIGURED_ROOT) / "web" / "index.html"]
    elif ROOT.resolve() != _DEFAULT_ROOT.resolve():
        candidates = [ROOT / "web" / "index.html"]
    else:
        candidates = [Path.cwd() / "web" / "index.html", Path("/app/web/index.html"), ROOT / "web" / "index.html"]
    return list(dict.fromkeys(path.resolve() for path in candidates))


def _dashboard_path() -> Path | None:
    return next((path for path in _dashboard_candidates() if path.is_file()), None)


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


class ExperimentIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    dataset: str = Field(min_length=1, max_length=32)
    detector: str = Field(default="CNN-LSTM", min_length=1, max_length=32)
    seed: int = Field(default=42, ge=0, le=2147483647)


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
    dashboard_path = _dashboard_path()
    return {"status": "ready", "dashboard": bool(dashboard_path and dashboard_path.is_file()), "max_events": MAX_EVENTS}


@app.get("/v2/datasets")
def dataset_status(xaita_api_key: str | None = Header(default=None)):
    _check_api_key(xaita_api_key)
    return {"schema_version": "XAITA-OT-V2-DATASET-STATUS-1.1", "datasets": {name: _dataset_status(path) for name, path in DATASET_PATHS.items()}}


@app.get("/v2/benchmark")
def benchmark_summary(xaita_api_key: str | None = Header(default=None)):
    _check_api_key(xaita_api_key)
    path = ROOT / "artifacts" / "toniOT_network_5seed_summary.json"
    if not path.is_file():
        raise HTTPException(status_code=404, detail="Benchmark summary artifact unavailable")
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise HTTPException(status_code=500, detail="Benchmark summary artifact is invalid") from exc


@app.post("/v2/experiment")
def run_v2_experiment(payload: ExperimentIn, xaita_api_key: str | None = Header(default=None)):
    _check_api_key(xaita_api_key)
    if payload.dataset not in DATASET_PATHS:
        raise HTTPException(status_code=400, detail="Unsupported dataset")
    path = DATASET_PATHS[payload.dataset]
    if not path:
        raise HTTPException(status_code=409, detail=f"{payload.dataset} dataset is not configured on this deployment")
    if not Path(path).exists():
        raise HTTPException(status_code=409, detail=f"{payload.dataset} dataset path is configured but unavailable")
    detector_key = _experiment_detector_name(payload.detector)
    try:
        csv_path = _find_dataset_csv(path, payload.dataset)
        cfg = load_config()
        run = run_detection(csv_path, payload.dataset, cfg, seed=payload.seed)
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=422, detail={"message": f"{payload.dataset} experiment could not be executed", "error_type": type(exc).__name__, "error": str(exc)}) from exc
    if detector_key not in run.metrics:
        raise HTTPException(status_code=400, detail=f"Unknown detector '{payload.detector}'. Available: {', '.join(sorted(run.metrics))}")
    return {
        "schema_version": "XAITA-OT-V2-RUN-1.1", "experiment_id": run.experiment_id,
        "dataset": run.dataset, "detector": payload.detector, "detector_key": detector_key,
        "seed": run.seed, "started_at": run.started_at, "duration_seconds": run.duration_seconds,
        "rows": run.rows, "windows": run.windows, "metrics": run.metrics[detector_key],
        "all_model_metrics": run.metrics, "dataset_file": str(csv_path),
    }


_DASHBOARD_ENHANCEMENT = r"""
<script>
(() => {
  const DATASETS = ['SWaT', 'BATADAL', 'TON-IoT'];
  const meta = {
    'SWaT': {domain:'Water treatment / ICS', role:'Industrial control telemetry'},
    'BATADAL': {domain:'Water distribution / ICS', role:'Cyber-physical anomaly validation'},
    'TON-IoT': {domain:'IIoT / Industry 4.0', role:'Network + telemetry benchmark'}
  };
  const esc = s => String(s ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const ensureStyle = () => {
    if (document.getElementById('xaita-dataset-style')) return;
    const s = document.createElement('style'); s.id='xaita-dataset-style';
    s.textContent = `
      .xaita-datasets{margin:12px 0;display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:10px}
      .xaita-dataset{position:relative;padding:14px;border:1px solid #21344a;border-radius:12px;background:linear-gradient(145deg,#0b131e,#0e1927);transition:.18s}
      .xaita-dataset:hover{transform:translateY(-1px);border-color:#36516e}
      .xaita-dataset .xd-top{display:flex;justify-content:space-between;gap:8px;align-items:center}.xaita-dataset h3{margin:0;font-size:13px}
      .xd-status{font-size:8px;font-weight:900;letter-spacing:.06em;border-radius:999px;padding:4px 7px;border:1px solid #21344a;color:#8498b0}
      .xd-status.ready{color:#4ed6a1;border-color:#24533f;background:#0a1715}.xd-status.off{color:#efc76b;border-color:#58451f;background:#18150c}
      .xd-meta{margin-top:8px;color:#8498b0;font-size:9px}.xd-path{margin-top:6px;color:#5e7188;font:8px ui-monospace,monospace;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
      .xd-action{margin-top:10px;width:100%;border:1px solid #21344a;background:#08121e;color:#e9f1fa;border-radius:7px;padding:7px;cursor:pointer;font-size:9px;font-weight:800}.xd-action:hover{border-color:#58d7ff}
      .xaita-lab-control{margin:10px 0 14px;padding:13px;border:1px solid #2d5076;border-radius:11px;background:linear-gradient(135deg,#0d1d30,#101d2c)}
      .xaita-lab-control .xl-head{display:flex;justify-content:space-between;gap:10px;align-items:center}.xl-title{font-size:12px;font-weight:900}.xl-note{font-size:8px;color:#8498b0}.xl-row{display:grid;grid-template-columns:1fr 1fr 1fr auto;gap:8px;margin-top:10px}.xl-field label{display:block;color:#8498b0;font-size:8px;margin-bottom:4px}.xl-field select{width:100%;background:#08121e;color:#e9f1fa;border:1px solid #21344a;border-radius:7px;padding:8px;font-size:9px}
      @media(max-width:900px){.xaita-datasets{grid-template-columns:1fr}.xl-row{grid-template-columns:1fr 1fr}.xl-run{grid-column:1/-1}}
    `; document.head.appendChild(s);
  };
  const fetchStatus = async () => {
    try { const r=await fetch('/v2/datasets',{cache:'no-store'}); if(!r.ok) throw new Error(); return await r.json(); }
    catch(e){ return null; }
  };
  const updateNativeSelector = (status) => {
    const select = document.getElementById('expDataset');
    if(!select) return;
    const current=select.value;
    select.innerHTML='';
    DATASETS.forEach(name=>{ const o=document.createElement('option'); o.value=name; o.textContent=name; const d=status?.datasets?.[name]; o.disabled=!!d&&!d.exists; select.appendChild(o); });
    if([...select.options].some(o=>o.value===current&&!o.disabled)) select.value=current;
    else { const first=[...select.options].find(o=>!o.disabled); if(first) select.value=first.value; }
  };
  const renderConsole = (status) => {
    ensureStyle();
    const research=document.getElementById('research'); if(!research) return;
    let host=document.getElementById('xaitaResearchConsole');
    if(!host){ host=document.createElement('div'); host.id='xaitaResearchConsole'; const anchor=research.querySelector('.research-banner')||research.firstElementChild; if(anchor) anchor.insertAdjacentElement('afterend',host); else research.prepend(host); }
    const datasets=status?.datasets||{};
    host.innerHTML=`<div class="card-head"><div><div class="card-title">Dataset readiness</div><div class="card-sub">Live deployment state · selectable datasets are resolved from the API</div></div><span class="badge blue">3 DATA SOURCES</span></div><div class="xaita-datasets">${DATASETS.map(name=>{const d=datasets[name]||{};const ready=!!d.ready;return `<div class="xaita-dataset"><div class="xd-top"><h3>${esc(name)}</h3><span class="xd-status ${ready?'ready':'off'}">${ready?'READY':'UNAVAILABLE'}</span></div><div class="xd-meta">${esc(meta[name].domain)} · ${esc(meta[name].role)}</div><div class="xd-meta">${d.csv_count??0} CSV file${d.csv_count===1?'':'s'}${d.sample_file?' · '+esc(d.sample_file):''}</div><div class="xd-path" title="${esc(d.path)}">${esc(d.path||'Not configured')}</div><button class="xd-action" ${ready?'':'disabled'} onclick="window.xaitaSelectDataset('${name}')">Use ${esc(name)} in Research Lab</button></div>`}).join('')}</div>`;
  };
  window.xaitaSelectDataset = name => { const s=document.getElementById('expDataset'); if(s){s.value=name;s.dispatchEvent(new Event('change',{bubbles:true}));} const r=document.getElementById('research'); if(r) r.scrollIntoView({behavior:'smooth',block:'start'}); };
  const boot=async()=>{ const status=await fetchStatus(); updateNativeSelector(status); renderConsole(status); };
  if(document.readyState==='loading') document.addEventListener('DOMContentLoaded',boot,{once:true}); else boot();
  window.addEventListener('focus',boot);
})();
</script>
"""


@app.get("/")
def dashboard():
    dashboard_path = _dashboard_path()
    if dashboard_path is None:
        raise HTTPException(status_code=503, detail="Dashboard asset unavailable")
    html = dashboard_path.read_text(encoding="utf-8")
    if "xaitaResearchConsole" not in html:
        html = html.replace("</body>", _DASHBOARD_ENHANCEMENT + "</body>")
    return HTMLResponse(content=html)


@app.post("/v1/analyze")
def analyze(events: list[EventIn], xaita_api_key: str | None = Header(default=None)):
    _check_api_key(xaita_api_key)
    if not events:
        raise HTTPException(status_code=400, detail="At least one event is required")
    if len(events) > MAX_EVENTS:
        raise HTTPException(status_code=413, detail=f"Maximum {MAX_EVENTS} events per request")
    ev = [DetectionEvent(**e.model_dump()) for e in events]
    return {"incidents": engine.analyze_events(ev)}
