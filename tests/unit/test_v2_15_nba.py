"""V2-15 NBA readiness fixes around the FROZEN estimator: provenance, freshness, exhibitions, first-snapshot dedup,
settlement resilience, Stage A sigma. No network."""
from __future__ import annotations

import importlib.util
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

from prediction_markets_lab.bet_selection_v2 import prices as PR
from prediction_markets_lab.bet_selection_v2.evaluate import evaluate_prediction, load_config as load_bs
from prediction_markets_lab.prediction_platform import adapters as A
from prediction_markets_lab.prediction_platform import settle as S
from prediction_markets_lab.prediction_platform import stage_a as SA
from prediction_markets_lab.prediction_platform.registry import Registry
from prediction_markets_lab.prediction_platform.schema import to_row

REPO = Path(__file__).resolve().parents[2]
NOW = datetime(2026, 10, 21, 16, 0, tzinfo=timezone.utc)
REG = Registry.load()
CTX = A.RunContext(None, None, 1.33)


def _load(name):
    spec = importlib.util.spec_from_file_location(f"{name}_t15", REPO / f"scripts/{name}.py")
    m = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = m
    spec.loader.exec_module(m)
    return m


def book(key, home, away, age_min=10):
    return {"key": key, "last_update": (NOW - timedelta(minutes=age_min)).isoformat(),
            "markets": [{"key": "h2h", "outcomes": [{"name": "Boston Celtics", "price": home},
                                                    {"name": "Washington Wizards", "price": away}]}]}


def event(books, home="Boston Celtics", away="Washington Wizards", hours=8, eid="g1"):
    return {"id": eid, "home_team": home, "away_team": away, "commence_time": (NOW + timedelta(hours=hours)).isoformat(),
            "bookmakers": books}


BOOKS = [book("williamhill", 1.20, 4.6), book("skybet", 1.22, 4.5), book("betway", 1.21, 4.4), book("betfair_ex_uk", 1.25, 5.0)]


def test_activation_date_unchanged():
    assert REG.get(A.NBA)["activation_date_utc"] == "2026-10-20"
    assert A.nba_from_odds([event(BOOKS)], REG, CTX, datetime(2026, 10, 19, tzinfo=timezone.utc), "t")[0] == []


def test_frozen_estimator_unchanged_and_actual_book_recorded():
    preds, _ = A.nba_from_odds([event(BOOKS)], REG, CTX, NOW, "t")
    p = preds[0]
    h, a = [1.20, 1.22, 1.21], [4.6, 4.5, 4.4]                      # exchange excluded, as before
    ih, ia = 1 / (sum(h) / 3), 1 / (sum(a) / 3)
    assert abs(p.estimated_probability - ih / (ih + ia)) < 1e-12 and p.selection == "Boston Celtics"
    assert p.live_price == 1.22 and p.live_price_source == "odds_api:skybet"


def test_stage_b_can_now_price_nba():
    p = to_row(A.nba_from_odds([event(BOOKS)], REG, CTX, NOW, "t")[0][0])
    snap = PR.from_ledger_row(p)
    assert snap is not None and snap.source == "skybet" and snap.p_same_snapshot == p["estimated_probability"]
    best, _ = evaluate_prediction(p, [snap], load_bs(), NOW)
    assert "NO_EXECUTABLE_PRICE" not in best.reasons and best.net_ev is not None


def test_stale_books_excluded_before_book_count():
    books = [book("williamhill", 1.20, 4.6), book("skybet", 1.22, 4.5), book("betway", 1.21, 4.4, age_min=7 * 60)]
    preds, skips = A.nba_from_odds([event(books)], REG, CTX, NOW, "t")
    assert preds == [] and "1 stale excluded" in skips[0].reason


def test_exhibition_skipped():
    preds, skips = A.nba_from_odds([event(BOOKS, home="Team LeBron", away="Team Giannis")], REG, CTX, NOW, "t")
    assert preds == [] and skips[0].reason.startswith("NOT_REGULAR_COMPETITION")


def test_favourite_flip_does_not_create_second_row():
    m = _load("run_unified_prediction_board")
    first = A.nba_from_odds([event(BOOKS)], REG, CTX, NOW, "t")[0]
    flipped_books = [book(k, 4.5, 1.2) for k in ("williamhill", "skybet", "betway")]
    later = A.nba_from_odds([event(flipped_books)], REG, CTX, NOW + timedelta(hours=1), "t")[0]
    assert later[0].selection == "Washington Wizards" and later[0].prediction_id != first[0].prediction_id
    keep, skips = m.first_snapshot_only(later, [to_row(first[0])])
    assert keep == [] and skips[0].reason == "ALREADY_PREDICTED_FIRST_SNAPSHOT_CANONICAL"
    keep2, _ = m.first_snapshot_only(first + first, [])
    assert len(keep2) == 1


def test_settlement_cadence_and_overdue_report():
    m = _load("run_unified_prediction_board")
    assert m.NBA_SCORES_EVERY_DAYS == 2 and m.NBA_SCORES_EVERY_DAYS < 3   # daysFrom=3 window keeps an overlap day
    p = to_row(A.nba_from_odds([event(BOOKS)], REG, CTX, NOW, "t")[0][0])
    assert m.nba_overdue([p], set(), NOW + timedelta(days=2)) == []
    od = m.nba_overdue([p], set(), NOW + timedelta(days=4))
    assert od[0]["status"] == "REVIEW_REQUIRED"
    assert m.nba_overdue([p], {p["prediction_id"]}, NOW + timedelta(days=9)) == []


def test_overtime_final_scores_settle_and_incomplete_do_not():
    p = to_row(A.nba_from_odds([event(BOOKS)], REG, CTX, NOW, "t")[0][0])
    ot = [{"id": "g1", "completed": True, "scores": [{"name": "Boston Celtics", "score": "121"},
                                                     {"name": "Washington Wizards", "score": "118"}]}]   # final incl. OT
    out = S.settle_from_odds_api_scores([p], set(), ot, NOW)
    assert out[0]["correct"] == 1 and out[0]["result"] == "Boston Celtics"
    live = [{**ot[0], "completed": False}]
    assert S.settle_from_odds_api_scores([p], set(), live, NOW) == []


def test_stage_a_nba_sigma_from_holdout_bands():
    ev = json.loads((REPO / "research/platform_v2/v2_15_nba/NBA_SIGMA_EVIDENCE.json").read_text())
    b80 = {b["band"]: b for b in ev["markets"]["moneyline"]}["80%+"]
    assert b80["rows"] == 550 and abs(b80["actual"] - 481 / 550) < 1e-12           # = verified holdout figures
    cfg = SA.load_config(REPO / "config/prediction_board_stage_a.yaml", REPO)
    se = SA.sport_sigma(cfg)
    p = to_row(A.nba_from_odds([event(BOOKS)], REG, CTX, NOW, "t")[0][0])
    board = SA.build([p], [], lambda x: [PR.from_ledger_row(x)], load_bs(), cfg, None, NOW, sport_se=se,
                     calibration_status={A.NBA: REG.get(A.NBA)["calibration_status"]})
    r = board["predictions"][0]
    band = next(b for b in ev["markets"]["moneyline"] if b["lo"] <= r["probability"] < b["hi"])
    assert r["sigma_method"] == SA.SIGMA_NBA and r["sigma"] == round(band["sigma_clustered_se"], 6)
    assert r["minutes_to_event_at_prediction"] == p["minutes_to_event"] and r["price_status"] != SA.UNAVAILABLE
