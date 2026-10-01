"""V2-11 (bsv2-4): the unified-ledger Betfair quote must carry the same-scan exchange quality or fail closed."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path

import yaml

from prediction_markets_lab.bet_selection_v2 import prices as PR
from prediction_markets_lab.bet_selection_v2.evaluate import (MULTI, PAPER_BET, REJECT, WATCH, evaluate_prediction,
                                                             load_config)
from prediction_markets_lab.prediction_platform import stage_a as SA
from prediction_markets_lab.prediction_platform.schema import PREDICTION_FIELDS

REPO = Path(__file__).resolve().parents[2]
CFG = load_config()
SCAN = "2026-09-30T12:54:22.695202+00:00"
NOW = datetime(2026, 9, 30, 12, 55, tzinfo=timezone.utc)
SPREAD = ("EXCHANGE_SPREAD_TOO_WIDE", "EXCHANGE_SPREAD_UNKNOWN")


def ledger_row(p=0.60, live="1.80", src="betfair_ex_uk back (odds_api)", sport="tennis", eid="e1", made=SCAN):
    return {**{k: "" for k in PREDICTION_FIELDS}, "prediction_id": "p1", "sport": sport, "engine_id": "atp_match_winner.betfair_market",
            "engine_status": "VALIDATED_HISTORICAL", "event_id": eid, "event_key": f"tennis|k|{eid}", "event_name": "Ann Able v Bea Bold",
            "event_start": (NOW + timedelta(hours=10)).isoformat(), "market": "match_winner", "selection": "Ann Able",
            "estimated_probability": str(p), "prediction_timestamp": made, "prediction_valid": "True",
            "live_price": live, "live_price_source": src}


def prob_row(width="0.01", source="EXCHANGE_MID", scan=SCAN, eid="e1", pa=0.60):
    return {"scan_timestamp_utc": scan, "sport_key": "k", "event_id": eid, "player_a": "Ann Able", "player_b": "Bea Bold",
            "source": source, "source_validated": "True", "p_a": str(pa), "p_b": str(1 - pa), "exchange_spread_prob": width}


def decide(row, prob):
    s = PR.from_ledger_row(row, prob)
    return s, evaluate_prediction(row, [s], CFG, NOW)[0]


def test_config_is_bsv2_4_with_gates_unchanged():
    c = yaml.safe_load((REPO / "config/bet_selection_v2.yaml").read_text())
    assert c["rule_version"] == "bsv2-4"
    assert c["data_quality"]["max_exchange_spread_prob"] == 0.03
    g = c["decision_gates"]["paper_bet"]
    assert (g["min_probability"], g["min_net_ev"], g["min_decimal_odds"], g["max_hours_to_event"], g["max_price_age_minutes"]) == \
        (0.50, 0.02, 1.33, 24.0, 240.0)
    assert c["real_money_enabled"] is False and c["multi"]["enabled"] is False


def test_ledger_quote_with_valid_narrow_spread_is_assessed_normally():
    s, b = decide(ledger_row(0.60, live="1.80"), [prob_row("0.01")])
    assert s.p_same_spread == 0.01 and s.p_same_source == "EXCHANGE_MID"
    assert not set(SPREAD) & set(b.reasons) and b.net_ev is not None     # existing gates decide (EV etc.)


def test_ledger_quote_with_wide_spread_rejected():
    _, b = decide(ledger_row(0.60), [prob_row("0.09")])
    assert b.decision == REJECT and "EXCHANGE_SPREAD_TOO_WIDE" in b.reasons


def test_ledger_quote_with_missing_spread_fails_closed():
    _, b = decide(ledger_row(0.60), [prob_row("")])
    assert b.decision == REJECT and "EXCHANGE_SPREAD_UNKNOWN" in b.reasons


def test_stale_spread_from_another_scan_is_never_used():
    s, b = decide(ledger_row(0.60), [prob_row("0.01", scan="2026-09-29T20:11:50.324947+00:00")])
    assert s.p_same_source == PR.UNRESOLVED_SOURCE and s.p_same_spread is None
    assert b.decision == REJECT and "EXCHANGE_SPREAD_UNKNOWN" in b.reasons


def test_mismatched_event_spread_is_never_used():
    s, b = decide(ledger_row(0.60), [prob_row("0.01", eid="other")])
    assert s.p_same_source == PR.UNRESOLVED_SOURCE and "EXCHANGE_SPREAD_UNKNOWN" in b.reasons


def test_no_probability_rows_fails_closed_by_default():
    s = PR.from_ledger_row(ledger_row())
    assert s.p_same_source == PR.UNRESOLVED_SOURCE
    assert "EXCHANGE_SPREAD_UNKNOWN" in evaluate_prediction(ledger_row(), [s], CFG, NOW)[0].reasons


def test_exchange_back_source_fails_closed_for_financial_use():
    """bsv2-4 (revised after the Track-0 audit): a back-only Betfair P has no measurable book width, so it can never be
    financially assessed (bsv2-3 exempted it). It is never observed prospectively so far (0 of 172 snapshots)."""
    s, b = decide(ledger_row(0.70, live="1.80"), [prob_row("", source="EXCHANGE_BACK", pa=0.70)])
    assert s.p_same_source == "EXCHANGE_BACK" and b.decision == REJECT and "EXCHANGE_SPREAD_UNKNOWN" in b.reasons
    price = [{"scan_timestamp_utc": SCAN, "sport_key": "k", "event_id": "e1", "player_a": "Ann Able", "player_b": "Bea Bold",
              "bookmaker": "betway", "market": "h2h", "odds_a": "1.80", "odds_b": "2.1", "last_update": SCAN}]
    snaps = PR.tennis_from_snapshots(ledger_row(0.70), price, [prob_row("", source="EXCHANGE_BACK", pa=0.70)])
    assert "EXCHANGE_SPREAD_UNKNOWN" in evaluate_prediction(ledger_row(0.70), snaps, CFG, NOW)[0].reasons


def test_football_bookmaker_ledger_quote_unaffected():
    row = ledger_row(0.60, live="1.80", src="odds_api:William Hill", sport="football")
    s = PR.from_ledger_row(row, [prob_row("0.5")])
    assert s.p_same_source is None and s.p_same_spread is None
    assert evaluate_prediction(row, [s], CFG, NOW)[0].decision == PAPER_BET      # 0.60 x 1.80 = +8%, all gates pass


def test_tennis_bookmaker_snapshot_path_unchanged():
    price = [{"scan_timestamp_utc": SCAN, "sport_key": "k", "event_id": "e1", "player_a": "Ann Able", "player_b": "Bea Bold",
              "bookmaker": "betway", "market": "h2h", "odds_a": "1.80", "odds_b": "2.1", "last_update": SCAN}]
    narrow = PR.tennis_from_snapshots(ledger_row(), price, [prob_row("0.01")])
    wide = PR.tennis_from_snapshots(ledger_row(), price, [prob_row("0.09")])
    assert evaluate_prediction(ledger_row(), narrow, CFG, NOW)[0].decision == PAPER_BET
    assert "EXCHANGE_SPREAD_TOO_WIDE" in evaluate_prediction(ledger_row(), wide, CFG, NOW)[0].reasons


def test_no_false_candidate_through_the_ledger_path():
    """A ledger quote that LOOKS strongly +EV (P 0.70 at 1.80 = +26%) can never become PAPER_BET/WATCH/MULTI unless the
    same-scan book is narrow."""
    for prob in ([prob_row("0.09", pa=0.70)], [prob_row("", pa=0.70)], [prob_row("0.01", scan="2026-09-30T06:00:00+00:00")],
                 [prob_row("0.01", eid="x")], []):
        _, b = decide(ledger_row(0.70, live="1.80"), prob)
        assert b.decision == REJECT and set(SPREAD) & set(b.reasons), prob
    _, ok = decide(ledger_row(0.70, live="1.80"), [prob_row("0.01", pa=0.70)])
    assert ok.decision in (PAPER_BET, WATCH, MULTI)      # the same quote with a verified narrow book is still assessable


def test_storm_hunter_2026_09_30_case():
    """Real case: ledger back 1.02, P 0.98256 from a 9.1pp-wide book looked +0.12% EV and was labelled MULTI under
    bsv2-3; bsv2-4 rejects it for book width."""
    row = ledger_row(0.98256, live="1.02")
    _, b = decide(row, [prob_row("0.090909", pa=0.98256)])
    assert b.decision == REJECT and "EXCHANGE_SPREAD_TOO_WIDE" in b.reasons


def test_prediction_remains_visible_on_stage_a_despite_quality_failure():
    cfg = SA.StageAConfig("stage-a-1", 0.70, REPO / "research/platform_v2/card_engine_v2_7/RESULTS.json",
                          REPO / "config/bet_selection_v2.yaml")
    row = ledger_row(0.98256, live="1.02")
    prob = [prob_row("0.090909", pa=0.98256)]
    board = SA.build([row], prob, lambda p: [PR.from_ledger_row(p, prob)], CFG, cfg, None, NOW)
    r = board["predictions"][0]
    assert r["strength"] == SA.STRONG and r["price_status"] == SA.QUALITY_FAIL and not r["financially_assessable"]
    unresolved = SA.build([row], [], lambda p: [PR.from_ledger_row(p, [])], CFG, cfg, None, NOW)["predictions"][0]
    assert unresolved["price_status"] == SA.QUALITY_FAIL and "EXCHANGE_SPREAD_UNKNOWN" in unresolved["price_status_reasons"]
