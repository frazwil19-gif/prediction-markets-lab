"""Liquidity-curve report: dry run on mock capture summaries (dedupe, ordering, corners/SOT only)."""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("blr", REPO / "scripts/betfair_liquidity_report.py")
R = importlib.util.module_from_spec(spec)
spec.loader.exec_module(R)


def summ(ts, both):
    g = {"family": "player_sot", "events": 5, "markets": 5, "runners": 220, "both": both, "back_only": 220 - both, "lay_only": 0, "none": 0,
         "two_sided_share": both / 220, "spread_p25_p50_p75": [0.03, 0.06, 0.12], "back_size_p25_p50_p75": [2, 5, 9],
         "lay_size_p25_p50_p75": [1, 3, 6], "market_matched_p25_p50_p75": [10, 40, 90], "mins_to_kickoff_range": [50, 70]}
    c = dict(g, family="corners", runners=10, both=10, back_only=0, markets_passing_preregistered_10pct_gate="2/5")
    o = dict(g, family="bookings_cards")
    return {"capture_ts": ts, "groups": {"E0|SHOTS_ON_TARGET_P1": g, "E0|OVER_UNDER_105_CORNR": c, "E0|BOOKING_ODDS": o}}


def test_report_dedupes_orders_and_filters(tmp_path):
    a, b = tmp_path / "a.json", tmp_path / "b.json"
    a.write_text(json.dumps(summ("2026-10-10T13:00:00", 120)))
    b.write_text(json.dumps(summ("2026-10-10T08:15:00", 20)))
    s = R.load([str(a), str(b), str(a)])
    assert [x["capture_ts"] for x in s] == ["2026-10-10T08:15:00", "2026-10-10T13:00:00"]
    t = R.table(s)
    assert t.count("SHOTS_ON_TARGET_P1") == 2 and "BOOKING_ODDS" not in t and "2/5" in t
