"""V2-6 Bet-Selection V2 tests (paper layer). No network, no gitignored data."""
from __future__ import annotations

import copy
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
import yaml

from prediction_markets_lab.bet_selection_v2 import bankroll as BK
from prediction_markets_lab.bet_selection_v2 import multi as M
from prediction_markets_lab.bet_selection_v2 import paper_ledger as L
from prediction_markets_lab.bet_selection_v2 import prices as PR
from prediction_markets_lab.bet_selection_v2 import report as R
from prediction_markets_lab.bet_selection_v2.evaluate import (MULTI, PAPER_BET, REJECT, WATCH, CONFIG_PATH, commission_for,
                                                              evaluate_prediction, load_config)

NOW = datetime(2026, 10, 10, 8, 0, tzinfo=timezone.utc)
CFG = load_config()


def pred(p=0.60, start=NOW + timedelta(hours=6), sport="tennis", status="VALIDATED_HISTORICAL", valid=True, pid="p1",
         live="", src="", name="Ann Able v Bea Bold", sel="Ann Able", market="match_winner", key=None, pred_ts=None):
    return {"prediction_id": pid, "engine_id": "wta_match_winner.betfair_market", "engine_status": status, "sport": sport,
            "event_id": "ev1", "event_key": key or f"tennis|tennis_wta_x|{pid}", "event_name": name,
            "event_start": start.isoformat(), "market": market, "selection": sel, "estimated_probability": str(p),
            "prediction_valid": str(valid), "live_price": live, "live_price_source": src,
            "prediction_timestamp": (pred_ts or NOW - timedelta(minutes=10)).isoformat()}


SAME = "SAME_AS_PREDICTION"   # test sentinel: the snapshot's engine P equals the prediction's P (same snapshot)


def snap(odds, source="bet365", at=NOW - timedelta(minutes=5), pid="p1", p=SAME):
    return PR.PriceSnapshot(pid, source, odds, at, at, "test", p)


def evaluate_same(pred_row, snaps, cfg, now):
    """Fill the SAME sentinel from the prediction row (tests written before bsv2-2 assume same-snapshot P)."""
    from dataclasses import replace
    snaps = [replace(x, p_same_snapshot=float(pred_row["estimated_probability"])) if x.p_same_snapshot == SAME else x
             for x in snaps]
    return evaluate_prediction(pred_row, snaps, cfg, now)


# ---------------------------------------------------------------- arithmetic
def test_fair_odds_break_even_and_ev_bookmaker():
    best, _ = evaluate_same(pred(0.60), [snap(1.80)], CFG, NOW)
    assert best.fair_odds == pytest.approx(1 / 0.60)
    assert best.break_even_probability == pytest.approx(1 / 1.80)
    assert best.gross_ev == pytest.approx(0.60 * 1.80 - 1)
    assert best.net_ev == pytest.approx(0.08)          # no commission at a bookmaker
    assert best.decision == PAPER_BET and "ALL_PAPER_GATES_PASSED" in best.reasons


def test_exchange_commission_applied_to_net_winnings():
    best, _ = evaluate_same(pred(0.60), [snap(1.80, "betfair_ex_uk")], CFG, NOW)
    assert best.is_exchange and best.commission == 0.05
    assert best.net_ev == pytest.approx(0.60 * 0.80 * 0.95 - 0.40)
    assert best.break_even_probability == pytest.approx(1 / (0.80 * 0.95 + 1))


def test_unknown_exchange_commission_is_rejected_not_assumed_zero():
    assert commission_for("matchbook", CFG) == (True, None)
    best, _ = evaluate_same(pred(0.60), [snap(1.90, "matchbook")], CFG, NOW)
    assert best.decision == REJECT and "COMMISSION_UNKNOWN" in best.reasons


def test_best_fresh_price_is_used_and_all_candidates_kept():
    best, cands = evaluate_same(pred(0.60), [snap(1.70), snap(1.85, "williamhill"), snap(1.75, "betfair_ex_uk")], CFG, NOW)
    assert len(cands) == 3 and best.source == "williamhill"


# ---------------------------------------------------------------- decisions and gates
@pytest.mark.parametrize("p,odds,hours,status,expect,reason", [
    (0.60, 1.70, 6, "VALIDATED_HISTORICAL", WATCH, "NET_EV_BELOW_PAPER_GATE"),        # EV +2.0%? no: 0.6*1.7-1=0.02 -> boundary below
    (0.60, 1.80, 30, "VALIDATED_HISTORICAL", WATCH, "OUTSIDE_EVENT_HORIZON"),
    (0.80, 1.30, 6, "VALIDATED_HISTORICAL", MULTI, "ODDS_BELOW_PAYOUT_FLOOR"),
    (0.60, 1.80, 6, "PROVISIONAL_PROSPECTIVE", WATCH, "ENGINE_NOT_VALIDATED_FOR_PAPER_BET"),
    (0.60, 1.60, 6, "VALIDATED_HISTORICAL", REJECT, "NET_EV_NOT_POSITIVE"),
    (0.45, 2.60, 6, "VALIDATED_HISTORICAL", REJECT, "P_BELOW_FLOOR"),
    (0.60, 1.80, 6, "RESEARCH_VALIDATED", REJECT, "ENGINE_STATUS_INELIGIBLE"),
])
def test_decision_table(p, odds, hours, status, expect, reason):
    best, _ = evaluate_same(pred(p, start=NOW + timedelta(hours=hours), status=status), [snap(odds)], CFG, NOW)
    assert best.decision == expect and reason in best.reasons


def test_strong_prediction_poor_price_is_multi_research_not_bet():
    best, _ = evaluate_same(pred(0.90), [snap(1.09, "betfair_ex_uk")], CFG, NOW)
    assert best.net_ev < 0 and best.decision == MULTI


def test_gates_are_the_existing_money_gates():
    t = yaml.safe_load((CONFIG_PATH.parents[0] / "thresholds.yaml").read_text())
    g = CFG["decision_gates"]["paper_bet"]
    assert g["min_probability"] == t["money_qualification"]["min_probability"]
    assert g["min_net_ev"] == t["money_qualification"]["min_net_ev"]
    assert g["min_decimal_odds"] == t["payout_policy"]["normal_min_decimal_odds"]
    assert g["max_hours_to_event"] == t["money_qualification"]["event_horizon_hours"]
    assert g["max_price_age_minutes"] == t["data_quality"]["max_quote_age_minutes"]


def test_config_guards_real_money_and_same_event(tmp_path):
    for patch in ({"real_money_enabled": True}, {"multi": {"enabled": False, "same_event_allowed": True}}):
        cfg = {**copy.deepcopy(CFG), **patch}
        p = tmp_path / "c.yaml"
        p.write_text(yaml.safe_dump(cfg))
        with pytest.raises(ValueError):
            load_config(p)


# ---------------------------------------------------------------- timestamps and validity
def test_stale_price_and_price_after_start_rejected():
    best, _ = evaluate_same(pred(0.60), [snap(1.90, at=NOW - timedelta(minutes=241))], CFG, NOW)
    assert best.decision == REJECT and "PRICE_STALE" in best.reasons
    start = NOW + timedelta(hours=1)
    best, _ = evaluate_same(pred(0.60, start=start), [snap(1.90, at=start)], CFG, NOW)
    assert "PRICE_AT_OR_AFTER_START" in best.reasons and best.decision == REJECT


def test_event_started_and_invalid_prediction_rejected():
    best, _ = evaluate_same(pred(0.60, start=NOW - timedelta(minutes=1)), [snap(1.90)], CFG, NOW)
    assert best.decision == REJECT and "EVENT_STARTED" in best.reasons
    best, _ = evaluate_same(pred(0.60, valid=False), [snap(1.90)], CFG, NOW)
    assert best.decision == REJECT and "PREDICTION_NOT_VALID" in best.reasons
    best, _ = evaluate_same(pred(0.60), [], CFG, NOW)
    assert best.decision == REJECT and "NO_EXECUTABLE_PRICE" in best.reasons


# ---------------------------------------------------------------- price-source compatibility
def test_ledger_price_sources():
    t = PR.from_ledger_row(pred(live="1.30", src="betfair_ex_uk back (odds_api)"))
    assert t.source == "betfair_ex_uk" and t.decimal_odds == 1.30
    f = PR.from_ledger_row(pred(live="2.10", src="odds_api:William Hill"))
    assert f.source == "william hill"
    assert PR.from_ledger_row(pred(live="1.40", src="SYNTHETIC_DUTCH_BEST_1X2")) is None  # DC dutch is not executable
    assert PR.from_ledger_row(pred(live="1.40", src="something else")) is None           # unknown provenance never guessed
    assert PR.from_ledger_row(pred(live="", src="")) is None


def test_tennis_snapshot_capture_and_matching(tmp_path):
    from prediction_markets_lab.tennis_prospective.engine import TennisEventQuotes
    q = TennisEventQuotes(event_id="ev1", sport_key="tennis_wta_x", sport_title="WTA X", tour="WTA",
                          commence_time=NOW + timedelta(hours=6), player_a="Ann Able", player_b="Bea Bold",
                          exchange_back={"a": 1.60, "b": 2.5}, exchange_last_update=NOW - timedelta(minutes=3),
                          bookmaker_h2h={"williamhill": (1.72, 2.1)}, bookmaker_last_update={"williamhill": NOW - timedelta(minutes=2)})
    rows = PR.tennis_snapshot_rows([q], NOW)
    path = tmp_path / "s.csv"
    assert PR.append_tennis_snapshots(path, rows) == 2
    snaps = PR.tennis_from_snapshots(pred(), L.read_rows(path))
    assert {(s.source, s.decimal_odds) for s in snaps} == {("betfair_ex_uk", 1.6), ("williamhill", 1.72)}
    other = PR.tennis_from_snapshots(pred(sel="Bea Bold"), L.read_rows(path))
    assert {s.decimal_odds for s in other} == {2.5, 2.1}
    assert PR.tennis_from_snapshots(pred(name="Ann Able v Someone Else"), L.read_rows(path)) == []


def test_football_card_prices_match_exact_selection():
    ko = "2026-10-10T14:00:00Z"
    card = {"data_timestamp": NOW.isoformat(), "candidates": [
        {"competition": "Premier League", "event": "A v B", "kickoff_time": ko, "market": "1x2", "selection": "home",
         "available_odds": 2.2, "bookmaker": "Betfair", "price_timestamp": NOW.isoformat()},
        {"competition": "Premier League", "event": "A v B", "kickoff_time": ko, "market": "1x2", "selection": "away",
         "available_odds": 3.4, "bookmaker": "Casumo", "price_timestamp": NOW.isoformat()}]}
    p = pred(sport="football", market="1x2", sel="home", key="football|Premier League|A v B|2026-10-10T14:00:00+00:00")
    s = PR.football_from_card(p, card)
    assert len(s) == 1 and s[0].source == "betfair" and s[0].decimal_odds == 2.2
    assert commission_for("betfair", CFG) == (True, 0.05)   # card title "Betfair" is the exchange


# ---------------------------------------------------------------- immutable paper singles
def _paper(pid="p1", p=0.60, odds=1.80, start=NOW + timedelta(hours=6)):
    best, cands = evaluate_same(pred(p, start=start, pid=pid), [snap(odds, pid=pid)], CFG, NOW)
    return best, cands


def test_selection_recorded_once_retries_idempotent_and_immutable(tmp_path):
    path = tmp_path / "sel.csv"
    best, _ = _paper()
    assert L.record_selections(path, [best], "bsv2-1", 1.0, NOW) == 1
    before = path.read_bytes()
    later, _ = evaluate_same(pred(0.60), [snap(2.20, at=NOW + timedelta(minutes=30))], CFG, NOW + timedelta(hours=1))
    assert L.record_selections(path, [later, later], "bsv2-1", 1.0, NOW + timedelta(hours=1)) == 0
    assert path.read_bytes() == before
    row = L.read_rows(path)[0]
    assert float(row["decimal_odds"]) == 1.80 and row["selection_id"] == L.selection_id("bsv2-1", "p1")
    assert L.record_selections(path, [best], "bsv2-2", 1.0, NOW) == 1  # a new rule version is a separate selection


def test_mutation_of_existing_rows_raises(tmp_path, monkeypatch):
    path = tmp_path / "sel.csv"
    L.record_selections(path, [_paper()[0]], "bsv2-1", 1.0, NOW)
    real_read = Path.read_bytes
    calls = {"n": 0}

    def tampered(self):  # the post-write check sees a rewritten history
        calls["n"] += 1
        data = real_read(self)
        return data.replace(b"1.8", b"1.9") if calls["n"] > 1 else data
    monkeypatch.setattr(Path, "read_bytes", tampered)
    with pytest.raises(RuntimeError, match="immutability"):
        L.record_selections(path, [_paper("p2")[0]], "bsv2-1", 1.0, NOW)


def test_no_post_event_selection_even_if_decided_paper_bet(tmp_path):
    path = tmp_path / "sel.csv"
    best, _ = _paper(start=NOW + timedelta(minutes=30))
    assert best.decision == PAPER_BET
    assert L.record_selections(path, [best], "bsv2-1", 1.0, NOW + timedelta(minutes=31)) == 0  # decided, but too late
    assert not path.exists()


def test_only_paper_bets_become_selections_and_snapshots_are_separate(tmp_path):
    good, c1 = _paper("p1")
    watch, c2 = evaluate_same(pred(0.60, pid="p2"), [snap(1.70, pid="p2")], CFG, NOW)
    assert watch.decision == WATCH
    assert L.record_selections(tmp_path / "sel.csv", [good, watch], "bsv2-1", 1.0, NOW) == 1
    assert L.record_snapshots(tmp_path / "snap.csv", c1 + c2, {"p1": PAPER_BET, "p2": WATCH}) == 2
    assert L.record_snapshots(tmp_path / "snap.csv", c1 + c2, {}) == 0   # retry: no duplicates


# ---------------------------------------------------------------- settlement
def test_settlement_fail_closed_and_pnl(tmp_path):
    sels = [L.selection_row(_paper("p1")[0], "bsv2-1", 1.0, NOW),
            L.selection_row(evaluate_same(pred(0.60, pid="p2"), [snap(1.80, "betfair_ex_uk", pid="p2")], CFG, NOW)[0],
                            "bsv2-1", 1.0, NOW),
            L.selection_row(_paper("p3")[0], "bsv2-1", 1.0, NOW),
            L.selection_row(_paper("p4")[0], "bsv2-1", 1.0, NOW)]
    sels = [{k: str(v) for k, v in s.items()} for s in sels]
    plat = {"p1": {"settlement_status": "SETTLED", "correct": "1", "result": "Ann Able"},
            "p2": {"settlement_status": "SETTLED", "correct": "1"},
            "p3": {"settlement_status": "SETTLED", "correct": ""},          # ambiguous -> stays pending
            "p4": {"settlement_status": "VOID", "correct": ""}}
    out = {r["prediction_id"]: r for r in L.settle(sels, plat, set(), NOW)}
    assert out["p1"]["status"] == "WON" and out["p1"]["pnl_units"] == pytest.approx(0.80)
    assert out["p2"]["pnl_units"] == pytest.approx(0.80 * 0.95)          # exchange commission on winnings
    assert "p3" not in out and out["p4"]["status"] == "VOID" and out["p4"]["pnl_units"] == 0
    path = tmp_path / "st.csv"
    assert L.append_settlements(path, list(out.values())) == 3
    assert L.append_settlements(path, list(out.values())) == 0            # first settlement wins
    lost = L.settle(sels[:1], {"p1": {"settlement_status": "SETTLED", "correct": "0"}}, set(), NOW)
    assert lost[0]["status"] == "LOST" and lost[0]["pnl_units"] == -1.0


# ---------------------------------------------------------------- bankroll simulation
SIM = CFG["bankroll_simulation"]


def _settled(n, status="LOST", odds=1.8, p=0.6, exch=False, day0=NOW):
    return [{"selection_id": f"s{i}", "event_start": (day0 + timedelta(days=i)).isoformat(), "probability": p,
             "decimal_odds": odds, "commission": 0.05 if exch else 0.0, "is_exchange": str(exch), "status": status}
            for i in range(n)]


def test_min_stake_rounding_and_skips():
    r = BK.simulate(_settled(1, "WON", exch=True), 30, "flat_2pct", SIM["policies"]["flat_2pct"], SIM)
    assert r.rounded_up_to_min == 1 and r.bets == 1 and r.turnover == 1.00   # £0.60 -> £1 (3.3% <= 5% cap)
    r = BK.simulate(_settled(1, "WON", exch=True), 15, "flat_1pct", SIM["policies"]["flat_1pct"], SIM)
    assert r.bets == 0 and r.skipped == {"SKIP_MIN_STAKE": 1}                # £1 would be 6.7% > 5% cap
    r = BK.simulate(_settled(1, "WON"), 30, "flat_2pct", SIM["policies"]["flat_2pct"], SIM)
    assert r.turnover == 0.60 and r.rounded_up_to_min == 0                    # bookmaker min £0.10


def test_bankroll_arithmetic_and_no_martingale():
    rows = _settled(3, "LOST") + _settled(1, "WON", day0=NOW + timedelta(days=3))
    r = BK.simulate(rows, 100, "flat_2pct", SIM["policies"]["flat_2pct"], SIM)
    stakes = [x["stake"] for x in BK.simulate(rows, 100, "flat_2pct", SIM["policies"]["flat_2pct"], SIM).path]
    assert stakes[0] == 2.00 and all(b <= a for a, b in zip(stakes, stakes[1:]))  # stakes shrink after losses, never chase
    assert r.longest_losing_streak == 3
    assert r.final == pytest.approx(100 - 2 - 1.96 - 1.92 + 1.88 * 0.8, abs=0.02)
    with pytest.raises(ValueError):
        BK.policy_stake({"kind": "martingale"}, 100, 0.6, 1.8, 0.0, 0.1)


def test_daily_exposure_cap_and_loss_lock_and_drawdown_stop():
    same_day = [{**r, "event_start": NOW.isoformat(), "selection_id": f"d{i}"} for i, r in enumerate(_settled(8, "LOST"))]
    r = BK.simulate(same_day, 100, "flat_2pct", SIM["policies"]["flat_2pct"], SIM)
    assert r.bets <= 5 and sum(r.skipped.values()) >= 3           # 10% daily exposure / 10% loss lock
    r = BK.simulate(_settled(40, "LOST", exch=True), 20, "min_stake", SIM["policies"]["min_stake"], SIM)
    assert r.bets == 1 and r.skipped["SKIP_MIN_STAKE"] == 39      # after one loss, £1 is >5% of £19: exchange minimum infeasible
    r = BK.simulate(_settled(40, "LOST"), 100, "cap", {"kind": "fraction", "fraction": 0.05}, SIM)
    assert r.drawdown_stop_fired and r.skipped["DRAWDOWN_STOP"] > 0
    assert r.final >= 100 * (1 - SIM["drawdown_stop_fraction"]) - 5.0


def test_kelly_zero_when_no_edge():
    assert BK.kelly_fraction(0.5, 1.9, 0.0) == 0.0
    assert BK.kelly_fraction(0.6, 1.8, 0.0) == pytest.approx((0.8 * 0.6 - 0.4) / 0.8)


def test_report_results_and_funnel():
    sel = {k: str(v) for k, v in L.selection_row(_paper()[0], "bsv2-1", 1.0, NOW).items()}
    st = {sel["selection_id"]: {"status": "WON", "pnl_units": "0.8"}}
    res = R.results([sel], st, SIM)
    assert res["overall"]["settled"] == 1 and res["overall"]["realised_net_pnl_units"] == pytest.approx(0.8)
    assert res["overall"]["expected_net_pnl_units"] == pytest.approx(0.08)
    assert len(res["bankroll_simulations"]) == len(SIM["bankrolls_gbp"]) * len(SIM["policies"])
    fun = R.funnel_from_runs([{"run_at": "2026-10-10T08:00", "paper_bets_added": "0"},
                              {"run_at": "2026-10-11T08:00", "paper_bets_added": "2"}])
    assert fun["no_bet_days"] == ["2026-10-10"] and fun["bet_days"] == {"2026-10-11": 2}


# ---------------------------------------------------------------- multi research (disabled)
def test_multi_disabled_same_event_blocked_and_no_fabricated_odds():
    a, _ = evaluate_same(pred(0.90, pid="a", key="tennis|k|e1"), [snap(1.09, "betfair_ex_uk", pid="a")], CFG, NOW)
    b, _ = evaluate_same(pred(0.88, pid="b", key="tennis|k|e1"), [snap(1.12, "betfair_ex_uk", pid="b")], CFG, NOW)
    rec = M.assess_pair(a, b, CFG)
    assert not rec.enabled and rec.blocked and "SAME_EVENT" in rec.dependency_flags
    assert rec.combined_price_source == "NOT_QUOTED" and rec.quoted_multi_odds is None
    c, _ = evaluate_same(pred(0.88, pid="c", key="tennis|k|e2", name="Cy Cee v Di Dee", sel="Cy Cee"),
                               [snap(1.12, "betfair_ex_uk", pid="c")], CFG, NOW)
    rec = M.assess_pair(a, c, CFG)
    assert "SAME_TOURNAMENT_DRAW" in rec.dependency_flags and rec.joint_probability_status == "UNVALIDATED"
    assert rec.joint_probability_independent == pytest.approx(0.90 * 0.88)


def test_multi_leg_must_be_independently_eligible():
    a, _ = evaluate_same(pred(0.90, pid="a"), [snap(1.09, "betfair_ex_uk", pid="a")], CFG, NOW)
    bad, _ = evaluate_same(pred(0.90, pid="z", valid=False, key="tennis|q|z", name="Q v R", sel="Q"), [], CFG, NOW)
    assert M.assess_pair(a, bad, CFG).blocked


# ---------------------------------------------------------------- production compatibility
REPO = Path(__file__).resolve().parents[2]


def test_workflows_wire_v2_6_additively():
    for wf in ("daily_scan", "tennis_prediction_board", "settlement_and_performance"):
        y = yaml.safe_load((REPO / f".github/workflows/{wf}.yml").read_text())
        steps = y["jobs"][next(iter(y["jobs"]))]["steps"]
        bs = [s for s in steps if "Bet-Selection V2" in s.get("name", "")]
        assert len(bs) == 1 and bs[0].get("continue-on-error") is True
        assert "run_bet_selection_v2.py" in bs[0]["run"]


def test_bet_selection_never_imports_money_layer():
    src = REPO / "src/prediction_markets_lab/bet_selection_v2"
    text = "\n".join(p.read_text() for p in src.glob("*.py"))
    for forbidden in ("decisions.money_qualification", "risk.decision_gates", "run_daily_scan"):
        assert forbidden not in text


# ---------------------------------------------------------------- bsv2-2: same-snapshot probability (production defect 2026-09-29)
def test_stale_ledger_probability_never_paired_with_later_price():
    """Reproduces the first production run: ledger P 0.745 from 08:31, price 1.40 at 13:13 when the engine said 0.708."""
    best, _ = evaluate_prediction(pred(0.745489), [snap(1.40, "betfair_ex_uk", p=0.708376)], CFG, NOW)
    assert best.probability == pytest.approx(0.708376) and best.ledger_probability == pytest.approx(0.745489)
    assert best.net_ev < 0 and best.decision != PAPER_BET


def test_missing_same_snapshot_probability_is_rejected():
    best, _ = evaluate_prediction(pred(0.60), [snap(1.90, p=None)], CFG, NOW)
    assert best.decision == REJECT and "PROBABILITY_NOT_SAME_SNAPSHOT" in best.reasons


def test_only_latest_snapshot_quotes_are_compared():
    old = snap(2.10, "williamhill", at=NOW - timedelta(minutes=60), p=0.60)   # better price, but an older snapshot
    new = snap(1.75, "bet365", at=NOW - timedelta(minutes=5), p=0.60)
    best, cands = evaluate_prediction(pred(0.60), [old, new], CFG, NOW)
    assert len(cands) == 2 and best.source == "bet365"


def test_tennis_same_scan_probability_matching():
    rows = [{"scan_timestamp_utc": "t1", "event_id": "ev1", "player_a": "Ann Able", "player_b": "Bea Bold",
             "source_validated": "True", "p_a": "0.7", "p_b": "0.3"},
            {"scan_timestamp_utc": "t2", "event_id": "ev1", "player_a": "Ann Able", "player_b": "Bea Bold",
             "source_validated": "False", "p_a": "0.9", "p_b": "0.1"}]
    got = PR.same_scan_probability(pred(sel="Bea Bold"), rows)
    assert got == {"t1": 0.3}   # research-only scan never supplies P


def test_valid_legacy_selection_blocks_duplicate_exposure(tmp_path):
    path = tmp_path / "sel.csv"
    best, _ = _paper()
    assert L.record_selections(path, [best], "bsv2-2", 1.0, NOW, exclude_prediction_ids={"p1"}) == 0
    assert L.record_selections(path, [best], "bsv2-2", 1.0, NOW) == 1
    assert "LEDGER_P=" in L.read_rows(path)[0]["reasons"]
