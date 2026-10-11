import run_api


def test_local_api_default_binds_only_to_loopback(monkeypatch):
    monkeypatch.delenv("XAITA_API_HOST", raising=False)
    monkeypatch.setattr(run_api, "prepare_runtime_data", lambda: 0)
    captured = {}
    monkeypatch.setattr(run_api.uvicorn, "run", lambda *args, **kwargs: captured.update(kwargs))

    assert run_api.main() == 0
    assert captured["host"] == "127.0.0.1"


def test_container_or_reverse_proxy_can_explicitly_override_api_host(monkeypatch):
    monkeypatch.setenv("XAITA_API_HOST", "0.0.0.0")
    monkeypatch.setattr(run_api, "prepare_runtime_data", lambda: 0)
    captured = {}
    monkeypatch.setattr(run_api.uvicorn, "run", lambda *args, **kwargs: captured.update(kwargs))

    assert run_api.main() == 0
    assert captured["host"] == "0.0.0.0"
