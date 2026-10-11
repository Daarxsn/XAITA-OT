from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_local_startup_binds_loopback_unless_explicitly_overridden():
    source = (ROOT / "run_api.py").read_text(encoding="utf-8")
    assert 'os.environ.get("XAITA_HOST", "127.0.0.1")' in source


def test_compose_container_and_host_network_defaults_are_deliberate():
    source = (ROOT / "docker-compose.yml").read_text(encoding="utf-8")
    # Uvicorn listens on the container interface, but the host port is local-only.
    assert 'XAITA_HOST: ${XAITA_HOST:-0.0.0.0}' in source
    assert '"127.0.0.1:8080:8080"' in source
