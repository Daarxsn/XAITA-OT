from xaita_ot.api import app as api
from fastapi.testclient import TestClient

client = TestClient(api.app, base_url="http://localhost")


def test_request_body_limit(monkeypatch):
    monkeypatch.setattr(api, "MAX_REQUEST_BYTES", 32)
    response = client.post("/v1/analyze", content="x" * 64, headers={"Content-Type": "application/json"})
    assert response.status_code == 413
    assert response.json()["detail"].startswith("Maximum request body")


def test_system_and_ops_expose_resource_limits(monkeypatch):
    monkeypatch.setattr(api, "API_KEY", None)
    monkeypatch.setattr(api, "MAX_REQUEST_BYTES", 12345)
    system = client.get("/v2/system")
    ops = client.get("/v2/ops/summary")
    assert system.status_code == 200
    assert system.json()["security"]["max_request_bytes"] == 12345
    assert ops.status_code == 200
    assert ops.json()["security"]["max_request_bytes"] == 12345


def test_unhandled_request_error_is_sanitized(monkeypatch):
    def boom(*args, **kwargs):
        raise RuntimeError("secret-internal-detail")
    monkeypatch.setattr(api, "_dashboard_path", boom)
    response = client.get("/v2/ops/summary")
    assert response.status_code == 500
    assert "secret-internal-detail" not in response.text
    assert response.json()["detail"] == "Internal server error"
    assert response.json()["request_id"]
