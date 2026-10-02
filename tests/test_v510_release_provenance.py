from pathlib import Path
import json
import os
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[1]


def test_release_provenance_script_requires_release_artifacts(tmp_path):
    script = ROOT / "scripts" / "v5_release_provenance.py"
    result = subprocess.run(
        [sys.executable, str(script)],
        cwd=tmp_path,
        env={**os.environ, "PYTHONPATH": str(ROOT / "src")},
        capture_output=True,
        text=True,
    )
    assert result.returncode != 0


def test_provenance_schema_is_documented():
    doc = ROOT / "docs" / "V5_DAY17_RELEASE_PROVENANCE_LOCK.md"
    text = doc.read_text(encoding="utf-8")
    assert "V5.10-RELEASE-PROVENANCE-1.0" in text
    assert "SHA-256" in text
