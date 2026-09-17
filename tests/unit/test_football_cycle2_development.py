"""Tests for football_cycle2_development.py (H-FB2-001/H-FB2-002 support).

Settlement-function cases are hand-verified against real-world Asian
Handicap convention, matching the discovery-phase script's own
hand-traced cases (see FOOTBALL_CYCLE_2_DISCOVERY_CHECKPOINT.md).
"""

from __future__ import annotations

import pytest

from prediction_markets_lab.research.football_cycle2_development import (
    FavouritePerspective,
    bootstrap_ci_mean,
    favourite_perspective,
    settle_asian_handicap_home,
    settle_half_line_home,
)


def test_settle_half_line_home_win_loss_push():
    assert settle_half_line_home(margin=2, line=-1.0) == 1.0  # home wins by 2, -1 line -> covers
    assert settle_half_line_home(margin=0, line=-1.0) == 0.0  # draw, -1 line -> home loses
    assert settle_half_line_home(margin=1, line=-1.0) == 0.5  # exact push
    assert settle_half_line_home(margin=-1, line=0.5) == 0.0  # home loses by 1, +0.5 -> away covers


def test_settle_asian_handicap_home_quarter_line_half_result():
    # -0.25 line, draw (margin=0): "half lost" for home backers (matches
    # real-world convention, hand-verified in the discovery checkpoint).
    result = settle_asian_handicap_home(margin=0, line=-0.25)
    assert result == 0.25


def test_settle_asian_handicap_home_quarter_line_clean_win():
    # -0.25 line, home wins by 2: both neighbouring half-lines (0 and
    # -0.5) settle as a clean home win -> 1.0, not a quarter-result.
    result = settle_asian_handicap_home(margin=2, line=-0.25)
    assert result == 1.0


def test_settle_asian_handicap_home_whole_line_matches_half_line():
    assert settle_asian_handicap_home(margin=3, line=-1.0) == settle_half_line_home(3, -1.0)


def test_favourite_perspective_home_favourite_passes_through_unchanged():
    fp = favourite_perspective(
        favourite_side="home",
        ah_home_probability=0.6,
        ah_away_probability=0.4,
        home_result_fraction=1.0,
    )
    assert fp.favourite_cover_probability == 0.6
    assert fp.favourite_result_fraction == 1.0
    assert fp.is_clean is True
    assert fp.favourite_covers is True


def test_favourite_perspective_away_favourite_flips_home_framing():
    # Away is the favourite; home settlement fraction of 0.0 (away
    # covers) must become favourite_covers=True from the away
    # favourite's own perspective, using the AWAY fair probability.
    fp = favourite_perspective(
        favourite_side="away",
        ah_home_probability=0.35,
        ah_away_probability=0.65,
        home_result_fraction=0.0,
    )
    assert fp.favourite_cover_probability == 0.65
    assert fp.favourite_result_fraction == 1.0
    assert fp.favourite_covers is True


def test_favourite_perspective_push_is_not_clean_either_side():
    fp_home = favourite_perspective("home", 0.55, 0.45, 0.5)
    fp_away = favourite_perspective("away", 0.55, 0.45, 0.5)
    assert fp_home.is_clean is False
    assert fp_away.is_clean is False
    assert fp_home.favourite_covers is None
    assert fp_away.favourite_covers is None


def test_favourite_perspective_quarter_result_is_not_clean():
    fp = favourite_perspective("home", 0.6, 0.4, 0.25)
    assert fp.is_clean is False
    assert fp.favourite_covers is None


def test_favourite_perspective_rejects_invalid_side():
    with pytest.raises(ValueError):
        favourite_perspective("draw", 0.5, 0.5, 1.0)


def test_bootstrap_ci_mean_constant_values_has_zero_width_ci():
    ci = bootstrap_ci_mean([0.1, 0.1, 0.1, 0.1], seed=42)
    assert ci["point_estimate"] == pytest.approx(0.1)
    assert ci["ci_lower"] == pytest.approx(0.1)
    assert ci["ci_upper"] == pytest.approx(0.1)


def test_bootstrap_ci_mean_rejects_empty():
    with pytest.raises(ValueError):
        bootstrap_ci_mean([])


def test_bootstrap_ci_mean_is_deterministic_given_seed():
    values = [0.0, 1.0, 0.0, 1.0, 1.0, 0.0, 1.0, 0.0]
    ci1 = bootstrap_ci_mean(values, seed=42)
    ci2 = bootstrap_ci_mean(values, seed=42)
    assert ci1 == ci2


def test_signed_ah_pricing_residual_positive_when_favourites_cover_more_than_implied():
    from prediction_markets_lab.research.football_cycle2_development import (
        signed_ah_pricing_residual,
    )

    # Market implies 0.5 cover probability but favourites actually
    # cover 100% of the time in this synthetic sample -> positive
    # residual (market underprices the favourite covering).
    rows = [
        FavouritePerspective(
            favourite_cover_probability=0.5,
            favourite_result_fraction=1.0,
            is_clean=True,
            favourite_covers=True,
        )
        for _ in range(150)
    ]
    result = signed_ah_pricing_residual(rows)
    assert result["n"] == 150
    assert result["mean_signed_residual"] == pytest.approx(0.5)
    assert result["ci_95"][0] > 0.0


def test_signed_ah_pricing_residual_excludes_pushes_and_quarter_results():
    from prediction_markets_lab.research.football_cycle2_development import (
        signed_ah_pricing_residual,
    )

    clean = FavouritePerspective(0.5, 1.0, True, True)
    push = FavouritePerspective(0.5, 0.5, False, None)
    quarter = FavouritePerspective(0.5, 0.25, False, None)
    result = signed_ah_pricing_residual([clean, push, quarter])
    assert result["n"] == 1


def test_signed_ah_pricing_residual_empty_after_filtering_reports_insufficient_n():
    from prediction_markets_lab.research.football_cycle2_development import (
        signed_ah_pricing_residual,
    )

    push = FavouritePerspective(0.5, 0.5, False, None)
    result = signed_ah_pricing_residual([push])
    assert result == {"n": 0, "status": "insufficient_n"}
