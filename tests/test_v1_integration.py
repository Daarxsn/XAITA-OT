from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient

from xaita_ot.api.app import app


client = TestClient(app)


def _payload():
    t = datetime.now(timezone.utc)
    labels = ["reconnaissance", "protocol", "unauthorized_command", "process_deviation"]
    return [
        {
            "event_id": f"e{i+1}",
            "timestamp": (t + timedelta(seconds=i * 5)).isoformat(),
            "asset": "PLC-01",
            "protocol": "modbus",
            "source": "HMI-01",
            "destination": "PLC-01",
            "label": labels[i],
            "detection_confidence": 0.80 + i * 0.03,
            "features": {"command_anomaly": 0.8, "packet_rate": 0.6},
        }
        for i in range(4)
    ]


def test_health_and_ready():
    health = client.get("/health")
    assert health.status_code == 200
    assert health.json()["status"] == "ok"
    ready = client.get("/ready")
    assert ready.status_code == 200
    assert "dashboard" in ready.json()


def test_analyze_end_to_end_contract():
    response = client.post("/v1/analyze", json=_payload())
    assert response.status_code == 200
    body = response.json()
    assert len(body["incidents"]) == 1
    incident = body["incidents"][0]
    assert incident["detection"]["event_ids"] == ["e1", "e2", "e3", "e4"]
    assert incident["behavior"]["episode_id"].startswith("EP-")
    assert incident["behavior"]["correlation_edges"]
    assert incident["attribution"]["belief"] <= incident["attribution"]["plausibility"]
    assert incident["provenance"] == ["e1", "e2", "e3", "e4"]
    assert incident["human_validation_required"] is True
    assert incident["autonomous_ot_action"] is False


def test_analyze_rejects_empty_input():
    response = client.post("/v1/analyze", json=[])
    assert response.status_code == 400


def test_analyze_rejects_unknown_fields():
    payload = _payload()
    payload[0]["unexpected"] = "reject-me"
    response = client.post("/v1/analyze", json=payload)
    assert response.status_code == 422
