#!/usr/bin/env python3
"""XAITA-OT V5 deployment preflight.

The preflight is intentionally read-only apart from a short-lived write test in
artifacts/. It validates the application package, dashboard/config assets and
production security requirements without touching benchmark data.
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import sys
import tempfile


PROJECT_ROOT = Path(__file__).resolve().parents[1]
REQUIRED_ROLES = {"viewer", "analyst", "admin"}


def _result(name: str, ok: bool, detail: str, *, severity: str = "error") -> dict:
    return {"check": name, "status": "pass" if ok else severity, "detail": detail}


def _csv_count(path: Path) -> int:
    if path.is_file() and path.suffix.lower() == ".csv":
        return 1
    if not path.is_dir():
        return 0
    return sum(1 for item in path.rglob("*") if item.is_file() and item.suffix.lower() == ".csv")


def run_preflight(*, require_datasets: bool = False) -> list[dict]:
    checks: list[dict] = []

    py = sys.version_info
    checks.append(_result(
        "python_version",
        (3, 10) <= (py.major, py.minor) < (3, 14),
        f"Python {py.major}.{py.minor}.{py.micro}",
    ))

    try:
        import xaita_ot  # noqa: F401
        from xaita_ot import __version__
        checks.append(_result("package_import", True, f"xaita-ot {__version__}"))
    except Exception as exc:  # pragma: no cover - exercised by deployment failures
        checks.append(_result("package_import", False, f"package import failed: {type(exc).__name__}: {exc}"))

    for relative, label in (("configs/datasets.yaml", "dataset configuration"), ("web/index.html", "dashboard asset")):
        path = PROJECT_ROOT / relative
        checks.append(_result(label, path.is_file(), str(path)))

    artifacts = PROJECT_ROOT / "artifacts"
    artifacts.mkdir(parents=True, exist_ok=True)
    try:
        with tempfile.NamedTemporaryFile(prefix=".preflight-", dir=artifacts, delete=True):
            pass
        checks.append(_result("artifact_write", True, str(artifacts)))
    except OSError as exc:
        checks.append(_result("artifact_write", False, f"{artifacts}: {exc}"))

    environment = os.environ.get("XAITA_ENV", "development").strip().lower()
    production = environment in {"staging", "production"}
    allowed_hosts = [h.strip() for h in os.environ.get("XAITA_ALLOWED_HOSTS", "127.0.0.1,localhost").split(",") if h.strip()]
    cors = [o.strip() for o in os.environ.get("XAITA_CORS_ORIGINS", "").split(",") if o.strip()]

    if production:
        raw_keys = os.environ.get("XAITA_API_KEYS_JSON", "").strip()
        legacy_key = os.environ.get("XAITA_API_KEY", "").strip()
        try:
            parsed = json.loads(raw_keys) if raw_keys else {}
            valid_keys = isinstance(parsed, dict) and all(
                str(role).strip().lower() in REQUIRED_ROLES and isinstance(secret, str) and bool(secret)
                for role, secret in parsed.items()
            )
        except json.JSONDecodeError:
            valid_keys = False
        auth_ok = bool(legacy_key) or valid_keys
        checks.append(_result("production_auth", auth_ok, "API credentials configured" if auth_ok else "configure XAITA_API_KEY or XAITA_API_KEYS_JSON"))
        checks.append(_result("production_https", os.environ.get("XAITA_FORCE_HTTPS", "false").lower() == "true", "XAITA_FORCE_HTTPS=true" if os.environ.get("XAITA_FORCE_HTTPS", "false").lower() == "true" else "set XAITA_FORCE_HTTPS=true"))
        checks.append(_result("production_hosts", bool(allowed_hosts) and "*" not in allowed_hosts, ", ".join(allowed_hosts) or "no allowed hosts configured"))
        checks.append(_result("production_cors", "*" not in cors, ", ".join(cors) if cors else "CORS disabled"))
    else:
        checks.append(_result("environment", True, f"{environment} (production controls are advisory)", severity="warning"))

    if require_datasets:
        datasets = {
            "SWaT": os.environ.get("XAITA_SWAT_PATH", str(PROJECT_ROOT / "data/raw/swat")),
            "BATADAL": os.environ.get("XAITA_BATADAL_PATH", str(PROJECT_ROOT / "data/raw/batadal")),
            "TON-IoT": os.environ.get("XAITA_TONIOT_PATH", str(PROJECT_ROOT / "data/raw/ton_iot")),
        }
        for name, raw_path in datasets.items():
            path = Path(raw_path)
            count = _csv_count(path) if path.exists() else 0
            checks.append(_result(f"dataset:{name}", count > 0, f"{path} ({count} CSV files)"))

    return checks


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run XAITA-OT V5 deployment preflight checks")
    parser.add_argument("--require-datasets", action="store_true", help="fail unless SWaT, BATADAL and TON-IoT each contain CSV data")
    parser.add_argument("--json", action="store_true", dest="as_json", help="emit machine-readable JSON")
    args = parser.parse_args(argv)

    checks = run_preflight(require_datasets=args.require_datasets)
    failures = [item for item in checks if item["status"] == "error"]
    if args.as_json:
        print(json.dumps({"schema_version": "XAITA-OT-V5-PREFLIGHT-1.0", "ok": not failures, "checks": checks}, indent=2))
    else:
        for item in checks:
            print(f"[{item['status'].upper():7}] {item['check']}: {item['detail']}")
        print(f"\nPreflight: {'PASS' if not failures else 'FAIL'} ({len(checks)} checks, {len(failures)} errors)")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
