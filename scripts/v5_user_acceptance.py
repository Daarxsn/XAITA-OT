#!/usr/bin/env python3
"""Independent-user acceptance workflow for XAITA-OT V5."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REQUIRED = [
    "README.md",
    "docs/OPERATIONS.md",
    "docs/RELEASE_READINESS.md",
    "scripts/v5_preflight.py",
    "scripts/v5_operational_check.py",
    "scripts/v5_e2e_smoke.py",
]


def _run(name: str, command: list[str]) -> dict:
    result = subprocess.run(command, cwd=ROOT, text=True, capture_output=True)
    return {
        "check": name,
        "status": "pass" if result.returncode == 0 else "fail",
        "returncode": result.returncode,
        "detail": (result.stdout + result.stderr)[-4000:],
    }


def run_acceptance(*, live_url: str | None = None) -> dict:
    checks = []
    missing = [path for path in REQUIRED if not (ROOT / path).is_file()]
    checks.append({
        "check": "required acceptance surface",
        "status": "pass" if not missing else "fail",
        "detail": "all required runbook/probe files present" if not missing else "missing: " + ", ".join(missing),
    })

    checks.append(_run("deployment preflight", [sys.executable, "scripts/v5_preflight.py", "--json"]))

    if live_url:
        checks.append(_run(
            "live operational probe",
            [sys.executable, "scripts/v5_operational_check.py", "--base-url", live_url, "--json"],
        ))
    else:
        checks.append({
            "check": "live operational probe",
            "status": "skipped",
            "detail": "no --base-url supplied; run against the approved deployment for independent live acceptance",
        })

    checks.append(_run("disposable end-to-end smoke", [sys.executable, "scripts/v5_e2e_smoke.py"]))

    failures = [item for item in checks if item["status"] == "fail"]
    payload = {
        "schema_version": "XAITA-OT-V5-INDEPENDENT-ACCEPTANCE-1.0",
        "status": "pass" if not failures else "fail",
        "live_validation": bool(live_url),
        "checks": checks,
        "verification_boundary": "Repository and disposable acceptance evidence only; live acceptance requires an approved deployment URL and environment-specific operator validation.",
    }
    return payload


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run XAITA-OT V5 independent-user acceptance workflow")
    parser.add_argument("--base-url", help="Approved live/staging deployment URL for the operational probe.")
    parser.add_argument("--json", action="store_true", dest="as_json")
    args = parser.parse_args()
    payload = run_acceptance(live_url=args.base_url)
    if args.as_json:
        print(json.dumps(payload, indent=2))
    else:
        for item in payload["checks"]:
            print(f"[{item['status'].upper():7}] {item['check']}: {item['detail']}")
        print(f"Independent acceptance: {payload['status'].upper()}")
    return 0 if payload["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
