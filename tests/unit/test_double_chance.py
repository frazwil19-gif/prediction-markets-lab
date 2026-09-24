import numpy as np
import pytest

from prediction_markets_lab.research.double_chance import best_selection, dc_outcomes, dc_probabilities


def test_dc_probabilities_and_outcomes() -> None:
    p = np.array([[0.6, 0.25, 0.15], [0.2, 0.3, 0.5]])
    dc = dc_probabilities(p)
    assert np.allclose(dc, [[0.85, 0.40, 0.75], [0.5, 0.8, 0.7]])
    assert np.allclose(dc.sum(1), 2.0)          # each outcome is covered by exactly two DC events
    w = dc_outcomes(np.array([0, 1, 2]))
    assert w.tolist() == [[1, 0, 1], [1, 1, 0], [0, 1, 1]]


def test_best_selection_floor_and_ties() -> None:
    i, pb = best_selection(dc_probabilities(np.array([[1 / 3, 1 / 3, 1 / 3], [0.1, 0.1, 0.8]])))
    assert i.tolist() == [0, 1] and pb[0] == pytest.approx(2 / 3) and pb[1] == pytest.approx(0.9)


def test_validation_errors() -> None:
    with pytest.raises(ValueError):
        dc_probabilities(np.array([[0.5, 0.5, 0.5]]))
    with pytest.raises(ValueError):
        dc_probabilities(np.array([0.5, 0.5]))
    with pytest.raises(ValueError):
        dc_outcomes(np.array([3]))
