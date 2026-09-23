import math

import numpy as np
import pytest

from prediction_markets_lab.research import probability_reliability as r


def test_band_table_counts_expected_vs_actual():
    p = [0.52, 0.53, 0.81, 0.83, 0.96, 0.40]
    w = [1, 0, 1, 1, 1, 0]
    t = {x["band"]: x for x in r.band_table(p, w)}
    assert t["50-54.9%"]["n"] == 2 and t["50-54.9%"]["actual_wins"] == 1
    assert t["50-54.9%"]["expected_wins"] == pytest.approx(1.05)
    assert t["80-84.9%"]["n"] == 2 and t["80-84.9%"]["actual_rate"] == 1.0
    assert t["95%+"]["n"] == 1
    assert t["60-64.9%"]["n"] == 0 and t["60-64.9%"]["actual_rate"] is None
    assert sum(x["n"] for x in t.values()) == 5  # the 0.40 pick is below every band


def test_threshold_table_is_cumulative():
    p = [0.55, 0.61, 0.72, 0.91, 0.97]
    w = [0, 1, 1, 1, 1]
    t = {x["threshold"]: x for x in r.threshold_table(p, w)}
    assert t[0.55]["n"] == 5 and t[0.60]["n"] == 4 and t[0.90]["n"] == 2 and t[0.95]["n"] == 1
    assert t[0.60]["share_of_events"] == pytest.approx(0.8)
    assert t[0.60]["expected_wins"] == pytest.approx(0.61 + 0.72 + 0.91 + 0.97)


def test_top_pick_two_and_three_way():
    assert r.top_pick([0.3, 0.7]) == (1, 0.7)
    assert r.top_pick([0.45, 0.25, 0.30]) == (0, 0.45)
    with pytest.raises(ValueError):
        r.top_pick([])


def test_multiclass_metrics():
    rows = [[0.5, 0.3, 0.2], [0.1, 0.1, 0.8]]
    ll = r.multiclass_log_loss(rows, [0, 2])
    assert ll == pytest.approx([-math.log(0.5), -math.log(0.8)])
    br = r.multiclass_brier(rows, [0, 2])
    assert br[0] == pytest.approx(0.25 + 0.09 + 0.04)


def test_wilson_and_bootstrap():
    lo, hi = r.wilson(80, 100)
    assert lo < 0.8 < hi
    assert r.wilson(0, 0) == (None, None)
    a = np.array([0.5, 0.6, 0.7]); b = a - 0.1
    m, lo, hi = r.paired_bootstrap_ci(a, b, seed=1)
    assert m == pytest.approx(0.1) and lo == pytest.approx(0.1) and hi == pytest.approx(0.1)
    assert r.paired_bootstrap_ci(a, b, seed=1) == r.paired_bootstrap_ci(a, b, seed=1)
    with pytest.raises(ValueError):
        r.paired_bootstrap_ci(a, b[:2], seed=1)
