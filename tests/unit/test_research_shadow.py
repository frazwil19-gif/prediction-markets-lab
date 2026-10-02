"""Track A research shadows: H1 power de-vig and H2 PRE_CLOSE_VALUE (diagnostic only)."""
from __future__ import annotations

import importlib.util
import json
import shutil
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from prediction_markets_lab.research_shadow import h1_devig as H1
from prediction_markets_lab.research_shadow import pre_close as PC

REPO = Path(__file__).resolve().parents[2]
NOW = datetime(2026, 10, 3, 14, 0, tzinfo=timezone.utc)


# ---------------- H1 ----------------
def test_power_devig_sums_to_one_and_lifts_favourite():
    odds = [1.30, 5.5, 11.0]
    pw, pr = H1.power_devig(odds), H1.proportional_devig(odds)
    assert sum(pw) == pytest.approx(1, abs=1e-9)
    assert pw[0] > pr[0] and pw[2] < pr[2]


def test_power_devig_rejects_bad_odds():
    with pytest.raises(ValueError):
        H1.power_devig([1.0, 3.0, 4.0])


def test_shadow_row_uses_complete_books_only(tmp_path):
    books = {"a": {"home": 2.0, "draw": 3.4, "away": 4.0}, "b": {"home": 2.1, "draw": 3.3}}
    frozen = {"home": 0.47, "draw": 0.28, "away": 0.24}
    r = H1.shadow_row("t", "m", {"competition": "Premier League"}, books, frozen)
    assert r["n_books"] == 1 and set(json.loads(r["book_odds_json"])) == {"a"}
    assert r["p_frozen_home"] == 0.47
    assert r["pn_power_home"] + r["pn_power_draw"] + r["pn_power_away"] == pytest.approx(1, abs=1e-5)
    assert H1.shadow_row("t", "m", {}, {"b": books["b"]}, frozen) is None
    p = tmp_path / "x.csv"
    assert H1.append_rows(p, [r]) == 1 and H1.append_rows(p, [r]) == 1
    assert len(p.read_text().splitlines()) == 3                    # header once, append-only


def test_scan_writes_h1_only_to_research_shadow():
    src = (REPO / "scripts/run_daily_scan.py").read_text()
    assert '"research_shadow"' in src and '"h1_devig"' in src
    assert "H1.shadow_row" in src and "H1.append_rows" in src


# ---------------- H2 ----------------
def sel(**kw):
    s = {"selection_id": "s1", "prediction_id": "p1", "rule_version": "bsv2-4", "sport": "tennis",
         "event_key": "tennis|tennis_atp_x|ev1", "event_name": "A v B", "event_start": (NOW + timedelta(minutes=40)).isoformat(),
         "selection": "B", "probability": "0.7", "decimal_odds": "1.5", "commission": "0", "source": "sport888",
         "decision_at": "d", "price_observed_at": "o"}
    s.update(kw)
    return s


def event(start_min=40, exch=True, uk=True):
    bms = []
    if exch:
        bms.append({"key": "betfair_ex_uk", "markets": [
            {"key": "h2h", "outcomes": [{"name": "A", "price": 3.0}, {"name": "B", "price": 1.5}]},
            {"key": "h2h_lay", "outcomes": [{"name": "A", "price": 3.1}, {"name": "B", "price": 1.52}]}]})
    if uk:
        bms += [{"key": "williamhill", "markets": [{"key": "h2h", "outcomes": [{"name": "A", "price": 2.8}, {"name": "B", "price": 1.44}]}]},
                {"key": "sport888", "markets": [{"key": "h2h", "outcomes": [{"name": "A", "price": 2.7}, {"name": "B", "price": 1.47}]}]}]
    return {"id": "ev1", "home_team": "A", "away_team": "B", "commence_time": (NOW + timedelta(minutes=start_min)).isoformat(),
            "bookmakers": bms}


def test_due_window_and_never_after_start():
    a = sel(selection_id="a")
    b = sel(selection_id="b", event_start=(NOW - timedelta(minutes=1)).isoformat())
    c = sel(selection_id="c", event_start=(NOW + timedelta(minutes=200)).isoformat())
    assert [s["selection_id"] for s in PC.due([a, b, c], set(), NOW, 75)] == ["a"]
    assert PC.due([a], {"a"}, NOW, 75) == []


def test_sport_keys():
    assert PC.sport_key_for(sel(), {}) == "tennis_atp_x"
    assert PC.sport_key_for(sel(event_key="nba|e9"), {}) == "basketball_nba"
    assert PC.sport_key_for(sel(event_key="football|Premier League|A v B|t"), {"Premier League": "soccer_epl"}) == "soccer_epl"
    assert PC.sport_key_for(sel(event_key="football|Unknown|A v B|t"), {"Premier League": "soccer_epl"}) is None


def test_reference_exchange_mid_then_uk_fallback():
    basis, p, uk, _ = PC.reference(event(), ["A", "B"])
    assert basis == "EXCHANGE_MID" and sum(p.values()) == pytest.approx(1) and "betfair_ex_uk" not in uk
    basis2, p2, _, _ = PC.reference(event(exch=False), ["A", "B"])
    assert basis2 == "UK_MEDIAN_FAIR" and p2["B"] > 0.6
    assert PC.reference(event(exch=False, uk=False), ["A", "B"]) is None


def test_measure_fields_and_quality():
    r = PC.measure(sel(), event(), NOW)
    assert r["clv_proxy_quality"] == "PRE_CLOSE" and r["best_uk_odds"] == 1.47 and r["n_uk_books"] == 2
    assert r["decision_odds"] == 1.5 and r["decision_probability"] == "0.7"            # copied, not modified
    p = r["p_ref"]
    assert r["pre_close_value"] == pytest.approx(p * 0.5 - (1 - p), abs=1e-6)
    assert PC.measure(sel(), event(start_min=5), NOW)["clv_proxy_quality"] == "NEAR_CLOSE"
    assert PC.measure(sel(), event(start_min=-1), NOW) is None


def test_find_event_football_requires_unique_name_match():
    s = sel(event_key="football|Premier League|A v B|t", event_name="A v B", selection="home")
    e = event()
    assert PC.find_event([e], s) is e
    assert PC.find_event([e, dict(e, id="ev2")], s) is None
    assert PC.measure(s, e, NOW) is None                   # no complete H/D/A quote -> no measurement
    fb = {"id": "f", "home_team": "A", "away_team": "B", "commence_time": e["commence_time"], "bookmakers": [
        {"key": "williamhill", "markets": [{"key": "h2h", "outcomes": [
            {"name": "A", "price": 1.6}, {"name": "Draw", "price": 4.0}, {"name": "B", "price": 5.5}]}]}]}
    r = PC.measure(s, fb, NOW)
    assert r["reference_basis"] == "UK_MEDIAN_FAIR" and r["best_uk_odds"] == 1.6 and r["selection"] == "home"


# ---------------- capture script budget guard ----------------
def _load_script():
    spec = importlib.util.spec_from_file_location("cpc", REPO / "scripts/capture_pre_close.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def _repo(tmp_path, selections):
    for f in ("config/api_budget.json", "config/football_coverage.yaml"):
        (tmp_path / f).parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(REPO / f, tmp_path / f)
    (tmp_path / "paper_betting_v2").mkdir()
    import csv
    with (tmp_path / "paper_betting_v2/selections.csv").open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(selections[0]))
        w.writeheader()
        w.writerows(selections)
    return tmp_path


def test_capture_spends_one_credit_per_key_and_logs(tmp_path):
    m = _load_script()
    repo = _repo(tmp_path, [sel(), sel(selection_id="s2")])
    calls = []

    def ev(key, cfg, h):
        h["x-requests-remaining"] = "450"
        return []

    def odds(key, cfg, h):
        calls.append((key, cfg.markets))
        h.update({"x-requests-last": "1", "x-requests-remaining": "449"})
        return [event()]
    out = m.run(repo, NOW, ev, odds)
    assert calls == [("tennis_atp_x", ("h2h",))] and out["captured"] == 2
    assert m.month_spend(repo / m.OUT_DIR / "credit_ledger.csv", NOW) == 1
    assert m.run(repo, NOW, ev, odds)["due"] == 0 and len(calls) == 1            # captured once only


def test_capture_respects_floor_and_cap(tmp_path):
    m = _load_script()
    repo = _repo(tmp_path, [sel()])
    called = []

    def low(key, cfg, h):
        h["x-requests-remaining"] = "0"
        return []
    out = m.run(repo, NOW, low, lambda *a: called.append(1))
    assert not called and out["captured"] == 0
    from prediction_markets_lab.ops import credit_ledger as CL
    for _ in range(25):
        CL.append(repo / m.OUT_DIR / "credit_ledger.csv", m.CONSUMER, "odds:x", CL.PAID, 1, 0, now=NOW)

    def ok(key, cfg, h):
        h["x-requests-remaining"] = "450"
        return []
    out = m.run(repo, NOW, ok, lambda *a: called.append(1))
    assert not called and out["skipped"][0][1] == "monthly cap"


def test_pre_close_not_in_cap_sum():
    b = json.loads((REPO / "config/api_budget.json").read_text())
    assert "pre_close_capture" not in b["consumers"] and b["pre_close_capture"]["monthly_cap"] == 25


def test_capture_logs_missed_and_isolates_failures(tmp_path):
    m = _load_script()
    past = sel(selection_id="old", event_start=(NOW - timedelta(minutes=30)).isoformat(), decision_at=(NOW - timedelta(hours=5)).isoformat())
    repo = _repo(tmp_path, [sel(), past])

    def ev(key, cfg, h):
        h["x-requests-remaining"] = "450"
        return []

    def boom(key, cfg, h):
        raise RuntimeError("network")
    out = m.run(repo, NOW, ev, boom)
    assert out["captured"] == 0
    rows = PC.read_rows(repo / m.OUT_DIR / "pre_close_missed.csv")
    assert {(r["selection_id"], r["status"]) for r in rows} == {("old", PC.NOT_CAPTURED), ("s1", PC.ATTEMPT_FAILED)}
    assert "ODDS_CALL_FAILED" in [r for r in rows if r["selection_id"] == "s1"][0]["reason"]
    m.run(repo, NOW, ev, boom)
    rows = PC.read_rows(repo / m.OUT_DIR / "pre_close_missed.csv")
    assert sum(r["status"] == PC.NOT_CAPTURED for r in rows) == 1                     # terminal row written once
    assert not (repo / m.OUT_DIR / "pre_close_value.csv").exists()               # nothing imputed


def test_measure_records_quote_timestamps():
    e = event()
    for b in e["bookmakers"]:
        for mk in b["markets"]:
            mk["last_update"] = f"2026-10-03T13:5{len(b['key']) % 10}:00Z"
    r = PC.measure(sel(), e, NOW)
    assert r["reference_quote_at"] and r["best_uk_quote_at"].startswith("2026-10-03T13:5")


# ---------------- H3/H7 panel ----------------
def test_panel_unusable_set_matches_bsv2():
    spec = importlib.util.spec_from_file_location("lpp", REPO / "scripts/live_price_panel.py")
    lpp = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(lpp)
    src = (REPO / "src/prediction_markets_lab/bet_selection_v2/evaluate.py").read_text()
    assert all(f'"{r}"' in src for r in lpp.UNUSABLE)


def test_panel_separates_decision_and_best_executable_price():
    spec = importlib.util.spec_from_file_location("lpp", REPO / "scripts/live_price_panel.py")
    lpp = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(lpp)
    rows, summary = lpp.build(REPO)
    if not rows:
        pytest.skip("no tennis decision-shadow rows in this checkout")
    need = {"decision_price", "decision_venue", "decision_price_basis", "decision_reasons", "best_executable_net_price",
            "best_executable_net_venue", "best_sportsbook_price", "exchange_back", "exchange_lay", "all_quotes_json"}
    assert need <= set(rows[0])
    assert all(r["decision_price_basis"] in (lpp.BEST_USABLE, lpp.FALLBACK) for r in rows)
    assert all(r["decision_price_basis"] == lpp.FALLBACK for r in rows if "EXCHANGE_SPREAD_TOO_WIDE" in r["decision_reasons"].split("|"))
