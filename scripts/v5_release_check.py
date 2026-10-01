#!/usr/bin/env python3
"""XAITA-OT V5.5 release-readiness gate.

This check is repository-local and deterministic. It verifies that the release
surface is present, the documented safety boundary is retained, deployment
hardening files exist, and the package metadata/CI contracts are aligned.
It does not claim external deployment, penetration testing, load capacity, or
customer-specific OT acceptance.
"""

from __future__ import annotations

import re
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]

REQUIRED_FILES = [
    "README.md",
    "pyproject.toml",
    "Dockerfile",
    "docker-compose.yml",
    ".env.example",
    ".github/workflows/ci.yml",
    ".github/workflows/v5-preflight.yml",
    ".github/workflows/v5-operational-check.yml",
    "scripts/v5_preflight.py",
    "scripts/v5_operational_check.py",
    "scripts/v5_e2e_smoke.py",
    "docs/V5_ROADMAP.md",
    "docs/V5.1_RELEASE_GATE.md",
    "docs/V5_DAY8_DEPLOYMENT_INTEGRATION_LOCK.md",
    "docs/V5_DAY9_EVIDENCE_PROVENANCE_LOCK.md",
    "docs/V5_DAY11_OPERATIONAL_ROBUSTNESS_LOCK.md",
]

TEXT_FILES = [
    "README.md",
    "pyproject.toml",
    "Dockerfile",
    "docker-compose.yml",
    ".env.example",
]


def check(name: str, ok: bool, detail: str) -> tuple[str, bool, str]:
    return name, ok, detail


def run() -> list[tuple[str, bool, str]]:
    results = []

    missing = [p for p in REQUIRED_FILES if not (ROOT / p).is_file()]
    results.append(check("required release files", not missing, "all present" if not missing else "missing: " + ", ".join(missing)))

    pyproject = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    version = re.search(r'^version\s*=\s*"([^"]+)"', pyproject, re.MULTILINE)
    results.append(check("package metadata", bool(version and version.group(1) == "0.5.1"), f"version={version.group(1) if version else 'missing'}"))

    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    safety_terms = [
        "Observation → Detection → Episode → Context → Attribution → Explanation → Risk → CTI",
        "Detection Confidence (DC) ≠ Attribution Confidence (AC)",
        "analyst-support security analytics system",
        "does not issue PLC/RTU/SCADA control commands",
    ]
    missing_safety = [term for term in safety_terms if term not in readme]
    results.append(check("safety boundary documentation", not missing_safety, "canonical safety statements present" if not missing_safety else "missing: " + ", ".join(missing_safety)))

    docker = (ROOT / "Dockerfile").read_text(encoding="utf-8")
    compose = (ROOT / "docker-compose.yml").read_text(encoding="utf-8")
    deployment_ok = all(token in docker for token in ["USER xaita", "HEALTHCHECK"]) and all(
        token in compose for token in ["read_only: true", "no-new-privileges:true", "cap_drop:", "- ALL"]
    )
    results.append(check("container hardening", deployment_ok, "non-root image user, healthcheck and least-privilege compose controls present"))

    env = (ROOT / ".env.example").read_text(encoding="utf-8")
    results.append(check("resource-control configuration", "XAITA_MAX_EVENTS=" in env and "XAITA_RATE_LIMIT_PER_MINUTE=" in env and "XAITA_MAX_REQUEST_BYTES=" in env, "resource controls documented in .env.example"))

    ci = (ROOT / ".github/workflows/ci.yml").read_text(encoding="utf-8")
    ci_contract = all(token in ci for token in ["python-version: ["3.11", "3.12"]", "pip-audit", "pytest -q", "scripts/v5_e2e_smoke.py"])
    results.append(check("CI release gate", ci_contract, "supported Python matrix, dependency audit, tests and deployment smoke are gated"))

    for path in TEXT_FILES:
        content = (ROOT / path).read_text(encoding="utf-8", errors="replace")
        suspicious = []
        if "BEGIN PRIVATE KEY" in content:
            suspicious.append("private-key marker")
        if re.search(r'(?i)(api[_-]?key|secret|token)\s*=\s*["\'](?!$)[^"\']{20,}["\']', content):
            suspicious.append("possible embedded credential")
        results.append(check(f"credential scan:{path}", not suspicious, "no obvious embedded credential" if not suspicious else ", ".join(suspicious)))

    return results


def main() -> int:
    results = run()
    failures = [r for r in results if not r[1]]
    for name, ok, detail in results:
        print(f"[{'PASS' if ok else 'FAIL'}] {name}: {detail}")
    print(f"Release readiness: {'PASS' if not failures else 'FAIL'} ({len(results)} checks, {len(failures)} failures)")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
