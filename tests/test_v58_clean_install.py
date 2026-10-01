from pathlib import Path
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[1]


def test_clean_install_script_exists_and_compiles():
    result = subprocess.run(
        [sys.executable, "-m", "py_compile", "scripts/v5_clean_install_smoke.py"],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stdout + result.stderr
