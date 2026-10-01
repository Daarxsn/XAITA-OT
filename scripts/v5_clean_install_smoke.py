#!/usr/bin/env python3
"""XAITA-OT V5.8 clean-install and handover smoke.

Verifies that a built wheel can be installed into an isolated environment and
that the public package and CLI entry point are usable. This is a packaging
handover check, not a production OT deployment or safety certification.
"""

from __future__ import annotations

import os
from pathlib import Path
import subprocess
import sys
import tempfile


ROOT = Path(__file__).resolve().parents[1]


def run(*args: str, cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(args, cwd=cwd or ROOT, text=True, capture_output=True)


def main() -> int:
    wheels = sorted((ROOT / "dist").glob("*.whl"))
    if len(wheels) != 1:
        raise RuntimeError("expected exactly one release wheel in dist/")

    with tempfile.TemporaryDirectory(prefix="xaita-v58-install-") as temp:
        venv = Path(temp) / "venv"
        subprocess.run([sys.executable, "-m", "venv", str(venv)], check=True)
        scripts = venv / ("Scripts" if os.name == "nt" else "bin")
        python = scripts / ("python.exe" if os.name == "nt" else "python")
        pip = scripts / ("pip.exe" if os.name == "nt" else "pip")

        install = run(str(pip), "install", str(wheels[0]))
        if install.returncode:
            print(install.stdout)
            print(install.stderr)
            return 1

        checks = [
            ("package import", [str(python), "-c", "import xaita_ot; print(xaita_ot.__name__)"]),
            ("CLI help", [str(scripts / ("xaita.exe" if os.name == "nt" else "xaita")), "--help"]),
        ]
        failed = []
        for name, command in checks:
            result = run(*command)
            ok = result.returncode == 0
            print(f"[{'PASS' if ok else 'FAIL'}] {name}")
            if not ok:
                print(result.stdout[-2000:])
                print(result.stderr[-2000:])
                failed.append(name)

        if failed:
            print("Clean-install smoke: FAIL — " + ", ".join(failed))
            return 1
        print("Clean-install smoke: PASS")
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
