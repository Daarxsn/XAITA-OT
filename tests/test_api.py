from datetime import datetime, timezone

from fastapi.testclient import TestClient

from xaita_ot.api import app as api


client = TestClient(api.app)


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
    assert response.headers["Cache-Control"] == "no-store"


def test_ready_reports_dashboard(tmp_path, monkeypatch):
    (tmp_path / "web").mkdir()
    (tmp_path / "web" / "index.html").write_text("<html></html>", encoding="utf-8")
    monkeypatch.setattr(api, "ROOT", tmp_path)
    response = client.get("/ready")
    assert response.status_code == 200
    assert response.json() == {
        "status": "ready",
        "dashboard": True,
        "max_events": api.MAX_EVENTS,
    }


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
    response = client.post(
        "/v1/analyze",
        json=[event_payload("evt-1"), event_payload("evt-2")],
    )
    assert response.status_code == 413
    assert response.json()["detail"] == "Maximum 1 events per request"


def test_api_key_protection(monkeypatch):
    monkeypatch.setattr(api, "API_KEY", "secret")
    missing = client.get("/v2/datasets")
    invalid = client.get("/v2/datasets", headers={"xaita-api-key": "wrong"})
    valid = client.get("/v2/datasets", headers={"xaita-api-key": "secret"})
    assert missing.status_code == 401
    assert invalid.status_code == 403
    assert valid.status_code == 200


def test_experiment_rejects_unknown_dataset(monkeypatch):
    monkeypatch.setattr(api, "API_KEY", None)
    response = client.post(
        "/v2/experiment",
        json={"dataset": "unknown", "detector": "CNN-LSTM", "seed": 42},
    )
    assert response.status_code == 400
    assert response.json()["detail"] == "Unsupported dataset"
