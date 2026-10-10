"""Prop price probe 2: timing rule, one-shot guard, no key leakage, and the pre-registered audit/Gate 0 logic."""
from __future__ import annotations

import importlib.util
from datetime import datetime, timedelta, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
NOW = datetime(2026, 10, 9, 23, 0, tzinfo=timezone.utc)


def load(name):
    spec = importlib.util.spec_from_file_location(name, REPO / f"scripts/{name}.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def ev(i, hours):
    return {"id": f"e{i}", "home_team": f"H{i}", "away_team": f"A{i}", "commence_time": (NOW + timedelta(hours=hours)).isoformat()}


def test_choose_prefers_6_12h_and_never_beyond_24h():
    m = load("prop_price_probe_2")
    assert m.choose([ev(1, 3), ev(2, 8), ev(3, 11)], NOW)[0]["id"] == "e2"
    assert m.choose([ev(1, 3), ev(2, 20)], NOW) == (ev(1, 3), "ELIGIBLE_1_24H")
    assert m.choose([ev(1, 0.5), ev(2, 30), ev(3, 190)], NOW)[0] is None


def test_no_paid_call_when_not_eligible_and_one_shot(tmp_path, monkeypatch):
    m = load("prop_price_probe_2")
    m.OUT = tmp_path
    monkeypatch.setenv("THE_ODDS_API_KEY", "SECRETKEY")
    paid = []

    def gj(url, s, c, h):
        paid.append(url)
        h.update({"x-requests-last": "2", "x-requests-used": "14", "x-requests-remaining": "486"})
        return {"id": "e2", "bookmakers": []}
    m.main(NOW, lambda s, c, h: [ev(1, 190)], gj)
    assert not paid and (tmp_path / "attempts.csv").exists() and not (tmp_path / "result.json").exists()
    m.main(NOW, lambda s, c, h: [ev(2, 8)], gj)
    m.main(NOW, lambda s, c, h: [ev(2, 8)], gj)
    assert len(paid) == 1
    assert "SECRETKEY" not in "".join(p.read_text() for p in tmp_path.iterdir())


def _book(key, line_prices):
    return {"key": key, "title": key, "markets": [{"key": "alternate_totals_corners", "last_update": "2026-10-10T03:00:00Z", "outcomes": [
        o for line, (ov, un) in line_prices.items() for o in
        ([{"name": "Over", "price": ov, "point": line}] if ov else []) + ([{"name": "Under", "price": un, "point": line}] if un else [])]}]}


def test_audit_gate0_outcomes():
    a = load("prop_probe_audit")
    comm = {"betfair_ex_uk": 0.05, "matchbook": None}
    assert a.audit({"bookmakers": []}, comm)["markets"]["alternate_totals_corners"]["gate0"] == "C"
    one_sided = {"bookmakers": [_book("skybet", {9.5: (1.9, None)})]}
    assert a.audit(one_sided, comm)["markets"]["alternate_totals_corners"]["gate0"] == "B"
    unknown_exch = {"bookmakers": [_book("matchbook", {9.5: (1.9, 1.95)})]}
    assert a.audit(unknown_exch, comm)["markets"]["alternate_totals_corners"]["gate0"] == "B"
    thin = {"bookmakers": [_book("skybet", {9.5: (1.9, 1.8)})]}
    r = a.audit(thin, comm)["markets"]["alternate_totals_corners"]
    assert r["gate0"] == "A (thin)" and abs(r["lines"]["9.5"]["median_overround"] - (1 / 1.9 + 1 / 1.8 - 1)) < 1e-4
    robust = {"bookmakers": [_book(k, {9.5: (1.9, 1.85)}) for k in ("skybet", "williamhill", "paddypower")]}
    assert a.audit(robust, comm)["markets"]["alternate_totals_corners"]["gate0"] == "A"
    q = a.quotes(thin)[0]
    assert abs(q["fair_p_over"] + q["fair_p_under"] - 1) < 1e-4
    assert a.audit(robust, comm)["markets"]["alternate_totals_cards"]["gate0"] == "C"
