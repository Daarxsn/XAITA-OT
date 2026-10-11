import sys
import time
from pathlib import Path

import pytest

from xaita_ot.operations.experiment_worker import (
    ExperimentTimeoutError,
    _run_process_with_timeout,
)


def test_worker_deadline_terminates_child_process():
    started = time.monotonic()
    with pytest.raises(ExperimentTimeoutError, match="was terminated"):
        _run_process_with_timeout(
            [sys.executable, "-c", "import time; time.sleep(30)"],
            timeout_seconds=0.1,
            cwd=Path(__file__).resolve().parents[1],
        )
    assert time.monotonic() - started < 5



def test_isolated_worker_completes_real_detector_run(tmp_path):
    import pandas as pd

    from xaita_ot.config import AppConfig
    from xaita_ot.operations.experiment_worker import run_detection_with_timeout

    project_root = Path(__file__).resolve().parents[1]
    row_count = 240
    labels = [(index // 20) % 2 for index in range(row_count)]
    csv_path = tmp_path / "worker-smoke.csv"
    pd.DataFrame({
        "timestamp": pd.date_range("2026-01-01", periods=row_count, freq="s"),
        "label": labels,
        "sensor": [index / row_count for index in range(row_count)],
    }).to_csv(csv_path, index=False)

    config = AppConfig()
    config.model.window_size = 4
    run = run_detection_with_timeout(
        csv_path,
        "SWaT",
        config,
        seed=42,
        detector="random_forest",
        timeout_seconds=30,
        project_root=project_root,
    )
    assert run.dataset == "SWaT"
    assert run.seed == 42
    assert run.config["detector"] == "random_forest"
    assert 0.0 <= run.metrics["random_forest"]["f1"] <= 1.0
