import numpy as np
import pandas as pd
import pytest

from xaita_ot.config import AppConfig
from xaita_ot.models.trainer import Detector
from xaita_ot.pipeline.evaluation import (
    binary_metrics,
    chronological_split,
    expected_calibration_error,
    select_threshold,
)
from xaita_ot.pipeline.v3_evaluation import confidence_bins as v3_confidence_bins
from xaita_ot.pipeline.v3_phase3 import confidence_bins as phase3_confidence_bins
from xaita_ot.pipeline.v3_phase4 import _metrics as phase4_metrics
from xaita_ot.pipeline.v3_phase5 import _metrics as phase5_metrics


@pytest.mark.parametrize(
    "call",
    [
        lambda: binary_metrics([0, 0.5, 1], [0.1, 0.4, 0.9]),
        lambda: select_threshold([0, 0.5, 1], [0.1, 0.4, 0.9]),
        lambda: expected_calibration_error([0, 0.5, 1], [0.1, 0.4, 0.9]),
        lambda: v3_confidence_bins([0, 0.5, 1], [0.1, 0.4, 0.9]),
        lambda: phase3_confidence_bins([0, 0.5, 1], [0.1, 0.4, 0.9]),
        lambda: phase4_metrics([0, 0.5, 1], [0.1, 0.4, 0.9]),
        lambda: phase5_metrics([0, 0.5, 1], [0.1, 0.4, 0.9]),
    ],
)
def test_evaluation_rejects_fractional_labels_before_casting(call):
    with pytest.raises(ValueError, match="binary"):
        call()


@pytest.mark.parametrize("labels", [[0, float("nan"), 1], [0, 2, 1], [0, float("inf"), 1]])
def test_evaluation_rejects_nonfinite_or_out_of_range_labels(labels):
    with pytest.raises(ValueError, match="binary"):
        binary_metrics(labels, [0.1, 0.4, 0.9])


@pytest.mark.parametrize("scores", [[-0.1, 0.4, 0.9], [0.1, 1.1, 0.9], [0.1, float("nan"), 0.9]])
def test_metrics_reject_invalid_probability_scores(scores):
    with pytest.raises(ValueError, match="probabilities"):
        binary_metrics([0, 1, 0], scores)


def test_chronological_split_rejects_fractional_labels():
    frame = pd.DataFrame({
        "sensor": np.arange(20, dtype=float),
        "label": [0, 1, 0, 1, 0.5] * 4,
    })
    with pytest.raises(ValueError, match="binary"):
        chronological_split(frame)


def test_neural_detector_evaluate_rejects_fractional_labels():
    detector = Detector(2, AppConfig().model, architecture="lstm")
    features = np.zeros((3, 4, 2), dtype=np.float32)
    with pytest.raises(ValueError, match="binary"):
        detector.evaluate(features, [0, 0.5, 1])
