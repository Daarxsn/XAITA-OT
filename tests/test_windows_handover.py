from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_windows_setup_installs_or_detects_python_and_runs_smokes():
    setup = (ROOT / "setup_windows.ps1").read_text(encoding="utf-8")
    assert "Python.Python.3.12" in setup
    assert "https://www.python.org/downloads/windows/" in setup
    assert "pip install -e ." in setup
    assert "synthetic_smoke.csv" in setup
    assert "demo_smoke.json" in setup
    assert "from xaita_ot.api.app import app" in setup
    assert "setup-install.log" in setup


def test_windows_dashboard_launcher_checks_health_and_logs_errors():
    launch = (ROOT / "launch_windows.ps1").read_text(encoding="utf-8")
    assert "http://127.0.0.1:8080/health" in launch
    assert 'Start-Process "$url/"' in launch
    assert "dashboard-stdout.log" in launch
    assert "dashboard-stderr.log" in launch


def test_double_click_windows_launchers_exist_and_call_powershell():
    setup_cmd = (ROOT / "SETUP_WINDOWS.cmd").read_text(encoding="utf-8")
    run_cmd = (ROOT / "RUN_DASHBOARD.cmd").read_text(encoding="utf-8")
    assert "setup_windows.ps1" in setup_cmd
    assert "launch_windows.ps1" in run_cmd
    assert "-ExecutionPolicy Bypass" in setup_cmd
    assert "-ExecutionPolicy Bypass" in run_cmd
