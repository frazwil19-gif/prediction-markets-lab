import math
from datetime import date

import pytest

from prediction_markets_lab.models.football_elo import (
    EloConfig,
    EloMatchInput,
    EloRatingBook,
    calibrate_draw_margin,
    run_elo_over_matches,
    simulate_pre_match_ratings,
    three_way_probabilities,
)


def _match(match_id, season, d, home, away, result):
    return EloMatchInput(match_id, season, d, home, away, result)


def test_config_rejects_non_positive_k_factor():
    with pytest.raises(ValueError):
        EloConfig(k_factor=0)


def test_config_rejects_reversion_fraction_out_of_range():
    with pytest.raises(ValueError):
        EloConfig(season_reversion_fraction=1.5)


def test_config_rejects_negative_draw_margin():
    with pytest.raises(ValueError):
        EloConfig(draw_margin=-10)


def test_three_way_probabilities_always_sum_to_one():
    for home_r, away_r in [(1500, 1500), (1800, 1400), (1200, 1650)]:
        probs = three_way_probabilities(home_r, away_r, home_advantage=100, draw_margin=100)
        assert math.isclose(sum(probs.values()), 1.0, abs_tol=1e-9)


def test_three_way_probabilities_never_negative():
    probs = three_way_probabilities(1500, 1500, home_advantage=0, draw_margin=100)
    assert all(p >= 0 for p in probs.values())


def test_three_way_probabilities_equal_ratings_favours_home_via_advantage():
    probs = three_way_probabilities(1500, 1500, home_advantage=100, draw_margin=100)
    assert probs["home"] > probs["away"]


def test_three_way_probabilities_zero_draw_margin_gives_no_draw():
    probs = three_way_probabilities(1600, 1500, home_advantage=0, draw_margin=0)
    assert probs["draw"] == pytest.approx(0.0, abs=1e-12)
    assert math.isclose(probs["home"] + probs["away"], 1.0, abs_tol=1e-9)


def test_three_way_probabilities_rejects_negative_draw_margin():
    with pytest.raises(ValueError):
        three_way_probabilities(1500, 1500, home_advantage=0, draw_margin=-5)


def test_rating_book_update_moves_winner_up_and_loser_down():
    book = EloRatingBook(EloConfig())
    before_home = book.get_rating("Arsenal")
    before_away = book.get_rating("Chelsea")
    book.update("Arsenal", "Chelsea", "H")
    assert book.get_rating("Arsenal") > before_home
    assert book.get_rating("Chelsea") < before_away


def test_rating_book_update_is_zero_sum():
    book = EloRatingBook(EloConfig())
    book.ratings["Arsenal"] = 1600
    book.ratings["Chelsea"] = 1500
    before_total = book.get_rating("Arsenal") + book.get_rating("Chelsea")
    book.update("Arsenal", "Chelsea", "D")
    after_total = book.get_rating("Arsenal") + book.get_rating("Chelsea")
    assert math.isclose(before_total, after_total, abs_tol=1e-9)


def test_rating_book_rejects_invalid_result():
    book = EloRatingBook(EloConfig())
    with pytest.raises(ValueError):
        book.update("A", "B", "X")


def test_season_reversion_pulls_ratings_toward_initial():
    config = EloConfig(initial_rating=1500, season_reversion_fraction=0.25)
    book = EloRatingBook(config)
    book.ratings["Arsenal"] = 1900
    book.apply_season_reversion()
    assert book.get_rating("Arsenal") == pytest.approx(1500 + 0.75 * 400)


def test_simulate_pre_match_ratings_first_match_uses_initial_rating():
    matches = [_match("m1", "2020_21", date(2020, 8, 1), "Arsenal", "Chelsea", "H")]
    simulated = simulate_pre_match_ratings(matches, EloConfig(initial_rating=1500))
    _, pre_home, pre_away = simulated[0]
    assert pre_home == 1500
    assert pre_away == 1500


def test_simulate_pre_match_ratings_rejects_out_of_order_matches():
    matches = [
        _match("m1", "2020_21", date(2020, 8, 15), "A", "B", "H"),
        _match("m2", "2020_21", date(2020, 8, 1), "C", "D", "A"),
    ]
    with pytest.raises(ValueError, match="chronologically"):
        simulate_pre_match_ratings(matches, EloConfig())


def test_simulate_pre_match_ratings_rejects_empty_input():
    with pytest.raises(ValueError):
        simulate_pre_match_ratings([], EloConfig())


def test_leakage_a_later_result_never_changes_an_earlier_pre_match_rating():
    base = [
        _match("m1", "2020_21", date(2020, 8, 1), "Arsenal", "Chelsea", "H"),
        _match("m2", "2020_21", date(2020, 8, 8), "Arsenal", "Everton", "H"),
        _match("m3", "2020_21", date(2020, 8, 15), "Arsenal", "Fulham", "H"),
    ]
    altered = [
        _match("m1", "2020_21", date(2020, 8, 1), "Arsenal", "Chelsea", "H"),
        _match("m2", "2020_21", date(2020, 8, 8), "Arsenal", "Everton", "H"),
        _match("m3", "2020_21", date(2020, 8, 15), "Arsenal", "Fulham", "A"),  # changed, last match
    ]
    base_sim = simulate_pre_match_ratings(base, EloConfig())
    altered_sim = simulate_pre_match_ratings(altered, EloConfig())
    # m1 and m2's pre-match ratings must be identical regardless of m3's result.
    assert base_sim[0][1:] == altered_sim[0][1:]
    assert base_sim[1][1:] == altered_sim[1][1:]


def test_season_reversion_applied_between_seasons_not_mid_season():
    config = EloConfig(initial_rating=1500, k_factor=20, season_reversion_fraction=0.5)
    matches = [
        _match("m1", "2020_21", date(2020, 8, 1), "Arsenal", "Chelsea", "H"),
        _match("m2", "2020_21", date(2020, 8, 8), "Arsenal", "Chelsea", "H"),
        _match("m3", "2021_22", date(2021, 8, 1), "Arsenal", "Chelsea", "H"),
    ]
    simulated = simulate_pre_match_ratings(matches, config)
    # m2 is still within 2020_21 -- must see m1's un-reverted post-match rating.
    rating_after_m1 = EloRatingBook(config)
    rating_after_m1.update("Arsenal", "Chelsea", "H")
    assert simulated[1][1] == pytest.approx(rating_after_m1.get_rating("Arsenal"))

    # Compute what Arsenal's rating is after m1 AND m2 (two home wins), then
    # what a 50% reversion toward 1500 must produce exactly -- m3's pre-match
    # rating must match that precise value, not merely "some other number."
    replay = EloRatingBook(config)
    replay.update("Arsenal", "Chelsea", "H")
    replay.update("Arsenal", "Chelsea", "H")
    rating_after_m2 = replay.get_rating("Arsenal")
    expected_reverted = 0.5 * rating_after_m2 + 0.5 * 1500
    assert simulated[2][1] == pytest.approx(expected_reverted)


def test_run_elo_over_matches_produces_valid_probabilities_for_every_match():
    matches = [
        _match("m1", "2020_21", date(2020, 8, 1), "Arsenal", "Chelsea", "H"),
        _match("m2", "2020_21", date(2020, 8, 8), "Chelsea", "Arsenal", "D"),
        _match("m3", "2020_21", date(2020, 8, 15), "Arsenal", "Everton", "A"),
    ]
    preds = run_elo_over_matches(matches, EloConfig())
    assert len(preds) == 3
    for p in preds:
        total = p.p_home + p.p_draw + p.p_away
        assert math.isclose(total, 1.0, abs_tol=1e-9)
        assert p.p_home >= 0 and p.p_draw >= 0 and p.p_away >= 0


def test_calibrate_draw_margin_picks_a_candidate_from_the_list():
    matches = [
        _match(f"m{i}", "2020_21", date(2020, 8, 1 + i), "Arsenal" if i % 2 == 0 else "Chelsea",
               "Chelsea" if i % 2 == 0 else "Arsenal", ["H", "D", "A"][i % 3])
        for i in range(15)
    ]
    candidates = [50.0, 100.0, 150.0]
    chosen = calibrate_draw_margin(matches, EloConfig(), candidates)
    assert chosen in candidates


def test_calibrate_draw_margin_rejects_empty_candidates():
    matches = [_match("m1", "2020_21", date(2020, 8, 1), "A", "B", "H")]
    with pytest.raises(ValueError):
        calibrate_draw_margin(matches, EloConfig(), [])


def test_calibrate_draw_margin_rejects_negative_candidates():
    matches = [_match("m1", "2020_21", date(2020, 8, 1), "A", "B", "H")]
    with pytest.raises(ValueError):
        calibrate_draw_margin(matches, EloConfig(), [-50.0, 50.0])
