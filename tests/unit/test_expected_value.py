import pytest

from prediction_markets_lab.ev.expected_value import (
    break_even_probability,
    edge_relative_to_market,
    evaluate,
    gross_expected_value,
    net_expected_value,
    probability_edge,
)


def test_gross_expected_value_positive_edge():
    # True probability 0.55 at odds 2.10 (implied 0.476) is +EV gross.
    ev = gross_expected_value(0.55, 2.10)
    assert ev > 0


def test_gross_expected_value_matches_hand_calculation():
    # p=0.5, O=2.0 -> fair price, gross EV should be 0.
    ev = gross_expected_value(0.5, 2.0)
    assert ev == pytest.approx(0.0)


def test_net_expected_value_lower_than_gross_with_commission():
    p, odds = 0.55, 2.10
    gross = gross_expected_value(p, odds)
    net = net_expected_value(p, odds, commission=0.02)
    assert net < gross


def test_net_expected_value_matches_hand_calculation():
    # p=0.6, O=2.5, c=0.05
    # EV = 0.6*(1.5)*(0.95) - 0.4 = 0.855 - 0.4 = 0.455
    net = net_expected_value(0.6, 2.5, 0.05)
    assert net == pytest.approx(0.455, abs=1e-9)


def test_expected_value_rejects_invalid_probability():
    with pytest.raises(ValueError):
        gross_expected_value(0.0, 2.0)
    with pytest.raises(ValueError):
        gross_expected_value(1.0, 2.0)


def test_expected_value_rejects_invalid_odds():
    with pytest.raises(ValueError):
        gross_expected_value(0.5, 1.0)


def test_net_expected_value_rejects_invalid_commission():
    with pytest.raises(ValueError):
        net_expected_value(0.5, 2.0, commission=1.0)
    with pytest.raises(ValueError):
        net_expected_value(0.5, 2.0, commission=-0.01)


def test_break_even_probability_matches_zero_net_ev():
    odds, commission = 2.5, 0.02
    p_break_even = break_even_probability(odds, commission)
    ev_at_break_even = net_expected_value(p_break_even, odds, commission)
    assert ev_at_break_even == pytest.approx(0.0, abs=1e-9)


def test_probability_edge_positive_when_estimate_above_market():
    edge = probability_edge(0.55, 0.476)
    assert edge == pytest.approx((0.55 - 0.476) * 100.0)


def test_edge_relative_to_market():
    relative = edge_relative_to_market(0.55, 0.50)
    assert relative == pytest.approx(0.10)


def test_edge_relative_to_market_rejects_zero_market_probability():
    with pytest.raises(ValueError):
        edge_relative_to_market(0.5, 0.0)


def test_evaluate_full_breakdown_internally_consistent():
    result = evaluate(probability=0.55, decimal_odds=2.10, commission=0.02)
    assert result.exchange_implied_probability == pytest.approx(1.0 / 2.10)
    assert result.net_ev == pytest.approx(
        net_expected_value(0.55, 2.10, 0.02)
    )
    assert result.expected_roi == pytest.approx(result.net_ev * 100.0)
    assert result.probability_edge_pp == pytest.approx(
        probability_edge(0.55, result.exchange_implied_probability)
    )


def test_distinct_quantities_are_not_conflated():
    # Sanity check that gross EV, net EV and expected ROI are not
    # accidentally identical/aliased for a case where they should differ.
    result = evaluate(probability=0.6, decimal_odds=2.5, commission=0.05)
    assert result.gross_ev != result.net_ev
    assert result.expected_roi == pytest.approx(result.net_ev * 100.0)
