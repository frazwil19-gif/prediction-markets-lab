"""Unit tests for src/prediction_markets_lab/research/outcome_discovery_analysis.py.

Covers: candidate label correctness (Home/Draw/Away target assignment), signed-feature
orientation (home/away/draw), chronological season partitioning, Cohen's d edge cases
(small samples, zero variance), probability-band bucketing and calibration-error math,
top-pick accuracy computation, and the discovery-vs-validation stability verdict --
including the specific bug this test guards against: a missing (None) holdout Cohen's d
must be reported as INSUFFICIENT_DATA / "DATA UNAVAILABLE", never silently scored as an
UNSTABLE sign-disagreement.
"""
from prediction_markets_lab.research.outcome_discovery_analysis import (
    MODEL_PREFIXES,
    build_candidates,
    cohens_d,
    conditional_market_analysis,
    draw_analysis,
    favourite_analysis,
    feature_stability,
    partition_season,
    probability_bands_report,
    top_pick_accuracy,
    underdog_analysis,
    winner_loser_table,
)


def _match(match_id, season, outcome, market_home, market_draw, market_away, competition="E0"):
    def probs_for(h, d, a):
        return {"home": h, "draw": d, "away": a}

    return {
        "match_id": match_id,
        "competition_code": competition,
        "season": season,
        "outcome": outcome,
        "probs": {
            "market": probs_for(market_home, market_draw, market_away),
            "elo_poisson": probs_for(market_home, market_draw, market_away),
            "fundamentals": probs_for(market_home, market_draw, market_away),
            "market_fundamentals": probs_for(market_home, market_draw, market_away),
            "ensemble": probs_for(market_home, market_draw, market_away),
        },
    }


def test_build_candidates_target_correctness():
    matches = {"m1": _match("m1", "2020_21", "home", 0.6, 0.2, 0.2)}
    feats = {"m1": {"elo_gap": 100.0}}
    candidates = build_candidates(matches, feats)
    assert len(candidates) == 3
    by_side = {c["side"]: c for c in candidates}
    assert by_side["home"]["target"] == 1
    assert by_side["draw"]["target"] == 0
    assert by_side["away"]["target"] == 0


def test_build_candidates_signed_feature_orientation():
    matches = {"m1": _match("m1", "2020_21", "home", 0.6, 0.2, 0.2)}
    feats = {"m1": {"elo_gap": 100.0, "diff_goals_for_last10": None, "diff_shots_for_last10": None,
                    "diff_points_per_game_last10": None, "diff_goals_for_last5": None,
                    "diff_shots_for_last5": None, "diff_points_per_game_last5": None,
                    "diff_sot_for_last10": None, "diff_sot_against_last10": None,
                    "diff_corners_for_last10": None, "diff_cards_for_last10": None}}
    candidates = build_candidates(matches, feats)
    by_side = {c["side"]: c for c in candidates}
    # home candidate keeps the raw (home-favouring) sign
    assert by_side["home"]["signed_elo_gap"] == 100.0
    # away candidate sees the mirrored (negated) advantage
    assert by_side["away"]["signed_elo_gap"] == -100.0
    # draw candidate scores on closeness: -abs(value), so a big gap scores low for the draw
    assert by_side["draw"]["signed_elo_gap"] == -100.0


def test_build_candidates_missing_features_are_none_not_zero():
    matches = {"m1": _match("m1", "2025_26", "away", 0.3, 0.2, 0.5)}
    candidates = build_candidates(matches, feats={})  # no feature row at all for this match
    for c in candidates:
        assert c["signed_elo_gap"] is None


def test_partition_season():
    assert partition_season("2020_21") == "discovery"
    assert partition_season("2022_23") == "discovery"
    assert partition_season("2023_24") == "validation"
    assert partition_season("2024_25") == "validation"
    assert partition_season("2025_26") == "holdout"
    assert partition_season("1999_00") == "unknown"


def test_cohens_d_basic_direction_and_magnitude():
    winners = [10.0, 12.0, 11.0, 9.0, 13.0]
    losers = [1.0, 2.0, 0.0, 3.0, 1.0]
    d, n_w, n_l, mean_w, mean_l = cohens_d(winners, losers)
    assert n_w == 5 and n_l == 5
    assert mean_w > mean_l
    assert d is not None and d > 0


def test_cohens_d_insufficient_sample_returns_none():
    d, n_w, n_l, mean_w, mean_l = cohens_d([1.0, 2.0], [3.0, 4.0])
    assert d is None
    assert mean_w is None and mean_l is None
    assert n_w == 2 and n_l == 2


def test_cohens_d_skips_none_values():
    winners = [10.0, None, 12.0, 11.0, 9.0, 13.0]
    d, n_w, n_l, mean_w, mean_l = cohens_d(winners, [1.0, 2.0, 3.0, 4.0, 5.0])
    assert n_w == 5  # the None was dropped, not counted or treated as zero


def test_probability_bands_report_calibration_error_sign():
    candidates = [
        {"prob_market": 0.72, "target": 1},
        {"prob_market": 0.71, "target": 0},
        {"prob_market": 0.73, "target": 1},
    ]
    report = probability_bands_report(candidates, "market")
    band = next(r for r in report if r["band"] == "70-79.9%")
    assert band["n"] == 3
    assert band["actual_win_rate"] == round(2 / 3, 4)
    assert band["calibration_error"] == round(band["actual_win_rate"] - band["mean_predicted"], 4)


def test_probability_bands_report_empty_band_is_reported_not_dropped():
    candidates = [{"prob_market": 0.1, "target": 0}]
    report = probability_bands_report(candidates, "market")
    band = next(r for r in report if r["band"] == "80%+")
    assert band["n"] == 0
    assert band["actual_win_rate"] is None


def test_top_pick_accuracy_never_picks_draw_when_draw_never_argmax():
    matches = {
        "m1": _match("m1", "2020_21", "home", 0.6, 0.2, 0.2),
        "m2": _match("m2", "2020_21", "away", 0.3, 0.25, 0.45),
    }
    result = top_pick_accuracy(matches, "market")
    assert result["by_side"]["draw"]["n_picked"] == 0
    assert result["n_matches"] == 2
    assert result["correct"] == 2  # m1 picks home (correct), m2 picks away (correct)
    assert result["accuracy"] == 1.0


def test_top_pick_accuracy_skips_matches_with_missing_probabilities():
    matches = {
        "m1": _match("m1", "2020_21", "home", None, 0.2, 0.2),
        "m2": _match("m2", "2020_21", "away", 0.3, 0.25, 0.45),
    }
    result = top_pick_accuracy(matches, "market")
    assert result["n_matches"] == 1


def test_favourite_analysis_excludes_draw_favourites():
    matches = {
        "m1": _match("m1", "2020_21", "draw", 0.3, 0.4, 0.3),  # draw itself is favourite -> excluded
    }
    rows, n_won, n_lost = favourite_analysis(matches, feats={})
    assert n_won == 0 and n_lost == 0


def test_favourite_and_underdog_are_complementary_for_home_away_only_matches():
    matches = {
        "m1": _match("m1", "2020_21", "home", 0.6, 0.2, 0.2),
    }
    feats = {"m1": {"elo_gap": 50.0, "diff_goals_for_last10": None, "diff_shots_for_last10": None,
                    "diff_points_per_game_last10": None, "diff_goals_for_last5": None,
                    "diff_shots_for_last5": None, "diff_points_per_game_last5": None,
                    "diff_sot_for_last10": None, "diff_sot_against_last10": None,
                    "diff_corners_for_last10": None, "diff_cards_for_last10": None}}
    _, n_fav_won, n_fav_lost = favourite_analysis(matches, feats)
    _, n_dog_won, n_dog_lost = underdog_analysis(matches, feats)
    assert n_fav_won == 1 and n_fav_lost == 0
    assert n_dog_won == 0 and n_dog_lost == 1


def test_draw_analysis_target_is_draw_occurrence():
    matches = {
        f"m{i}": _match(f"m{i}", "2020_21", "draw" if i % 2 == 0 else "home", 0.4, 0.3, 0.3)
        for i in range(10)
    }
    feats = {
        f"m{i}": {"elo_gap": float(i), "diff_goals_for_last10": None, "diff_shots_for_last10": None,
                  "diff_points_per_game_last10": None, "diff_goals_for_last5": None,
                  "diff_shots_for_last5": None, "diff_points_per_game_last5": None,
                  "diff_sot_for_last10": None, "diff_sot_against_last10": None,
                  "diff_corners_for_last10": None, "diff_cards_for_last10": None}
        for i in range(10)
    }
    candidates = build_candidates(matches, feats)
    rows = draw_analysis(candidates, {"2020_21"})
    elo_row = next(r for r in rows if r["feature"] == "elo_gap")
    assert elo_row["n_winners"] == 5  # 5 draws occurred
    assert elo_row["n_losers"] == 5


def test_conditional_market_analysis_restricted_to_home_away_and_band():
    matches = {
        "m1": _match("m1", "2020_21", "home", 0.55, 0.25, 0.20),  # in band
        "m2": _match("m2", "2020_21", "away", 0.80, 0.10, 0.10),  # out of band
    }
    feats = {mid: {"elo_gap": 10.0, "diff_goals_for_last10": None, "diff_shots_for_last10": None,
                   "diff_points_per_game_last10": None, "diff_goals_for_last5": None,
                   "diff_shots_for_last5": None, "diff_points_per_game_last5": None,
                   "diff_sot_for_last10": None, "diff_sot_against_last10": None,
                   "diff_corners_for_last10": None, "diff_cards_for_last10": None}
             for mid in matches}
    candidates = build_candidates(matches, feats)
    rows = conditional_market_analysis(candidates, {"2020_21"}, 0.50, 0.65)
    elo_row = next(r for r in rows if r["feature"] == "elo_gap")
    # only m1's home/away candidates fall in the 0.50-0.65 band
    assert elo_row["n_winners"] + elo_row["n_losers"] <= 2


def test_feature_stability_reports_missing_holdout_as_insufficient_data_not_unstable():
    """Regression test for the bug caught and fixed during this research cycle: a feature with
    no holdout data available (None cohens_d) must not be mislabelled UNSTABLE."""
    matches = {}
    feats = {}
    for i in range(30):
        season = "2020_21" if i < 15 else "2023_24"
        mid = f"m{i}"
        outcome = "home" if i % 2 == 0 else "away"
        matches[mid] = _match(mid, season, outcome, 0.55, 0.25, 0.20)
        feats[mid] = {
            "elo_gap": 50.0 if outcome == "home" else -50.0,
            "diff_goals_for_last10": None, "diff_shots_for_last10": None,
            "diff_points_per_game_last10": None, "diff_goals_for_last5": None,
            "diff_shots_for_last5": None, "diff_points_per_game_last5": None,
            "diff_sot_for_last10": None, "diff_sot_against_last10": None,
            "diff_corners_for_last10": None, "diff_cards_for_last10": None,
        }
    candidates = build_candidates(matches, feats)
    rows = feature_stability(candidates)
    elo_row = next(r for r in rows if r["feature"] == "elo_gap")
    # No 2025_26 (holdout) matches exist in this fixture at all -> holdout cohens_d is None
    assert elo_row["cohens_d_holdout"] != "UNSTABLE (discovery-validation)"
    assert "DATA UNAVAILABLE" in str(elo_row["cohens_d_holdout"]) or elo_row["cohens_d_holdout"] is None
    assert elo_row["verdict"] in ("STABLE (discovery-validation)", "UNSTABLE (discovery-validation)", "INSUFFICIENT_DATA")


def test_winner_loser_table_pools_home_and_away_by_default():
    matches = {
        "m1": _match("m1", "2020_21", "home", 0.6, 0.2, 0.2),
        "m2": _match("m2", "2020_21", "away", 0.2, 0.2, 0.6),
    }
    feats = {
        "m1": {"elo_gap": 100.0, "diff_goals_for_last10": None, "diff_shots_for_last10": None,
               "diff_points_per_game_last10": None, "diff_goals_for_last5": None,
               "diff_shots_for_last5": None, "diff_points_per_game_last5": None,
               "diff_sot_for_last10": None, "diff_sot_against_last10": None,
               "diff_corners_for_last10": None, "diff_cards_for_last10": None},
        "m2": {"elo_gap": -100.0, "diff_goals_for_last10": None, "diff_shots_for_last10": None,
               "diff_points_per_game_last10": None, "diff_goals_for_last5": None,
               "diff_shots_for_last5": None, "diff_points_per_game_last5": None,
               "diff_sot_for_last10": None, "diff_sot_against_last10": None,
               "diff_corners_for_last10": None, "diff_cards_for_last10": None},
    }
    candidates = build_candidates(matches, feats)
    rows = winner_loser_table(candidates, ["elo_gap"], {"2020_21"})
    row = rows[0]
    # both winning candidates (m1 home, m2 away) have signed_elo_gap == +100 (both favoured to win)
    assert row["n_winners"] == 2
    assert row["n_losers"] == 2
