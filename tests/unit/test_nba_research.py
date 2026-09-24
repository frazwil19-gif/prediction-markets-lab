from datetime import date
from pathlib import Path

import pandas as pd
import pytest

from prediction_markets_lab.nba.data import american_to_decimal, sbr_franchise, season_label
from prediction_markets_lab.nba.features import EloParams, elo_probabilities, mov_multiplier, team_state_features


def _games(rows):
    d = pd.DataFrame(rows, columns=["date", "home", "away", "home_score", "away_score"])
    d["season"] = d.date.map(season_label)
    d["neutral"] = False
    return d.sort_values("date").reset_index(drop=True)


def test_season_label_handles_bubble_and_october_start():
    assert season_label(date(2020, 10, 11)) == "2019-20"   # bubble finals
    assert season_label(date(2020, 12, 22)) == "2020-21"
    assert season_label(date(2023, 10, 24)) == "2023-24"
    assert season_label(date(2024, 4, 1)) == "2023-24"


def test_team_identity_and_odds_conversion():
    assert sbr_franchise("Hornets", 2012) == "NOP" and sbr_franchise("Hornets", 2015) == "CHA"
    assert sbr_franchise("NewJersey", 2011) == "BKN" and sbr_franchise("Nobody", 2015) is None
    assert american_to_decimal(-200) == pytest.approx(1.5) and american_to_decimal(150) == pytest.approx(2.5)
    assert american_to_decimal(0) is None


def test_winner_label_and_overtime_scores_valid():
    g = _games([(date(2024, 1, 1), "BOS", "NYK", 120, 118)])  # an OT game is just a higher final score
    assert int(g.home_score[0] > g.away_score[0]) == 1


def test_rest_b2b_and_shifted_rolling():
    g = _games([(date(2024, 1, 1), "BOS", "NYK", 110, 100), (date(2024, 1, 2), "BOS", "MIA", 90, 100),
                (date(2024, 1, 5), "NYK", "BOS", 100, 101)])
    f = team_state_features(g)
    assert f.loc[0, "home_rest"] == 5 and f.loc[0, "home_roll10_pd"] == 0.0  # no history
    assert f.loc[1, "home_b2b"] == 1 and f.loc[1, "home_rest"] == 1 and f.loc[1, "home_roll10_pd"] == 10
    assert f.loc[2, "away_rest"] == 3 and f.loc[2, "away_roll10_pd"] == 0.0  # BOS: +10, -10
    assert f.loc[2, "away_games_7d"] == 2 and f.loc[2, "home_roll10_win"] == 0.0


def test_own_result_never_leaks_into_own_features():
    rows = [(date(2024, 1, d), "BOS", "NYK", 100 + d, 100) for d in range(1, 8, 2)]
    base = team_state_features(_games(rows))
    changed = rows[:-1] + [(date(2024, 1, 7), "BOS", "NYK", 50, 140)]
    alt = team_state_features(_games(changed))
    cols = ["home_roll10_pd", "home_season_pd", "roll10_pd_diff", "home_rest"]
    assert base.iloc[-1][cols].tolist() == alt.iloc[-1][cols].tolist()


def test_elo_chronology_pre_game_and_future_invariance():
    rows = [(date(2024, 1, d), "BOS", "NYK", 110, 100) for d in range(1, 6)]
    g = _games(rows)
    p = elo_probabilities(g, EloParams(k=20, hca=0))
    assert p[0] == pytest.approx(0.5)  # before any result
    assert p[1] > p[0]
    changed = _games(rows[:-1] + [(date(2024, 1, 5), "BOS", "NYK", 80, 130)])
    assert elo_probabilities(changed, EloParams(k=20, hca=0))[:5] == p[:5]  # own result never used pre-game


def test_elo_home_advantage_neutral_and_carryover():
    g = _games([(date(2024, 1, 1), "BOS", "NYK", 100, 90)])
    assert elo_probabilities(g, EloParams(hca=100))[0] > 0.5
    g["neutral"] = True
    assert elo_probabilities(g, EloParams(hca=100))[0] == pytest.approx(0.5)
    two = _games([(date(2024, 3, 1), "BOS", "NYK", 120, 90), (date(2024, 11, 1), "BOS", "NYK", 100, 90)])
    full = elo_probabilities(two, EloParams(k=20, hca=0, carry=1.0))[1]
    shrunk = elo_probabilities(two, EloParams(k=20, hca=0, carry=0.5))[1]
    assert 0.5 < shrunk < full


def test_mov_multiplier_and_sorting_guard():
    assert mov_multiplier(20, 0) > mov_multiplier(2, 0)
    g = _games([(date(2024, 1, 2), "BOS", "NYK", 1, 0), (date(2024, 1, 1), "MIA", "NYK", 1, 0)])
    with pytest.raises(ValueError):
        elo_probabilities(g.iloc[::-1].reset_index(drop=True), EloParams())


def test_probability_complement_and_bounds():
    g = _games([(date(2024, 1, d), "BOS", "NYK", 110, 100) for d in range(1, 30)])
    for p in elo_probabilities(g, EloParams(k=25, hca=100, mov=True)):
        assert 0 < p < 1 and p + (1 - p) == pytest.approx(1.0)


def test_real_source_parsing_if_present():
    raw = Path(__file__).resolve().parents[2] / "data/raw/basketball"
    if not (raw / "wippa_nba").exists():
        pytest.skip("raw NBA data not present (gitignored)")
    from prediction_markets_lab.nba.data import build_games
    g = build_games(raw)
    assert g.date.is_monotonic_increasing and g.game_id.is_unique
    assert not g[g.source != "sbr"].stage.isin(["unknown"]).any()
