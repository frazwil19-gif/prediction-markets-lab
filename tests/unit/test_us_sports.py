"""NHL/NFL moneyline adapter + settlement (2026-10-08)."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from prediction_markets_lab.prediction_platform import adapters as A
from prediction_markets_lab.prediction_platform import settle as S
from prediction_markets_lab.prediction_platform.registry import Registry

NOW = datetime(2026, 10, 9, 12, 0, tzinfo=timezone.utc)


def ev(eid, hours, books):
    return {"id": eid, "commence_time": (NOW + timedelta(hours=hours)).isoformat().replace("+00:00", "Z"), "home_team": "Boston Bruins",
            "away_team": "Toronto Maple Leafs", "bookmakers": [{"key": k, "last_update": NOW.isoformat(), "markets": [{"key": "h2h", "outcomes": [
                {"name": "Boston Bruins", "price": h}, {"name": "Toronto Maple Leafs", "price": a}]}]} for k, h, a in books]}


def test_nhl_adapter_consensus_and_guards():
    reg = Registry.load()
    ctx = A.RunContext("MANUAL", NOW.isoformat(), 1.33)
    raw = [ev("g1", 10, [("b1", 1.60, 2.40), ("b2", 1.62, 2.35), ("b3", 1.58, 2.45), ("betfair_ex_uk", 1.7, 2.5)]),
           ev("g2", 10, [("b1", 1.6, 2.4)]), ev("g3", 50, [("b1", 1.6, 2.4), ("b2", 1.6, 2.4), ("b3", 1.6, 2.4)])]
    preds, skips = A.us_moneyline_from_odds(raw, reg, ctx, NOW, "icehockey_nhl", "t")
    assert len(preds) == 1 and preds[0].selection == "Boston Bruins" and preds[0].sport == "icehockey"
    assert 0.59 < preds[0].estimated_probability < 0.61 and preds[0].live_price == 1.62
    assert preds[0].engine_status == "PROVISIONAL_PROSPECTIVE" and preds[0].single_eligible is False
    reasons = " ".join(s.reason for s in skips)
    assert "DATA_INVALID" in reasons and "OUTSIDE_36H_WINDOW" in reasons


def test_settle_sport_param_and_ties():
    preds = [{"prediction_id": "x", "sport": "americanfootball", "event_id": "e1", "selection": "A"},
             {"prediction_id": "y", "sport": "americanfootball", "event_id": "e2", "selection": "A"},
             {"prediction_id": "z", "sport": "basketball", "event_id": "e1", "selection": "A"}]
    scores = [{"id": "e1", "completed": True, "scores": [{"name": "A", "score": "24"}, {"name": "B", "score": "17"}]},
              {"id": "e2", "completed": True, "scores": [{"name": "A", "score": "20"}, {"name": "B", "score": "20"}]}]
    out = S.settle_from_odds_api_scores(preds, set(), scores, NOW, sport="americanfootball")
    assert [o["prediction_id"] for o in out] == ["x"] and out[0]["correct"] == 1   # tie left for review; other sport untouched


def test_registry_us_engines():
    reg = Registry.load()
    assert reg.get("nfl_moneyline.market")["status"] == "VALIDATED_HISTORICAL" and reg.get("nfl_moneyline.market")["money_eligible"] is True
    assert reg.get("nhl_moneyline.market")["status"] == "PROVISIONAL_PROSPECTIVE" and reg.get("nhl_moneyline.market")["money_eligible"] is False
