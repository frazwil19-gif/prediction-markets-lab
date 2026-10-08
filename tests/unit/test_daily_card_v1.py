"""card-v1: probability-first board, bsv2-only bet decisions, stake/exposure policy, research rows never bettable."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path

from prediction_markets_lab.daily_card import card as C

REPO = Path(__file__).resolve().parents[2]
NOW = datetime(2026, 10, 10, 8, 0, tzinfo=timezone.utc)
CFG = C.CardConfig.load(REPO / "config/daily_card_v1.yaml")


def pred(pid, p, event, hours=5, status="PRICE_VALID", engine_status="VALIDATED_HISTORICAL"):
    return {"prediction_id": pid, "sport": "football", "competition": "Premier League", "event_key": event, "event_name": event,
            "event_start": (NOW + timedelta(hours=hours)).isoformat(), "market": "1x2", "selection": "home", "probability": p,
            "sigma": 0.02, "engine_status": engine_status, "engine_id": "football_1x2.market_consensus", "price_status": status,
            "best_clean_odds": 1.9, "best_clean_source": "bk", "best_clean_net_ev": 0.03}


def cand(pid, decision, ev=0.03, odds=1.9):
    return {"prediction_id": pid, "decision": decision, "net_ev": str(ev), "decimal_odds": str(odds), "source": "bk",
            "reasons": "" if decision == "PAPER_BET" else "NET_EV_NOT_POSITIVE", "price_observed_at": NOW.isoformat()}


def test_config_is_manual_live_one_pound_no_two_pound_rule():
    pol = CFG["live_policy"]
    assert pol["real_money_enabled"] is True and pol["money_eligibility"] == "registry"
    assert pol["default_stake_gbp"] == 1.0 and pol["enhanced_stake_rule_enabled"] is False and pol["max_daily_exposure_gbp"] == 5.0


def test_bets_only_from_bsv2_and_stake_caps():
    board = {"predictions": [pred(f"p{i}", 0.6 + i / 100, f"E{i}") for i in range(7)] + [pred("dup", 0.58, "E0"),
             pred("late", 0.9, "EL", hours=60), pred("nob", 0.95, "EN", status="POOR_PAYOUT")]}
    cands = [cand(f"p{i}", "PAPER_BET") for i in range(7)] + [cand("dup", "PAPER_BET"), cand("nob", "REJECT")]
    c = C.build(board, cands, [], CFG, NOW)
    staked = [b for b in c["best_bets"] if b["stake_gbp"] > 0]
    assert len(staked) == 5 and c["summary"]["total_stake_gbp"] == 5.0          # £5 daily cap at £1 each
    assert all(b["stake_gbp"] in (0.0, 1.0) for b in c["best_bets"])             # no £2 while the rule is disabled
    assert {b["prediction_id"] for b in c["best_bets"]} == {f"p{i}" for i in range(7)} | {"dup"}
    assert next(b for b in c["best_bets"] if b["prediction_id"] == "dup")["stake_note"].startswith("SKIP")  # one bet per event
    assert "late" not in {p["prediction_id"] for p in c["best_predictions"]}     # outside the window
    assert c["best_predictions"][0]["prediction_id"] == "nob"                     # ranked by probability, not price
    assert "nob" in {p["prediction_id"] for p in c["strong_price_too_low"]}
    md = C.render_md(c)
    assert "LIVE — manual £1 bets" in md and "## 2. Best bets today" in md


def test_research_rows_are_never_bets_and_show_more_likely_side():
    rows = [{"run_ts": "2026-10-09T10:00", "event_key": "k1", "kickoff_date": "2026-10-10", "kickoff_time": "15:00", "competition": "E0",
             "home": "A", "away": "B", "p_total_over_8.5": "0.72", "p_total_over_9.5": "0.40", "p_total_over_10.5": "", "p_total_over_11.5": "0.2"},
            {"run_ts": "2026-10-08T10:00", "event_key": "k1", "kickoff_date": "2026-10-10", "kickoff_time": "15:00", "competition": "E0",
             "home": "A", "away": "B", "p_total_over_8.5": "0.10"}]
    r = C.corners_research(rows, [8.5, 9.5, 10.5, 11.5], NOW, 36, "corners-A-1.0", "ev")
    assert [(x["selection"], x["probability"]) for x in r] == [("under 11.5", 0.8), ("over 8.5", 0.72), ("under 9.5", 0.6)]
    assert all(x["status"] == C.RESEARCH_STATUS for x in r)
    c = C.build({"predictions": []}, [], r, CFG, NOW)
    assert c["best_bets"] == [] and "NOT betting recommendations" in C.render_md(c) and "Bet if" not in C.render_md(c)


def test_band_and_fair_odds():
    assert C.band(0.83, [0.8, 0.7, 0.6, 0.5]) == "80%+" and C.band(0.45, [0.8, 0.7, 0.6, 0.5]) == "<50%" and C.fair_odds(0.6) == 1.67


def test_live_mode_only_stakes_money_eligible_engines():
    import copy
    raw = copy.deepcopy(CFG.raw); raw["live_policy"]["real_money_enabled"] = True
    cfg = C.CardConfig(raw)
    board = {"predictions": [pred("a", 0.7, "E1"), {**pred("b", 0.8, "E2"), "engine_id": "wta_match_winner.betfair_market"}]}
    c = C.build(board, [cand("a", "PAPER_BET"), cand("b", "PAPER_BET")], [], cfg, NOW, {"football_1x2.market_consensus"})
    st = {b["prediction_id"]: (b["stake_gbp"], b["stake_note"]) for b in c["best_bets"]}
    assert st["a"] == (1.0, "") and st["b"][0] == 0.0 and "not money-eligible" in st["b"][1]
    assert "LIVE" in c["mode"]


def test_registry_money_engines_are_validated():
    eng = C.money_eligible_engines(REPO)
    assert "football_1x2.market_consensus" in eng and all("research" not in e for e in eng)


def test_big_card_only_from_qualifying_legs_on_different_events():
    board = {"predictions": [pred(f"q{i}", 0.6 + i / 100, f"E{i}") for i in range(4)] + [pred("same", 0.9, "E0"), pred("rej", 0.95, "EX")]}
    cands = [cand(f"q{i}", "PAPER_BET", odds=1.8) for i in range(4)] + [cand("same", "PAPER_BET", odds=1.2), cand("rej", "REJECT")]
    c = C.build(board, cands, [], CFG, NOW)
    m = c["big_card"]
    assert m and 3 <= len(m["legs"]) <= 5 and len({g["event_name"] for g in m["legs"]}) == len(m["legs"])
    assert all(g["event_name"] != "EX" for g in m["legs"])
    jp = 1.0
    for g in m["legs"]:
        jp *= g["probability"]
    assert abs(m["joint_probability"] - round(jp, 4)) < 1e-9 and m["min_acceptable_acca_odds"] == round(1.02 / jp, 2)
    assert c["summary"]["total_stake_gbp"] <= CFG["live_policy"]["max_daily_exposure_gbp"]
    assert "Big Card" in C.render_md(c)
    two = C.build({"predictions": board["predictions"][:2]}, cands[:2], [], CFG, NOW)
    assert two["big_card"] is None and "No Big Card today" in C.render_md(two)


def test_min_bookmaker_odds():
    assert C.min_bookmaker_odds(0.60) == 1.70 and C.min_bookmaker_odds(0.5) == 2.04 and C.min_bookmaker_odds(0.9) == 1.33
    p = 0.63
    assert p * C.min_bookmaker_odds(p) - 1 >= 0.02
