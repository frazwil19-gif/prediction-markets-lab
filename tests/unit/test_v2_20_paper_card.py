"""V2-20 pcard-1: grades follow the pre-registered rule; bsv2 decisions are never changed; stakes respect the bsv2
caps; enrichment is append-only first-sight; dashboard separates prediction quality from money; paper only."""
from __future__ import annotations

import csv
import importlib.util
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import pytest
import yaml

from prediction_markets_lab.paper_card import card as PC

REPO = Path(__file__).resolve().parents[2]
NOW = datetime(2026, 10, 8, 9, 0, tzinfo=timezone.utc)
CFG = PC.load_config(REPO / "config/paper_card.yaml", REPO)


def cand(pid, decision, p, odds, comm=0.0, exch=False, engine="atp_match_winner.betfair_market", start="2026-10-09T12:00:00+00:00"):
    return {"prediction_id": pid, "sport": "tennis", "engine_id": engine, "event_key": f"tennis|tennis_atp_x|{pid}",
            "event_name": f"{pid} v Other", "event_start": start, "market": "match_winner", "selection": pid,
            "probability": str(p), "fair_odds": str(1 / p), "decimal_odds": str(odds), "source": "betfair_ex_uk" if exch else "bk",
            "is_exchange": str(exch), "commission": str(comm), "price_observed_at": "2026-10-08T08:59:00+00:00",
            "price_age_minutes": "1.0", "net_ev": str(PC.ev(p, odds, comm)), "decision": decision, "reasons": "",
            "evaluated_at": NOW.isoformat()}


def stage_a(*pairs):
    return {"predictions": [{"prediction_id": pid, "sigma": s, "sigma_method": "x", "calibration_status": "c",
                             "competition": "ATP X"} for pid, s in pairs]}


def test_config_reuses_bsv2_bankroll_block_and_states_are_valid():
    bs = yaml.safe_load((REPO / "config/bet_selection_v2.yaml").read_text())["bankroll_simulation"]
    assert CFG.sim == bs and CFG.sim["bankrolls_gbp"] == [20, 30, 50, 100]
    assert CFG.z_a == 1.0 and CFG.z_a_plus == 1.645
    # A+ is structurally empty today: no engine has reached PROSPECTIVE_CALIBRATION_SUPPORTED
    idx = CFG.states.index(CFG.a_plus_min_state)
    assert all(CFG.states.index(s) < idx for s in CFG.engine_state.values())


def test_grade_rule_matches_preregistration():
    g = lambda d, p, s, o, st="PROSPECTIVE_SHADOW": PC.grade(CFG, d, p, s, o, 0.0, st)[0]
    assert g("PAPER_BET", 0.75, 0.01, 1.45) == PC.A                       # EV(0.74) > 0
    assert g("PAPER_BET", 0.75, 0.05, 1.40) == PC.B                       # EV(0.70) < 0
    assert g("PAPER_BET", 0.75, None, 1.45) == PC.B                       # sigma unknown
    assert g("PAPER_BET", 0.75, 0.01, 1.45, "PROSPECTIVE_CALIBRATION_SUPPORTED") == PC.A_PLUS
    assert g("PAPER_BET", 0.75, 0.04, 1.45, "PAPER_FINANCIAL_VALIDATION") == PC.A   # fails at 1.645σ, passes at 1σ
    assert g("WATCH", 0.95, 0.01, 1.03) == PC.C and g("MULTI_RESEARCH_ELIGIBLE", 0.8, 0.01, 1.2) == PC.C
    assert g("REJECT", 0.95, 0.01, 3.0) == PC.REJECT                     # a grade never upgrades a bsv2 REJECT


def test_card_ranks_by_grade_then_probability_and_never_changes_decisions():
    cs = [cand("r", "REJECT", 0.99, 1.01), cand("b", "PAPER_BET", 0.80, 1.30), cand("a1", "PAPER_BET", 0.70, 1.60),
          cand("a2", "PAPER_BET", 0.78, 1.45), cand("w", "WATCH", 0.95, 1.03)]
    card = PC.build_card(CFG, cs, stage_a(("b", 0.05), ("a1", 0.01), ("a2", 0.01)), [], NOW)
    order = [r["prediction_id"] for r in card["rows"]]
    assert order == ["a2", "a1", "b", "w", "r"]
    assert {r["prediction_id"]: r["bsv2_decision"] for r in card["rows"]} == {c["prediction_id"]: c["decision"] for c in cs}
    assert all(r["money_eligible"] is False for r in card["rows"]) and card["real_money_enabled"] is False
    assert card["no_bet_today"] is False and card["grade_counts"]["A"] == 2


def test_no_bet_day_is_explicit():
    card = PC.build_card(CFG, [cand("w", "WATCH", 0.95, 1.03)], stage_a(), [], NOW)
    assert card["no_bet_today"] and "NO PAPER BETS TODAY" in PC.render_card_md(card)


def test_stakes_respect_caps_min_stake_and_daily_exposure():
    cs = [cand(f"p{i}", "PAPER_BET", 0.75, 1.45, exch=True, comm=0.05) for i in range(6)] + [cand("w", "WATCH", 0.9, 1.05)]
    card = PC.build_card(CFG, cs, stage_a(*[(f"p{i}", 0.01) for i in range(6)]), [], NOW)
    rows = {r["prediction_id"]: r for r in card["rows"]}
    # £20 at 1%: £0.20 < exchange min £1.00 = the 5% cap -> raised to £1.00; 10% daily cap (£2) allows two
    assert [rows[f"p{i}"]["stake_20_flat_1pct"] for i in range(6)].count(1.0) == 2
    assert PC.SKIP_DAILY_CAP in [rows[f"p{i}"]["stake_20_flat_1pct"] for i in range(6)]
    # £100 at 2%: £2 each, daily cap £10 -> five staked, sixth skipped
    assert [rows[f"p{i}"]["stake_100_flat_2pct"] for i in range(6)].count(2.0) == 5
    assert rows["w"]["stake_100_flat_1pct"] == ""                       # grade C never gets a stake
    for col in card["stake_columns"]:
        for r in card["rows"]:
            v = r[col]
            if isinstance(v, float):
                assert v <= int(col.split("_")[1]) * CFG.sim["max_stake_fraction"] + 1e-9


def test_kelly_zero_and_below_min_are_labelled():
    sim = {**CFG.sim, "practical_min_stake_gbp": {"exchange": 5.0, "bookmaker": 5.0}}
    rows = [{"grade": PC.A, "is_exchange": False, "probability": 0.6, "decimal_odds": 1.5, "commission": 0.0,
             "event_start": "2026-10-09"}]                                   # negative edge -> Kelly 0
    PC.hypothetical_stakes(rows, sim)
    assert rows[0]["stake_20_kelly_1_8"] == PC.SKIP_ZERO_STAKE and rows[0]["stake_20_flat_1pct"] == PC.SKIP_BELOW_MIN


def test_unknown_staking_kind_is_refused(tmp_path):
    bs = yaml.safe_load((REPO / "config/bet_selection_v2.yaml").read_text())
    bs["bankroll_simulation"]["policies"]["martingale"] = {"kind": "martingale"}
    (tmp_path / "config").mkdir()
    (tmp_path / "config/bet_selection_v2.yaml").write_text(yaml.safe_dump(bs))
    (tmp_path / "config/paper_card.yaml").write_text((REPO / "config/paper_card.yaml").read_text())
    with pytest.raises(ValueError, match="refused"):
        PC.load_config(tmp_path / "config/paper_card.yaml", tmp_path)


def _load_script():
    spec = importlib.util.spec_from_file_location("run_paper_card_t20", REPO / "scripts/run_paper_card.py")
    m = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = m
    spec.loader.exec_module(m)
    return m


def _write(path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)


def test_end_to_end_first_sight_enrichment_is_immutable_and_dashboard_separates_quality(tmp_path):
    m = _load_script()
    (tmp_path / "config").mkdir()
    for f in ("paper_card.yaml", "bet_selection_v2.yaml"):
        (tmp_path / "config" / f).write_text((REPO / "config" / f).read_text())
    from prediction_markets_lab.bet_selection_v2 import paper_ledger as L
    c_new, c_old = cand("new", "PAPER_BET", 0.75, 1.45), cand("old", "PAPER_BET", 0.74, 1.45)
    sel = lambda c, at: {**{k: "" for k in L.SELECTION_FIELDS}, **{k: c[k] for k in c if k in L.SELECTION_FIELDS},
                         "selection_id": L.selection_id("bsv2-4", c["prediction_id"]), "rule_version": "bsv2-4",
                         "decision_at": at, "stake_units": "1.0", "engine_status": "VALIDATED_HISTORICAL"}
    _write(tmp_path / "paper_betting_v2/selections.csv", [sel(c_new, NOW.isoformat()), sel(c_old, "2026-10-07T09:00:00+00:00")])
    _write(tmp_path / "reports/bet_selection_v2_candidates.csv", [c_new, c_old])
    (tmp_path / "reports/latest_stage_a_board.json").write_text(json.dumps(stage_a(("new", 0.01), ("old", 0.01))))
    out = m.run(tmp_path, NOW, tmp_path / "config/paper_card.yaml")
    enr = {r["prediction_id"]: r for r in L.read_rows(tmp_path / "paper_betting_v2/card_enrichment.csv")}
    assert enr["new"]["grade"] == PC.A and enr["old"]["grade"] == PC.UNGRADED     # decided in an earlier run: not back-filled
    before = (tmp_path / "paper_betting_v2/card_enrichment.csv").read_bytes()
    out2 = m.run(tmp_path, NOW, tmp_path / "config/paper_card.yaml")
    assert out2["enrichment_added"] == 0 and (tmp_path / "paper_betting_v2/card_enrichment.csv").read_bytes() == before
    _write(tmp_path / "paper_betting_v2/settlements.csv",
           [{"selection_id": L.selection_id("bsv2-4", "new"), "prediction_id": "new", "status": "WON", "result": "",
             "settled_at": NOW.isoformat(), "settlement_source": "t", "pnl_units": "0.45", "rule_version": "bsv2-4"}])
    d = m.run(tmp_path, NOW, tmp_path / "config/paper_card.yaml")["dashboard"]
    assert d["prediction_quality_headline"]["n"] == 1 and d["prediction_quality_headline"]["brier"] == round(0.25 ** 2, 5)
    assert d["financial"]["overall"]["realised_net_pnl_units"] == 0.45
    assert d["breakdowns_all_selections"]["grade"][PC.A]["financial"]["won"] == 1
    assert (tmp_path / "reports/paper_dashboard.md").exists() and (tmp_path / "reports/daily_paper_card.md").exists()


def test_decision_shadow_covers_whole_decided_space_is_analytical_and_append_only(tmp_path):
    cs = [cand("pb", "PAPER_BET", 0.75, 1.45), cand("w", "WATCH", 0.95, 1.03), cand("r", "REJECT", 0.60, 1.20)]
    card = PC.build_card(CFG, cs, stage_a(("pb", 0.01), ("w", 0.01)), [], NOW)
    rows = PC.shadow_rows(card)
    assert {r["prediction_id"] for r in rows} == {"pb", "w", "r"} and all(r["analytical_only"] is True for r in rows)
    assert all("stake_20_flat_1pct" not in r for r in rows)                      # never staked, never a paper bet
    w = next(r for r in rows if r["prediction_id"] == "w")
    assert w["ev_minus_1sigma"] is not None and w["ev_minus_1sigma"] < w["ev_at_p"] and w["bsv2_decision"] == "WATCH"
    p = tmp_path / "decision_shadow.csv"
    assert PC.append_shadow(p, rows) == 3 and PC.append_shadow(p, rows) == 0     # same price + decision -> no new row
    moved = PC.shadow_rows(PC.build_card(CFG, [cand("w", "WATCH", 0.95, 1.04)], stage_a(("w", 0.01)), [], NOW))
    assert PC.append_shadow(p, moved) == 1                                       # price moved -> one new row


def test_card_md_shows_directive_fields():
    card = PC.build_card(CFG, [cand("pb", "PAPER_BET", 0.75, 1.45)], {"predictions": [
        {"prediction_id": "pb", "sigma": 0.01, "competition": "ATP X", "engine_version": "1"}]}, [], NOW)
    md = PC.render_card_md(card)
    for s in ("ATP X", "match_winner", "bk", "2026-10-08T08:59", "atp_match_winner.betfair_market v1", "EV@P−1σ", "£20 1%"):
        assert s in md
    assert card["candidates_evaluated_at"] == NOW.isoformat()


def test_dashboard_has_band_breakdowns_and_no_fabricated_clv(tmp_path):
    from prediction_markets_lab.bet_selection_v2 import paper_ledger as L
    s = {**{k: "" for k in L.SELECTION_FIELDS}, **{k: v for k, v in cand("x", "PAPER_BET", 0.75, 1.45).items() if k in L.SELECTION_FIELDS},
         "selection_id": "s1", "rule_version": "bsv2-4", "stake_units": "1.0"}
    d = PC.dashboard(CFG, [s], {}, {}, {}, "bsv2-4", NOW)
    assert set(d["breakdowns_all_selections"]) >= {"probability_band", "odds_band", "grade", "competition", "rule_version"}
    assert "70-79.9%" in d["breakdowns_all_selections"]["probability_band"] and d["clv"].startswith("NOT_AVAILABLE")
