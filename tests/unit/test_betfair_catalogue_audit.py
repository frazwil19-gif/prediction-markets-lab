"""Betfair catalogue audit: read-only whitelist, family classification, coverage matrix, no credential leakage."""
from __future__ import annotations

import importlib.util
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("bfa", REPO / "scripts/betfair_catalogue_audit.py")
B = importlib.util.module_from_spec(spec)
spec.loader.exec_module(B)
NOW = datetime(2026, 10, 9, 8, 0, tzinfo=timezone.utc)


def test_source_contains_no_order_methods():
    src = (REPO / "scripts/betfair_catalogue_audit.py").read_text()
    for m in ("placeOrders", "cancelOrders", "replaceOrders", "updateOrders", "listCurrentOrders", "account"):
        assert m not in src.replace("READ_ONLY", "")
    assert B.READ_ONLY_METHODS == {"listCompetitions", "listMarketTypes", "listEvents", "listMarketCatalogue", "listMarketBook"}


def test_client_refuses_non_read_methods():
    c = B.Client("k", "t", transport=lambda *a: pytest.fail("no request may be built"))
    with pytest.raises(PermissionError):
        c.call("placeOrders", {})


@pytest.mark.parametrize("code,name,fam", [("MATCH_ODDS", "Match Odds", "match_odds"), ("CORNER_ODDS", "Corners Over/Under 10.5", "corners"),
                                           ("BOOKING_ODDS", "Booking Points", "bookings_cards"), ("", "Player Shots On Target 1+", "player_sot"),
                                           ("TO_SCORE", "To Score", "player_to_score"), ("", "Player Shown A Card", "player_card"),
                                           ("", "Goalkeeper Saves 3+", "gk_saves"), ("OVER_UNDER_25", "Over/Under 2.5 Goals", "other"),
                                           ("BOTH_TEAMS_TO_SCORE", "Both teams to Score?", "other"), ("TOP_GOALSCORER", "Top Goalscorer", "other"),
                                           ("MATCH_ODDS_AND_BTTS", "Match Odds and Both teams to Score", "other"), ("TEAM_A_WIN_TO_NIL", "X Win to Nil", "other")])
def test_family_classification(code, name, fam):
    assert B.family_of(code, name) == fam


def fake_transport(calls):
    def t(url, body, headers):
        req = json.loads(body)
        m = req["method"].split("/")[-1]
        calls.append(m)
        p = req["params"]
        if m == "listCompetitions":
            return {"result": [{"competition": {"id": "10932509", "name": "English Premier League"}, "marketCount": 900},
                               {"competition": {"id": "1", "name": "English Premier League Women"}, "marketCount": 50},
                               {"competition": {"id": "2", "name": "Belgian Beloften Pro League Reserve"}, "marketCount": 999},
                               {"competition": {"id": "3", "name": "Belgian Pro League"}, "marketCount": 10}]}
        if m == "listMarketTypes":
            return {"result": [{"marketType": "MATCH_ODDS", "marketCount": 10}, {"marketType": "CORNER_ODDS", "marketCount": 10}]}
        if m == "listEvents":
            return {"result": [{"event": {"id": f"e{i}", "openDate": f"2026-10-10T1{i}:00:00Z"}} for i in range(2)]}
        if m == "listMarketCatalogue":
            e = p["filter"]["eventIds"][0]
            return {"result": [{"marketId": f"{e}.mo", "marketName": "Match Odds", "description": {"marketType": "MATCH_ODDS"}, "event": {"id": e},
                                "marketStartTime": "2026-10-10T11:30:00Z", "runners": [{}, {}, {}]}]
                    + ([{"marketId": f"{e}.c", "marketName": "Corners Over/Under 10.5", "description": {"marketType": "CORNER_ODDS"}, "event": {"id": e},
                         "marketStartTime": "2026-10-10T11:30:00Z", "runners": [{}, {}]}] if e == "e0" else [])}
        if m == "listMarketBook":
            out = []
            for mid in p["marketIds"]:
                n = 3 if mid.endswith(".mo") else 2
                out.append({"marketId": mid, "status": "OPEN", "inplay": False, "totalMatched": 1000.0,
                            "runners": [{"ex": {"availableToBack": [{"price": 2.0}], "availableToLay": [{"price": 2.04}]}} for _ in range(n)]})
            return {"result": out}
        raise AssertionError(m)
    return t


def test_audit_builds_coverage_matrix_with_read_methods_only(tmp_path, monkeypatch):
    calls = []
    cov, raw = B.audit(B.Client("APPKEY", "TOKEN", transport=fake_transport(calls)), NOW, 8, 10)
    assert set(calls) <= B.READ_ONLY_METHODS
    e0 = cov["competitions"]["E0"]
    assert e0["betfair_competition"]["name"] == "English Premier League"          # women's league excluded
    assert e0["families"]["match_odds"]["classification"] == "GOOD COVERAGE"
    assert e0["families"]["corners"]["classification"] == "PARTIAL COVERAGE"      # 1 of 2 events
    assert e0["families"]["player_sot"]["classification"] == "ABSENT"
    assert cov["competitions"]["E1"]["families"]["corners"]["classification"] == "UNRESOLVED"
    assert cov["competitions"]["B1"]["betfair_competition"]["name"] == "Belgian Pro League"   # reserve league excluded
    far, _ = B.audit(B.Client("APPKEY", "TOKEN", transport=fake_transport([])), NOW - timedelta(days=3), 8, 10)
    assert far["competitions"]["E0"]["families"]["corners"]["classification"] == "UNRESOLVED"  # events > 36h away not sampled
    monkeypatch.setattr(B, "OUT", tmp_path)
    B.write_outputs(cov, raw, NOW)
    text = "".join(p.read_text() for p in tmp_path.rglob("*") if p.is_file())
    assert "APPKEY" not in text and "TOKEN" not in text
