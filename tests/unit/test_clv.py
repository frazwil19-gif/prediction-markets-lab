import importlib.util
import shutil
from datetime import datetime, timedelta, timezone
from pathlib import Path

import yaml

from prediction_markets_lab.clv import core as C

REPO = Path(__file__).resolve().parents[2]
CFG = yaml.safe_load((REPO / "config/clv.yaml").read_text())
NOW = datetime(2026, 10, 9, 12, 0, tzinfo=timezone.utc)
spec = importlib.util.spec_from_file_location("clv_script", REPO / "scripts/clv.py")
S = importlib.util.module_from_spec(spec)
spec.loader.exec_module(S)


def shadow(pid, t, decision="REJECT", reasons="NET_EV_BELOW_PAPER_GATE", ev="0.005", odds="1.6", sport="tennis"):
    return {"prediction_id": pid, "evaluated_at": t, "sport": sport, "engine_id": "wta_match_winner.betfair_market",
            "engine_version": "1", "market": "match_winner", "selection": "A", "probability": "0.63", "decimal_odds": odds,
            "source": "betway", "commission": "0", "net_ev": ev, "bsv2_decision": decision, "bsv2_reasons": reasons,
            "event_start": "2026-10-09T12:20:00+00:00", "price_observed_at": t, "price_age_minutes": "0.5"}


LEDGER = {p: {"event_key": f"tennis|tennis_wta_x|ev{p}", "event_name": "A v B"} for p in "abcdef"}


def test_study_cohort_first_clean_evaluation_only():
    rows = [shadow("a", "2026-10-08T10:00:00+00:00"),                       # before study start: excluded
            shadow("b", "2026-10-08T18:00:00+00:00", reasons="EXCHANGE_SPREAD_TOO_WIDE|NET_EV_NOT_POSITIVE"),
            shadow("b", "2026-10-08T20:00:00+00:00", reasons="NET_EV_NOT_POSITIVE", ev="-0.02"),   # first CLEAN eval
            shadow("b", "2026-10-09T08:00:00+00:00", reasons="NET_EV_BELOW_PAPER_GATE", ev="0.015"),  # never replaces
            shadow("c", "2026-10-08T18:00:00+00:00", decision="PAPER_BET", reasons="ALL_PAPER_GATES_PASSED", ev="0.03"),
            shadow("d", "2026-10-08T18:00:00+00:00", reasons="NET_EV_BELOW_PAPER_GATE|OUTSIDE_EVENT_HORIZON"),
            shadow("e", "2026-10-08T18:00:00+00:00", sport="basketball")]
    co = {t["prediction_id"]: t for t in C.study_cohort(rows, LEDGER, CFG)}
    assert set(co) == {"b", "c"}
    assert co["b"]["ev_band"] == "<0" and co["b"]["decided_at"].startswith("2026-10-08T20")
    assert co["c"]["ev_band"] == "2-4" and co["c"]["event_key"] == "tennis|tennis_wta_x|evc"
    assert not C.capture_eligible(co["b"], CFG) and C.capture_eligible(co["c"], CFG)


def test_bands_and_clv_math():
    b = CFG["study"]["bands"]
    assert [C.band(x, b) for x in (-0.001, 0.0, 0.0099, 0.01, 0.02, 0.0399, 0.04)] == ["<0", "0-1", "0-1", "1-2", "2-4", "2-4", "4+"]
    r = C.clv_row({"entry_odds": "2.0", "entry_commission": "0", "p_close": "0.55", "entry_p": "0.52",
                   "close_same_book_odds": "1.8", "close_best_uk_odds": "1.9"})
    assert abs(r["fair_clv"] - 0.10) < 1e-9 and abs(r["price_clv_same_book"] - (2 / 1.8 - 1)) < 1e-9
    assert abs(r["p_move"] - 0.03) < 1e-9
    ex = C.clv_row({"entry_odds": "2.0", "entry_commission": "0.05", "p_close": "0.5", "entry_p": "0.5",
                    "close_same_book_odds": "", "close_best_uk_odds": ""})
    assert abs(ex["fair_clv"] - (0.5 * 1.95 - 1)) < 1e-9 and ex["price_clv_same_book"] is None


def _event(start):
    return {"id": "evc", "commence_time": start, "home_team": "A", "away_team": "B", "bookmakers": [
        {"key": "betfair_ex_uk", "markets": [{"key": "h2h", "outcomes": [{"name": "A", "price": 1.60}, {"name": "B", "price": 2.70}]},
                                             {"key": "h2h_lay", "outcomes": [{"name": "A", "price": 1.62}, {"name": "B", "price": 2.74}]}]},
        {"key": "betway", "markets": [{"key": "h2h", "outcomes": [{"name": "A", "price": 1.57}, {"name": "B", "price": 2.5}]}]},
        {"key": "williamhill", "markets": [{"key": "h2h", "outcomes": [{"name": "A", "price": 1.55}, {"name": "B", "price": 2.6}]}]}]}


def test_measure_uses_exchange_mid_and_never_after_start():
    t = C.study_cohort([shadow("c", "2026-10-08T18:00:00+00:00", decision="PAPER_BET", reasons="X", ev="0.03")], LEDGER, CFG)[0]
    ev = _event("2026-10-09T12:20:00Z")
    m = C.measure(t, ev, NOW, 10, "tennis_wta_x")
    assert m["close_basis"] == "EXCHANGE_MID" and m["close_same_book_odds"] == 1.57 and m["close_best_uk_book"] == "betway"
    assert m["capture_quality"] == "PRE_CLOSE" and m["minutes_before_start"] == 20.0
    assert C.measure(t, ev, NOW + timedelta(minutes=21), 10, "x") is None
    assert C.sport_key({"event_key": "nfl|abc"}, {}) == "americanfootball_nfl"


def _tmp_repo(tmp_path: Path) -> Path:
    for f in ("config/clv.yaml", "config/api_budget.json", "config/football_coverage.yaml", "config/bet_selection_v2.yaml"):
        (tmp_path / f).parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(REPO / f, tmp_path / f)
    t = C.study_cohort([shadow("c", "2026-10-08T18:00:00+00:00", decision="PAPER_BET", reasons="X", ev="0.005")], LEDGER, CFG)
    C.append(tmp_path / "research_shadow/clv/targets.csv", C.COHORT_FIELDS, t)
    return tmp_path


def test_capture_respects_floor_and_daily_cap(tmp_path):
    repo = _tmp_repo(tmp_path)
    calls = []

    def ev_ok(key, cfg, hdr):
        hdr["x-requests-remaining"] = "480"
        return []

    def odds(key, cfg, hdr):
        calls.append((key, cfg.markets))
        hdr["x-requests-last"] = "1"
        return [_event("2026-10-09T12:20:00Z")]
    s = S.capture(repo, NOW, ev_ok, odds)
    assert s["captured"] == 1 and calls == [("tennis_wta_x", ("h2h",))]
    assert S.capture(repo, NOW, ev_ok, odds)["captured"] == 0 and len(calls) == 1          # never re-captured
    low = _tmp_repo(tmp_path / "low")

    def ev_low(key, cfg, hdr):
        hdr["x-requests-remaining"] = "120"
        return []
    assert S.capture(low, NOW, ev_low, odds)["captured"] == 0 and len(calls) == 1          # below the floor: no call
    assert "SKIPPED_CREDIT_FLOOR" in (low / "research_shadow/clv/missed.csv").read_text()


def test_report_seals_0_2_bands_until_look(tmp_path):
    repo = _tmp_repo(tmp_path)
    r = S.report(repo, NOW)
    assert "sealed" in r["ev_band_study"]["bands"]["0-1"] and "fair_clv" in r["ev_band_study"]["bands"]["<0"]
    assert r["credits"]["monthly_cap"] == 100


def test_market_probe_summary_and_daily_limit(tmp_path):
    spec2 = importlib.util.spec_from_file_location("probe", REPO / "scripts/market_probe_c3.py")
    P = importlib.util.module_from_spec(spec2)
    spec2.loader.exec_module(P)
    for f in ("config/market_probe_c3.yaml", "config/api_budget.json"):
        (tmp_path / f).parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(REPO / f, tmp_path / f)
    now = datetime(2026, 10, 21, 12, tzinfo=timezone.utc)
    ev = {"id": "g1", "commence_time": "2026-10-21T23:30:00Z", "home_team": "H", "away_team": "A", "bookmakers": [
        {"key": b, "markets": [{"key": "totals", "outcomes": [{"name": "Over", "point": pt, "price": 1.91},
                                                             {"name": "Under", "point": pt, "price": 1.91}]}]}
        for b, pt in (("williamhill", 221.5), ("skybet", 222.5), ("paddypower", 221.5))]}
    calls = []

    def evs(key, cfg, hdr):
        hdr["x-requests-remaining"] = "450"
        return [{"commence_time": "2026-10-21T23:30:00Z"}]

    def odds(key, cfg, hdr):
        calls.append(key)
        hdr["x-requests-last"] = "2"
        return [ev]
    P.run(tmp_path, now, evs, odds)
    P.run(tmp_path, now + timedelta(hours=1), evs, odds)          # once per probe per UTC day
    assert calls == ["basketball_nba"]
    s = P.summarise(P._read(tmp_path / "research_shadow/market_probe_c3/quotes.csv"), {"min_uk_books_per_event": 3, "min_event_share": 0.5})
    t = s["nba_lines:totals"]
    assert t["events"] == 1 and t["median_uk_books"] == 3 and t["max_line_spread"] == 1.0 and not t["availability_kill"]
