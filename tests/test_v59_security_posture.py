from pathlib import Path
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[1]


def test_security_posture_gate_passes():
    result = subprocess.run(
        [sys.executable, "scripts/v5_security_posture_check.py"],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert "Security posture: PASS" in result.stdout
