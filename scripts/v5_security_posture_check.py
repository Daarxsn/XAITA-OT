#!/usr/bin/env python3
"""XAITA-OT V5.9 deterministic deployment-security posture gate."""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def require(results, name, condition, detail):
    results.append((name, bool(condition), detail))


def main() -> int:
    results = []
    docker = (ROOT / "Dockerfile").read_text(encoding="utf-8")
    compose = (ROOT / "docker-compose.yml").read_text(encoding="utf-8")
    env = (ROOT / ".env.example").read_text(encoding="utf-8")

    require(results, "non-root container", "USER xaita" in docker, "Dockerfile runs as xaita")
    require(results, "container healthcheck", "HEALTHCHECK" in docker, "Dockerfile has a healthcheck")
    require(results, "read-only runtime", "read_only: true" in compose, "compose filesystem is read-only")
    require(results, "no-new-privileges", "no-new-privileges:true" in compose, "compose disables privilege escalation")
    require(results, "all Linux capabilities dropped", re.search(r"cap_drop:\s*\n\s*- ALL", compose) is not None, "compose drops all capabilities")
    require(results, "temporary filesystem hardened", "tmpfs:" in compose and "noexec,nosuid" in compose, "temporary storage is noexec/nosuid")
    require(results, "request limit propagated", "XAITA_MAX_REQUEST_BYTES" in compose, "compose exposes the API request-size control")
    require(results, "resource controls documented", all(x in env for x in ("XAITA_MAX_EVENTS=", "XAITA_RATE_LIMIT_PER_MINUTE=", "XAITA_MAX_REQUEST_BYTES=")), "all resource controls are documented")

    workflow_dir = ROOT / ".github" / "workflows"
    workflows = sorted(workflow_dir.glob("*.yml")) + sorted(workflow_dir.glob("*.yaml"))
    missing_permissions = [p.name for p in workflows if "permissions:" not in p.read_text(encoding="utf-8")]
    require(results, "workflow permissions", not missing_permissions, "all workflows declare explicit permissions" if not missing_permissions else "missing permissions: " + ", ".join(missing_permissions))

    for path in [ROOT / "Dockerfile", ROOT / "docker-compose.yml", ROOT / ".env.example"]:
        content = path.read_text(encoding="utf-8", errors="replace")
        leaked = bool(re.search(r"(?i)(BEGIN (RSA |EC |OPENSSH )?PRIVATE KEY|ghp_[A-Za-z0-9]{20,}|sk-[A-Za-z0-9]{20,})", content))
        require(results, f"credential marker:{path.name}", not leaked, "no obvious credential marker")

    failures = [x for x in results if not x[1]]
    for name, ok, detail in results:
        print(f"[{'PASS' if ok else 'FAIL'}] {name}: {detail}")
    print(f"Security posture: {'PASS' if not failures else 'FAIL'} ({len(results)} checks, {len(failures)} failures)")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
