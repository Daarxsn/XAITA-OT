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
