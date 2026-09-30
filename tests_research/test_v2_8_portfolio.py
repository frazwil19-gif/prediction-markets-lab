"""V2-8 portfolio library tests (research; outside the production gate)."""
from __future__ import annotations

import itertools
import math

import numpy as np
import pytest

from prediction_markets_lab.research import portfolio as PF


def test_structure_line_counts():
    s5, s3 = PF.structures(5), PF.structures(3)
    assert len(s5["FULL_COVER"]) == 26 and len(s5["FULL_COVER+SINGLES"]) == 31 and len(s5["RR_DOUBLES"]) == 10
    assert len(s5["RR_TREBLES"]) == 10 and s5["ACC_5"] == [(0, 1, 2, 3, 4)] and s5["2DBL+SINGLE"] == [(0, 1), (2, 3), (4,)]
    assert len(s3["FULL_COVER"]) == 4 and len(s3["FULL_COVER+SINGLES"]) == 7 and "RR_TREBLES" not in s3


def test_expected_return_margin_compounds_per_leg_regardless_of_structure_split():
    p = np.array([0.86, 0.84, 0.81, 0.77, 0.75])
    for e in (0.0, 0.03, -0.0476):
        o = (1 + e) / p
        for name, lines in PF.structures(5).items():
            d = PF.distribution(p, o, lines)
            exp = np.mean([(1 + e) ** len(l) - 1 for l in lines])
            assert d["expected_return"] == pytest.approx(exp, abs=1e-9), name


def test_full_loss_probabilities():
    p = np.array([0.8, 0.7, 0.6])
    o = 1 / p
    assert PF.distribution(p, o, PF.structures(3)["SINGLES"])["p_full_loss"] == pytest.approx(0.2 * 0.3 * 0.4)
    assert PF.distribution(p, o, PF.structures(3)["ACC_3"])["p_full_loss"] == pytest.approx(1 - 0.336)
    rr = PF.distribution(p, o, PF.structures(3)["RR_DOUBLES"])          # all doubles lose unless >= 2 legs win
    assert rr["p_full_loss"] == pytest.approx(PF.poisson_binomial(p)[:2].sum())


def test_poisson_binomial_brute_force():
    p = np.array([0.9, 0.6, 0.75, 0.55])
    pmf = PF.poisson_binomial(p)
    bf = np.zeros(5)
    for y in itertools.product((0, 1), repeat=4):
        bf[sum(y)] += math.prod(pi if yi else 1 - pi for pi, yi in zip(p, y))
    assert np.allclose(pmf, bf) and pmf.sum() == pytest.approx(1)


def test_near_miss_expectations_match_simulation():
    rng = np.random.default_rng(2)
    ps = [np.sort(rng.uniform(0.7, 0.9, 5))[::-1] for _ in range(4000)]
    ys = [(rng.random(5) < p).astype(int) for p in ps]
    nm = PF.near_miss(ps, ys)
    assert abs(nm["exactly_one_loser"]["obs_share"] - nm["exactly_one_loser"]["exp_share"]) < 0.03
    assert abs(nm["lowest_p_leg_lost"]["obs_share"] - nm["lowest_p_leg_lost"]["exp_share"]) < 0.03
    g = PF.gof_count(ps[:500], [int(y.sum()) for y in ys[:500]], n_sim=2000)
    assert g["p_sim"] > 0.001 and sum(g["observed"]) == 500


def test_realised_and_exposure():
    o = np.array([2.0, 3.0, 1.5])
    y = np.array([1, 1, 0])
    s = PF.structures(3)
    assert PF.realised(o, y, s["SINGLES"]) == pytest.approx((1 + 2 - 1) / 3)
    assert PF.realised(o, y, s["ACC_3"]) == -1.0
    assert PF.realised(o, y, s["RR_DOUBLES"]) == pytest.approx((5 - 1 - 1) / 3)
    assert PF.exposure(s["ACC_3"], 3)["max_share_on_one_leg"] == 1.0
    assert PF.exposure(s["SINGLES"], 3)["max_share_on_one_leg"] == pytest.approx(1 / 3)


def test_kelly_and_marginal():
    f, g = PF.kelly_single(0.6, 2.0)
    assert f == pytest.approx(0.2) and g == pytest.approx(0.6 * math.log(1.2) + 0.4 * math.log(0.8))
    assert PF.kelly_single(0.5, 1.9) == (0.0, 0.0)
    path = PF.marginal_path(np.array([0.8, 0.7]), np.array([1.3, 1.5]), np.array([0.01, 0.01]))
    assert path[1]["p_joint"] == pytest.approx(0.56) and path[1]["odds"] == pytest.approx(1.95)


def test_bankroll_rounding_min_stake_and_no_scaling():
    days = [{"p": [0.8, 0.8], "o": [1.25, 1.25], "y": [1, 1]}] * 3
    lines = PF.structures(2)["SINGLES"]
    r = PF.bankroll_path(days, lines, 20.0, 0.02, 0.10)                 # 0.40 capital -> 0.20 per line
    assert r["bet_days"] == 3 and r["final"] == pytest.approx(20 + 3 * 0.1, abs=0.02)
    r1 = PF.bankroll_path(days, lines, 20.0, 0.02, 1.00)               # 0.20 < 1.00 minimum -> never bet
    assert r1["bet_days"] == 0 and r1["skipped_min_stake"] == 3 and r1["final"] == 20.0
