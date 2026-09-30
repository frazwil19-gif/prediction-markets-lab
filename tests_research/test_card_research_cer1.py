"""V2-7 research card engine tests (offline; no network, no production ledgers)."""
from __future__ import annotations

import csv
import json
import math
from datetime import datetime, timezone
from pathlib import Path

import pytest

from prediction_markets_lab.card_engine import cards as C
from prediction_markets_lab.card_engine import io as IO

SCAN = "2026-09-29T20:00:00+00:00"
CAL = lambda p: 0.01   # noqa: E731


def leg(ev_id="e1", p=0.6, odds=1.73, book="betway", sel=None, opp=None, sk="tennis_wta_x", width=0.01, quality=()):
    sel = sel or f"A{ev_id}"
    opp = opp or f"B{ev_id}"
    return C.Leg(SCAN, book, sk, ev_id, f"{sel} v {opp}", "2026-09-30T06:00:00+00:00", sel, opp, p, odds,
                 "2026-09-29T19:59:00+00:00", width, "wta@1", tuple(quality))


# ---------------------------------------------------------------- probability / odds algebra
def test_ev_algebra_compounds_multiplicatively():
    a, b, c = leg("e1", 0.6, 1.73), leg("e2", 0.7, 1.45), leg("e3", 0.55, 1.9)
    card = C.build_card("t", C.POS_EV, (a, b, c), CAL)
    assert card.p_joint == pytest.approx(0.6 * 0.7 * 0.55)
    assert card.odds_indicative == pytest.approx(1.73 * 1.45 * 1.9)
    assert card.ev == pytest.approx((1 + a.ev) * (1 + b.ev) * (1 + c.ev) - 1)
    assert card.break_even == pytest.approx(1 / card.odds_indicative)
    assert card.fair_odds == pytest.approx(1 / card.p_joint)


def test_negative_leg_drags_card_down():
    good, bad = leg("e1", 0.6, 1.80), leg("e2", 0.7, 1.35)       # +8% and -5.5%
    assert C.build_card("t", C.HIGH_P, (good, bad), CAL).ev < good.ev


def test_uncertainty_delta_method_and_ev_range():
    a, b = leg("e1", 0.6, 1.73, width=0.02), leg("e2", 0.7, 1.45, width=0.0)
    card = C.build_card("t", C.POS_EV, (a, b), CAL)
    sa, sb = math.sqrt(0.01 ** 2 + 0.01 ** 2), 0.01
    assert card.sigma_joint == pytest.approx(0.42 * math.sqrt((sa / 0.6) ** 2 + (sb / 0.7) ** 2))
    assert card.ev_low < card.ev < card.ev_high


# ---------------------------------------------------------------- dependence and classification
def test_same_event_and_same_participant_are_unverified_no_joint_p():
    card = C.build_card("t", C.HIGH_P, (leg("e1"), leg("e1", sel="X", opp="Y")), CAL)
    assert card.dependence == C.UNVERIFIED and card.p_joint is None and card.status == "RESEARCH_ONLY_UNVERIFIED"
    shared = C.build_card("t", C.HIGH_P, (leg("e1", sel="Sam", opp="Bo"), leg("e2", sel="Sam", opp="Cy")), CAL)
    assert shared.dependence == C.UNVERIFIED and "SAME_PARTICIPANT" in shared.dependence_flags


def test_same_tournament_is_flagged_not_blocked():
    card = C.build_card("t", C.POS_EV, (leg("e1"), leg("e2")), CAL)
    assert card.dependence == C.INDEPENDENT and "SAME_TOURNAMENT" in card.dependence_flags


def test_statuses():
    assert C.build_card("t", C.POS_EV, (leg("e1", 0.6, 1.80),), CAL).status == "SHADOW_CANDIDATE"
    assert C.build_card("t", C.POS_EV, (leg("e1", 0.6, 1.68),), CAL).status == "SHADOW_WATCH"      # +0.8%, low bound < 0
    assert C.build_card("t", C.HIGH_P, (leg("e1", 0.8, 1.2),), CAL).status == "RESEARCH_HIGH_P"
    bad = C.build_card("t", C.POS_EV, (leg("e1", quality=("EXCHANGE_BOOK_TOO_WIDE",)),), CAL)
    assert bad.status == "REJECT_LEG_QUALITY" and "EXCHANGE_BOOK_TOO_WIDE" in bad.reasons
    assert all("ODDS_INDICATIVE_NOT_EXECUTION_VERIFIED" in c.reasons for c in (bad,))


# ---------------------------------------------------------------- enumeration bounds, same-book rule, determinism
def test_enumeration_same_book_bounded_deterministic_and_excludes_unclean():
    legs = [leg(f"e{i}", 0.72 + i * 0.01, 1.5, book=b) for i in range(15) for b in ("b1", "b2")]
    legs.append(leg("bad", 0.95, 3.0, book="b1", quality=("EXCHANGE_BOOK_TOO_WIDE",)))
    cards, space = C.enumerate_cards("t", legs, CAL, max_legs_per_pool=12)
    assert all(len({l.book for l in c.legs}) == 1 for c in cards)                       # never mixes bookmakers
    assert not any(l.event_id == "bad" for c in cards for l in c.legs)                  # unclean never combined
    assert space["b1|HIGH_P"]["truncated"] == 3 and space["b1|HIGH_P"]["quality_rejected_legs"] == 1
    assert space["b1|HIGH_P"]["cards"] == 12 + 66 + 220
    again, _ = C.enumerate_cards("t", list(reversed(legs)), CAL, max_legs_per_pool=12)
    assert sorted(c.card_id for c in cards) == sorted(c.card_id for c in again)         # order-independent


def test_card_id_is_order_independent_and_rule_scoped():
    a, b = leg("e1"), leg("e2")
    assert C.card_id("t", SCAN, "bk", "G", (a, b)) == C.card_id("t", SCAN, "bk", "G", (b, a))
    assert C.card_id("t", SCAN, "bk", "G", (a, b)) != C.card_id("t2", SCAN, "bk", "G", (a, b))


# ---------------------------------------------------------------- equal-capital comparison
def test_equal_capital_single_leg_identity_and_known_values():
    one = C.equal_capital((leg("e1", 0.6, 1.73),), 0.02)
    assert one["card_log_growth"] == pytest.approx(one["singles_log_growth"])
    two = C.equal_capital((leg("e1", 0.6, 1.73), leg("e2", 0.6, 1.73)), 0.01)
    assert two["card_ev"] == pytest.approx(0.01 * (0.36 * 1.73 ** 2 - 1))
    assert two["singles_ev"] == pytest.approx(0.01 * (0.6 * 1.73 - 1))
    assert two["better_growth"] == "CARD"                                               # small stake: card wins
    assert C.equal_capital((leg("e1", 0.6, 1.73), leg("e2", 0.6, 1.73)), 0.10)["better_growth"] == "SINGLES"
    assert two["card_p_total_loss"] == pytest.approx(0.64) and two["singles_p_total_loss"] == pytest.approx(0.16)


# ---------------------------------------------------------------- loading legs (quality, timestamps) and ledger
def _prob(width="0.01", validated="True", start="2026-09-30T06:00:00+00:00"):
    return [{"scan_timestamp_utc": SCAN, "sport_key": "tennis_wta_x", "event_id": "e1", "player_a": "Ann", "player_b": "Bea",
             "commence_time": start, "source": "EXCHANGE_MID", "source_validated": validated, "p_a": "0.6", "p_b": "0.4",
             "raw_prices": "", "exchange_spread_prob": width}]


def _price(book="betway", lu="2026-09-29T19:59:00+00:00"):
    return [{"scan_timestamp_utc": SCAN, "sport_key": "tennis_wta_x", "event_id": "e1", "player_a": "Ann", "player_b": "Bea",
             "bookmaker": book, "market": "h2h", "odds_a": "1.73", "odds_b": "2.2", "last_update": lu}]


def test_load_legs_quality_and_fail_closed():
    ok = IO.load_legs(_prob(), _price(), SCAN)
    assert len(ok) == 1 and ok[0].clean and ok[0].selection == "Ann" and ok[0].odds == 1.73
    assert IO.load_legs(_prob(), _price(book="betfair_ex_uk"), SCAN) == []               # exchange prices never a card leg
    assert IO.load_legs(_prob(validated="False"), _price(), SCAN) == []                  # research-only P never used
    assert "EXCHANGE_BOOK_TOO_WIDE" in IO.load_legs(_prob(width="0.2"), _price(), SCAN)[0].quality
    assert "EXCHANGE_WIDTH_UNKNOWN" in IO.load_legs(_prob(width=""), _price(), SCAN)[0].quality
    assert "QUOTE_STALE_OR_UNTIMED" in IO.load_legs(_prob(), _price(lu="2026-09-29T10:00:00+00:00"), SCAN)[0].quality
    assert "EVENT_STARTED" in IO.load_legs(_prob(start="2026-09-29T19:00:00+00:00"), _price(), SCAN)[0].quality


def test_ledger_idempotent_append_only(tmp_path):
    p = tmp_path / "cards.csv"
    c = C.build_card("t", C.POS_EV, (leg("e1", 0.6, 1.8),), CAL)
    row = IO.card_row(c, "now", {"x": 1})
    assert IO.append_unique(p, IO.CARD_FIELDS, "card_id", [row, row]) == 1
    before = p.read_bytes()
    assert IO.append_unique(p, IO.CARD_FIELDS, "card_id", [row]) == 0 and p.read_bytes() == before


def test_settlement_fail_closed():
    c = C.build_card("t", C.POS_EV, (leg("e1", sel="Ann", opp="Bea"), leg("e2", sel="Cy", opp="Di")), CAL)
    rows = [IO.card_row(c, "now", {})]
    preds = [{"prediction_id": "p1", "event_id": "e1"}, {"prediction_id": "p2", "event_id": "e2"}]
    now = datetime(2026, 10, 1, tzinfo=timezone.utc)
    assert IO.settle(rows, preds, [{"prediction_id": "p1", "status": "SETTLED_CORRECT", "winner": "Ann"}], set(), now) == []
    both = [{"prediction_id": "p1", "status": "SETTLED_CORRECT", "winner": "Ann"},
            {"prediction_id": "p2", "status": "SETTLED_INCORRECT", "winner": "Di"}]
    out = IO.settle(rows, preds, both, set(), now)
    assert out[0]["status"] == "LOST" and out[0]["legs_won"] == 1
    void = [both[0], {"prediction_id": "p2", "status": "VOID", "winner": ""}]
    assert IO.settle(rows, preds, void, set(), now)[0]["status"] == "VOID"
    assert IO.settle(rows, preds, both, {c.card_id}, now) == []                          # first settlement wins


def test_research_code_never_touches_production_ledgers():
    repo = Path(__file__).resolve().parents[1]
    src = "\n".join(p.read_text() for p in (repo / "src/prediction_markets_lab/card_engine").glob("*.py"))
    src += (repo / "scripts/run_card_research.py").read_text()
    for forbidden in ("paper_betting_v2", "record_selections", "unified_ledger", "append_predictions"):
        assert forbidden not in src
