import math
from datetime import date

import pytest

from prediction_markets_lab.models.football_poisson import (
    PoissonConfig,
    PoissonMatchInput,
    PoissonRatingBook,
    run_poisson_over_matches,
    scoreline_probabilities_to_1x2,
    simulate_pre_match_lambdas,
)


def _match(match_id, comp, d, home, away, hg, ag, result):
    return PoissonMatchInput(match_id, "2020_21", d, comp, home, away, hg, ag, result)


def test_config_rejects_bad_max_goals():
    with pytest.raises(ValueError):
        PoissonConfig(max_goals=0)


def test_config_rejects_negative_shrinkage():
    with pytest.raises(ValueError):
        PoissonConfig(shrinkage_matches=-1)


def test_config_rejects_non_positive_default_averages():
    with pytest.raises(ValueError):
        PoissonConfig(default_league_avg_home_goals=0)


def test_scoreline_probabilities_sum_to_one():
    for lh, la in [(1.5, 1.1), (0.3, 3.0), (2.8, 2.8)]:
        probs = scoreline_probabilities_to_1x2(lh, la, max_goals=10)
        assert math.isclose(sum(probs.values()), 1.0, abs_tol=1e-9)


def test_scoreline_probabilities_never_negative():
    probs = scoreline_probabilities_to_1x2(1.5, 1.1, max_goals=10)
    assert all(p >= 0 for p in probs.values())


def test_scoreline_probabilities_higher_home_lambda_favours_home():
    probs = scoreline_probabilities_to_1x2(2.5, 0.8, max_goals=10)
    assert probs["home"] > probs["away"]


def test_scoreline_probabilities_equal_lambdas_are_symmetric():
    probs = scoreline_probabilities_to_1x2(1.5, 1.5, max_goals=10)
    assert probs["home"] == pytest.approx(probs["away"], abs=1e-9)


def test_truncation_error_is_negligible_for_realistic_lambdas():
    # Sum of untruncated (pre-renormalisation) mass must be extremely
    # close to 1.0 for any realistic football-scoring lambda, including
    # an unusually one-sided fixture -- if it weren't, renormalising
    # would be hiding a real truncation problem rather than a
    # floating-point rounding one. This directly measures the
    # truncation tolerance rather than assuming it (see PoissonConfig
    # docstring for the max_goals=15 choice this motivated).
    import math as _math

    def pmf(k, lam):
        return _math.exp(-lam) * lam**k / _math.factorial(k)

    for lh, la in [(1.5, 1.1), (3.5, 0.5), (4.0, 4.0)]:
        max_goals = PoissonConfig().max_goals
        total = sum(
            pmf(x, lh) * pmf(y, la) for x in range(max_goals + 1) for y in range(max_goals + 1)
        )
        assert total > 0.99998, f"truncated mass {total} too far from 1.0 for lambda=({lh},{la})"


def test_rating_book_league_averages_use_defaults_before_any_matches():
    config = PoissonConfig(default_league_avg_home_goals=1.5, default_league_avg_away_goals=1.1)
    book = PoissonRatingBook(config)
    avg_home, avg_away = book.league_averages("E0")
    assert avg_home == 1.5
    assert avg_away == 1.1


def test_rating_book_unobserved_team_gets_average_ratio():
    config = PoissonConfig(default_league_avg_home_goals=1.5, default_league_avg_away_goals=1.1)
    book = PoissonRatingBook(config)
    lambda_home, lambda_away = book.predict("E0", "NewTeamA", "NewTeamB")
    # Both teams unobserved -> shrunk ratios are exactly 1.0 -> lambdas equal league averages.
    assert lambda_home == pytest.approx(1.5)
    assert lambda_away == pytest.approx(1.1)


def test_rating_book_update_then_predict_shifts_lambda_toward_observed_scoring():
    config = PoissonConfig(shrinkage_matches=1.0)
    book = PoissonRatingBook(config)
    # Establish a modest league baseline from OTHER teams first, so the
    # league average is not trivially defined by BigTeam alone.
    for _ in range(10):
        book.update("E0", "MidTeamA", "MidTeamB", home_goals=1, away_goals=1)
    # BigTeam then scores far above that established baseline, repeatedly.
    for _ in range(5):
        book.update("E0", "BigTeam", "SmallTeam", home_goals=4, away_goals=0)
    lambda_home, _ = book.predict("E0", "BigTeam", "AnotherTeam")
    avg_home, _ = book.league_averages("E0")
    assert lambda_home > avg_home


def test_simulate_pre_match_lambdas_rejects_out_of_order_matches():
    matches = [
        _match("m1", "E0", date(2020, 8, 15), "A", "B", 1, 1, "D"),
        _match("m2", "E0", date(2020, 8, 1), "C", "D", 2, 0, "H"),
    ]
    with pytest.raises(ValueError, match="chronologically"):
        simulate_pre_match_lambdas(matches, PoissonConfig())


def test_simulate_pre_match_lambdas_rejects_empty_input():
    with pytest.raises(ValueError):
        simulate_pre_match_lambdas([], PoissonConfig())


def test_simulate_pre_match_lambdas_rejects_invalid_result():
    matches = [_match("m1", "E0", date(2020, 8, 1), "A", "B", 1, 1, "X")]
    with pytest.raises(ValueError):
        simulate_pre_match_lambdas(matches, PoissonConfig())


def test_leakage_a_later_result_never_changes_an_earlier_pre_match_lambda():
    base = [
        _match("m1", "E0", date(2020, 8, 1), "Arsenal", "Chelsea", 2, 1, "H"),
        _match("m2", "E0", date(2020, 8, 8), "Arsenal", "Everton", 3, 0, "H"),
        _match("m3", "E0", date(2020, 8, 15), "Arsenal", "Fulham", 1, 1, "D"),
    ]
    altered = [
        _match("m1", "E0", date(2020, 8, 1), "Arsenal", "Chelsea", 2, 1, "H"),
        _match("m2", "E0", date(2020, 8, 8), "Arsenal", "Everton", 3, 0, "H"),
        _match("m3", "E0", date(2020, 8, 15), "Arsenal", "Fulham", 0, 4, "A"),  # changed, last match
    ]
    base_sim = simulate_pre_match_lambdas(base, PoissonConfig())
    altered_sim = simulate_pre_match_lambdas(altered, PoissonConfig())
    assert base_sim[0][1:] == altered_sim[0][1:]
    assert base_sim[1][1:] == altered_sim[1][1:]


def test_competitions_tracked_independently():
    config = PoissonConfig()
    book = PoissonRatingBook(config)
    book.update("E0", "TeamA", "TeamB", home_goals=5, away_goals=0)
    # SC0's averages/team ratios must be untouched by E0 activity.
    avg_home_sc0, avg_away_sc0 = book.league_averages("SC0")
    assert avg_home_sc0 == config.default_league_avg_home_goals
    assert avg_away_sc0 == config.default_league_avg_away_goals


def test_run_poisson_over_matches_produces_valid_probabilities():
    matches = [
        _match("m1", "E0", date(2020, 8, 1), "Arsenal", "Chelsea", 2, 1, "H"),
        _match("m2", "E0", date(2020, 8, 8), "Chelsea", "Arsenal", 0, 0, "D"),
        _match("m3", "E0", date(2020, 8, 15), "Arsenal", "Everton", 0, 3, "A"),
    ]
    preds = run_poisson_over_matches(matches, PoissonConfig())
    assert len(preds) == 3
    for p in preds:
        total = p.p_home + p.p_draw + p.p_away
        assert math.isclose(total, 1.0, abs_tol=1e-9)
        assert p.p_home >= 0 and p.p_draw >= 0 and p.p_away >= 0
        assert p.lambda_home > 0 and p.lambda_away > 0
