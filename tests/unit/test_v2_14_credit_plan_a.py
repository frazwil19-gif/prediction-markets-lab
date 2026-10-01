"""V2-14 Credit Plan A: fixtures-first gating (football), safe upcoming-event gate (tennis), caps/floors, accounting.
No network: every API call is monkeypatched."""
from __future__ import annotations

import importlib.util
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from prediction_markets_lab.ingestion import the_odds_api_loader as L
from prediction_markets_lab.ops import credit_ledger as CL
from prediction_markets_lab.prediction_platform import adapters as A

REPO = Path(__file__).resolve().parents[2]
NOW = datetime(2026, 10, 7, 13, 0, tzinfo=timezone.utc)


def _load(name):
    spec = importlib.util.spec_from_file_location(f"{name}_t14", REPO / f"scripts/{name}.py")
    m = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = m
    spec.loader.exec_module(m)
    return m


def ev(hours):
    return {"id": f"e{hours}", "commence_time": (NOW + timedelta(hours=hours)).isoformat().replace("+00:00", "Z")}


@pytest.fixture
def cfg(monkeypatch):
    monkeypatch.setenv("THE_ODDS_API_KEY", "test-key-not-real")
    budget = json.loads((REPO / "config/api_budget.json").read_text())["consumers"]["football_daily_scan"]
    return L.TheOddsApiConfig(gate_horizon_hours=budget["fixture_gate_hours"], hard_floor_remaining=budget["hard_floor_remaining"])


def test_budget_config_plan_a():
    b = json.loads((REPO / "config/api_budget.json").read_text())
    c = b["consumers"]
    assert sum(x["monthly_cap"] for x in c.values()) <= b["monthly_target_max"] <= b["monthly_plan_limit"] - b["global_reserve_remaining"]
    assert c["tennis_prediction_board"]["monthly_cap"] == 150 and c["tennis_prediction_board"]["min_remaining"] == 100
    assert c["nba_prediction_board"]["min_remaining"] == 100 and c["football_daily_scan"]["hard_floor_remaining"] == 25
    # the gate horizon IS the unified ledger's football first-snapshot window (no separate magic number)
    assert c["football_daily_scan"]["fixture_gate_hours"] * 60 == A.FOOTBALL_WINDOW_MIN


def test_gate_pays_only_with_a_fixture_inside_the_horizon(cfg, monkeypatch):
    monkeypatch.setattr(L, "fetch_events_raw", lambda sk, c, h=None: [ev(60), ev(200)])
    assert not L.fixture_gate("soccer_epl", cfg, NOW).pay
    monkeypatch.setattr(L, "fetch_events_raw", lambda sk, c, h=None: [ev(60), ev(47.5)])
    g = L.fixture_gate("soccer_epl", cfg, NOW)
    assert g.pay and g.events_in_horizon == 1
    monkeypatch.setattr(L, "fetch_events_raw", lambda sk, c, h=None: [ev(-2)])          # already started only
    assert not L.fixture_gate("soccer_epl", cfg, NOW).pay


def test_gate_fails_open_on_unparseable_time_and_closed_on_credit_floor(cfg, monkeypatch):
    monkeypatch.setattr(L, "fetch_events_raw", lambda sk, c, h=None: [{"id": "x", "commence_time": "garbage"}])
    assert L.fixture_gate("soccer_epl", cfg, NOW).pay

    def low(sk, c, h=None):
        h.update({"x-requests-remaining": "20"})
        return [ev(10)]
    monkeypatch.setattr(L, "fetch_events_raw", low)
    g = L.fixture_gate("soccer_epl", cfg, NOW)
    assert not g.pay and "credit floor" in g.reason


def test_fetch_and_canonicalise_skips_only_gated_leagues(cfg, monkeypatch):
    windows = {"soccer_epl": [ev(30)], "soccer_efl_champ": [ev(100)], "soccer_spl": []}
    monkeypatch.setattr(L, "fetch_events_raw", lambda sk, c, h=None: windows[sk])
    paid = []

    def odds(sk, c, h=None):
        paid.append(sk)
        h.update({"x-requests-last": "2"})
        return []
    monkeypatch.setattr(L, "fetch_odds_raw", odds)
    log: list = []
    _, _, warnings = L.fetch_and_canonicalise(cfg, now=NOW, call_log=log)
    assert paid == ["soccer_epl"]
    assert [(x["call"], x["outcome"]) for x in log] == [("odds:soccer_epl", "PAID"), ("odds:soccer_efl_champ", "SKIPPED"),
                                                       ("odds:soccer_spl", "SKIPPED")]
    assert sum(x.get("credits_saved_estimate", 0) for x in log) == 4 and len([w for w in warnings if "skipped" in w]) == 2


def test_no_gate_keeps_previous_behaviour(monkeypatch):
    monkeypatch.setenv("THE_ODDS_API_KEY", "test-key-not-real")
    monkeypatch.setattr(L, "fetch_events_raw", lambda *a, **k: pytest.fail("events must not be called without a gate"))
    paid = []
    monkeypatch.setattr(L, "fetch_odds_raw", lambda sk, c, h=None: paid.append(sk) or [])
    L.fetch_and_canonicalise(L.TheOddsApiConfig())
    assert paid == list(L.TheOddsApiConfig().sport_keys)


def test_daily_scan_builds_gated_config_and_logs(tmp_path, monkeypatch):
    m = _load("run_daily_scan")
    c = m.gated_odds_config()
    assert c.gate_horizon_hours == 48 and c.hard_floor_remaining == 25 and c.markets == ("h2h", "totals")
    monkeypatch.setattr(m, "CREDIT_LEDGER", tmp_path / "ledger.csv")
    m.log_calls([{"call": "odds:soccer_epl", "outcome": "PAID", "credits_charged": "2", "headers": {"x-requests-used": "9"}},
                 {"call": "odds:soccer_spl", "outcome": "SKIPPED", "reason": "no fixture", "credits_saved_estimate": 2}])
    rows = CL.read(tmp_path / "ledger.csv")
    assert [(r["outcome"], r["credits_charged"], r["credits_saved_estimate"]) for r in rows] == \
        [(CL.PAID, "2", "0"), (CL.SKIPPED_GATE, "0", "2")]


def test_tennis_gate_never_applies_a_horizon():
    m = _load("run_tennis_prediction_board")
    assert m.has_upcoming_event([ev(-1), ev(300)], NOW)               # far-future event still pays (frozen snapshot rule)
    assert not m.has_upcoming_event([ev(-1), ev(-5)], NOW)            # only started events -> 0 credits
    assert not m.has_upcoming_event([], NOW)
    assert m.has_upcoming_event([{"commence_time": "??"}], NOW)        # fail open


def test_credit_report_counts_spend_and_savings(tmp_path):
    m = _load("credit_report")
    p = tmp_path / "status/credit_ledger.csv"
    t = datetime(2026, 10, 3, 14, tzinfo=timezone.utc)
    CL.append(p, "football_daily_scan", "odds:soccer_epl", CL.PAID, 2, 0, {"x-requests-used": "20"}, now=t)
    CL.append(p, "football_daily_scan", "odds:soccer_spl", CL.SKIPPED_GATE, 0, 2, None, "no fixture", now=t)
    CL.append(p, "tennis_prediction_board", "odds:k", CL.PAID, 1, 0, {"x-requests-used": "21"}, now=t)
    CL.append(p, "tennis_prediction_board", "odds:k", CL.PAID, 1, 0, None, now=datetime(2026, 9, 30, tzinfo=timezone.utc))
    r = m.build(tmp_path, datetime(2026, 10, 3, 20, tzinfo=timezone.utc))
    assert r["by_consumer"]["football_daily_scan"] == {"paid_calls": 1, "credits_charged": 2, "skipped_calls": 1,
                                                       "credits_saved_estimate": 2}
    assert r["by_consumer"]["tennis_prediction_board"]["credits_charged"] == 1            # September row excluded
    assert r["account_used_month_to_date_latest_counter"] == 21
    assert r["football_counterfactual"] == {"scan_days_logged": 1, "baseline_credits_if_ungated": 6, "actual": 2}
    assert "Plan A to date" in m.render_md(r)
