"""Start the XAITA-OT API and verify core operational endpoints."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BASE_URL = "http://127.0.0.1:8765"


def request(path: str, payload: dict | list | None = None) -> tuple[int, dict]:
    data = None
    headers = {}
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(f"{BASE_URL}{path}", data=data, headers=headers)
    with urllib.request.urlopen(req, timeout=5) as response:
        return response.status, json.loads(response.read().decode("utf-8"))


def main() -> int:
    env = os.environ.copy()
    env["PORT"] = "8765"
    process = subprocess.Popen(
        [sys.executable, "run_api.py"], cwd=ROOT, env=env,
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
    )
    try:
        deadline = time.monotonic() + 20
        last_error: Exception | None = None
        while time.monotonic() < deadline:
            try:
                status, body = request("/health")
                if status == 200:
                    print(f"/health: {body}")
                    break
            except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
                last_error = exc
            time.sleep(0.25)
        else:
            output = process.stdout.read() if process.stdout else ""
            raise RuntimeError(f"API did not become ready: {last_error}\n{output}")

        status, body = request("/ready")
        assert status == 200 and body["status"] == "ready", body
        print(f"/ready: {body}")

        event = {
            "event_id": "startup-smoke-1",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "asset": "plc-01", "protocol": "modbus",
            "source": "10.0.0.1", "destination": "10.0.0.2",
            "label": "normal", "detection_confidence": 0.8,
            "features": {"flow_rate": 1.0},
        }
        status, body = request("/v1/analyze", [event])
        assert status == 200 and "incidents" in body, body
        print(f"/v1/analyze: {body}")
        print("API startup smoke: PASS")
        return 0
    finally:
        process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=5)


if __name__ == "__main__":
    raise SystemExit(main())
