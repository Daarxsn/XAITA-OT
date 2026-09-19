from datetime import datetime
import hmac
import os
import json
from pathlib import Path

from fastapi import FastAPI, Header, HTTPException, Request
from fastapi.responses import FileResponse
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
    candidates = [
        ROOT / default_relative,
        Path("/app") / default_relative,
    ]
    for candidate in candidates:
        if candidate.exists():
            return str(candidate)
    # Keep the conventional path visible in status responses so a mounted
    # deployment can become ready without changing application code.
    return str(candidates[0])


def _dataset_status(path: str | None) -> dict:
    """Return dataset presence without requiring benchmark data in the repo."""
    return {
        "configured": bool(path),
        "exists": bool(path and Path(path).exists()),
        "path": path,
    }


def _experiment_detector_name(name: str) -> str:
    """Normalize UI/API detector labels to the internal metric keys."""
    aliases = {
        "rf": "random_forest",
        "random forest": "random_forest",
        "random_forest": "random_forest",
        "cnn": "cnn",
        "lstm": "lstm",
        "cnn-lstm": "cnn_lstm",
        "cnn_lstm": "cnn_lstm",
    }
    key = name.strip().lower()
    return aliases.get(key, name.strip())


def _find_dataset_csv(path: str | Path, dataset: str) -> Path:
    """Resolve a benchmark CSV from either a direct file or a dataset directory."""
    root = Path(path)
    if root.is_file():
        return root
    if not root.is_dir():
        raise HTTPException(status_code=409, detail=f"{dataset} dataset path is configured but unavailable")

    patterns = {
        "TON-IoT": [
            "**/train_test_network.csv",
            "**/Train_Test_IoT_*.csv",
            "**/*.csv",
        ],
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
    """Return dashboard locations using explicit overrides before safe fallbacks."""
    if _CONFIGURED_ROOT:
        candidates = [Path(_CONFIGURED_ROOT) / "web" / "index.html"]
    elif ROOT.resolve() != _DEFAULT_ROOT.resolve():
        candidates = [ROOT / "web" / "index.html"]
    else:
        candidates = [
            Path.cwd() / "web" / "index.html",
            Path("/app/web/index.html"),
            ROOT / "web" / "index.html",
        ]
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
    return {
        "schema_version": "XAITA-OT-V2-DATASET-STATUS-1.1",
        "datasets": {
            name: _dataset_status(path)
            for name, path in DATASET_PATHS.items()
        },
    }


@app.get("/v2/benchmark")
def benchmark_summary(xaita_api_key: str | None = Header(default=None)):
    """Return committed, reproducible benchmark summaries for dashboard display."""
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
        raise HTTPException(
            status_code=422,
            detail={
                "message": f"{payload.dataset} experiment could not be executed",
                "error_type": type(exc).__name__,
                "error": str(exc),
            },
        ) from exc

    if detector_key not in run.metrics:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown detector '{payload.detector}'. Available: {', '.join(sorted(run.metrics))}",
        )

    return {
        "schema_version": "XAITA-OT-V2-RUN-1.1",
        "experiment_id": run.experiment_id,
        "dataset": run.dataset,
        "detector": payload.detector,
        "detector_key": detector_key,
        "seed": run.seed,
        "started_at": run.started_at,
        "duration_seconds": run.duration_seconds,
        "rows": run.rows,
        "windows": run.windows,
        "metrics": run.metrics[detector_key],
        "all_model_metrics": run.metrics,
        "dataset_file": str(csv_path),
    }


@app.get("/")
def dashboard():
    dashboard_path = _dashboard_path()
    if dashboard_path is None:
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
