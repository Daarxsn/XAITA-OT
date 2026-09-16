from pathlib import Path

from xaita_ot.api import app as api


def test_dashboard_path_prefers_configured_root(tmp_path, monkeypatch):
    configured = tmp_path / "configured"
    configured_web = configured / "web"
    configured_web.mkdir(parents=True)
    dashboard = configured_web / "index.html"
    dashboard.write_text("<!doctype html>", encoding="utf-8")

    monkeypatch.setattr(api, "_CONFIGURED_ROOT", str(configured))
    monkeypatch.setattr(api, "_PROJECT_ROOT", tmp_path / "missing-project")
    monkeypatch.setattr(api, "Path", Path)

    assert api._dashboard_path() == dashboard.resolve()


def test_dashboard_path_falls_back_to_working_directory(tmp_path, monkeypatch):
    web = tmp_path / "web"
    web.mkdir()
    dashboard = web / "index.html"
    dashboard.write_text("<!doctype html>", encoding="utf-8")

    monkeypatch.setattr(api, "_CONFIGURED_ROOT", None)
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(api, "_PROJECT_ROOT", tmp_path / "missing-project")

    assert api._dashboard_path() == dashboard.resolve()


def test_ready_reports_dashboard_availability(tmp_path, monkeypatch):
    monkeypatch.setattr(api, "_dashboard_path", lambda: tmp_path / "web" / "index.html")
    response = api.ready()
    assert response["status"] == "ready"
    assert response["dashboard"] is False
