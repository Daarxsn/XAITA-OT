import numpy as np
import pytest

from xaita_ot.explain.fidelity import (
    explanation_stability,
    perturbation_fidelity,
    validate_fidelity_score,
    validate_stability_score,
)


def test_perturbation_fidelity_is_finite_and_non_negative():
    X = np.ones((2, 2, 2), dtype=np.float32)

    def predict(value):
        return value[:, :, 0].mean(axis=1)

    score = perturbation_fidelity(
        predict, X, [{"index": 0, "importance": 1.0}], top_k=1, baseline=0.0
    )
    assert score == 1.0
    assert validate_fidelity_score(score) == score


def test_stability_is_bounded():
    score = explanation_stability([1, 0], [1, 0])
    assert score == 1.0
    assert validate_stability_score(score) == 1.0


@pytest.mark.parametrize("score", [-1.0, float("nan"), float("inf")])
def test_fidelity_rejects_invalid_scores(score):
    with pytest.raises(ValueError):
        validate_fidelity_score(score)


@pytest.mark.parametrize("score", [-1.1, 1.1, float("nan"), float("inf")])
def test_stability_rejects_invalid_scores(score):
    with pytest.raises(ValueError):
        validate_stability_score(score)


def test_fidelity_is_deterministic():
    X = np.arange(8, dtype=np.float32).reshape(2, 2, 2)

    def predict(value):
        return value.mean(axis=(1, 2))

    importances = [{"index": 0, "importance": 0.9}, {"index": 1, "importance": 0.1}]
    first = perturbation_fidelity(predict, X, importances, top_k=1)
    second = perturbation_fidelity(predict, X, importances, top_k=1)
    assert first == second
