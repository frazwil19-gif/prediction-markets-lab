"""V2-6E pilot guard tests (no network, no paid calls)."""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("pilot", REPO / "scripts/v2_6e_historical_pilot.py")
P = importlib.util.module_from_spec(spec)
import sys  # noqa: E402
sys.modules["pilot"] = P
spec.loader.exec_module(P)


def _ev(i, ex=True, books=2, lu="2024-06-30T19:55:00Z"):
    mk = lambda k, a, b: {"key": k, "last_update": lu, "outcomes": [{"name": "Ann Able", "price": a}, {"name": "Bea Bold", "price": b}]}
    bm = []
    if ex:
        bm.append({"key": "betfair_ex_uk", "markets": [mk("h2h", 1.5, 2.9), mk("h2h_lay", 1.52, 3.0)]})
    for j in range(books):
        bm.append({"key": f"book{j}", "markets": [mk("h2h", 1.55, 2.6)]})
    return {"id": f"e{i}", "sport_key": "tennis_atp_wimbledon", "commence_time": "2024-07-01T10:00:00Z",
            "home_team": "Ann Able", "away_team": "Bea Bold", "bookmakers": bm}


def _payload(events):
    return {"timestamp": "2024-06-30T20:00:00Z", "previous_timestamp": "x", "next_timestamp": "y", "data": events}


@pytest.fixture
def tmp_out(tmp_path, monkeypatch):
    monkeypatch.setattr(P, "OUT", tmp_path)
    monkeypatch.setattr(P, "RAW", tmp_path / "raw")
    return tmp_path


def test_plan_is_frozen_and_within_cap():
    plan = P.build_plan(P.match_days_from_tennis_data(None))
    assert len(plan) * P.COST_PER_CALL <= P.HARD_CAP
    assert plan[0].sport_key == "tennis_atp_wimbledon" and plan[0].snapshot == "2024-06-30T20:00:00Z"
    assert len({c.fname for c in plan}) == len(plan)


def test_execute_refuses_without_authorisation(monkeypatch, capsys):
    monkeypatch.delenv("PILOT_AUTHORISED", raising=False)
    monkeypatch.setattr("sys.argv", ["x", "execute"])
    assert P.main() == 2 and "REFUSED" in capsys.readouterr().out


def test_validation_gate():
    assert P.validation_gate(_payload([_ev(1), _ev(2)]))[0]
    ok, why = P.validation_gate(_payload([_ev(1, ex=False)]))
    assert not ok and "NO_BETFAIR_BACK_AND_LAY" in why
    ok, why = P.validation_gate(_payload([_ev(1, books=1), _ev(2, books=0)]))
    assert not ok and "FEWER_THAN_HALF_EVENTS_WITH_2_UK_BOOKS" in why
    ok, why = P.validation_gate(_payload([_ev(1, lu="")]))
    assert not ok and "MISSING_QUOTE_LAST_UPDATE" in why


class FakeAPI:
    def __init__(self, payload, cost=10):
        self.used, self.n, self.payload, self.cost = 1000, 0, payload, cost

    def __call__(self, url):
        assert "apiKey=k" in url and "/historical/sports/" in url and "regions=uk" in url and "markets=h2h" in url
        self.n += 1
        self.used += self.cost
        return self.payload, {"x-requests-used": str(self.used), "x-requests-remaining": "0", "x-requests-last": str(self.cost)}


def _plan(n):
    return [P.Call("tennis_atp_wimbledon", f"2024-07-{i + 1:02d}", f"2024-06-{30 if i == 0 else i:02d}T20:00:00Z") for i in range(n)]


def test_validation_failure_stops_after_first_call(tmp_out):
    api = FakeAPI(_payload([_ev(1, ex=False)]))
    log = P.execute(_plan(5), "k", getter=api)
    assert api.n == 1 and log["stopped"] == "VALIDATION_GATE_FAILED" and log["spent"] == 10


def test_hard_cap_enforced_and_idempotent(tmp_out):
    api = FakeAPI(_payload([_ev(1)]))
    log = P.execute(_plan(10), "k", getter=api, cap=45)
    assert api.n == 4 and log["spent"] == 40 and log["stopped"].startswith("HARD_CAP")
    api2 = FakeAPI(_payload([_ev(1)]))
    log2 = P.execute(_plan(4), "k", getter=api2, cap=45)   # already-saved snapshots are never re-bought
    assert api2.n == 0 and all("skipped" in c for c in log2["calls"])


def test_unexpected_cost_stops(tmp_out):
    api = FakeAPI(_payload([_ev(1)]), cost=20)
    log = P.execute(_plan(3), "k", getter=api)
    assert api.n == 1 and log["stopped"].startswith("UNEXPECTED_COST")


def test_pilot_never_touches_paper_ledgers():
    src = (REPO / "scripts/v2_6e_historical_pilot.py").read_text()
    assert "paper_betting_v2" not in src.replace("Never writes paper_betting_v2/", "")
    assert "record_selections" not in src and "append_settlements" not in src
