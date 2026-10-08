from datetime import datetime, timezone
from pathlib import Path

import yaml

from prediction_markets_lab.daily_card import capacity as Q

REPO = Path(__file__).resolve().parents[2]
CFG = yaml.safe_load((REPO / "config/qualified_capacity.yaml").read_text())


def sel(i, p, odds, ev, day):
    return {"selection_id": f"s{i}", "sport": "tennis", "market": "match_winner", "engine_id": "e", "probability": str(p),
            "decimal_odds": str(odds), "net_ev": str(ev), "decision_at": f"2026-10-{day:02d}T10:00:00+00:00"}


def test_expected_vs_realised_sums():
    s = [sel(1, 0.6, 1.8, 0.08, 1), sel(2, 0.7, 1.5, 0.05, 1), sel(3, 0.5, 2.1, 0.05, 2)]
    st = {"s1": {"status": "WON", "pnl_units": "0.8"}, "s2": {"status": "LOST", "pnl_units": "-1"}}
    r = Q.expected_vs_realised(s, st)
    assert r["settled_bets"] == 2 and r["open_bets"] == 1
    assert r["expected_profit_gbp"] == 0.13 and r["realised_profit_gbp"] == -0.2
    assert r["expected_wins"] == 1.3 and r["actual_wins"] == 1


def test_capacity_counts_zero_bet_days_and_daily_cap():
    s = [sel(i, 0.6, 1.8, 0.1 - i / 100, 1) for i in range(8)]   # 8 bets on day 1, none on days 2..10
    c = Q.capacity(s, CFG, "2026-10-01", "2026-10-10")
    assert c["days_observed"] == 10 and c["qualifying_per_month"] == 24.0
    b50 = c["bankroll_scenarios"]["£50"]
    assert b50["max_bets_per_day"] == 5 and b50["expected_profit_per_month_after_daily_cap_gbp"] < b50["expected_profit_per_month_theoretical_gbp"]
    assert c["limits"]["execution_price"].startswith("UNMEASURED")


def test_rejection_categories_use_latest_evaluation():
    rows = [{"prediction_id": "a", "evaluated_at": "1", "bsv2_decision": "REJECT", "bsv2_reasons": "NET_EV_NOT_POSITIVE"},
            {"prediction_id": "a", "evaluated_at": "2", "bsv2_decision": "PAPER_BET", "bsv2_reasons": ""},
            {"prediction_id": "b", "evaluated_at": "1", "bsv2_decision": "REJECT", "bsv2_reasons": "P_BELOW_FLOOR|NET_EV_NOT_POSITIVE"}]
    r = Q.rejection_categories(rows)
    assert r == {"predictions_evaluated": 2, "rejections_by_reason": {"P_BELOW_FLOOR": 1, "NET_EV_NOT_POSITIVE": 1}}


def test_build_runs_on_repo():
    r = Q.build(REPO, CFG, datetime(2026, 10, 8, tzinfo=timezone.utc))
    assert "expected_vs_realised" in r and Q.render_md(r).startswith("# Qualified")


def test_credit_utilisation_review_is_advisory_and_complete():
    import importlib.util
    spec = importlib.util.spec_from_file_location("credit_report", REPO / "scripts/credit_report.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    u = m.utilisation(REPO, {"tennis_prediction_board": {"credits_charged": 30}}, datetime(2026, 10, 8, tzinfo=timezone.utc))
    t = u["consumers"]["tennis_prediction_board"]
    assert t["allocation"] == 150 and t["consumed"] == 30 and t["unused"] == 120 and t["utilisation_pct"] == 20.0
    assert u["consumers"]["football_settlement"]["recommendation"].startswith("idle")
    assert "advisory" in u["note"]


def test_capacity_uses_current_rule_version_only():
    r = Q.build(REPO, CFG, datetime(2026, 10, 8, tzinfo=timezone.utc))
    rule = Q.current_rule_version(REPO)
    assert r["capacity_rule_version"] == rule
    assert r["capacity"]["qualifying_bets"] == r["paper_bets_by_rule_version"].get(rule, 0)
