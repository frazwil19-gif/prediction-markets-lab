import csv
from datetime import date, datetime, timedelta, timezone

import pytest

from prediction_markets_lab.tennis_prospective import board as B
from prediction_markets_lab.tennis_prospective.engine import (
    ENGINE_VERSION, band_of, make_prediction_id, parse_tennis_odds, predict, tour_of)
from prediction_markets_lab.tennis_prospective.ledger import (
    append_predictions, append_settlements, read_predictions, read_settlements)
from prediction_markets_lab.tennis_prospective.performance import engine_performance, maturity
from prediction_markets_lab.tennis_prospective.settlement import parse_result_date, settle_one

NOW = datetime(2026, 9, 23, 7, 0, tzinfo=timezone.utc)
START = "2026-09-23T12:00:00Z"


def _market(key, a, pa, b, pb, lu="2026-09-23T06:55:00Z"):
    return {"key": key, "last_update": lu, "outcomes": [{"name": a, "price": pa}, {"name": b, "price": pb}]}


def _event(eid="e1", a="Carlos Alcaraz", b="Jannik Sinner", bookmakers=None, start=START):
    return {"id": eid, "sport_key": "tennis_atp_china_open", "sport_title": "ATP China Open", "commence_time": start,
            "home_team": a, "away_team": b, "bookmakers": bookmakers or []}


EX_FULL = [{"key": "betfair_ex_uk", "markets": [_market("h2h", "Carlos Alcaraz", 1.25, "Jannik Sinner", 5.0),
                                                 _market("h2h_lay", "Carlos Alcaraz", 1.27, "Jannik Sinner", 5.2)]}]
BOOKS = [{"key": k, "markets": [_market("h2h", "Carlos Alcaraz", 1.22, "Jannik Sinner", 4.33)]} for k in ("b1", "b2", "b3")]


def test_tour_detection_and_rejects_non_tennis():
    assert tour_of("tennis_atp_us_open") == "ATP" and tour_of("tennis_wta_us_open") == "WTA"
    assert tour_of("soccer_epl") is None
    with pytest.raises(ValueError):
        parse_tennis_odds([], "soccer_epl")


def test_parse_exchange_back_and_lay_and_books():
    q = parse_tennis_odds([_event(bookmakers=EX_FULL + BOOKS)], "tennis_atp_china_open")[0]
    assert q.player_a == "Carlos Alcaraz" and q.exchange_back == {"a": 1.25, "b": 5.0}
    assert q.exchange_lay == {"a": 1.27, "b": 5.2} and len(q.bookmaker_h2h) == 3


def test_parse_skips_malformed_events():
    bad = [_event(a="", b="X"), {"id": "x", "home_team": "A", "away_team": "B", "commence_time": "nonsense"}]
    assert parse_tennis_odds(bad, "tennis_atp_china_open") == []


def test_exchange_mid_probability_sums_to_one_and_bounds():
    p = predict(parse_tennis_odds([_event(bookmakers=EX_FULL)], "tennis_atp_china_open")[0], NOW)
    assert p.source == "EXCHANGE_MID" and p.source_validated
    assert p.p_a + p.p_b == pytest.approx(1.0) and 0 < p.p_b < p.p_a < 1
    mid_a, mid_b = 1.26, 5.1
    assert p.p_a == pytest.approx((1 / mid_a) / (1 / mid_a + 1 / mid_b), abs=1e-6)
    assert p.predicted_winner == "Carlos Alcaraz" and p.probability_band == band_of(p.predicted_probability)


def test_source_hierarchy_back_only_then_consensus_then_none():
    back_only = [{"key": "betfair_ex_uk", "markets": [EX_FULL[0]["markets"][0]]}]
    p = predict(parse_tennis_odds([_event(bookmakers=back_only)], "tennis_atp_china_open")[0], NOW)
    assert p.source == "EXCHANGE_BACK" and p.source_validated
    p = predict(parse_tennis_odds([_event(bookmakers=BOOKS)], "tennis_atp_china_open")[0], NOW)
    assert p.source == "BOOKMAKER_CONSENSUS" and not p.source_validated and not p.multi_research_eligible
    assert predict(parse_tennis_odds([_event(bookmakers=BOOKS[:2])], "tennis_atp_china_open")[0], NOW) is None


def test_missing_or_stale_exchange_quote():
    stale = [{"key": "betfair_ex_uk", "markets": [_market("h2h", "Carlos Alcaraz", 1.25, "Jannik Sinner", 5.0, lu="2026-09-22T20:00:00Z")]}]
    p = predict(parse_tennis_odds([_event(bookmakers=stale + BOOKS)], "tennis_atp_china_open")[0], NOW)
    assert p.source == "BOOKMAKER_CONSENSUS"  # stale exchange quote not used


def test_no_prediction_after_start():
    q = parse_tennis_odds([_event(bookmakers=EX_FULL)], "tennis_atp_china_open")[0]
    assert predict(q, datetime(2026, 9, 23, 12, 0, tzinfo=timezone.utc)) is None


def test_prediction_id_stable_and_engine_scoped():
    a = make_prediction_id("atp_match_winner.betfair_market", ENGINE_VERSION, "e1")
    assert a == make_prediction_id("atp_match_winner.betfair_market", ENGINE_VERSION, "e1")
    assert a != make_prediction_id("wta_match_winner.betfair_market", ENGINE_VERSION, "e1")


def test_atp_wta_separation():
    ev = _event(bookmakers=EX_FULL)
    pa = predict(parse_tennis_odds([ev], "tennis_atp_china_open")[0], NOW)
    pw = predict(parse_tennis_odds([ev], "tennis_wta_china_open")[0], NOW)
    assert pa.engine_id.startswith("atp_") and pw.engine_id.startswith("wta_") and pa.prediction_id != pw.prediction_id


def test_ledger_append_only_duplicates_and_immutability(tmp_path):
    path = tmp_path / "l.csv"
    p1 = predict(parse_tennis_odds([_event(bookmakers=EX_FULL)], "tennis_atp_china_open")[0], NOW)
    assert append_predictions(path, [p1]) == (1, 0)
    before = path.read_bytes()
    later = predict(parse_tennis_odds([_event(bookmakers=BOOKS)], "tennis_atp_china_open")[0], NOW + timedelta(hours=1))
    assert later.prediction_id == p1.prediction_id
    assert append_predictions(path, [later]) == (0, 1)  # first snapshot stays canonical
    assert path.read_bytes() == before
    p2 = predict(parse_tennis_odds([_event(eid="e2", bookmakers=EX_FULL)], "tennis_atp_china_open")[0], NOW)
    append_predictions(path, [p2])
    assert path.read_bytes().startswith(before) and len(read_predictions(path)) == 2


def _pred_row(winner="Carlos Alcaraz", p=0.8):
    return {"prediction_id": "x1", "player_a": "Carlos Alcaraz", "player_b": "Jannik Sinner", "predicted_winner": winner,
            "predicted_probability": str(p), "commence_time": "2026-09-23T12:00:00+00:00", "source_validated": "True"}


def test_settlement_correct_incorrect_retirement_and_walkover():
    res = [{"winner_name": "Carlos Alcaraz", "loser_name": "Jannik Sinner", "score": "6-3 2-1 RET", "result_date": date(2026, 9, 21)}]
    s = settle_one(_pred_row(), res, NOW)
    assert s["status"] == "SETTLED_CORRECT"  # retirement counts with the official winner
    s = settle_one(_pred_row(winner="Jannik Sinner"), res, NOW)
    assert s["status"] == "SETTLED_INCORRECT"
    wo = [{**res[0], "score": "W/O"}]
    assert settle_one(_pred_row(), wo, NOW)["status"] == "VOID"


def test_settlement_not_found_or_ambiguous_is_never_guessed():
    assert settle_one(_pred_row(), [], NOW) is None
    far = [{"winner_name": "Carlos Alcaraz", "loser_name": "Jannik Sinner", "score": "6-1", "result_date": date(2026, 1, 1)}]
    assert settle_one(_pred_row(), far, NOW) is None
    two = [{"winner_name": "Carlos Alcaraz", "loser_name": "Jannik Sinner", "score": "6-1", "result_date": date(2026, 9, 21)}] * 2
    assert settle_one(_pred_row(), two, NOW) is None


def test_settlement_file_first_wins(tmp_path):
    p = tmp_path / "s.csv"
    row = {"prediction_id": "x1", "status": "SETTLED_CORRECT", "winner": "A", "score": "", "result_source": "t",
           "settlement_timestamp": "t", "correct": 1}
    assert append_settlements(p, [row]) == 1
    assert append_settlements(p, [{**row, "status": "SETTLED_INCORRECT"}]) == 0
    assert read_settlements(p)["x1"]["status"] == "SETTLED_CORRECT"


def test_parse_result_dates():
    assert parse_result_date("2026/09/21") == date(2026, 9, 21)
    assert parse_result_date("20260921") == date(2026, 9, 21)
    assert parse_result_date("2026-09-21") == date(2026, 9, 21)


def test_maturity_rules():
    assert maturity(10, 5) == "COLLECTING"
    assert maturity(60, 5) == "EARLY"
    assert maturity(400, 90) == "EARLY"
    assert maturity(400, 120) == "INTERMEDIATE"
    assert maturity(1200, 350) == "MATURE"


def test_performance_excludes_research_only_and_void():
    preds = [{"prediction_id": "a", "predicted_probability": "0.9", "source_validated": "True"},
             {"prediction_id": "b", "predicted_probability": "0.82", "source_validated": "True"},
             {"prediction_id": "c", "predicted_probability": "0.7", "source_validated": "False"},
             {"prediction_id": "d", "predicted_probability": "0.6", "source_validated": "True"}]
    st = {"a": {"status": "SETTLED_CORRECT"}, "b": {"status": "SETTLED_INCORRECT"}, "c": {"status": "SETTLED_CORRECT"},
          "d": {"status": "VOID"}}
    r = engine_performance(preds, st)
    assert r["settled"] == 2 and r["correct"] == 1 and r["settled_ge_80"] == 2
    assert r["expected_correct"] == pytest.approx(1.72)
    t = {x["threshold"]: x for x in r["thresholds"]}
    assert t[0.85]["n"] == 1 and t[0.85]["actual_wins"] == 1


def test_board_ranks_by_probability_and_separates_research_only():
    evs = [_event(eid="e1", bookmakers=EX_FULL),
           _event(eid="e2", a="Player X", b="Player Y", bookmakers=[{"key": "betfair_ex_uk", "markets": [_market("h2h", "Player X", 1.9, "Player Y", 2.0)]}]),
           _event(eid="e3", bookmakers=BOOKS)]
    preds = [predict(q, NOW) for q in parse_tennis_odds(evs, "tennis_atp_china_open")]
    reg = {"engines": {"atp_match_winner": {"holdout_n": 5066, "bands": {"80-84.9%": {"n": 411, "actual_rate": 0.822, "wilson95": [0.78, 0.86]}}}}}
    b = B.build_board("2026-09-23", preds, reg, {"active_keys": ["tennis_atp_china_open"], "events_returned": 3})
    ps = [r["predicted_probability"] for r in b["predictions"]]
    assert ps == sorted(ps, reverse=True) and len(b["research_only"]) == 1
    md = B.render_markdown(b)
    assert "PAPER" in md and "EV" not in md and "stake" not in md.lower().replace("no stakes", "")
