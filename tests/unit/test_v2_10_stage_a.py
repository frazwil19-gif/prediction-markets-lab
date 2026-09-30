"""V2-10 fix B: Stage A shows every valid prediction regardless of price; Stage B unchanged. No outcomes, no network."""
from __future__ import annotations

import copy
import json
import hashlib
import importlib.util
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

from prediction_markets_lab.bet_selection_v2 import prices as PR
from prediction_markets_lab.bet_selection_v2.evaluate import evaluate_prediction, load_config as load_bs
from prediction_markets_lab.prediction_platform import stage_a as SA
from prediction_markets_lab.prediction_platform.schema import PREDICTION_FIELDS

REPO = Path(__file__).resolve().parents[2]
NOW = datetime(2026, 9, 30, 12, 59, tzinfo=timezone.utc)
SCAN = "2026-09-30T12:54:00+00:00"
CFG = SA.StageAConfig("stage-a-1", 0.70, REPO / "research/platform_v2/card_engine_v2_7/RESULTS.json",
                      REPO / "config/bet_selection_v2.yaml")
BS = load_bs(CFG.bet_selection_config)


def pred(eid, a, b, p, pid=None, valid="True", start="2026-10-01T07:00:00+00:00"):
    return {**{k: "" for k in PREDICTION_FIELDS}, "prediction_id": pid or f"p_{eid}", "sport": "tennis", "competition": "ATP Tokyo",
            "event_id": eid, "event_key": f"tennis|tennis_atp_japan_open|{eid}", "event_name": f"{a} v {b}",
            "event_start": start, "market": "match_winner", "selection": a, "estimated_probability": str(p),
            "probability_band": "80%+", "engine_id": "tennis_atp.exchange_mid", "engine_version": "v1",
            "engine_status": "VALIDATED_HISTORICAL", "prediction_timestamp": "2026-09-29T08:31:00+00:00",
            "prediction_valid": valid}


def prob_row(eid, a, b, pa, width):
    return {"scan_timestamp_utc": SCAN, "sport_key": "tennis_atp_japan_open", "event_id": eid, "player_a": a, "player_b": b,
            "commence_time": "2026-10-01T07:00:00+00:00", "source": "EXCHANGE_MID", "source_validated": "True",
            "p_a": str(pa), "p_b": str(1 - pa), "exchange_spread_prob": str(width)}


def price_row(eid, a, b, book, oa, ob):
    return {"scan_timestamp_utc": SCAN, "sport_key": "tennis_atp_japan_open", "event_id": eid, "player_a": a, "player_b": b,
            "bookmaker": book, "market": "h2h", "odds_a": str(oa), "odds_b": str(ob), "last_update": SCAN}


def scenario():
    preds = [pred("wide", "Liudmila Samsonova", "Linda Fruhvirtova", 0.92),      # strong, wide exchange book
             pred("none", "Aryna Sabalenka", "Renata Zarazua", 0.95),           # strong, no quotes at all
             pred("poor", "Alexander Zverev", "Cameron Norrie", 0.88),          # strong, clean, below fair
             pred("value", "Daniil Medvedev", "Pablo Carreno Busta", 0.79),     # strong, clean, above fair
             pred("weak", "Holger Rune", "Kyrian Jacquet", 0.62),               # below strong threshold
             pred("inv", "A Player", "B Player", 0.90, valid="False")]          # invalid -> never on the board
    prob = [prob_row("wide", "Liudmila Samsonova", "Linda Fruhvirtova", 0.9263, 0.218),
            prob_row("poor", "Alexander Zverev", "Cameron Norrie", 0.8867, 0.0079),
            prob_row("value", "Daniil Medvedev", "Pablo Carreno Busta", 0.7879, 0.0188),
            prob_row("weak", "Holger Rune", "Kyrian Jacquet", 0.6237, 0.01)]
    prices = [price_row("wide", "Liudmila Samsonova", "Linda Fruhvirtova", "boylesports", 1.25, 3.6),
              price_row("poor", "Alexander Zverev", "Cameron Norrie", "betano_uk", 1.10, 7.0),
              price_row("value", "Daniil Medvedev", "Pablo Carreno Busta", "betvictor", 1.29, 3.6),
              price_row("weak", "Holger Rune", "Kyrian Jacquet", "betway", 1.55, 2.4)]

    def snaps_for(p):
        return PR.tennis_from_snapshots(p, prices, prob)
    return preds, prob, snaps_for


def build():
    preds, prob, snaps_for = scenario()
    return SA.build(preds, prob, snaps_for, BS, CFG, SA.calibration_se(CFG.calibration_results), NOW)


def test_every_valid_prediction_shown_whatever_the_price():
    b = build()
    by = {r["prediction_id"]: r for r in b["predictions"]}
    assert set(by) == {"p_wide", "p_none", "p_poor", "p_value", "p_weak"}          # invalid excluded, nothing else dropped
    assert by["p_wide"]["price_status"] == SA.QUALITY_FAIL and "EXCHANGE_SPREAD_TOO_WIDE" in by["p_wide"]["price_status_reasons"]
    assert by["p_none"]["price_status"] == SA.UNAVAILABLE
    assert by["p_poor"]["price_status"] == SA.POOR_PAYOUT
    assert by["p_value"]["price_status"] == SA.PRICE_VALID
    assert by["p_wide"]["stage_a_label"] == "STRONG_PREDICTION_PRICE_QUALITY_FAIL"
    assert not by["p_wide"]["financially_assessable"] and not by["p_none"]["financially_assessable"]
    assert b["summary"]["strong_predictions"] == 4


def test_strong_prediction_is_never_a_bet_recommendation():
    assert all(r["is_bet_recommendation"] is False for r in build()["predictions"])


def test_ranked_by_probability_only():
    ps = [r["probability"] for r in build()["predictions"]]
    assert ps == sorted(ps, reverse=True)
    assert [r["rank"] for r in build()["predictions"]] == list(range(1, len(ps) + 1))


def test_probability_is_latest_same_scan_with_ledger_kept_and_sigma_traced():
    r = {x["prediction_id"]: x for x in build()["predictions"]}["p_value"]
    assert r["probability"] == 0.7879 and r["ledger_probability"] == 0.79 and r["probability_basis"] == SA.BASIS_SCAN
    assert abs(r["sigma"] ** 2 - (r["sigma_calibration"] ** 2 + r["sigma_half_width"] ** 2)) < 1e-6
    none = {x["prediction_id"]: x for x in build()["predictions"]}["p_none"]
    assert none["probability_basis"] == SA.BASIS_LEDGER and none["probability"] == 0.95


def test_stage_b_decisions_unchanged_by_stage_a():
    preds, prob, snaps_for = scenario()
    before = [evaluate_prediction(copy.deepcopy(p), snaps_for(p), BS, NOW)[0].row() for p in preds]
    inputs = copy.deepcopy(preds)
    SA.build(preds, prob, snaps_for, BS, CFG, None, NOW)
    after = [evaluate_prediction(copy.deepcopy(p), snaps_for(p), BS, NOW)[0].row() for p in preds]
    assert before == after and preds == inputs
    # no Stage B PAPER_BET is created by showing strong predictions (Medvedev +1.6% < 2% gate)
    assert all(r["decision"] != "PAPER_BET" for r in after)


def test_duplicate_rows_collapsed_to_latest_prediction():
    preds, prob, snaps_for = scenario()
    dup = dict(preds[2], prediction_id="p_poor_v2", prediction_timestamp="2026-09-30T12:54:00+00:00")
    b = SA.build(preds + [dup], prob, snaps_for, BS, CFG, None, NOW)
    ids = [r["prediction_id"] for r in b["predictions"]]
    assert "p_poor_v2" in ids and "p_poor" not in ids and b["summary"]["duplicate_prediction_rows_collapsed"] == 1


def test_calibration_se_matches_v2_7_logger():
    spec = importlib.util.spec_from_file_location("run_card_shadow_t", REPO / "scripts/run_card_shadow.py")
    m = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = m
    spec.loader.exec_module(m)
    a, b = SA.calibration_se(CFG.calibration_results), m.cal_se_fn(CFG.calibration_results)
    assert all(a(p) == b(p) for p in (0.55, 0.66, 0.79, 0.81, 0.97))


def test_config_threshold_matches_existing_high_p_definitions():
    import yaml
    c = yaml.safe_load((REPO / "config/prediction_board_stage_a.yaml").read_text())
    shadow = yaml.safe_load((REPO / "config/card_research_shadow.yaml").read_text())
    assert c["strong_prediction_min_probability"] == BS["high_probability_threshold"] == shadow["cohorts"]["HIGH_P"]["min_leg_p"]


def test_frozen_v2_7_config_hash_unchanged():
    """V2-7 cer-2 config must stay byte-identical (sha recorded at activation: 9e52b67df08691d0)."""
    assert hashlib.sha256((REPO / "config/card_research_shadow.yaml").read_bytes()).hexdigest()[:16] == "9e52b67df08691d0"


def test_markdown_states_not_a_bet():
    md = SA.render_md(build())
    assert "not a bet" in md.lower() and "STRONG_PREDICTION_PRICE_UNAVAILABLE" in md


def test_wide_book_is_quality_fail_even_with_a_same_time_ledger_exchange_quote():
    """V2-10 finding: a ledger row created in the same scan carries the exchange back price with no spread info, so the
    bsv2-3 evaluator sees it as 'clean'. Stage A must still report the wide book as not financially assessable."""
    preds, prob, _ = scenario()
    p = dict(preds[0], prediction_timestamp=SCAN, live_price="1.04", live_price_source="betfair_ex_uk back (odds_api)")

    def snaps_for(x):
        return [PR.from_ledger_row(x)]
    b = SA.build([p], prob, snaps_for, BS, CFG, None, NOW)
    r = b["predictions"][0]
    assert r["price_status"] == SA.QUALITY_FAIL and r["price_status_reasons"] == "EXCHANGE_SPREAD_TOO_WIDE"
    assert r["stage_a_label"] == "STRONG_PREDICTION_PRICE_QUALITY_FAIL"


def test_stage_a_failure_never_blocks_production_board(tmp_path, monkeypatch):
    spec = importlib.util.spec_from_file_location("run_unified_t", REPO / "scripts/run_unified_prediction_board.py")
    m = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = m
    spec.loader.exec_module(m)

    def boom(*a, **k):
        raise RuntimeError("synthetic")
    monkeypatch.setattr(m, "build_stage_a", boom)
    monkeypatch.setattr(m, "REPORTS", tmp_path)
    monkeypatch.setattr(m.H, "evaluate", lambda repo, now, st: {"overall": "HEALTHY", "api_credits": {"remaining": None},
                                                                   "components": {}, "warnings": []})
    m.build(m.Registry.load(), {})
    assert (tmp_path / "latest_prediction_board.json").exists()
    assert json.loads((tmp_path / "latest_stage_a_board.json").read_text())["status"] == "STAGE_A_BUILD_FAILED"
