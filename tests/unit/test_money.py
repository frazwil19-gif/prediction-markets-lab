import pytest

from prediction_markets_lab.utils.money import format_gbp, round_gbp


def test_round_gbp_rounds_to_nearest_penny():
    assert round_gbp(0.2549999) == pytest.approx(0.25)
    assert round_gbp(0.255) == pytest.approx(0.26)


def test_round_gbp_handles_whole_numbers():
    assert round_gbp(10.0) == pytest.approx(10.0)


def test_format_gbp_includes_currency_symbol_and_two_decimals():
    assert format_gbp(0.25) == "£0.25"
    assert format_gbp(10) == "£10.00"
    assert format_gbp(0.2549999) == "£0.25"
