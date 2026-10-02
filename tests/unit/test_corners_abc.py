"""Corners A/B/C pipeline: quality rules, main line, timing, stacking, staged evaluation (synthetic data)."""
from __future__ import annotations

import numpy as np
import pandas as pd

from prediction_markets_lab.research_shadow import corners_abc as C


def quotes_for(ek, kickoff, capture, books, line=9.5, exch=None):
    rows = []
    for v, (o, u) in books.items():
        rows += [{"capture_ts": capture, "event_key": ek, "competition": "E0", "kickoff_utc": kickoff, "venue": v, "is_exchange": "False",
                  "line": line, "side": s, "back": px, "lay": np.nan, "quote_ts": capture, "source": "test"} for s, px in (("over", o), ("under", u))]
    for v, ((ob, ol), (ub, ul)) in (exch or {}).items():
        rows += [{"capture_ts": capture, "event_key": ek, "competition": "E0", "kickoff_utc": kickoff, "venue": v, "is_exchange": "True",
                  "line": line, "side": s, "back": b, "lay": l, "quote_ts": capture, "source": "test"} for s, b, l in (("over", ob, ol), ("under", ub, ul))]
    return rows


def test_quality_rules_one_sided_wide_spread_and_overround():
    q = pd.DataFrame(quotes_for("e", "2026-10-10T14:00:00Z", "2026-10-10T08:00:00Z", {"a": (1.9, 1.9), "b": (1.5, 1.5)},
                                exch={"x": ((2.0, 2.6), (1.9, 1.95))}))
    q = pd.concat([q, pd.DataFrame([{**q.iloc[0].to_dict(), "venue": "c"}])])          # one-sided venue c
    fair = C.valid_two_way(q)
    assert set(fair) == {("a", 9.5)}                    # b overround 0.33 > 0.15; x spread 30%; c one-sided


def test_build_rows_main_line_timing_and_outcome_join():
    k, cap_late, cap_ok = "2026-10-10T14:00:00Z", "2026-10-10T13:30:00Z", "2026-10-10T08:00:00Z"
    q = pd.DataFrame(quotes_for("e", k, cap_ok, {"a": (1.9, 1.9)}, 9.5) + quotes_for("e", k, cap_ok, {"a": (2.5, 1.55)}, 10.5)
                     + quotes_for("e", k, cap_late, {"a": (1.2, 4.0)}, 9.5))            # inside 60 min: ignored
    preds = pd.DataFrame([{"event_key": "e", "run_ts": "2026-10-10T07:41:00+00:00", **{f"p_total_over_{L}": 0.6 for L in C.LINES}},
                          {"event_key": "e", "run_ts": "2026-10-10T09:00:00Z", **{f"p_total_over_{L}": 0.1 for L in C.LINES}}])
    outs = pd.DataFrame([{"event_key": "e", "total_corners": 11}])
    df, exc = C.build_rows(preds, q, outs)
    r = df.iloc[0]
    assert r.main_line == 9.5 and abs(r.p_b - 0.5) < 1e-9 and r.p_a == 0.6 and r.y == 1     # A made before capture only


def test_staged_evaluation_and_stacking_recovers_signal():
    rng = np.random.default_rng(1)
    n = 500
    p_true = rng.uniform(0.3, 0.7, n)
    y = (rng.random(n) < p_true).astype(int)
    df = pd.DataFrame({"p_b": np.clip(p_true + rng.normal(0, 0.08, n), 0.05, 0.95), "p_a": np.clip(p_true + rng.normal(0, 0.08, n), 0.05, 0.95), "y": y})
    assert C.evaluate(df.iloc[:100])["stage"] == "COLLECTING"
    res = C.evaluate(df)
    assert res["stage"] == "CONFIRMATORY" and res["evaluation_block"] == 350
    assert res["eval_C_minus_B"]["mean"] < 0                 # independent info in A helps when it exists
    assert C.evaluate(pd.DataFrame())["n_events"] == 0
