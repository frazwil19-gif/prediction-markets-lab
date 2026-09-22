"""Tests for prediction_markets_lab.research.ou25_probability_architecture
(Phase 4 -- Gate 1b, football Over/Under 2.5 probability-architecture
comparison)."""
from __future__ import annotations

import pytest

from prediction_markets_lab.research.ou25_probability_architecture import (
    Candidate,
    Prediction,
    accuracy_at_threshold,
    build_candidate,
    calibration_band_for,
    fixed_band_calibration_report,
    naive_frequency_baseline,
    partition_season,
    predict_fundamentals,
    predict_market,
    predict_market_fundamentals,
    predict_naive,
    run_walk_forward_comparison,
    top_misses,
)

FEATURE_NAMES = [
    "home_team_overall_last10_avg_goals_for",
    "home_team_overall_last10_avg_goals_against",
    "home_team_overall_last10_avg_shots_for",
    "home_team_overall_last10_avg_shots_against",
    "home_team_overall_last10_avg_sot_for",
    "home_team_overall_last10_avg_sot_against",
    "home_team_overall_last10_avg_corners_for",
    "home_team_overall_last10_avg_corners_against",
    "home_team_overall_last10_points_per_game",
    "away_team_overall_last10_avg_goals_for",
    "away_team_overall_last10_avg_goals_against",
    "away_team_overall_last10_avg_shots_for",
    "away_team_overall_last10_avg_shots_against",
    "away_team_overall_last10_avg_sot_for",
    "away_team_overall_last10_avg_sot_against",
    "away_team_overall_last10_avg_corners_for",
    "away_team_overall_last10_avg_corners_against",
    "away_team_overall_last10_points_per_game",
    "elo_rating_gap_incl_home_advantage",
]


def _row(match_id, season, home_goals, away_goals, market_prob="0.55", bm_count="3", feature_val="1.0", missing_features=False):
    row = {
        "match_id": match_id,
        "season": season,
        "match_date": "2021-01-01",
        "outcome_full_time_home_goals": str(home_goals),
        "outcome_full_time_away_goals": str(away_goals),
        "market_ou25_closing_source_avg_over_probability": market_prob,
        "market_ou25_closing_individual_bookmaker_count": bm_count,
    }
    if not missing_features:
        for name in FEATURE_NAMES:
            row[name] = feature_val
    return row


def test_build_candidate_target_over_and_under():
    over_row = _row("m1", "2020_21", 2, 2)  # total 4 > 2.5
    under_row = _row("m2", "2020_21", 1, 0)  # total 1 <= 2.5
    over_c = build_candidate(over_row)
    under_c = build_candidate(under_row)
    assert over_c.target == 1
    assert over_c.total_goals == 4.0
    assert under_c.target == 0
    assert under_c.total_goals == 1.0


def test_build_candidate_boundary_exactly_2_5_impossible_but_2_goals_is_under():
    row = _row("m3", "2020_21", 1, 1)  # total 2, not > 2.5
    c = build_candidate(row)
    assert c.target == 0


def test_build_candidate_returns_none_when_result_missing():
    row = _row("m4", "2020_21", 1, 1)
    row["outcome_full_time_home_goals"] = ""
    assert build_candidate(row) is None


def test_build_candidate_market_and_fundamentals_missing_individually():
    row = _row("m5", "2020_21", 1, 1)
    row["market_ou25_closing_source_avg_over_probability"] = ""
    c = build_candidate(row)
    assert c is not None
    assert c.market_probability is None
    assert c.fundamentals is not None  # fundamentals still present


def test_build_candidate_fundamentals_none_when_any_feature_missing():
    row = _row("m6", "2020_21", 1, 1, missing_features=True)
    row[FEATURE_NAMES[0]] = "1.0"  # only one of many present
    c = build_candidate(row)
    assert c.fundamentals is None


def test_partition_season():
    assert partition_season("2020_21") == "discovery"
    assert partition_season("2022_23") == "discovery"
    assert partition_season("2023_24") == "validation"
    assert partition_season("2024_25") == "holdout"
    assert partition_season("2025_26") == "unknown"


@pytest.mark.parametrize(
    "p,expected",
    [
        (0.10, "<50%"),
        (0.499, "<50%"),
        (0.50, "50-54.9%"),
        (0.549, "50-54.9%"),
        (0.55, "55-59.9%"),
        (0.699, "65-69.9%"),
        (0.70, "70-79.9%"),
        (0.80, "80%+"),
        (0.999, "80%+"),
    ],
)
def test_calibration_band_for(p, expected):
    assert calibration_band_for(p) == expected


def test_naive_frequency_baseline():
    cands = [
        Candidate("m1", "2020_21", "2021-01-01", 1, 3.0, None, None, None),
        Candidate("m2", "2020_21", "2021-01-01", 0, 1.0, None, None, None),
        Candidate("m3", "2020_21", "2021-01-01", 1, 4.0, None, None, None),
    ]
    assert naive_frequency_baseline(cands) == pytest.approx(2 / 3)


def test_naive_frequency_baseline_raises_on_empty():
    with pytest.raises(ValueError):
        naive_frequency_baseline([])


def test_predict_market_skips_candidates_without_a_quote():
    cands = [
        Candidate("m1", "2020_21", "d", 1, 3.0, 0.6, 3, None),
        Candidate("m2", "2020_21", "d", 0, 1.0, None, None, None),
    ]
    preds = predict_market(cands)
    assert len(preds) == 1
    assert preds[0].match_id == "m1"
    assert preds[0].predicted_probability == 0.6


def _synthetic_candidates(n_per_season: int = 60):
    """Build a synthetic multi-season dataset where fundamentals genuinely
    predict the target (a controlled sanity check that fitting/prediction
    plumbing works end-to-end), distinct from the real-data finding that
    market beats fundamentals on the actual historical data."""
    import random

    rng = random.Random(42)
    seasons = ["2020_21", "2021_22", "2022_23", "2023_24", "2024_25"]
    cands = []
    for season in seasons:
        for i in range(n_per_season):
            signal = rng.uniform(-3, 3)
            fundamentals = tuple([signal] + [rng.uniform(-1, 1) for _ in range(len(FEATURE_NAMES) - 1)])
            target = 1 if signal + rng.gauss(0, 1.5) > 0 else 0
            market_prob = min(max(0.5 + signal * 0.05 + rng.gauss(0, 0.05), 0.01), 0.99)
            cands.append(
                Candidate(
                    match_id=f"{season}_{i}",
                    season=season,
                    match_date="2021-01-01",
                    target=target,
                    total_goals=3.0 if target else 1.0,
                    market_probability=market_prob,
                    market_bookmaker_count=3,
                    fundamentals=fundamentals,
                )
            )
    return cands


def test_predict_fundamentals_fits_and_predicts_reasonable_probabilities():
    cands = _synthetic_candidates()
    train = [c for c in cands if c.season in ("2020_21", "2021_22", "2022_23")]
    evaluate = [c for c in cands if c.season == "2023_24"]
    model, preds = predict_fundamentals(train, evaluate)
    assert len(preds) == len(evaluate)
    assert all(0.0 <= p.predicted_probability <= 1.0 for p in preds)
    assert len(model.feature_names) == len(FEATURE_NAMES)


def test_predict_market_fundamentals_uses_one_more_feature_than_fundamentals():
    cands = _synthetic_candidates()
    train = [c for c in cands if c.season in ("2020_21", "2021_22", "2022_23")]
    evaluate = [c for c in cands if c.season == "2023_24"]
    model, _ = predict_market_fundamentals(train, evaluate)
    assert len(model.feature_names) == len(FEATURE_NAMES) + 1


def test_run_walk_forward_comparison_produces_four_folds_and_all_models():
    cands = _synthetic_candidates()
    results = run_walk_forward_comparison(cands)
    assert len(results.folds) == 4
    for key in ("naive", "market", "fundamentals", "market_fundamentals"):
        assert key in results.pooled_predictions
        assert len(results.pooled_predictions[key]) > 0


def test_fixed_band_calibration_report_reports_empty_bands_with_zero_n():
    preds = [Prediction("m1", "2020_21", 0.10, 0), Prediction("m2", "2020_21", 0.12, 1)]
    report = fixed_band_calibration_report(preds)
    bands = {r["band"]: r for r in report}
    assert bands["<50%"]["n"] == 2
    assert bands["80%+"]["n"] == 0
    assert bands["80%+"]["mean_predicted_probability"] is None


def test_top_misses_ranks_worst_confident_wrong_predictions_first():
    preds = [
        Prediction("correct_confident", "2020_21", 0.95, 1),
        Prediction("wrong_confident", "2020_21", 0.95, 0),
        Prediction("wrong_unsure", "2020_21", 0.55, 0),
    ]
    misses = top_misses(preds, n=2)
    assert misses[0]["match_id"] == "wrong_confident"
    assert misses[1]["match_id"] == "wrong_unsure"


def test_accuracy_at_threshold():
    preds = [
        Prediction("m1", "2020_21", 0.7, 1),
        Prediction("m2", "2020_21", 0.3, 0),
        Prediction("m3", "2020_21", 0.6, 0),
    ]
    assert accuracy_at_threshold(preds) == pytest.approx(2 / 3)


def test_accuracy_at_threshold_raises_on_empty():
    with pytest.raises(ValueError):
        accuracy_at_threshold([])
