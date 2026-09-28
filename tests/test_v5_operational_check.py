from scripts.v5_operational_check import run_check


def test_operational_check_passes_expected_service_contract(monkeypatch):
    responses = {
        "/health": (200, {"X-Request-ID": "abc", "X-Content-Type-Options": "nosniff", "X-Frame-Options": "DENY", "Referrer-Policy": "no-referrer", "Cache-Control": "no-store"}, {"status": "ok"}),
        "/ready": (200, {}, {"status": "ready", "dashboard": True}),
        "/": (200, {"X-Request-ID": "abc", "X-Content-Type-Options": "nosniff", "X-Frame-Options": "DENY", "Referrer-Policy": "no-referrer", "Cache-Control": "no-store"}, "html"),
        "/v2/datasets": (200, {}, {"datasets": {"SWaT": {}, "BATADAL": {}, "TON-IoT": {}}}),
        "/v2/system": (200, {}, {"schema_version": "XAITA-OT-V5-SYSTEM-1.0"}),
        "/v1/analyze": (401, {}, {"detail": "API authentication required"}),
    }

    def fake_request(base_url, path, api_key=None, timeout=10.0):
        return responses[path]

    monkeypatch.setattr("scripts.v5_operational_check._request", fake_request)
    results = run_check("http://test", require_auth=True)
    assert all(item.status == "pass" for item in results)


def test_operational_check_detects_missing_security_headers(monkeypatch):
    responses = {
        "/health": (200, {}, {"status": "ok"}),
        "/ready": (200, {}, {"status": "ready", "dashboard": True}),
        "/": (200, {"X-Request-ID": "abc"}, "html"),
        "/v2/datasets": (200, {}, {"datasets": {}}),
        "/v2/system": (200, {}, {"schema_version": "XAITA-OT-V5-SYSTEM-1.0"}),
        "/v1/analyze": (401, {}, {}),
    }
    monkeypatch.setattr("scripts.v5_operational_check._request", lambda base_url, path, api_key=None, timeout=10.0: responses[path])
    results = run_check("http://test", require_auth=True)
    assert next(item for item in results if item.name == "security headers").status == "fail"
