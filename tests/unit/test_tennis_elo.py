"""Tests for prediction_markets_lab.models.tennis_elo -- the leakage-safe
Elo model backing Workstream A4's global and surface Elo baselines.

Mirrors the hand-verified rigor of tests/unit/test_football_elo.py, adapted
for tennis's binary (no-draw) outcome and the pluggable rating_key design
that lets ONE rating engine serve both global and surface-specific Elo.
"""
import math
from datetime import date

import pytest

from prediction_markets_lab.models.tennis_elo import (
    EloConfig,
    EloRatingBook,
    calibrate_k_factor,
    global_rating_key,
    run_elo_over_matches,
    simulate_pre_match_ratings,
    surface_rating_key,
)
from prediction_markets_lab.models.tennis_elo import EloMatchInput


def _match(match_id, d, surface, player_a, player_b, outcome_a_won):
    return EloMatchInput(match_id, d, surface, player_a, player_b, outcome_a_won)


def test_config_rejects_non_positive_k_factor():
    with pytest.raises(ValueError):
        EloConfig(k_factor=0)


def test_global_rating_key_ignores_surface():
    assert global_rating_key("player1", "hard") == global_rating_key("player1", "clay")
    assert global_rating_key("player1", "hard") == "player1"


def test_surface_rating_key_distinguishes_surfaces():
    key_hard = surface_rating_key("player1", "hard")
    key_clay = surface_rating_key("player1", "clay")
    assert key_hard != key_clay
    assert key_hard == ("player1", "hard")


def test_rating_book_get_rating_defaults_to_initial_rating():
    book = EloRatingBook(EloConfig(initial_rating=1500.0), global_rating_key)
    assert book.get_rating("nobody", "hard") == 1500.0


def test_rating_book_update_moves_winner_up_and_loser_down():
    book = EloRatingBook(EloConfig(), global_rating_key)
    before_a = book.get_rating("A", "hard")
    before_b = book.get_rating("B", "hard")
    book.update("A", "B", "hard", 1)
    assert book.get_rating("A", "hard") > before_a
    assert book.get_rating("B", "hard") < before_b


def test_rating_book_update_is_zero_sum():
    book = EloRatingBook(EloConfig(), global_rating_key)
    book.ratings[global_rating_key("A", "hard")] = 1600.0
    book.ratings[global_rating_key("B", "hard")] = 1500.0
    before_total = book.get_rating("A", "hard") + book.get_rating("B", "hard")
    book.update("A", "B", "hard", 0)
    after_total = book.get_rating("A", "hard") + book.get_rating("B", "hard")
    assert math.isclose(before_total, after_total, abs_tol=1e-9)


def test_rating_book_rejects_invalid_outcome():
    book = EloRatingBook(EloConfig(), global_rating_key)
    with pytest.raises(ValueError):
        book.update("A", "B", "hard", 2)


def test_rating_book_update_exact_delta_with_equal_ratings():
    # Equal pre-match ratings -> e_a = 0.5 exactly, so for the default
    # k_factor=32 a win moves the winner up by k*(1-0.5)=16 points and
    # the loser down by the same amount -- hand-computed, not just
    # "moved in the right direction."
    config = EloConfig(initial_rating=1500.0, k_factor=32.0)
    book = EloRatingBook(config, global_rating_key)
    book.update("A", "B", "hard", 1)
    assert book.get_rating("A", "hard") == pytest.approx(1516.0)
    assert book.get_rating("B", "hard") == pytest.approx(1484.0)


def test_global_book_updates_from_every_surface_and_shares_one_rating():
    book = EloRatingBook(EloConfig(), global_rating_key)
    book.update("A", "B", "hard", 1)
    rating_after_hard = book.get_rating("A", "hard")
    book.update("A", "C", "clay", 1)
    # A single global rating -- looked up via either surface label -- must
    # have moved again after the clay-court match.
    assert book.get_rating("A", "clay") != rating_after_hard
    assert book.get_rating("A", "hard") == book.get_rating("A", "clay")


def test_surface_book_isolates_ratings_per_surface():
    book = EloRatingBook(EloConfig(), surface_rating_key)
    book.update("A", "B", "hard", 1)
    assert book.get_rating("A", "hard") > EloConfig().initial_rating
    # A's clay rating must be completely untouched by the hard-court win.
    assert book.get_rating("A", "clay") == EloConfig().initial_rating


def test_simulate_pre_match_ratings_first_match_uses_initial_rating():
    matches = [_match("m1", date(2020, 1, 1), "hard", "A", "B", 1)]
    simulated = simulate_pre_match_ratings(matches, EloConfig(initial_rating=1500.0), global_rating_key)
    _, pre_a, pre_b = simulated[0]
    assert pre_a == 1500.0
    assert pre_b == 1500.0


def test_simulate_pre_match_ratings_rejects_out_of_order_matches():
    matches = [
        _match("m1", date(2020, 1, 15), "hard", "A", "B", 1),
        _match("m2", date(2020, 1, 1), "hard", "C", "D", 0),
    ]
    with pytest.raises(ValueError, match="chronologically"):
        simulate_pre_match_ratings(matches, EloConfig(), global_rating_key)


def test_simulate_pre_match_ratings_rejects_empty_input():
    with pytest.raises(ValueError):
        simulate_pre_match_ratings([], EloConfig(), global_rating_key)


def test_leakage_a_later_result_never_changes_an_earlier_pre_match_rating():
    base = [
        _match("m1", date(2020, 1, 1), "hard", "A", "B", 1),
        _match("m2", date(2020, 1, 8), "hard", "A", "C", 1),
        _match("m3", date(2020, 1, 15), "hard", "A", "D", 1),
    ]
    altered = [
        _match("m1", date(2020, 1, 1), "hard", "A", "B", 1),
        _match("m2", date(2020, 1, 8), "hard", "A", "C", 1),
        _match("m3", date(2020, 1, 15), "hard", "A", "D", 0),  # changed, last match only
    ]
    base_sim = simulate_pre_match_ratings(base, EloConfig(), global_rating_key)
    altered_sim = simulate_pre_match_ratings(altered, EloConfig(), global_rating_key)
    # m1 and m2's pre-match ratings must be identical regardless of m3's result.
    assert base_sim[0][1:] == altered_sim[0][1:]
    assert base_sim[1][1:] == altered_sim[1][1:]


def test_run_elo_over_matches_hand_verified_first_and_second_match():
    matches = [
        _match("m1", date(2020, 1, 1), "hard", "A", "B", 1),
        _match("m2", date(2020, 1, 8), "hard", "A", "B", 0),
    ]
    config = EloConfig(initial_rating=1500.0, k_factor=32.0)
    preds = run_elo_over_matches(matches, config, global_rating_key)

    assert preds[0].pre_match_a_rating == 1500.0
    assert preds[0].pre_match_b_rating == 1500.0
    assert preds[0].p_a_win == pytest.approx(0.5)

    # After m1 (A won 1500-vs-1500), delta = 32*(1-0.5) = 16 -> A=1516, B=1484.
    assert preds[1].pre_match_a_rating == pytest.approx(1516.0)
    assert preds[1].pre_match_b_rating == pytest.approx(1484.0)
    expected_p2 = 1.0 / (1.0 + 10.0 ** (-(1516.0 - 1484.0) / 400.0))
    assert preds[1].p_a_win == pytest.approx(expected_p2)


def test_run_elo_over_matches_produces_probabilities_in_unit_interval():
    matches = [
        _match("m1", date(2020, 1, 1), "hard", "A", "B", 1),
        _match("m2", date(2020, 1, 8), "clay", "B", "A", 0),
        _match("m3", date(2020, 1, 15), "hard", "A", "C", 1),
    ]
    preds = run_elo_over_matches(matches, EloConfig(), global_rating_key)
    assert len(preds) == 3
    for p in preds:
        assert 0.0 <= p.p_a_win <= 1.0


def test_run_elo_over_matches_with_surface_key_keeps_surfaces_independent():
    matches = [
        _match("m1", date(2020, 1, 1), "clay", "A", "B", 1),  # A beats B on clay
        _match("m2", date(2020, 1, 8), "hard", "A", "B", 1),  # first-ever hard meeting
    ]
    preds = run_elo_over_matches(matches, EloConfig(), surface_rating_key)
    # m2 is on a surface neither player has a rating history on yet, so
    # despite A's clay win in m1 its surface-specific pre-match ratings
    # for m2 must still be at parity.
    assert preds[1].pre_match_a_rating == pytest.approx(1500.0)
    assert preds[1].pre_match_b_rating == pytest.approx(1500.0)
    assert preds[1].p_a_win == pytest.approx(0.5)


def test_calibrate_k_factor_rejects_empty_candidates():
    matches = [_match("m1", date(2020, 1, 1), "hard", "A", "B", 1)]
    with pytest.raises(ValueError):
        calibrate_k_factor(matches, EloConfig(), [], global_rating_key)


def test_calibrate_k_factor_rejects_non_positive_candidates():
    matches = [_match("m1", date(2020, 1, 1), "hard", "A", "B", 1)]
    with pytest.raises(ValueError):
        calibrate_k_factor(matches, EloConfig(), [-10.0, 32.0], global_rating_key)


def test_calibrate_k_factor_returns_first_candidate_when_tied_on_a_single_match():
    # With only one match, every player starts at the initial rating
    # regardless of k_factor, so every candidate predicts p_a_win=0.5 and
    # has identical log loss -- calibrate_k_factor's "loss < best" (strict)
    # comparison must then keep the first candidate in the list, not the
    # last, since no later candidate strictly improves on the tie.
    matches = [_match("m1", date(2020, 1, 1), "hard", "A", "B", 1)]
    candidates = [16.0, 32.0, 64.0]
    chosen = calibrate_k_factor(matches, EloConfig(), candidates, global_rating_key)
    assert chosen == candidates[0]


def test_calibrate_k_factor_prefers_higher_k_when_it_improves_confidence_correctly():
    # A beats the same opponent B twice. After match 1 (equal pre-match
    # ratings), A's rating pulls ahead by exactly k_factor points
    # (delta = k*(1-0.5)=0.5k each way -> gap = k). Match 2's predicted
    # p_a_win is then the logistic curve at that gap, which strictly
    # increases with k_factor -- and since A wins match 2 as well, a
    # larger k_factor is strictly more confident AND correct, so it must
    # have the lowest training log loss of any candidate here.
    matches = [
        _match("m1", date(2020, 1, 1), "hard", "A", "B", 1),
        _match("m2", date(2020, 1, 8), "hard", "A", "B", 1),
    ]
    candidates = [8.0, 32.0, 128.0]
    chosen = calibrate_k_factor(matches, EloConfig(), candidates, global_rating_key)
    assert chosen == max(candidates)
