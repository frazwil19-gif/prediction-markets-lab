"""V2-13 stage-a-2: tennis + football + NBA coexist on one probability-first board; P_FIRST_SNAPSHOT vs P_CURRENT_SCAN
are explicit; football 1X2 is shown as the normalised triplet (raw kept); sigma per sport; price never suppresses."""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from prediction_markets_lab.bet_selection_v2 import prices as PR
from prediction_markets_lab.bet_selection_v2.evaluate import load_config as load_bs
from prediction_markets_lab.prediction_platform import stage_a as SA
from prediction_markets_lab.prediction_platform.registry import Registry
from prediction_markets_lab.prediction_platform.schema import PREDICTION_FIELDS

REPO = Path(__file__).resolve().parents[2]
NOW = datetime(2026, 10, 8, 9, 0, tzinfo=timezone.utc)
CFG = SA.load_config(REPO / "config/prediction_board_stage_a.yaml", REPO)
BS = load_bs(CFG.bet_selection_config)
FSE = SA.football_sigma(CFG.football_sigma_evidence)
STATUS = {eid: e["calibration_status"] for eid, e in Registry.load().engines.items()}


def row(pid, sport, engine, market, sel, p, key, name="Home FC v Away FC", ts="2026-10-08T07:00:00+00:00", **kw):
    return {**{k: "" for k in PREDICTION_FIELDS}, "prediction_id": pid, "sport": sport, "competition": "C", "engine_id": engine,
            "engine_version": "1", "engine_status": "VALIDATED_HISTORICAL", "event_key": key, "event_name": name,
            "event_start": "2026-10-10T14:00:00+00:00", "market": market, "selection": sel, "estimated_probability": str(p),
            "probability_band": "x", "prediction_timestamp": ts, "prediction_valid": "True", **kw}


def football_triplet(key, ph, pd_, pa):
    e = "football_1x2.market_consensus"
    return [row(f"{key}h", "football", e, "1x2", "home", ph, key), row(f"{key}d", "football", e, "1x2", "draw", pd_, key),
            row(f"{key}a", "football", e, "1x2", "away", pa, key)]


def board(rows, prob=(), snaps=lambda p: []):
    return SA.build(rows, list(prob), snaps, BS, CFG, SA.calibration_se(CFG.calibration_results), NOW, FSE, STATUS)


def test_config_is_stage_a_2_and_threshold_unchanged():
    assert CFG.board_version == "stage-a-2" and CFG.strong_min_probability == 0.70


def test_football_1x2_triplet_is_normalised_for_display_raw_kept():
    rows = football_triplet("f1", 0.80, 0.13, 0.08)            # sums to 1.01
    b = {r["prediction_id"]: r for r in board(rows)["predictions"]}
    h = b["f1h"]
    assert h["normalisation"] == SA.NORMALISED and h["ledger_probability"] == 0.80
    assert abs(h["probability"] - 0.80 / 1.01) < 1e-6 and h["probability_basis"] == SA.BASIS_LEDGER
    assert abs(sum(b[k]["probability"] for k in ("f1h", "f1d", "f1a")) - 1.0) < 1e-5
    assert h["p_current_scan"] is None and h["p_first_snapshot"] == h["probability"]


def test_incomplete_triplet_is_flagged_not_normalised():
    rows = football_triplet("f2", 0.75, 0.15, 0.11)[:2]
    b = {r["prediction_id"]: r for r in board(rows)["predictions"]}
    assert b["f2h"]["normalisation"] == SA.INCOMPLETE and b["f2h"]["probability"] == 0.75


def test_football_sigma_band_specific_and_labelled():
    rows = football_triplet("f3", 0.82, 0.11, 0.07) + [row("dc", "football", "football_double_chance.derived_1x2",
                                                             "double_chance", "1X", 0.90, "f3")]
    b = {r["prediction_id"]: r for r in board(rows)["predictions"]}
    assert b["f3h"]["sigma"] == round(FSE("1x2", b["f3h"]["probability"]), 6) and b["f3h"]["sigma_method"] == SA.SIGMA_FOOTBALL
    assert b["dc"]["sigma"] == round(FSE("double_chance", 0.90), 6)
    assert b["dc"]["calibration_status"].startswith("EXPOSED_DATA_ONLY")
    assert b["f3h"]["calibration_status"].startswith("HISTORICAL_CLOSING_ESTIMATOR_ONLY")


def test_nba_row_coexists_sigma_not_estimated():
    rows = [row("n1", "basketball", "nba_moneyline.market", "moneyline", "Boston Celtics", 0.86, "nba|1",
                name="Boston Celtics v Washington Wizards", live_price="1.15", live_price_source="odds_api best book")]
    r = board(rows)["predictions"][0]
    assert r["sigma"] is None and r["sigma_method"] == SA.SIGMA_NONE and r["strength"] == SA.STRONG
    assert r["price_status"] == SA.UNAVAILABLE and r["calibration_status"].startswith("HOLDOUT_PASSED")


def test_tennis_first_snapshot_vs_current_scan_are_distinct():
    t = row("t1", "tennis", "atp_match_winner.betfair_market", "match_winner", "Ann Able", 0.85, "tennis|k|e1",
            name="Ann Able v Bea Bold", event_id="e1")
    prob = [{"scan_timestamp_utc": "2026-10-08T08:00:00+00:00", "sport_key": "k", "event_id": "e1", "player_a": "Ann Able",
             "player_b": "Bea Bold", "source": "EXCHANGE_MID", "source_validated": "True", "p_a": "0.78", "p_b": "0.22",
             "exchange_spread_prob": "0.01"}]
    r = board([t], prob)["predictions"][0]
    assert r["probability_basis"] == SA.BASIS_SCAN and r["p_current_scan"] == 0.78 and r["p_first_snapshot"] == 0.85
    assert r["probability"] == 0.78 and r["sigma_method"] == SA.SIGMA_TENNIS


def test_multi_sport_ranking_is_probability_only_and_nothing_suppressed():
    rows = (football_triplet("f4", 0.55, 0.25, 0.21)
            + [row("n2", "basketball", "nba_moneyline.market", "moneyline", "X", 0.91, "nba|2"),
               row("dc2", "football", "football_double_chance.derived_1x2", "double_chance", "1X", 0.79, "f4")])
    b = board(rows)
    ps = [r["probability"] for r in b["predictions"]]
    assert ps == sorted(ps, reverse=True) and len(b["predictions"]) == 5
    assert b["summary"]["strong_by_sport"] == {"basketball": 1, "football": 1}
    assert all(r["is_bet_recommendation"] is False for r in b["predictions"])
    assert all(r["price_status"] == SA.UNAVAILABLE for r in b["predictions"])   # no prices -> still shown


def test_markdown_shows_both_probability_bases():
    md = SA.render_md(board(football_triplet("f5", 0.81, 0.12, 0.08)))
    assert "P first snapshot" in md and "P current scan" in md and "not a bet" in md.lower()
