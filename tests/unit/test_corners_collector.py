"""Corners prospective collector: maths identical to the frozen research script, leakage-safe states, row hygiene."""
from __future__ import annotations

import importlib.util
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from prediction_markets_lab.research_shadow import corners_collector as CC

REPO = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("cma_frozen_t", REPO / "scripts/corners_model_a.py")
FROZEN = importlib.util.module_from_spec(spec)
spec.loader.exec_module(FROZEN)
PARAMS = REPO / "research/platform_v2/corners_abc/corners_A_v1_params.json"


def test_maths_identical_to_frozen_script():
    g = CC.grid(int(FROZEN.GRID[-1]))
    mu = np.array([5.2, 4.1])
    assert np.allclose(CC.nb_pmf_grid(mu, 0.08, g), FROZEN.nb_pmf_grid(mu, 0.08))
    ph, pa = FROZEN.nb_pmf_grid(np.array([5.5]), 0.07), FROZEN.nb_pmf_grid(np.array([4.4]), 0.09)
    assert np.allclose(CC.copula_total_pmf(ph, pa, -0.18, FROZEN.MC_DRAWS, FROZEN.MC_SEED, FROZEN.MC_MIX), FROZEN.copula_total_pmf(ph, pa, -0.18))


def test_params_frozen_spec_consistency():
    m = CC.ModelA.load(PARAMS)
    assert m.params["version"] == "corners-A-1.0" and m.params["family"] == "MA4" and m.params["train_end"] == "2026-07-01"
    assert m.params["groups"] == ["G3_corners20"] and -0.3 < m.params["rho"] < 0


def _played():
    rows = []
    d0 = pd.Timestamp("2026-08-01")
    for i in range(30):
        rows.append({"Division": "E0", "MatchDate": d0 + pd.Timedelta(days=i), "HomeTeam": "A" if i % 2 else "B", "AwayTeam": "B" if i % 2 else "A",
                     "HomeCorners": 6.0 if i % 2 else 4.0, "AwayCorners": 4.0 if i % 2 else 6.0})
    for i in range(60):
        rows.append({"Division": "E0", "MatchDate": d0 + pd.Timedelta(days=i), "HomeTeam": f"X{i}", "AwayTeam": f"Y{i}", "HomeCorners": 5.0, "AwayCorners": 5.0})
    return pd.DataFrame(rows)


def test_team_states_use_only_played_and_last_window():
    p = _played()
    st, fill, lg = CC.team_states(p, 3, 380, 50)
    assert st["A"]["n"] == 30 and st["A"]["cf"] == pytest.approx(6.0) and st["A"]["ca"] == pytest.approx(4.0)
    future = p.assign(HomeCorners=np.nan, AwayCorners=np.nan, MatchDate=p.MatchDate + pd.Timedelta(days=400))
    st2, _, _ = CC.team_states(pd.concat([p, future]), 3, 380, 50)
    assert st2["A"] == st["A"]                                  # unplayed rows never enter a state
    assert lg["E0"]["H"] == pytest.approx(p.HomeCorners.mean())


def test_prediction_rows_have_no_market_prices_and_flag_low_history():
    p = _played()
    st, fill, lg = CC.team_states(p, 3, 380, 50)
    fx = pd.DataFrame([{"Division": "E0", "MatchDate": pd.Timestamp("2026-10-10"), "Time": "12:30", "HomeTeam": "A", "AwayTeam": "NEWCOMER"}])
    feats = CC.fixture_features(fx, st, fill, lg)
    rows = CC.prediction_rows(feats, CC.ModelA.load(PARAMS), datetime(2026, 10, 3, tzinfo=timezone.utc))
    r = rows[0]
    assert r["market_status"] == CC.NO_PRICE and r["consensus_p_over"] == "" and r["best_exec_over_odds"] == "" and r["decision_price"] == ""
    assert r["uncertainty_flag"] == "LOW_HISTORY"
    ps = [r[f"p_total_over_{L}"] for L in CC.TOTAL_LINES]
    assert all(a > b for a, b in zip(ps, ps[1:]))


def test_outcomes_dedupe_and_parse_fixtures_bom():
    p = _played()
    out = CC.outcome_rows(p, pd.Timestamp("2026-08-01").date(), set(), datetime(2026, 10, 3, tzinfo=timezone.utc))
    assert len(out) == len(p) and out[0]["total_corners"] == 10
    keys = {o["event_key"] for o in out}
    assert CC.outcome_rows(p, pd.Timestamp("2026-08-01").date(), keys, datetime(2026, 10, 3, tzinfo=timezone.utc)) == []
    fx = CC.parse_fixtures("﻿Div,Date,Time,HomeTeam,AwayTeam\nE0,10/10/2026,12:30,Arsenal,Leeds\nZZ,10/10/2026,12:30,X,Y\n")
    assert list(fx.HomeTeam) == ["Arsenal"]
