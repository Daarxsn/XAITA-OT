"""Verify the documented XAITA-OT installation and basic operational paths."""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def run(*args: str) -> str:
    completed = subprocess.run(
        list(args),
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    return completed.stdout.strip()


def main() -> int:
    print(f"Python: {sys.version.split()[0]}")
    print(f"Executable: {sys.executable}")

    version = run(sys.executable, "-c", "from xaita_ot import __version__; print(__version__)")
    print(f"Package version: {version}")

    cli = shutil.which("xaita")
    if cli is None:
        raise RuntimeError("Installed xaita console command was not found on PATH")

    cli_help = run(cli, "--help")
    if "synthetic-data" not in cli_help or "demo" not in cli_help:
        raise RuntimeError("Installed CLI help does not expose the documented commands")
    print(f"CLI commands: OK ({cli})")

    output = run(cli, "demo", "--out", "artifacts/v4_verification_cti.json")
    output_path = ROOT / output
    if not output_path.exists():
        raise RuntimeError(f"Demo output was not created: {output_path}")
    json.loads(output_path.read_text(encoding="utf-8"))
    print(f"Demo workflow: OK ({output_path})")

    print("Installation verification: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
