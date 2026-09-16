"""Tests for football_leakage_safe_features.py (Football Cycle 2, step D).

Includes mechanical look-ahead-leakage checks, per the operator's
explicit instruction: perturb a match's OWN stats or a LATER match's
stats and assert an EARLIER snapshot is byte-identical.
"""

from copy import deepcopy
from dataclasses import replace
from datetime import date, timedelta

from prediction_markets_lab.features.football_leakage_safe_features import (
    TeamMatchInput,
    compute_rolling_features,
)


def _tm(match_id, d, team, is_home, gf=1, ga=1, sf=10, sa=10, sotf=5, sota=5, cf=5, ca=5, cdf=2, cda=2, pts=1):
    return TeamMatchInput(
        match_id=match_id, match_date=d, team=team, is_home=is_home,
        goals_for=gf, goals_against=ga, shots_for=sf, shots_against=sa,
        shots_on_target_for=sotf, shots_on_target_against=sota,
        corners_for=cf, corners_against=ca, cards_for=cdf, cards_against=cda,
        result_points=pts,
    )


def test_first_match_has_no_history_not_zero():
    rows = [_tm("m1", date(2021, 1, 1), "Arsenal", True)]
    feats = compute_rolling_features(rows, windows=(5,))
    snap = feats[0].overall[5]
    assert snap.matches_in_window == 0
    assert snap.avg_goals_for is None
    assert snap.points_per_game is None


def test_second_match_reflects_only_the_first():
    rows = [
        _tm("m1", date(2021, 1, 1), "Arsenal", True, gf=3, ga=0, sf=15, pts=3),
        _tm("m2", date(2021, 1, 8), "Arsenal", False, gf=1, ga=1, sf=8, pts=1),
    ]
    feats = compute_rolling_features(rows, windows=(5,))
    snap_m2 = [f for f in feats if f.match_id == "m2"][0].overall[5]
    assert snap_m2.matches_in_window == 1
    assert snap_m2.avg_goals_for == 3.0
    assert snap_m2.points_per_game == 3.0


def test_rolling_window_caps_at_window_size():
    base_date = date(2021, 1, 1)
    rows = [
        _tm(f"m{i}", base_date + timedelta(days=i * 7), "Arsenal", True, gf=i, pts=1)
        for i in range(1, 8)  # 7 prior matches
    ]
    feats = compute_rolling_features(rows, windows=(5,))
    last = [f for f in feats if f.match_id == "m7"][0].overall[5]
    # Only the 5 matches strictly before m7 (m2..m6) should be in the window.
    assert last.matches_in_window == 5
    assert last.avg_goals_for == sum(range(2, 7)) / 5


def test_leakage_perturbing_own_match_stats_does_not_change_own_snapshot_input():
    # A match's pre-match snapshot must be computable BEFORE that
    # match's own result is known -- perturbing match m2's own stats
    # must not change m2's OWN pre-match snapshot (which only reflects
    # m1), only m3's (which comes after m2).
    base = [
        _tm("m1", date(2021, 1, 1), "Arsenal", True, gf=1, pts=1),
        _tm("m2", date(2021, 1, 8), "Arsenal", True, gf=2, pts=3),
        _tm("m3", date(2021, 1, 15), "Arsenal", True, gf=3, pts=0),
    ]
    perturbed = deepcopy(base)
    perturbed[1] = replace(perturbed[1], goals_for=99, result_points=3)  # change m2's OWN stats

    snap_before = compute_rolling_features(base, windows=(5,))
    snap_after = compute_rolling_features(perturbed, windows=(5,))

    m2_before = [f for f in snap_before if f.match_id == "m2"][0].overall[5]
    m2_after = [f for f in snap_after if f.match_id == "m2"][0].overall[5]
    assert m2_before == m2_after  # m2's pre-match snapshot must be unaffected by m2's own perturbed result

    m3_before = [f for f in snap_before if f.match_id == "m3"][0].overall[5]
    m3_after = [f for f in snap_after if f.match_id == "m3"][0].overall[5]
    assert m3_before != m3_after  # m3 SHOULD change: it legitimately depends on m2's result


def test_leakage_perturbing_a_later_match_never_changes_an_earlier_snapshot():
    base = [
        _tm("m1", date(2021, 1, 1), "Arsenal", True, gf=1, pts=1),
        _tm("m2", date(2021, 1, 8), "Arsenal", True, gf=2, pts=3),
        _tm("m3", date(2021, 1, 15), "Arsenal", True, gf=3, pts=0),
    ]
    perturbed = deepcopy(base)
    perturbed[2] = replace(perturbed[2], goals_for=999, result_points=3)  # change m3 (the LAST match)

    feats_before = compute_rolling_features(base, windows=(5,))
    feats_after = compute_rolling_features(perturbed, windows=(5,))

    for mid in ("m1", "m2"):
        before = [f for f in feats_before if f.match_id == mid][0]
        after = [f for f in feats_after if f.match_id == mid][0]
        assert before == after  # m1 and m2 must be completely unaffected by a change to the later m3


def test_home_and_away_context_windows_are_independent():
    rows = [
        _tm("m1", date(2021, 1, 1), "Arsenal", True, gf=5, pts=3),   # home
        _tm("m2", date(2021, 1, 8), "Arsenal", False, gf=1, pts=0),  # away
        _tm("m3", date(2021, 1, 15), "Arsenal", True, gf=9, pts=3),  # home -- snapshot should see only m1's home data
    ]
    feats = compute_rolling_features(rows, windows=(5,))
    m3 = [f for f in feats if f.match_id == "m3"][0]
    assert m3.home_context[5].matches_in_window == 1
    assert m3.home_context[5].avg_goals_for == 5.0
    assert m3.away_context[5].matches_in_window == 1
    assert m3.away_context[5].avg_goals_for == 1.0
    # overall must include both prior matches regardless of venue
    assert m3.overall[5].matches_in_window == 2


def test_missing_stat_is_excluded_from_average_not_treated_as_zero():
    rows = [
        _tm("m1", date(2021, 1, 1), "Arsenal", True, gf=2, sf=None),  # shots missing for m1
        _tm("m2", date(2021, 1, 8), "Arsenal", True, gf=4, sf=20),
        _tm("m3", date(2021, 1, 15), "Arsenal", True, gf=1, sf=10),
    ]
    feats = compute_rolling_features(rows, windows=(5,))
    m3 = [f for f in feats if f.match_id == "m3"][0].overall[5]
    # avg_shots_for must average only the one match with a real value (20), not (0+20)/2
    assert m3.avg_shots_for == 20.0
    assert m3.matches_in_window == 2  # both matches count toward the window even though one lacks shots


def test_conversion_rate_none_when_shots_unavailable_or_zero():
    rows = [
        _tm("m1", date(2021, 1, 1), "Arsenal", True, gf=1, sf=None),
        _tm("m2", date(2021, 1, 8), "Arsenal", True, gf=2, sf=10),
    ]
    feats = compute_rolling_features(rows, windows=(5,))
    m2 = [f for f in feats if f.match_id == "m2"][0].overall[5]
    # only m1 in window, and its shots are missing -> conversion rate undefined
    assert m2.conversion_rate is None


def test_goal_difference_volatility_requires_at_least_two_matches():
    rows = [
        _tm("m1", date(2021, 1, 1), "Arsenal", True, gf=3, ga=0),
        _tm("m2", date(2021, 1, 8), "Arsenal", True, gf=1, ga=1),
        _tm("m3", date(2021, 1, 15), "Arsenal", True, gf=0, ga=2),
    ]
    feats = compute_rolling_features(rows, windows=(5,))
    m2 = [f for f in feats if f.match_id == "m2"][0].overall[5]  # only 1 prior match
    m3 = [f for f in feats if f.match_id == "m3"][0].overall[5]  # 2 prior matches
    assert m2.goal_difference_volatility is None
    assert m3.goal_difference_volatility is not None


def test_appearance_number_counts_cumulative_matches_for_team():
    rows = [
        _tm("m1", date(2021, 1, 1), "Arsenal", True),
        _tm("m2", date(2021, 1, 8), "Arsenal", False),
        _tm("m3", date(2021, 1, 15), "Arsenal", True),
    ]
    feats = compute_rolling_features(rows, windows=(5,))
    numbers = {f.match_id: f.appearance_number for f in feats}
    assert numbers == {"m1": 1, "m2": 2, "m3": 3}


def test_two_teams_are_tracked_independently():
    rows = [
        _tm("m1", date(2021, 1, 1), "Arsenal", True, gf=5, pts=3),
        _tm("m1", date(2021, 1, 1), "Chelsea", False, gf=0, pts=0),
        _tm("m2", date(2021, 1, 8), "Arsenal", True, gf=2, pts=1),
    ]
    feats = compute_rolling_features(rows, windows=(5,))
    arsenal_m2 = [f for f in feats if f.match_id == "m2" and f.team == "Arsenal"][0]
    assert arsenal_m2.overall[5].matches_in_window == 1
    assert arsenal_m2.overall[5].avg_goals_for == 5.0


def test_unsorted_input_is_handled_correctly():
    # Feed rows out of chronological order -- the function must sort
    # internally per team rather than assume caller-provided order.
    rows = [
        _tm("m3", date(2021, 1, 15), "Arsenal", True, gf=3, pts=0),
        _tm("m1", date(2021, 1, 1), "Arsenal", True, gf=1, pts=1),
        _tm("m2", date(2021, 1, 8), "Arsenal", True, gf=2, pts=3),
    ]
    feats = compute_rolling_features(rows, windows=(5,))
    m3 = [f for f in feats if f.match_id == "m3"][0].overall[5]
    assert m3.matches_in_window == 2
    assert m3.avg_goals_for == 1.5
