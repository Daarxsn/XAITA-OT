"""XAITA-OT V5 end-to-end deployment smoke.

Starts a disposable local API instance with synthetic dataset mounts, verifies the
externally visible V5 service contract, then terminates the instance. No benchmark
data is modified and no real detector training is executed.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request


VIEWER_KEY = "xaita-viewer-smoke"
ANALYST_KEY = "xaita-analyst-smoke"
ADMIN_KEY = "xaita-admin-smoke"


def _free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def _request(base_url: str, path: str, api_key: str | None = None) -> tuple[int, dict]:
    headers = {"Accept": "application/json", "User-Agent": "XAITA-OT-v5-e2e-smoke/1.0"}
    if api_key:
        headers["X-XAITA-API-Key"] = api_key
    request = urllib.request.Request(base_url.rstrip("/") + path, headers=headers)
    try:
        with urllib.request.urlopen(request, timeout=8) as response:
            raw = response.read()
            body = json.loads(raw.decode("utf-8")) if raw else {}
            return response.status, body
    except urllib.error.HTTPError as exc:
        raw = exc.read()
        try:
            body = json.loads(raw.decode("utf-8")) if raw else {}
        except json.JSONDecodeError:
            body = {}
        return exc.code, body


def _wait_for_health(base_url: str, process: subprocess.Popen[str]) -> None:
    deadline = time.time() + 30
    while time.time() < deadline:
        if process.poll() is not None:
            raise RuntimeError(f"API exited early with code {process.returncode}")
        status, body = _request(base_url, "/health")
        if status == 200 and body.get("status") == "ok":
            return
        time.sleep(0.25)
    raise RuntimeError("API did not become healthy within 30 seconds")


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="xaita-v5-e2e-") as temp:
        root = Path(temp)
        dataset_paths = {}
        for name in ("swat", "batadal", "ton_iot"):
            path = root / name
            path.mkdir(parents=True)
            (path / "smoke.csv").write_text("timestamp,label\n2026-01-01T00:00:00Z,0\n", encoding="utf-8")
            dataset_paths[name] = path

        port = _free_port()
        base_url = f"http://127.0.0.1:{port}"
        env = os.environ.copy()
        env.update(
            {
                "XAITA_ENV": "staging",
                "XAITA_ALLOWED_HOSTS": "127.0.0.1,localhost",
                "XAITA_CORS_ORIGINS": "",
                "XAITA_FORCE_HTTPS": "false",
                "XAITA_API_KEYS_JSON": json.dumps(
                    {"viewer": VIEWER_KEY, "analyst": ANALYST_KEY, "admin": ADMIN_KEY}
                ),
                "XAITA_SWAT_PATH": str(dataset_paths["swat"]),
                "XAITA_BATADAL_PATH": str(dataset_paths["batadal"]),
                "XAITA_TONIOT_PATH": str(dataset_paths["ton_iot"]),
                "PYTHONUNBUFFERED": "1",
            }
        )

        process = subprocess.Popen(
            [sys.executable, "-m", "uvicorn", "xaita_ot.api.app:app", "--host", "127.0.0.1", "--port", str(port)],
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
        )
        try:
            _wait_for_health(base_url, process)

            checks: list[tuple[str, bool, str]] = []

            status, body = _request(base_url, "/ready")
            checks.append(("readiness", status == 200 and body.get("status") == "ready" and body.get("dashboard") is True, f"HTTP {status}"))

            status, body = _request(base_url, "/")
            checks.append(("dashboard", status == 200, f"HTTP {status}"))

            status, body = _request(base_url, "/v2/datasets", VIEWER_KEY)
            datasets = body.get("datasets", {}) if isinstance(body, dict) else {}
            checks.append(
                (
                    "datasets",
                    status == 200
                    and all(datasets.get(name, {}).get("ready") is True for name in ("SWaT", "BATADAL", "TON-IoT")),
                    f"HTTP {status}",
                )
            )

            status, body = _request(base_url, "/v2/system", VIEWER_KEY)
            checks.append(("system", status == 200 and body.get("schema_version") == "XAITA-OT-V5-SYSTEM-1.0", f"HTTP {status}"))

            status, body = _request(base_url, "/v2/capabilities", VIEWER_KEY)
            checks.append(
                (
                    "capabilities",
                    status == 200
                    and set(body.get("datasets", [])) == {"SWaT", "BATADAL", "TON-IoT"}
                    and {item.get("id") for item in body.get("detectors", [])} == {"random_forest", "cnn", "lstm", "cnn_lstm"},
                    f"HTTP {status}",
                )
            )

            status, body = _request(base_url, "/v2/ops/summary", VIEWER_KEY)
            checks.append(("operations summary", status == 200 and body.get("schema_version") == "XAITA-OT-V5-OPS-1.0", f"HTTP {status}"))

            status, body = _request(base_url, "/v1/analyze")
            checks.append(("authentication boundary", status in {401, 403}, f"HTTP {status}"))

            status, body = _request(base_url, "/v2/system", "wrong-key")
            checks.append(("invalid credential rejection", status == 403, f"HTTP {status}"))

            failed = [name for name, ok, _ in checks if not ok]
            for name, ok, detail in checks:
                print(f"[{'PASS' if ok else 'FAIL':4}] {name}: {detail}")

            if failed:
                print("E2E smoke: FAIL — " + ", ".join(failed))
                return 1
            print("E2E smoke: PASS")
            return 0
        finally:
            process.terminate()
            try:
                process.wait(timeout=8)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=3)


if __name__ == "__main__":
    raise SystemExit(main())
