"""Tests for decisions.liquidity (Daily Engine V1 build, 2026-09-18)."""

from __future__ import annotations

import pytest

from prediction_markets_lab.decisions.liquidity import assess_liquidity


def test_bookmaker_price_with_no_size_figure_is_always_adequate():
    assert assess_liquidity(stake_gbp=0.50, available_size_gbp=None) is True


def test_exchange_price_with_adequate_depth():
    assert assess_liquidity(stake_gbp=0.50, available_size_gbp=10.0) is True


def test_exchange_price_with_inadequate_depth():
    assert assess_liquidity(stake_gbp=5.0, available_size_gbp=1.0) is False


def test_exact_boundary_is_adequate():
    assert assess_liquidity(stake_gbp=2.0, available_size_gbp=2.0) is True


def test_raises_on_non_positive_stake():
    with pytest.raises(ValueError, match="stake_gbp"):
        assess_liquidity(stake_gbp=0.0)


def test_raises_on_negative_available_size():
    with pytest.raises(ValueError, match="available_size_gbp"):
        assess_liquidity(stake_gbp=1.0, available_size_gbp=-1.0)
