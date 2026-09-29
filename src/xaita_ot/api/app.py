from datetime import datetime
import hmac
import json
import logging
import os
from pathlib import Path
import threading
import time
from uuid import uuid4

from fastapi import FastAPI, Header, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.middleware.httpsredirect import HTTPSRedirectMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel, ConfigDict, Field

from .. import __version__
from ..config import load_config
from ..core.schemas import DetectionEvent
from ..pipeline.engine import XAITAEngine
from ..pipeline.experiments import attribution_configurations, run_detection

VERSION = __version__
_PROJECT_ROOT = Path(__file__).resolve().parents[3]
_CONFIGURED_ROOT = os.environ.get("XAITA_OT_ROOT")
ROOT = Path(_CONFIGURED_ROOT) if _CONFIGURED_ROOT else _PROJECT_ROOT
_DEFAULT_ROOT = ROOT
MAX_EVENTS = int(os.environ.get("XAITA_MAX_EVENTS", "5000"))
MAX_REQUEST_BYTES = max(1024, int(os.environ.get("XAITA_MAX_REQUEST_BYTES", str(8 * 1024 * 1024))))
API_KEY = os.environ.get("XAITA_API_KEY")
API_KEY_ROLE = os.environ.get("XAITA_API_KEY_ROLE", "admin").strip().lower()
ENVIRONMENT = os.environ.get("XAITA_ENV", "development").strip().lower()
REQUIRE_AUTH = ENVIRONMENT in {"staging", "production"} or os.environ.get("XAITA_REQUIRE_AUTH", "false").lower() == "true"
RATE_LIMIT_PER_MINUTE = max(1, int(os.environ.get("XAITA_RATE_LIMIT_PER_MINUTE", "30")))
RATE_LIMIT_WINDOW_SECONDS = 60
ENABLE_DOCS = os.environ.get("XAITA_ENABLE_DOCS", "true").lower() == "true"
FORCE_HTTPS = os.environ.get("XAITA_FORCE_HTTPS", "false").lower() == "true"
ALLOWED_HOSTS = [h.strip() for h in os.environ.get("XAITA_ALLOWED_HOSTS", "127.0.0.1,localhost").split(",") if h.strip()]
CORS_ORIGINS = [o.strip() for o in os.environ.get("XAITA_CORS_ORIGINS", "").split(",") if o.strip()]
SUPPORTED_DETECTORS = ("random_forest", "cnn", "lstm", "cnn_lstm")
SUPPORTED_DATASETS = ("SWaT", "BATADAL", "TON-IoT")

logger = logging.getLogger("xaita_ot.api")
logging.basicConfig(level=os.environ.get("LOG_LEVEL", "INFO").upper(), format="%(message)s")
_rate_lock = threading.Lock()
_rate_buckets: dict[str, list[float]] = {}


def _dataset_path(env_name: str, default_relative: str) -> str | None:
    configured = os.environ.get(env_name)
    if configured:
        return configured
    candidates = [ROOT / default_relative, Path("/app") / default_relative]
    for candidate in candidates:
        if candidate.exists():
            return str(candidate)
    return str(candidates[0])


def _dataset_status(path: str | None) -> dict:
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
            sample = sorted(csvs)[0].name if csvs else None
    return {"configured": bool(path), "exists": exists, "ready": exists and csv_count > 0, "csv_count": csv_count, "sample_file": sample, "path": path}


def _experiment_detector_name(name: str) -> str:
    aliases = {"rf": "random_forest", "random forest": "random_forest", "random_forest": "random_forest", "cnn": "cnn", "lstm": "lstm", "cnn-lstm": "cnn_lstm", "cnn_lstm": "cnn_lstm"}
    return aliases.get(name.strip().lower(), name.strip())


def _find_dataset_csv(path: str | Path, dataset: str) -> Path:
    root = Path(path)
    if root.is_file():
        return root
    if not root.is_dir():
        raise HTTPException(status_code=409, detail=f"{dataset} dataset path is configured but unavailable")
    patterns = {"TON-IoT": ["**/train_test_network.csv", "**/Train_Test_IoT_*.csv", "**/*.csv"], "SWaT": ["**/*.csv", "**/*.CSV"], "BATADAL": ["**/*.csv", "**/*.CSV"]}.get(dataset, ["**/*.csv"])
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


DATASET_PATHS = {"SWaT": _dataset_path("XAITA_SWAT_PATH", "data/raw/swat"), "BATADAL": _dataset_path("XAITA_BATADAL_PATH", "data/raw/batadal"), "TON-IoT": _dataset_path("XAITA_TONIOT_PATH", "data/raw/ton_iot")}

app = FastAPI(title="XAITA-OT API", version=VERSION, description="Evidence-continuous OT/ICS security analytics API", docs_url="/docs" if ENABLE_DOCS else None, redoc_url="/redoc" if ENABLE_DOCS else None, openapi_url="/openapi.json" if ENABLE_DOCS else None)
if ALLOWED_HOSTS:
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=ALLOWED_HOSTS)
if FORCE_HTTPS:
    app.add_middleware(HTTPSRedirectMiddleware)
if CORS_ORIGINS:
    app.add_middleware(CORSMiddleware, allow_origins=CORS_ORIGINS, allow_credentials=False, allow_methods=["GET", "POST"], allow_headers=["Authorization", "Content-Type", "X-XAITA-API-Key", "xaita-api-key", "X-Request-ID"])
app.add_middleware(GZipMiddleware, minimum_size=1000)
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


def _configured_api_keys() -> dict[str, str]:
    keys: dict[str, str] = {}
    raw = os.environ.get("XAITA_API_KEYS_JSON", "").strip()
    if raw:
        try:
            value = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise RuntimeError("XAITA_API_KEYS_JSON must contain valid JSON") from exc
        if not isinstance(value, dict):
            raise RuntimeError("XAITA_API_KEYS_JSON must be a JSON object of role to key")
        for role, secret in value.items():
            role_key = str(role).strip().lower()
            if role_key not in {"viewer", "analyst", "admin"} or not isinstance(secret, str) or not secret:
                raise RuntimeError("XAITA_API_KEYS_JSON roles must be viewer, analyst or admin with non-empty secrets")
            keys[role_key] = secret
    if API_KEY:
        keys[API_KEY_ROLE if API_KEY_ROLE in {"viewer", "analyst", "admin"} else "admin"] = API_KEY
    return keys


def _auth_ready() -> bool:
    return bool(_configured_api_keys())


def _role_allows(actual: str, required: str) -> bool:
    rank = {"viewer": 1, "analyst": 2, "admin": 3}
    return rank.get(actual, 0) >= rank.get(required, 99)


def _check_api_key(header_key: str | None, authorization: str | None = None, legacy_key: str | None = None, required_role: str = "viewer") -> str:
    keys = _configured_api_keys()
    auth_required = REQUIRE_AUTH or bool(keys)
    if not auth_required:
        return "anonymous"
    if not keys:
        raise HTTPException(status_code=503, detail="API authentication is required but not configured")
    candidate = header_key or legacy_key
    if not candidate and authorization:
        scheme, _, token = authorization.partition(" ")
        if scheme.lower() == "bearer" and token:
            candidate = token.strip()
    if not candidate:
        raise HTTPException(status_code=401, detail="API authentication required")
    matched_role = next((role for role, secret in keys.items() if hmac.compare_digest(candidate, secret)), None)
    if matched_role is None:
        raise HTTPException(status_code=403, detail="Invalid API credentials")
    if not _role_allows(matched_role, required_role):
        raise HTTPException(status_code=403, detail=f"Role '{matched_role}' is not authorized for this operation")
    return matched_role


def _enforce_rate_limit(request: Request, role: str, scope: str) -> None:
    identity = request.client.host if request.client else "unknown"
    key = f"{identity}:{role}:{scope}"
    now = time.monotonic()
    cutoff = now - RATE_LIMIT_WINDOW_SECONDS
    with _rate_lock:
        bucket = [stamp for stamp in _rate_buckets.get(key, []) if stamp > cutoff]
        if len(bucket) >= RATE_LIMIT_PER_MINUTE:
            retry_after = max(1, int(RATE_LIMIT_WINDOW_SECONDS - (now - bucket[0])))
            _rate_buckets[key] = bucket
            raise HTTPException(status_code=429, detail="Rate limit exceeded for this operation", headers={"Retry-After": str(retry_after)})
        bucket.append(now)
        _rate_buckets[key] = bucket
        if len(_rate_buckets) > 2000:
            stale = [k for k, values in _rate_buckets.items() if not values or values[-1] <= cutoff]
            for stale_key in stale[:1000]:
                _rate_buckets.pop(stale_key, None)
        if len(_rate_buckets) > 2000:
            oldest = sorted(_rate_buckets, key=lambda item: _rate_buckets[item][-1] if _rate_buckets[item] else 0)
            for stale_key in oldest[: max(1, len(_rate_buckets) - 2000)]:
                _rate_buckets.pop(stale_key, None)


@app.middleware("http")
async def security_headers(request: Request, call_next):
    request_id = request.headers.get("X-Request-ID", "").strip()[:128] or uuid4().hex
    started = time.perf_counter()
    content_length = request.headers.get("content-length")
    if content_length:
        try:
            declared_length = int(content_length)
        except ValueError:
            declared_length = -1
        if declared_length < 0 or declared_length > MAX_REQUEST_BYTES:
            response = JSONResponse(status_code=413, content={"detail": f"Maximum request body is {MAX_REQUEST_BYTES} bytes"})
            response.headers["X-Request-ID"] = request_id
            return response
    try:
        response = await call_next(request)
    except Exception as exc:
        logger.exception(json.dumps({"event": "request_error", "request_id": request_id, "path": request.url.path, "error_type": type(exc).__name__}, separators=(",", ":")))
        response = JSONResponse(status_code=500, content={"detail": "Internal server error", "request_id": request_id})
    duration_ms = round((time.perf_counter() - started) * 1000, 2)
    response.headers["X-Request-ID"] = request_id
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "no-referrer"
    response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
    response.headers["Cache-Control"] = "no-store"
    if FORCE_HTTPS:
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    logger.info(json.dumps({"event": "http_request", "request_id": request_id, "method": request.method, "path": request.url.path, "status": response.status_code, "duration_ms": duration_ms, "client": request.client.host if request.client else None}, separators=(",", ":")))
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


@app.get("/health")
def health():
    return {"status": "ok", "service": "xaita-ot", "version": VERSION}


@app.get("/ready")
def ready():
    dashboard_ready = bool(_dashboard_path())
    datasets = {name: _dataset_status(path) for name, path in DATASET_PATHS.items()}
    datasets_ready = all(item["ready"] for item in datasets.values())
    status = "ready" if dashboard_ready and datasets_ready else "degraded"
    return {"status": status, "dashboard": dashboard_ready, "datasets_ready": datasets_ready, "datasets": {name: item["ready"] for name, item in datasets.items()}, "max_events": MAX_EVENTS, "max_request_bytes": MAX_REQUEST_BYTES}


@app.get("/v2/system")
def system_status(xaita_api_key: str | None = Header(default=None, alias="X-XAITA-API-Key"), authorization: str | None = Header(default=None), legacy_api_key: str | None = Header(default=None, alias="xaita-api-key")):
    role = _check_api_key(xaita_api_key, authorization, legacy_api_key, "viewer")
    datasets = {name: _dataset_status(path) for name, path in DATASET_PATHS.items()}
    return {"schema_version": "XAITA-OT-V5-SYSTEM-1.0", "service": "xaita-ot", "version": VERSION, "environment": ENVIRONMENT, "role": role, "dashboard": bool(_dashboard_path()), "datasets": datasets, "security": {"authentication_required": REQUIRE_AUTH or bool(_configured_api_keys()), "authentication_configured": _auth_ready(), "force_https": FORCE_HTTPS, "allowed_hosts": ALLOWED_HOSTS, "rate_limit_per_minute": RATE_LIMIT_PER_MINUTE, "max_request_bytes": MAX_REQUEST_BYTES, "max_events": MAX_EVENTS}}


@app.get("/v2/capabilities")
def capabilities(xaita_api_key: str | None = Header(default=None, alias="X-XAITA-API-Key"), authorization: str | None = Header(default=None), legacy_api_key: str | None = Header(default=None, alias="xaita-api-key")):
    role = _check_api_key(xaita_api_key, authorization, legacy_api_key, "viewer")
    return {"schema_version": "XAITA-OT-V5-CAPABILITIES-1.0", "role": role, "datasets": list(SUPPORTED_DATASETS), "detectors": [{"id": "random_forest", "label": "Random Forest"}, {"id": "cnn", "label": "CNN"}, {"id": "lstm", "label": "LSTM"}, {"id": "cnn_lstm", "label": "CNN-LSTM"}], "attribution_configurations": attribution_configurations(), "access_roles": ["viewer", "analyst", "admin"], "operations": {"read": ["health", "ready", "system", "datasets", "benchmark", "capabilities"], "execute": ["experiment", "analyze"]}, "safety_boundary": "Analyst-support only; no autonomous PLC/RTU/SCADA control action."}


@app.get("/v2/ops/summary")
def operations_summary(xaita_api_key: str | None = Header(default=None, alias="X-XAITA-API-Key"), authorization: str | None = Header(default=None), legacy_api_key: str | None = Header(default=None, alias="xaita-api-key")):
    role = _check_api_key(xaita_api_key, authorization, legacy_api_key, "viewer")
    datasets = {name: _dataset_status(path) for name, path in DATASET_PATHS.items()}
    ready_count = sum(1 for item in datasets.values() if item["ready"])
    benchmark_path = ROOT / "artifacts" / "toniOT_network_5seed_summary.json"
    dashboard_ready = bool(_dashboard_path())
    auth_configured = _auth_ready()
    return {"schema_version": "XAITA-OT-V5-OPS-1.0", "status": "operational" if dashboard_ready and ready_count == len(datasets) else "degraded", "role": role, "release": {"version": VERSION, "environment": ENVIRONMENT}, "dashboard": {"ready": dashboard_ready}, "datasets": {"ready_count": ready_count, "total": len(datasets), "items": datasets}, "execution": {"detectors": list(SUPPORTED_DETECTORS), "attribution_configurations": attribution_configurations(), "rate_limit_per_minute": RATE_LIMIT_PER_MINUTE}, "security": {"authentication_required": REQUIRE_AUTH or bool(_configured_api_keys()), "authentication_configured": auth_configured, "force_https": FORCE_HTTPS, "allowed_hosts": ALLOWED_HOSTS}, "research": {"benchmark_summary_available": benchmark_path.is_file(), "benchmark_summary_path": str(benchmark_path) if benchmark_path.is_file() else None}, "safety_boundary": "Analyst-support only; no autonomous PLC/RTU/SCADA control action."}


@app.get("/v2/datasets")
def dataset_status(xaita_api_key: str | None = Header(default=None, alias="X-XAITA-API-Key"), authorization: str | None = Header(default=None), legacy_api_key: str | None = Header(default=None, alias="xaita-api-key")):
    _check_api_key(xaita_api_key, authorization, legacy_api_key, "viewer")
    return {"schema_version": "XAITA-OT-V2-DATASET-STATUS-1.1", "datasets": {name: _dataset_status(path) for name, path in DATASET_PATHS.items()}}


@app.get("/v2/benchmark")
def benchmark_summary(xaita_api_key: str | None = Header(default=None, alias="X-XAITA-API-Key"), authorization: str | None = Header(default=None), legacy_api_key: str | None = Header(default=None, alias="xaita-api-key")):
    _check_api_key(xaita_api_key, authorization, legacy_api_key, "viewer")
    path = ROOT / "artifacts" / "toniOT_network_5seed_summary.json"
    if not path.is_file():
        raise HTTPException(status_code=404, detail="Benchmark summary artifact unavailable")
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise HTTPException(status_code=500, detail="Benchmark summary artifact is invalid") from exc


@app.post("/v2/experiment")
def run_v2_experiment(payload: ExperimentIn, request: Request, xaita_api_key: str | None = Header(default=None, alias="X-XAITA-API-Key"), authorization: str | None = Header(default=None), legacy_api_key: str | None = Header(default=None, alias="xaita-api-key")):
    role = _check_api_key(xaita_api_key, authorization, legacy_api_key, "analyst")
    _enforce_rate_limit(request, role, "experiment")
    if payload.dataset not in DATASET_PATHS:
        raise HTTPException(status_code=400, detail="Unsupported dataset")
    detector_key = _experiment_detector_name(payload.detector)
    if detector_key not in SUPPORTED_DETECTORS:
        raise HTTPException(status_code=400, detail=f"Unknown detector '{payload.detector}'. Available: {', '.join(SUPPORTED_DETECTORS)}")
    path = DATASET_PATHS[payload.dataset]
    if not path:
        raise HTTPException(status_code=409, detail=f"{payload.dataset} dataset is not configured on this deployment")
    if not Path(path).exists():
        raise HTTPException(status_code=409, detail=f"{payload.dataset} dataset path is configured but unavailable")
    try:
        csv_path = _find_dataset_csv(path, payload.dataset)
        run = run_detection(csv_path, payload.dataset, load_config(), seed=payload.seed, detector=detector_key)
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=422, detail={"message": f"{payload.dataset} experiment could not be executed", "error_type": type(exc).__name__, "error": str(exc)}) from exc
    return {"schema_version": "XAITA-OT-V2-RUN-1.2", "experiment_id": run.experiment_id, "dataset": run.dataset, "detector": payload.detector, "detector_key": detector_key, "seed": run.seed, "started_at": run.started_at, "duration_seconds": run.duration_seconds, "rows": run.rows, "windows": run.windows, "metrics": run.metrics[detector_key], "all_model_metrics": run.metrics, "dataset_file": str(csv_path)}


@app.get("/")
def dashboard():
    dashboard_path = _dashboard_path()
    if dashboard_path is None:
        raise HTTPException(status_code=503, detail="Dashboard asset unavailable")
    return FileResponse(dashboard_path)


@app.post("/v1/analyze")
def analyze(events: list[EventIn], request: Request, xaita_api_key: str | None = Header(default=None, alias="X-XAITA-API-Key"), authorization: str | None = Header(default=None), legacy_api_key: str | None = Header(default=None, alias="xaita-api-key")):
    role = _check_api_key(xaita_api_key, authorization, legacy_api_key, "analyst")
    _enforce_rate_limit(request, role, "analyze")
    if not events:
        raise HTTPException(status_code=400, detail="At least one event is required")
    if len(events) > MAX_EVENTS:
        raise HTTPException(status_code=413, detail=f"Maximum {MAX_EVENTS} events per request")
    ev = [DetectionEvent(**e.model_dump()) for e in events]
    return {"incidents": engine.analyze_events(ev)}
