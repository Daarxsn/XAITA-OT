"""V5 production operational acceptance probe.

The probe is intentionally stdlib-only so it can run on a deployment host
without adding monitoring dependencies. It validates the externally visible
service contract, security headers, request correlation, and authentication
behavior. It never prints credential values.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any


@dataclass
class ProbeResult:
    name: str
    status: str
    detail: str

    def as_dict(self) -> dict[str, str]:
        return {"check": self.name, "status": self.status, "detail": self.detail}


def _request(base_url: str, path: str, api_key: str | None = None, timeout: float = 10.0) -> tuple[int, dict[str, str], Any]:
    headers = {"Accept": "application/json", "User-Agent": "XAITA-OT-v5-operational-check/1.0"}
    if api_key:
        headers["X-XAITA-API-Key"] = api_key
    request = urllib.request.Request(base_url.rstrip("/") + path, headers=headers)
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            raw = response.read()
            content_type = response.headers.get("Content-Type", "")
            body: Any = raw.decode("utf-8", errors="replace")
            if "json" in content_type:
                try:
                    body = json.loads(body)
                except json.JSONDecodeError:
                    pass
            return response.status, dict(response.headers.items()), body
    except urllib.error.HTTPError as exc:
        raw = exc.read()
        body: Any = raw.decode("utf-8", errors="replace")
        try:
            body = json.loads(body)
        except json.JSONDecodeError:
            pass
        return exc.code, dict(exc.headers.items()), body


def _header(headers: dict[str, str], name: str) -> str | None:
    wanted = name.lower()
    return next((value for key, value in headers.items() if key.lower() == wanted), None)


def run_check(base_url: str, api_key: str | None = None, require_auth: bool = False) -> list[ProbeResult]:
    results: list[ProbeResult] = []

    status, headers, body = _request(base_url, "/health", timeout=5)
    results.append(ProbeResult("health", "pass" if status == 200 and isinstance(body, dict) and body.get("status") == "ok" else "fail", f"HTTP {status}"))

    status, headers, body = _request(base_url, "/ready", timeout=5)
    ready_ok = status == 200 and isinstance(body, dict) and body.get("status") == "ready" and body.get("dashboard") is True
    results.append(ProbeResult("readiness", "pass" if ready_ok else "fail", f"HTTP {status}; dashboard={body.get('dashboard') if isinstance(body, dict) else 'unknown'}"))

    status, headers, _ = _request(base_url, "/", timeout=5)
    request_id = _header(headers, "X-Request-ID")
    results.append(ProbeResult("dashboard", "pass" if status == 200 else "fail", f"HTTP {status}"))
    results.append(ProbeResult("request correlation", "pass" if request_id else "fail", "X-Request-ID present" if request_id else "X-Request-ID missing"))

    required_headers = ["X-Content-Type-Options", "X-Frame-Options", "Referrer-Policy", "Cache-Control"]
    missing = [name for name in required_headers if not _header(headers, name)]
    results.append(ProbeResult("security headers", "pass" if not missing else "fail", "all baseline headers present" if not missing else "missing: " + ", ".join(missing)))

    status, _, body = _request(base_url, "/v2/datasets", api_key=api_key, timeout=10)
    results.append(ProbeResult("dataset status", "pass" if status == 200 and isinstance(body, dict) and "datasets" in body else "fail", f"HTTP {status}"))

    status, _, body = _request(base_url, "/v2/system", api_key=api_key, timeout=10)
    system_ok = status == 200 and isinstance(body, dict) and body.get("schema_version") == "XAITA-OT-V5-SYSTEM-1.0"
    results.append(ProbeResult("system status", "pass" if system_ok else "fail", f"HTTP {status}"))

    status, _, _ = _request(base_url, "/v1/analyze", timeout=5)
    if require_auth:
        auth_ok = status in {401, 403}
        detail = f"HTTP {status}; unauthenticated access blocked"
    else:
        auth_ok = status in {401, 403, 405, 422}
        detail = f"HTTP {status}; endpoint is not anonymously executable"
    results.append(ProbeResult("authentication boundary", "pass" if auth_ok else "fail", detail))

    return results


def main() -> int:
    parser = argparse.ArgumentParser(description="XAITA-OT V5 production operational acceptance probe")
    parser.add_argument("--base-url", default=os.environ.get("XAITA_BASE_URL", "http://127.0.0.1:8080"))
    parser.add_argument("--api-key", default=os.environ.get("XAITA_API_KEY"))
    parser.add_argument("--require-auth", action="store_true", default=os.environ.get("XAITA_ENV", "").lower() in {"staging", "production"})
    parser.add_argument("--json", action="store_true", dest="as_json")
    args = parser.parse_args()

    results = run_check(args.base_url, args.api_key, args.require_auth)
    payload = {"schema_version": "XAITA-OT-V5-OPS-1.0", "base_url": args.base_url.rstrip("/"), "checks": [item.as_dict() for item in results], "status": "pass" if all(item.status == "pass" for item in results) else "fail"}
    if args.as_json:
        print(json.dumps(payload, separators=(",", ":")))
    else:
        for item in results:
            print(f"[{item.status.upper():4}] {item.name}: {item.detail}")
        print(f"Overall: {payload['status'].upper()}")
    return 0 if payload["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
