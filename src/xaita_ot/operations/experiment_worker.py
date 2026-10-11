"""Deadline-bounded detector execution in a separate process.

The worker isolates model fitting from the API process. The deadline helper kills
the complete worker process group/tree when supported, then reaps the direct child.
"""
from __future__ import annotations

import argparse
from dataclasses import asdict
import json
import math
import os
from pathlib import Path
import signal
import subprocess
import sys
import tempfile
from types import SimpleNamespace
from typing import Any, Sequence

from ..config import AppConfig


class ExperimentTimeoutError(TimeoutError):
    """Raised after the isolated experiment process is terminated at its deadline."""


class ExperimentWorkerError(RuntimeError):
    """Raised when an isolated experiment worker fails."""

    def __init__(self, error_type: str, message: str):
        super().__init__(message)
        self.error_type = str(error_type or "ExperimentWorkerError")


def _terminate_process_tree(process: subprocess.Popen) -> None:
    """Terminate the worker and descendants, then reap the direct child."""
    if process.poll() is not None:
        return
    if os.name == "nt":
        # taskkill /T is needed because libraries such as joblib may create child
        # processes of their own. Fall back to killing the direct worker if taskkill
        # is unavailable or fails.
        try:
            subprocess.run(
                ["taskkill", "/PID", str(process.pid), "/T", "/F"],
                stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                timeout=5,
                check=False,
            )
        except (OSError, subprocess.TimeoutExpired):
            pass
        if process.poll() is None:
            process.kill()
    else:
        try:
            os.killpg(process.pid, signal.SIGTERM)
        except ProcessLookupError:
            pass
        try:
            process.wait(timeout=0.5)
        except subprocess.TimeoutExpired:
            pass
        # The worker may have exited while one of its descendants remains.
        # Check and kill the group even when the direct child was already reaped.
        try:
            os.killpg(process.pid, 0)
        except ProcessLookupError:
            pass
        else:
            try:
                os.killpg(process.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
    try:
        process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait()


def _run_process_with_timeout(
    command: Sequence[str],
    *,
    timeout_seconds: float,
    cwd: str | Path,
) -> int:
    """Run a command under a hard deadline and terminate it if it overruns."""
    timeout = float(timeout_seconds)
    if not math.isfinite(timeout) or timeout <= 0:
        raise ValueError("timeout_seconds must be finite and positive")
    kwargs: dict[str, Any] = {
        "cwd": str(Path(cwd).resolve()),
        "stdin": subprocess.DEVNULL,
        "stdout": subprocess.DEVNULL,
        "stderr": subprocess.DEVNULL,
    }
    if os.name == "nt":
        kwargs["creationflags"] = getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)
    else:
        # Makes the child's PID its own process-group ID so descendants can be killed.
        kwargs["start_new_session"] = True

    process = subprocess.Popen(list(command), **kwargs)
    try:
        return process.wait(timeout=timeout)
    except subprocess.TimeoutExpired as exc:
        _terminate_process_tree(process)
        raise ExperimentTimeoutError(
            f"Experiment worker exceeded {timeout:g}s and was terminated."
        ) from exc


def _json_default(value: Any) -> Any:
    if hasattr(value, "item"):
        return value.item()
    if isinstance(value, Path):
        return str(value)
    raise TypeError(f"Unsupported result value: {type(value).__name__}")


def _worker_main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--request", required=True)
    parser.add_argument("--result", required=True)
    args = parser.parse_args(argv)
    result_path = Path(args.result)
    try:
        request = json.loads(Path(args.request).read_text(encoding="utf-8"))
        from ..pipeline.experiments import run_detection

        config = AppConfig.model_validate(request["config"])
        run = run_detection(
            request["csv_path"],
            request["dataset"],
            config,
            seed=int(request["seed"]),
            detector=request["detector"],
        )
        payload = {"ok": True, "run": asdict(run)}
    except Exception as exc:
        payload = {
            "ok": False,
            "error_type": type(exc).__name__,
            "error": str(exc)[:2000],
        }

    try:
        serialized = json.dumps(payload, allow_nan=False, default=_json_default)
    except Exception as exc:
        serialized = json.dumps({
            "ok": False,
            "error_type": type(exc).__name__,
            "error": "Worker result was not finite JSON-serializable output.",
        })
        payload = {"ok": False}
    temporary_result = result_path.with_suffix(result_path.suffix + ".tmp")
    temporary_result.write_text(serialized + "\n", encoding="utf-8")
    temporary_result.replace(result_path)
    return 0 if payload.get("ok") else 1


def run_detection_with_timeout(
    csv_path: str | Path,
    dataset: str,
    config: AppConfig,
    *,
    seed: int,
    detector: str,
    timeout_seconds: float,
    project_root: str | Path | None = None,
):
    """Run detector evaluation in a child process with an enforced deadline."""
    timeout = float(timeout_seconds)
    if not math.isfinite(timeout) or timeout <= 0:
        raise ValueError("timeout_seconds must be finite and positive")
    config_payload = config.model_dump(mode="json") if isinstance(config, AppConfig) else dict(config)
    request_payload = {
        "csv_path": str(Path(csv_path).resolve()),
        "dataset": str(dataset),
        "config": config_payload,
        "seed": int(seed),
        "detector": str(detector),
    }
    cwd = Path(project_root).resolve() if project_root is not None else Path.cwd().resolve()

    with tempfile.TemporaryDirectory(prefix="xaita-experiment-") as temporary:
        temp = Path(temporary)
        request_path = temp / "request.json"
        result_path = temp / "result.json"
        request_path.write_text(
            json.dumps(request_payload, sort_keys=True, allow_nan=False) + "\n",
            encoding="utf-8",
        )
        command = [
            sys.executable,
            "-m",
            "xaita_ot.operations.experiment_worker",
            "--request",
            str(request_path),
            "--result",
            str(result_path),
        ]
        return_code = _run_process_with_timeout(
            command, timeout_seconds=timeout, cwd=cwd
        )
        if not result_path.is_file():
            raise ExperimentWorkerError(
                "WorkerProcessError",
                f"Experiment worker exited with code {return_code} without a result.",
            )
        try:
            result = json.loads(result_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise ExperimentWorkerError(
                "WorkerProtocolError", "Experiment worker produced an unreadable result."
            ) from exc
        if not result.get("ok"):
            raise ExperimentWorkerError(
                result.get("error_type", "ExperimentWorkerError"),
                result.get("error", "Experiment worker failed."),
            )
        if return_code != 0:
            raise ExperimentWorkerError(
                "WorkerProcessError",
                f"Experiment worker exited with code {return_code}.",
            )
        return SimpleNamespace(**result["run"])


if __name__ == "__main__":
    raise SystemExit(_worker_main())
