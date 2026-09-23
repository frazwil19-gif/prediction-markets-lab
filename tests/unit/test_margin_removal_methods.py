import math

import pytest

from prediction_markets_lab.probability.margin_removal import margin_free_probabilities_from_odds
from prediction_markets_lab.research import margin_removal_methods as m

BOOKS = [[1.25, 6.0, 12.0], [2.10, 3.40, 3.60], [1.08, 13.0, 34.0], [1.90, 1.90], [1.30, 3.55], [1.02, 21.0]]


@pytest.mark.parametrize("odds", BOOKS)
@pytest.mark.parametrize("method", m.METHODS)
def test_probabilities_valid_and_sum_to_one(odds, method):
    p = m.devig(odds, method)
    assert len(p) == len(odds)
    assert all(0.0 <= x <= 1.0 for x in p)
    assert sum(p) == pytest.approx(1.0, abs=1e-9)


@pytest.mark.parametrize("odds", BOOKS)
def test_multiplicative_equals_production_proportional(odds):
    assert m.multiplicative(odds) == pytest.approx(margin_free_probabilities_from_odds(odds), abs=1e-12)


@pytest.mark.parametrize("method", m.METHODS)
def test_fair_book_is_left_unchanged(method):
    odds = [2.0, 4.0, 4.0]  # implied sums to exactly 1
    assert m.devig(odds, method) == pytest.approx([0.5, 0.25, 0.25], abs=1e-9)


@pytest.mark.parametrize("method", m.METHODS)
def test_order_preserved(method):
    p = m.devig([1.25, 6.0, 12.0], method)
    assert p[0] > p[1] > p[2]


def test_favourite_ordering_across_methods_known_direction():
    # With a positive margin, power/shin/odds-ratio shift more margin onto longshots than
    # multiplicative does, so they give the favourite a HIGHER probability.
    odds = [1.25, 6.0, 12.0]
    mult = m.multiplicative(odds)[0]
    for method in ("power", "shin", "odds_ratio", "additive"):
        assert m.devig(odds, method)[0] > mult


def test_power_solution_exact():
    q = [1 / 1.25, 1 / 6.0, 1 / 12.0]
    p = m.power([1.25, 6.0, 12.0])
    k = math.log(p[0]) / math.log(q[0])
    assert [x ** k for x in q] == pytest.approx(p, abs=1e-9)


def test_binary_under_round_book_handled():
    # exchange last-traded prices can imply a book slightly BELOW 100%
    for method in m.METHODS:
        p = m.devig([1.30, 4.50], method)
        assert sum(p) == pytest.approx(1.0) and p[0] > p[1]


def test_additive_clips_negative_longshot():
    p = m.additive([1.01, 30.0, 60.0])
    assert min(p) >= 0.0 and sum(p) == pytest.approx(1.0)


@pytest.mark.parametrize("bad", [[1.0, 2.0], [0.5, 3.0], [2.0], [float("nan"), 2.0], [None, 2.0]])
def test_invalid_odds_rejected(bad):
    with pytest.raises(ValueError):
        m.devig(bad, "power")


def test_unknown_method_rejected():
    with pytest.raises(ValueError):
        m.devig([2.0, 2.0], "magic")


def test_consensus_mean_and_determinism():
    books = [[1.25, 6.0, 12.0], [1.30, 5.5, 11.0]]
    c = m.consensus(books, "shin")
    assert sum(c) == pytest.approx(1.0)
    assert c == m.consensus(books, "shin")
    with pytest.raises(ValueError):
        m.consensus([[1.5, 3.0], [1.5, 3.0, 5.0]], "power")
    with pytest.raises(ValueError):
        m.consensus([], "power")
