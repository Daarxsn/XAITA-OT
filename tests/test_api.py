from datetime import datetime, timezone

from fastapi.testclient import TestClient

from xaita_ot.api import app as api


client = TestClient(api.app, base_url="http://localhost")


def event_payload(event_id="evt-1"):
    return {
        "event_id": event_id,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "asset": "plc-01",
        "protocol": "modbus",
        "source": "10.0.0.1",
        "destination": "10.0.0.2",
        "label": "normal",
        "detection_confidence": 0.8,
        "features": {"flow_rate": 1.0},
    }


def test_health_and_security_headers():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["service"] == "xaita-ot"
    assert response.json()["version"] == api.VERSION
    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert response.headers["X-Frame-Options"] == "DENY"
    assert response.headers["Referrer-Policy"] == "no-referrer"
    assert response.headers["Permissions-Policy"] == "camera=(), microphone=(), geolocation=()"
    assert response.headers["Cache-Control"] == "no-store"
    assert response.headers.get("X-Request-ID")


def test_ready_reports_dashboard(tmp_path, monkeypatch):
    (tmp_path / "web").mkdir()
    (tmp_path / "web" / "index.html").write_text("<html></html>", encoding="utf-8")
    for name in ("swat", "batadal", "ton_iot"):
        (tmp_path / "data" / "raw" / name).mkdir(parents=True)
        (tmp_path / "data" / "raw" / name / "sample.csv").write_text("timestamp,label\n2026-01-01,0\n", encoding="utf-8")
    monkeypatch.setattr(api, "ROOT", tmp_path)
    monkeypatch.setattr(api, "DATASET_PATHS", {
        "SWaT": str(tmp_path / "data" / "raw" / "swat"),
        "BATADAL": str(tmp_path / "data" / "raw" / "batadal"),
        "TON-IoT": str(tmp_path / "data" / "raw" / "ton_iot"),
    })
    response = client.get("/ready")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ready"
    assert body["dashboard"] is True
    assert body["datasets_ready"] is True
    assert body["datasets"] == {"SWaT": True, "BATADAL": True, "TON-IoT": True}
    assert body["max_events"] == api.MAX_EVENTS


def test_dashboard_serves_index(tmp_path, monkeypatch):
    (tmp_path / "web").mkdir()
    index = tmp_path / "web" / "index.html"
    index.write_text("dashboard", encoding="utf-8")
    monkeypatch.setattr(api, "ROOT", tmp_path)
    response = client.get("/")
    assert response.status_code == 200
    assert response.text == "dashboard"


def test_dashboard_returns_503_when_missing(tmp_path, monkeypatch):
    monkeypatch.setattr(api, "ROOT", tmp_path)
    response = client.get("/")
    assert response.status_code == 503
    assert response.json()["detail"] == "Dashboard asset unavailable"


def test_analyze_rejects_empty_request():
    response = client.post("/v1/analyze", json=[])
    assert response.status_code == 400
    assert response.json()["detail"] == "At least one event is required"


def test_analyze_returns_engine_result(monkeypatch):
    expected = [{"event_id": "evt-1", "severity": "low"}]

    def fake_analyze(events):
        assert len(events) == 1
        assert events[0].event_id == "evt-1"
        return expected

    monkeypatch.setattr(api.engine, "analyze_events", fake_analyze)
    response = client.post("/v1/analyze", json=[event_payload()])
    assert response.status_code == 200
    assert response.json() == {"incidents": expected}


def test_analyze_enforces_event_limit(monkeypatch):
    monkeypatch.setattr(api, "MAX_EVENTS", 1)
    response = client.post("/v1/analyze", json=[event_payload("evt-1"), event_payload("evt-2")])
    assert response.status_code == 413
    assert response.json()["detail"] == "Maximum 1 events per request"


def test_api_key_protection(monkeypatch):
    monkeypatch.setattr(api, "API_KEY", "secret")
    monkeypatch.setattr(api, "API_KEY_ROLE", "admin")
    missing = client.get("/v2/datasets")
    invalid = client.get("/v2/datasets", headers={"xaita-api-key": "wrong"})
    valid = client.get("/v2/datasets", headers={"xaita-api-key": "secret"})
    bearer = client.get("/v2/datasets", headers={"Authorization": "Bearer secret"})
    assert missing.status_code == 401
    assert invalid.status_code == 403
    assert valid.status_code == 200
    assert bearer.status_code == 200


def test_rbac_blocks_viewer_from_experiment(monkeypatch):
    monkeypatch.setattr(api, "API_KEY", "viewer-secret")
    monkeypatch.setattr(api, "API_KEY_ROLE", "viewer")
    response = client.post("/v2/experiment", json={"dataset": "unknown", "detector": "CNN-LSTM", "seed": 42}, headers={"X-XAITA-API-Key": "viewer-secret"})
    assert response.status_code == 403


def test_system_status_reports_security(monkeypatch):
    monkeypatch.setattr(api, "API_KEY", "secret")
    monkeypatch.setattr(api, "API_KEY_ROLE", "admin")
    response = client.get("/v2/system", headers={"X-XAITA-API-Key": "secret", "X-Request-ID": "test-request"})
    assert response.status_code == 200
    body = response.json()
    assert body["schema_version"] == "XAITA-OT-V5-SYSTEM-1.0"
    assert body["role"] == "admin"
    assert body["security"]["authentication_configured"] is True
    assert response.headers["X-Request-ID"] == "test-request"


def test_capabilities_contract(monkeypatch):
    monkeypatch.setattr(api, "API_KEY", None)
    response = client.get("/v2/capabilities")
    assert response.status_code == 200
    body = response.json()
    assert body["schema_version"] == "XAITA-OT-V5-CAPABILITIES-1.0"
    assert body["datasets"] == ["SWaT", "BATADAL", "TON-IoT"]
    assert {item["id"] for item in body["detectors"]} == {"random_forest", "cnn", "lstm", "cnn_lstm"}
    assert "DC+BSS+ECS+MAS" in body["attribution_configurations"]


def test_ops_summary_reports_dataset_readiness(tmp_path, monkeypatch):
    monkeypatch.setattr(api, "API_KEY", None)
    monkeypatch.setattr(api, "ROOT", tmp_path)
    (tmp_path / "web").mkdir()
    (tmp_path / "web" / "index.html").write_text("dashboard", encoding="utf-8")
    dataset_root = tmp_path / "data" / "raw"
    paths = {}
    for key, folder in (("SWaT", "swat"), ("BATADAL", "batadal"), ("TON-IoT", "ton_iot")):
        path = dataset_root / folder
        path.mkdir(parents=True)
        (path / "sample.csv").write_text("timestamp,label\n2026-01-01,0\n", encoding="utf-8")
        paths[key] = str(path)
    monkeypatch.setattr(api, "DATASET_PATHS", paths)
    response = client.get("/v2/ops/summary")
    assert response.status_code == 200
    body = response.json()
    assert body["schema_version"] == "XAITA-OT-V5-OPS-1.0"
    assert body["status"] == "operational"
    assert body["datasets"]["ready_count"] == 3
    assert body["execution"]["detectors"] == ["random_forest", "cnn", "lstm", "cnn_lstm"]


def test_experiment_rejects_unknown_dataset(monkeypatch):
    monkeypatch.setattr(api, "API_KEY", None)
    response = client.post("/v2/experiment", json={"dataset": "unknown", "detector": "CNN-LSTM", "seed": 42})
    assert response.status_code == 400
    assert response.json()["detail"] == "Unsupported dataset"


def test_experiment_rejects_unknown_detector(monkeypatch):
    monkeypatch.setattr(api, "API_KEY", None)
    response = client.post("/v2/experiment", json={"dataset": "TON-IoT", "detector": "unknown", "seed": 42})
    assert response.status_code == 400
    assert "Unknown detector" in response.json()["detail"]
