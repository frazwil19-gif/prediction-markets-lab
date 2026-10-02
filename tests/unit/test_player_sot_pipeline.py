"""Player SOT pipeline: audit, leakage-safe prior features, splits, baselines, evaluation, holdout guard."""
from __future__ import annotations

import importlib.util
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from prediction_markets_lab.research_shadow import player_sot as PS

REPO = Path(__file__).resolve().parents[2]


def toy() -> pd.DataFrame:
    rows = []
    dates = pd.date_range("2017-08-12", periods=6, freq="7D")
    for m, d in enumerate(dates):
        for team, opp in ((1, 2), (2, 1)):
            for i in range(11):
                pid = team * 100 + i
                sot = (m % 3) if i == 10 else 0
                rows.append({"source": "toy", "competition": "EPL", "season": "2017-18", "match_id": m, "date": d.date().isoformat(), "team_id": team,
                             "opponent_id": opp, "home": team == 1, "player_id": pid, "player_name": str(pid), "role": "FW" if i == 10 else "DF",
                             "starter": True, "minute_in": 0, "minute_out": 90, "minutes": 90, "shots": sot + 1 if i == 10 else 0, "sot": sot,
                             "goals": 1 if sot == 2 else 0})
    return pd.DataFrame(rows)


def test_audit_reports_quality_and_base_rates():
    a = PS.audit(toy())
    assert a["duplicates_match_player"] == 0 and a["starters_per_team_match"]["eq_11"] == 1.0
    assert a["violations"] == {"sot_gt_shots": 0, "goals_gt_sot": 0, "minutes_out_of_range": 0, "events_with_zero_minutes": 0}
    assert a["base_rates_starters_by_role"]["FW"]["sot_1plus"] == pytest.approx(4 / 6, abs=1e-3)


def test_prior_features_use_only_earlier_matches():
    f = PS.prior_features(toy())
    fw = f[f.player_id == 110].sort_values("date")
    assert np.isnan(fw.p_sot_prior.iloc[0])                     # first appearance: no history
    assert list(fw.p_sot_prior.iloc[1:4]) == [0, 1, 3]          # cumulative of earlier SOT only (0,1,2,...)
    assert np.isnan(fw.team_sot_for_prior.iloc[0]) and fw.team_sot_for_prior.iloc[1] == 0


def test_split_baselines_and_evaluation():
    f = PS.add_targets(PS.prior_features(toy()))
    tr, te = PS.chronological_split(f, ["2017-09-02"])
    assert pd.to_datetime(tr.date).max() < pd.Timestamp("2017-09-02") <= pd.to_datetime(te.date).min()
    p0 = PS.baseline_role_rate(tr, te, "sot_1plus")
    p1 = PS.baseline_player_rate(tr, te, "sot_1plus")
    assert p0.shape == p1.shape == (len(te),) and ((p1 > 0) & (p1 < 1)).all()
    e = PS.evaluate(te.sot_1plus.to_numpy(float), p0)
    assert {"logloss", "brier", "cal_slope"} <= set(e)


def test_holdout_guard(tmp_path):
    g = PS.HoldoutGuard(tmp_path / "spec.json", tmp_path / "opened.marker")
    with pytest.raises(PermissionError):
        g.open(lambda p: True)
    (tmp_path / "spec.json").write_text("{}")
    with pytest.raises(PermissionError):
        g.open(lambda p: False)
    assert g.open(lambda p: True) == {}
    with pytest.raises(PermissionError):
        g.open(lambda p: True)


def test_wyscout_builder_on_synthetic_json():
    spec = importlib.util.spec_from_file_location("wy", REPO / "scripts/wyscout_player_match.py")
    W = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(W)
    lineup = lambda base: [{"playerId": base + i} for i in range(11)]
    match = {"wyId": 7, "dateutc": "2018-05-13 14:00:00", "teamsData": {
        "1": {"side": "home", "formation": {"lineup": lineup(100), "bench": [{"playerId": 150}, {"playerId": 151}],
                                             "substitutions": [{"playerIn": 150, "playerOut": 110, "minute": 60}]}},
        "2": {"side": "away", "formation": {"lineup": lineup(200), "bench": [], "substitutions": "null"}}}}
    events = [{"matchId": 7, "playerId": 110, "teamId": 1, "eventName": "Shot", "subEventName": "Shot", "tags": [{"id": 101}, {"id": 1801}]},
              {"matchId": 7, "playerId": 110, "teamId": 1, "eventName": "Shot", "subEventName": "Shot", "tags": [{"id": 2101}, {"id": 1802}]},
              {"matchId": 7, "playerId": 150, "teamId": 1, "eventName": "Free Kick", "subEventName": "Free kick shot", "tags": [{"id": 1801}]},
              {"matchId": 7, "playerId": 150, "teamId": 1, "eventName": "Pass", "subEventName": "Simple pass", "tags": [{"id": 1801}]}]
    players = {110: {"shortName": "A", "role": {"code2": "FW"}}, 150: {"shortName": "B", "role": {"code2": "MD"}}}
    df = W.build_league([match], events, players, "EPL")
    a = df[df.player_id == 110].iloc[0]
    b = df[df.player_id == 150].iloc[0]
    assert (a.minutes, a.shots, a.sot, a.goals, a.starter) == (60, 2, 1, 1, True)
    assert (b.minutes, b.shots, b.sot, b.starter) == (30, 1, 1, False)
    assert 151 not in set(df.player_id)                         # unused substitute excluded
    assert len(df) == 23
