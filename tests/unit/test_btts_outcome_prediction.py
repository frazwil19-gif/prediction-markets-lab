"""Tests for Phase 5 BTTS outcome-prediction research module."""
from __future__ import annotations

import math
from datetime import date, timedelta

import numpy as np
import pytest

from prediction_markets_lab.research import btts_outcome_prediction as b


def _m(i, d, home, away, hg, ag, comp="E0", season="2021_22"):
    return b.RawMatch(f"m{i}", season, d, comp, home, away, hg, ag)


# --- target -------------------------------------------------------------------

@pytest.mark.parametrize("hg,ag,exp", [(0, 0, 0), (1, 0, 0), (0, 3, 0), (1, 1, 1), (4, 2, 1)])
def test_btts_target(hg, ag, exp):
    assert b.btts_target(hg, ag) == exp


def test_btts_target_rejects_negative():
    with pytest.raises(ValueError):
        b.btts_target(-1, 0)


@pytest.mark.parametrize("p", [0.0, 0.37, 0.5, 0.999, 1.0])
def test_yes_no_complement_sums_to_one(p):
    y, n = b.btts_yes_no(p)
    assert y + n == pytest.approx(1.0, abs=1e-15)


def test_yes_no_rejects_out_of_range():
    with pytest.raises(ValueError):
        b.btts_yes_no(1.2)


# --- Poisson ------------------------------------------------------------------

def test_closed_form_btts_matches_scoreline_grid():
    for lh, la in [(1.5, 1.1), (0.4, 2.9), (3.2, 0.2)]:
        grid = b.poisson_outcome_probabilities(np.array([lh]), np.array([la]), 15)["btts"][0]
        assert b.btts_probability_independent_poisson(lh, la) == pytest.approx(grid, abs=1e-6)


def test_poisson_outcome_probabilities_sum_to_one():
    p = b.poisson_outcome_probabilities(np.array([1.3, 2.0]), np.array([0.9, 1.7]), 15)
    assert np.allclose(p["home"] + p["draw"] + p["away"], 1.0)


def test_market_implied_lambdas_recover_known_lambdas():
    true = [(1.6, 1.1), (0.8, 2.2), (2.5, 0.6)]
    probs = b.poisson_outcome_probabilities(np.array([t[0] for t in true]), np.array([t[1] for t in true]), 15)
    fitted = b.fit_market_implied_lambdas(list(probs["home"]), list(probs["away"]), list(probs["over25"]))
    for (th, ta), (fh, fa) in zip(true, fitted):
        assert fh == pytest.approx(th, abs=0.006)
        assert fa == pytest.approx(ta, abs=0.006)


def test_market_implied_lambdas_work_without_over_line_and_are_deterministic():
    a = b.fit_market_implied_lambdas([0.45], [0.28], [None])
    assert a == b.fit_market_implied_lambdas([0.45], [0.28], [None])
    assert a[0][0] > a[0][1]


# --- rolling features / leakage ------------------------------------------------

def _league(n_days=12):
    d0 = date(2021, 8, 1)
    teams = ["A", "B", "C", "D"]
    out = []
    i = 0
    for day in range(n_days):
        d = d0 + timedelta(days=7 * day)
        pairs = [(teams[day % 4], teams[(day + 1) % 4]), (teams[(day + 2) % 4], teams[(day + 3) % 4])]
        for h, a in pairs:
            out.append(_m(i, d, h, a, (i * 7) % 3, (i * 5) % 2))
            i += 1
    return out


def test_rolling_scoring_and_clean_sheet_rates_hand_computed():
    cfg = b.BttsConfig(shrinkage_pseudo_matches=0.0)
    d = date(2021, 8, 1)
    ms = [
        _m(0, d, "A", "B", 2, 0),
        _m(1, d + timedelta(days=7), "A", "C", 0, 1),
        _m(2, d + timedelta(days=14), "A", "B", 1, 1),
    ]
    f = b.build_rolling_btts_features(ms, cfg)["m2"]
    assert f["home_scoring_rate_l10"] == pytest.approx(0.5)  # A scored in 1 of 2
    assert f["home_clean_sheet_rate_l10"] == pytest.approx(0.5)  # kept CS in 1 of 2
    assert f["home_failed_to_score_rate_l10"] == pytest.approx(0.5)
    assert f["home_btts_rate_l10"] == pytest.approx(0.0)
    assert f["away_scoring_rate_l10"] == pytest.approx(0.0)  # B scored 0 of 1
    assert f["away_clean_sheet_rate_l10"] == pytest.approx(0.0)
    assert f["home_history_matches"] == 2 and f["away_history_matches"] == 1


def test_no_history_team_gets_league_prior_not_missing():
    f = b.build_rolling_btts_features([_m(0, date(2021, 8, 1), "A", "B", 1, 1)])["m0"]
    assert f["home_history_matches"] == 0
    assert f["home_home_scoring_rate_l10"] == pytest.approx(b.DEFAULT_CONFIG.seed_home_scored_rate)


def test_own_result_never_affects_own_features():
    ms = _league()
    base = b.build_rolling_btts_features(ms)
    target = ms[10]
    changed = [
        b.RawMatch(m.match_id, m.season, m.match_date, m.competition, m.home_team, m.away_team, 9, 9)
        if m.match_id == target.match_id else m
        for m in ms
    ]
    assert b.build_rolling_btts_features(changed)[target.match_id] == base[target.match_id]


def test_same_day_fixture_result_never_leaks():
    ms = _league()
    base = b.build_rolling_btts_features(ms)
    same_day = [m for m in ms if m.match_date == ms[10].match_date and m.match_id != ms[10].match_id][0]
    changed = [
        b.RawMatch(m.match_id, m.season, m.match_date, m.competition, m.home_team, m.away_team, 0, 0)
        if m.match_id == same_day.match_id else m
        for m in ms
    ]
    assert b.build_rolling_btts_features(changed)[ms[10].match_id] == base[ms[10].match_id]


def test_future_results_never_affect_past_features():
    ms = _league()
    base = b.build_rolling_btts_features(ms)
    truncated = b.build_rolling_btts_features(ms[:12])
    for m in ms[:12]:
        assert truncated[m.match_id] == base[m.match_id]


def test_rolling_window_is_bounded():
    cfg = b.BttsConfig(rolling_window=3, shrinkage_pseudo_matches=0.0)
    d = date(2021, 8, 1)
    ms = [_m(i, d + timedelta(days=7 * i), "A", f"X{i}", 0 if i < 5 else 1, 0) for i in range(8)]
    f = b.build_rolling_btts_features(ms, cfg)["m7"]
    assert f["home_history_matches"] == 3
    assert f["home_scoring_rate_l10"] == pytest.approx(2 / 3)  # matches 4,5,6 -> 0,1,1


# --- models / chronology -------------------------------------------------------

def _bm(i, season, d, target, p=0.5):
    feats = {f: float((i * 13 + j) % 7) for j, f in enumerate(b.DATA_FEATURES)}
    return b.BttsMatch(
        match_id=f"x{i}", season=season, match_date=d, competition="E0", home_team="H", away_team="A",
        home_goals=target, away_goals=target, target=target, features=feats,
        p_market_implied_closing=p, p_market_implied_opening=p, p_poisson=p,
    )


def _dataset():
    rng = np.random.default_rng(0)
    out = []
    i = 0
    for si, s in enumerate(b.SEASONS_IN_ORDER):
        for k in range(60):
            p = float(rng.uniform(0.3, 0.7))
            out.append(_bm(i, s, date(2020 + si, 9, 1) + timedelta(days=k), int(rng.uniform() < p), p))
            i += 1
    return out


def test_predict_model_rejects_training_data_after_evaluation():
    ds = _dataset()
    with pytest.raises(ValueError):
        b.predict_model("naive", ds[100:], ds[:50])


def test_walk_forward_never_trains_on_holdout_or_same_season():
    ds = _dataset()
    preds = b.run_expanding_walk_forward(ds, b.DEVELOPMENT_EVAL_SEASONS, b.MODEL_KEYS)
    for k, ps in preds.items():
        assert {p.season for p in ps} <= set(b.DEVELOPMENT_EVAL_SEASONS)
        assert b.HOLDOUT_SEASON not in {p.season for p in ps}
    # naive in 2021_22 equals the 2020_21 base rate exactly (train = earlier seasons only)
    rate = sum(m.target for m in ds if m.season == "2020_21") / 60
    assert {round(p.p_yes, 12) for p in preds["naive"] if p.season == "2021_22"} == {round(rate, 12)}


def test_holdout_isolation_changing_holdout_outcomes_does_not_change_development_predictions():
    ds = _dataset()
    a = b.run_expanding_walk_forward(ds, b.DEVELOPMENT_EVAL_SEASONS, b.MODEL_KEYS)
    flipped = [
        b.BttsMatch(**{**m.__dict__, "target": 1 - m.target}) if m.season == b.HOLDOUT_SEASON else m for m in ds
    ]
    c = b.run_expanding_walk_forward(flipped, b.DEVELOPMENT_EVAL_SEASONS, b.MODEL_KEYS)
    for k in b.MODEL_KEYS:
        assert [p.p_yes for p in a[k]] == [p.p_yes for p in c[k]]


def test_walk_forward_is_deterministic_and_probabilities_valid():
    ds = _dataset()
    a = b.run_expanding_walk_forward(ds, b.DEVELOPMENT_EVAL_SEASONS, b.MODEL_KEYS)
    c = b.run_expanding_walk_forward(ds, b.DEVELOPMENT_EVAL_SEASONS, b.MODEL_KEYS)
    for k in b.MODEL_KEYS:
        assert [p.p_yes for p in a[k]] == [p.p_yes for p in c[k]]
        for p in a[k]:
            y, n = b.btts_yes_no(p.p_yes)
            assert 0 <= y <= 1 and y + n == pytest.approx(1.0)


def test_restrict_to_common_aligns_models():
    p = {"a": [b.Prediction("1", "s", "E0", 0.5, 1), b.Prediction("2", "s", "E0", 0.5, 0)],
         "b": [b.Prediction("2", "s", "E0", 0.4, 0)]}
    c = b.restrict_to_common(p)
    assert [x.match_id for x in c["a"]] == [x.match_id for x in c["b"]] == ["2"]


# --- reports -------------------------------------------------------------------

def test_probability_bands_yes_and_no_sides():
    preds = [b.Prediction(str(i), "s", "E0", p, a) for i, (p, a) in enumerate(
        [(0.52, 1), (0.53, 0), (0.71, 1), (0.30, 0), (0.18, 0), (0.82, 1)])]
    yes = {r["band"]: r for r in b.probability_band_report(preds, "YES")}
    no = {r["band"]: r for r in b.probability_band_report(preds, "NO")}
    assert yes["50-54.9%"]["n"] == 2 and yes["50-54.9%"]["occurred"] == 1
    assert yes["70-74.9%"]["n"] == 1 and yes["80%+"]["n"] == 1
    assert no["70-74.9%"]["n"] == 1 and no["70-74.9%"]["occurred"] == 1  # P(NO)=0.70 and NO happened
    assert no["80%+"]["n"] == 1 and no["80%+"]["occurred"] == 1       # P(NO)=0.82
    assert yes["75-79.9%"]["n"] == 0 and yes["75-79.9%"]["actual_rate"] is None


def test_top_pick_tie_goes_to_no_and_summary_counts():
    assert b.top_pick(0.5) == ("NO", 0.5)
    preds = [b.Prediction("1", "s", "E0", 0.6, 1), b.Prediction("2", "s", "E0", 0.3, 1)]
    s = b.top_prediction_summary(preds)
    assert s["correct"] == 1 and s["incorrect"] == 1 and s["expected_correct"] == pytest.approx(1.3)


def test_high_probability_report_thresholds():
    preds = [b.Prediction(str(i), "s", "E0", p, a) for i, (p, a) in enumerate([(0.62, 1), (0.66, 0), (0.25, 0)])]
    rows = {(r["threshold"], r["side"]): r for r in b.high_probability_report(preds)}
    assert rows[(0.60, "YES")]["n"] == 2 and rows[(0.60, "YES")]["occurred"] == 1
    assert rows[(0.75, "NO")]["n"] == 1 and rows[(0.75, "NO")]["occurred"] == 1
    assert rows[(0.60, "EITHER")]["n"] == 3


def test_decile_calibration_counts_all_predictions():
    preds = [b.Prediction(str(i), "s", "E0", i / 10, i % 2) for i in range(11)]
    assert sum(r["n"] for r in b.decile_calibration(preds)) == 11


def test_wilson_interval_bounds():
    lo, hi = b.wilson_interval(7, 10)
    assert 0 < lo < 0.7 < hi < 1
    assert b.wilson_interval(0, 0) == (None, None)


def test_cohens_d_and_univariate_auc():
    assert b.cohens_d([2, 3, 4], [0, 1, 2]) == pytest.approx(2.0)
    assert b.univariate_auc([1, 2, 3, 4], [0, 0, 1, 1]) == pytest.approx(1.0)
    assert b.univariate_auc([1, 1, 1, 1], [0, 1, 0, 1]) == pytest.approx(0.5)
