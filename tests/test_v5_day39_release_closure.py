from pathlib import Path

from scripts.v5_day39_release_closure import evaluate


def test_day39_release_closure_passes_on_repository_root():
    result = evaluate(Path(__file__).resolve().parents[1])
    assert result["status"] == "pass", result
    assert all(result["checks"].values())
