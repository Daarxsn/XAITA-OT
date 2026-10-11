from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_dashboard_does_not_generate_fake_live_telemetry():
    html = (ROOT / "web" / "index.html").read_text(encoding="utf-8")
    assert "Math.random()" not in html
    assert "const rows=[['09:42:18'" not in html
    assert "Live time series unavailable until an API telemetry endpoint is connected" in html
    assert "Illustrative demo scores · not live telemetry" in html


def test_dashboard_escapes_api_derived_strings_before_html_insertion():
    html = (ROOT / "web" / "index.html").read_text(encoding="utf-8")
    assert "function escapeHtml(value)" in html
    assert "escapeHtml(c.technique_id)" in html
    assert "escapeHtml(e.event_id)" in html
    assert "escapeHtml(a.hypothesis||'—')" in html


def test_dashboard_distinguishes_file_presence_from_benchmark_validation():
    html = (ROOT / "web" / "index.html").read_text(encoding="utf-8")
    assert "dataset files are present; benchmark validation is separate" in html
    assert "VALIDATION NOT RUN" in html
    assert "benchmark validation is separate" in html
