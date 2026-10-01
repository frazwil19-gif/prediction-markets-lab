"""V2-7H backtest library tests (research; outside the production gate)."""
from __future__ import annotations

import itertools
import math

import numpy as np
import pandas as pd
import pytest

from prediction_markets_lab.research import card_backtest as CB


def legs_frame(n_days=30, per_day=6, seed=1):
    rng = np.random.default_rng(seed)
    rows = []
    for d in range(n_days):
        for i in range(per_day):
            p = rng.uniform(0.5, 0.95)
            rows.append({"sport": "x", "event": f"d{d}e{i}", "day": f"2024-01-{d+1:02d}", "period": 2024, "group": f"g{i % 2}",
                         "p": p, "won": int(rng.random() < p), "participants": (f"a{d}{i}", f"b{d}{i}")})
    return pd.DataFrame(rows)


def test_selection_is_frozen_before_outcomes():
    lg = legs_frame()
    ctx = {"supported_bands": [(0.5, 1.0)], "band_se": lambda p: 0.01}
    for st in ("S1", "S2", "S5"):
        for k in (1, 2, 3):
            a = [CB.select_prob(g, k, st, ctx) for _, g in lg.groupby("day")]
            b = [CB.select_prob(g.assign(won=1 - g.won), k, st, ctx) for _, g in lg.groupby("day")]
            assert a == b
    q = lg.assign(book="B", odds=1 / lg.p * 1.03, comm=0.0)
    q["odds_net"], q["ev"] = q.odds, q.p * q.odds - 1
    for st in ("S3", "S4", "S6"):
        a = [CB.select_priced(g, 2, st) for _, g in q.groupby("day")]
        b = [CB.select_priced(g.assign(won=1 - g.won), 2, st) for _, g in q.groupby("day")]
        assert a == b and all(r is None or "won" not in r[0] for r in a)


def test_priced_selection_same_book_positive_ev_distinct_participants():
    rows = [{"event": "e1", "participants": ("A", "B"), "p": 0.6, "odds": 1.8, "odds_net": 1.8, "comm": 0, "book": "X"},
            {"event": "e2", "participants": ("A", "C"), "p": 0.6, "odds": 1.9, "odds_net": 1.9, "comm": 0, "book": "X"},
            {"event": "e3", "participants": ("D", "E"), "p": 0.6, "odds": 1.7, "odds_net": 1.7, "comm": 0, "book": "X"},
            {"event": "e3", "participants": ("D", "E"), "p": 0.6, "odds": 1.5, "odds_net": 1.5, "comm": 0, "book": "Y"}]
    q = pd.DataFrame(rows)
    q["ev"] = q.p * q.odds_net - 1
    c = CB.select_priced(q, 2, "S3")
    assert {r["book"] for r in c} == {"X"} and {r["event"] for r in c} == {"e2", "e3"}     # e1 shares participant A with e2
    assert CB.select_priced(q, 3, "S3") is None


def test_disjoint_cards_partition_and_participant_rule():
    lg = legs_frame(5, 7)
    c, dropped = CB.disjoint_cards(lg, 3)
    assert dropped == 0 and len(c) == 5 * 2
    assert all(len(set(t)) == 3 for t in c.events)
    assert len({e for t in c.events for e in t}) == len(c) * 3                           # no leg reused within k
    lg.at[1, "participants"] = lg.at[0, "participants"]
    assert CB.disjoint_cards(lg, 7)[1] >= 1


def test_elem_sym_and_exhaustive_match_brute_force():
    lg = legs_frame(4, 6)
    for k in (2, 3):
        res = CB.exhaustive_inlarge(lg, k)
        ep = ey = n = 0
        for _, g in lg.groupby("day"):
            for c in itertools.combinations(g.index, k):
                ep += math.prod(lg.loc[i, "p"] for i in c)
                ey += math.prod(lg.loc[i, "won"] for i in c)
                n += 1
        assert res["raw_cards"] == n and res["pred"] == pytest.approx(ep / n, abs=1e-5) and res["actual"] == pytest.approx(ey / n, abs=1e-5)


def test_pair_residual_matches_brute_force():
    lg = legs_frame(3, 5)
    st = CB.pair_residual_stats(lg, n_boot=50)
    s = n = 0
    for _, g in lg.groupby("day"):
        r = (g.won - g.p).values
        for i, j in itertools.combinations(range(len(r)), 2):
            s += r[i] * r[j]
            n += 1
    assert st["all_pairs"]["pairs"] == n and st["all_pairs"]["mean_residual_product"] == pytest.approx(s / n, abs=1e-6)


def test_calibration_metrics_on_perfectly_calibrated_synthetic():
    rng = np.random.default_rng(3)
    p = rng.uniform(0.2, 0.9, 20000)
    y = (rng.random(20000) < p).astype(int)
    m = CB.calib_metrics(p, y, np.arange(20000) // 10)
    assert abs(m["bias"]) < 0.01 and m["bias_ci95"][0] < 0 < m["bias_ci95"][1] and 0.9 < m["recal_slope"] < 1.1
    a, b = CB.logistic_recal(p, y)
    assert abs(a) < 0.1 and abs(b - 1) < 0.1


def test_run_probability_dp_against_simulation():
    rng = np.random.default_rng(5)
    q = rng.uniform(0.2, 0.7, 60)
    sims = rng.random((20000, 60)) < q
    emp = np.mean([CB.longest_run(r) >= 5 for r in sims])
    assert CB.p_run_at_least(q, 5) == pytest.approx(emp, abs=0.01)


def test_simulate_card_and_singles_known_paths_and_equal_capital():
    days = [{"p": [0.6, 0.6], "o": [2.0, 2.0], "y": [1, 1]}, {"p": [0.6, 0.6], "o": [2.0, 2.0], "y": [1, 0]}]
    c = CB.simulate(days, 0.02, "card", n_boot=50)
    s = CB.simulate(days, 0.02, "singles", n_boot=50)
    assert c["final_bankroll"] == pytest.approx((1 + 0.02 * 3) * (1 - 0.02), abs=1e-4)
    assert s["final_bankroll"] == pytest.approx((1 + 0.02) * 1.0, abs=1e-4)
    g_card, g_sing = CB.growth_pair([0.6, 0.6], [2.0, 2.0], 0.02)
    assert c["model_expected_log_growth"] == pytest.approx(g_card, abs=1e-6)
    assert s["model_expected_log_growth"] == pytest.approx(g_sing, abs=1e-6)


def test_kish_and_tolerance():
    p = {"a": 0.6, "b": 0.7, "c": 0.8}
    assert CB.kish_neff([("a", "b")] * 4, p) == pytest.approx(1.0)
    assert CB.kish_neff([("a",), ("b",), ("c",)], p) == pytest.approx(3.0)
    d = CB.tolerance([0.6, 0.6], 1.05 / 0.36)
    assert (0.6 - d) ** 2 * (1.05 / 0.36) == pytest.approx(1.0, abs=1e-6)
    assert CB.tolerance([0.6], 1.5) == 0.0                                                  # already -EV
