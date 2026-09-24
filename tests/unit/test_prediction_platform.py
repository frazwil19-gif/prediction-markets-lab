import csv
import json
from dataclasses import replace
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from prediction_markets_lab.prediction_platform import adapters as A
from prediction_markets_lab.prediction_platform import board as B
from prediction_markets_lab.prediction_platform import health as H
from prediction_markets_lab.prediction_platform import performance as P
from prediction_markets_lab.prediction_platform import settle as S
from prediction_markets_lab.prediction_platform.ledger import LedgerIntegrityError, append_unique, read_rows
from prediction_markets_lab.prediction_platform.registry import Registry
from prediction_markets_lab.prediction_platform.schema import (
    PREDICTION_FIELDS, SETTLEMENT_FIELDS, band_of, fair_odds, make_prediction_id, to_row, validate)

NOW = datetime(2026, 9, 25, 12, 0, tzinfo=timezone.utc)
CTX = A.RunContext("2026-09-25T07:00:00+00:00", "2026-09-25T11:58:00+00:00", 1.33)


@pytest.fixture(scope="module")
def reg():
    return Registry.load()


def card(data_ts=NOW - timedelta(minutes=5), ko="2026-09-26T14:00:00Z", probs=(0.70, 0.18, 0.12), extra=()):
    rows = [{"sport": "football", "competition": "Premier League", "event": "Arsenal v Leeds United", "market": "1x2",
             "selection": s, "estimated_probability": p, "available_odds": o, "bookmaker": "BookA", "kickoff_time": ko}
            for s, p, o in zip(("home", "draw", "away"), probs, (1.40, 5.5, 8.0))]
    rows += [{"sport": "football", "competition": "Premier League", "event": "Arsenal v Leeds United", "market": "over_under_2_5",
              "selection": s, "estimated_probability": p, "available_odds": o, "bookmaker": "BookB", "kickoff_time": ko}
             for s, p, o in (("over", 0.58, 1.66), ("under", 0.42, 2.3))]
    return {"data_timestamp": data_ts.isoformat(), "candidates": rows + list(extra)}


# ---------------- registry / schema
def test_registry_valid_and_statuses(reg):
    assert reg.validate() == []
    assert reg.get("football_double_chance.derived_1x2")["status"] == "PROVISIONAL_PROSPECTIVE"
    assert reg.get("football_double_chance.derived_1x2")["money_eligible"] is False
    for eid in ("atp_match_winner.betfair_market", "wta_match_winner.betfair_market", "nba_moneyline.market"):
        assert reg.get(eid)["money_eligible"] is False
    with pytest.raises(KeyError):
        reg.get("nope")


def test_registry_rejects_money_on_provisional(reg):
    data = json.loads(json.dumps(reg.data))
    data["engines"][-1]["money_eligible"] = True
    assert any("money_eligible" in e for e in Registry(data).validate())


def test_nba_activation_gate(reg):
    assert not reg.collectable("nba_moneyline.market", datetime(2026, 10, 19, tzinfo=timezone.utc))
    assert reg.collectable("nba_moneyline.market", datetime(2026, 10, 20, tzinfo=timezone.utc))
    assert not reg.collectable("football_btts.market_implied_poisson", NOW)


def test_bands_fair_odds_ids():
    assert band_of(0.80) == "80-84.9%" and band_of(0.9999) == "95%+" and band_of(0.3) == "<50%"
    assert fair_odds(0.8) == pytest.approx(1.25)
    for bad in (0.0, 1.0, -0.1):
        with pytest.raises(ValueError):
            fair_odds(bad)
    a = make_prediction_id("e", "1", "k", "m", "s")
    assert a == make_prediction_id("e", "1", "k", "m", "s") and a != make_prediction_id("e", "2", "k", "m", "s")


# ---------------- football adapter (1X2, O/U, DC)
def test_football_ingestion_dc_and_statuses(reg):
    preds, skips = A.football_from_card(card(), reg, CTX, NOW, origin="t")
    by = {(p.engine_id, p.selection): p for p in preds}
    assert len([p for p in preds if p.engine_id == A.FOOTBALL_DC]) == 3
    assert by[(A.FOOTBALL_DC, "1X")].estimated_probability == pytest.approx(0.88)
    assert by[(A.FOOTBALL_DC, "12")].estimated_probability == pytest.approx(0.82)
    assert by[(A.FOOTBALL_DC, "1X")].live_price == pytest.approx(1 / (1 / 1.40 + 1 / 5.5), rel=1e-3)
    dc = by[(A.FOOTBALL_DC, "1X")]
    assert dc.engine_status == "PROVISIONAL_PROSPECTIVE" and dc.prediction_valid
    assert dc.single_eligible is False and dc.multi_research_eligible is True      # short price, not a single
    assert by[(A.FOOTBALL_1X2, "home")].single_eligible is True                  # 1/0.7 = 1.43 >= 1.33, money engine
    assert by[(A.FOOTBALL_1X2, "draw")].multi_research_eligible is False
    assert (A.FOOTBALL_OU, "over") in by and (A.FOOTBALL_OU, "under") not in by
    assert all(validate(p) == [] for p in preds)
    assert dc.minutes_to_event == pytest.approx((datetime(2026, 9, 26, 14, tzinfo=timezone.utc) - (NOW - timedelta(minutes=5))).total_seconds() / 60)
    assert dc.configured_scan_time == CTX.configured_scan_time and dc.actual_workflow_start == CTX.actual_workflow_start


def test_football_fail_closed(reg):
    assert A.football_from_card(card(data_ts=NOW - timedelta(hours=7)), reg, CTX, NOW, "t")[0] == []
    p, s = A.football_from_card(card(ko="2026-09-28T14:00:00Z"), reg, CTX, NOW, "t")
    assert p == [] and s[0].reason == "OUTSIDE_48H_WINDOW"
    p, s = A.football_from_card(card(ko="2026-09-25T11:00:00Z"), reg, CTX, NOW, "t")
    assert p == [] and s[0].reason == "EVENT_STARTED"
    p, s = A.football_from_card(card(probs=(0.7, 0.4, 0.12)), reg, CTX, NOW, "t")
    assert not [x for x in p if x.engine_id in (A.FOOTBALL_1X2, A.FOOTBALL_DC)]
    dup = card()["candidates"][0]
    p, s = A.football_from_card(card(extra=[dup]), reg, CTX, NOW, "t")
    assert p == [] and "REVIEW_REQUIRED" in s[0].reason


# ---------------- tennis mirror (migration compatibility)
TROW = {"prediction_id": "bd5f7921242f7ae2", "engine_id": "wta_match_winner.betfair_market", "engine_version": "1", "tour": "WTA",
        "sport_key": "tennis_wta_x", "tournament": "WTA X", "event_id": "ev1", "player_a": "A One", "player_b": "B Two",
        "commence_time": "2026-09-24T05:00:00+00:00", "prediction_timestamp": "2026-09-23T20:05:58+00:00",
        "source": "EXCHANGE_MID", "source_validated": "True", "raw_prices": "ex_back=1.09/10.0;ex_lay=1.11/12.0",
        "p_a": "0.909091", "p_b": "0.090909", "predicted_winner": "A One", "predicted_probability": "0.909091",
        "probability_band": "90-94.9%", "multi_research_eligible": "True", "status": "PREDICTED"}


def test_tennis_mirror_keeps_ids_and_marks_research_only(reg):
    run_log = [{"scan_timestamp_utc": "2026-09-23T20:06:30+00:00", "configured_schedule_utc": "MANUAL"}]
    bad = {**TROW, "prediction_id": "x2", "source": "BOOKMAKER_CONSENSUS", "source_validated": "False"}
    preds, skips = A.tennis_from_ledger([TROW, bad], run_log, reg, 1.33, "t")
    a, b = preds
    assert a.prediction_id == TROW["prediction_id"] == a.origin_prediction_id
    assert a.live_price == 1.09 and a.prediction_valid and a.configured_scan_time == "MANUAL"
    assert b.prediction_valid is False and b.paper_status == "RESEARCH_ONLY_SOURCE"
    assert a.single_eligible is False and a.single_ineligible_reason == "engine not money-eligible"


def test_real_tennis_ledger_mirrors_cleanly(reg):
    repo = Path(__file__).resolve().parents[2]
    rows = read_rows(repo / "tennis_predictions/ledger_predictions.csv")
    preds, skips = A.tennis_from_ledger(rows, [], reg, 1.33, "t")
    assert len(preds) == len(rows) and not skips


# ---------------- NBA adapter
def nba_event(minutes=600, n_books=3):
    bms = [{"key": f"b{i}", "markets": [{"key": "h2h", "outcomes": [{"name": "Boston Celtics", "price": 1.25},
                                                                    {"name": "Detroit Pistons", "price": 4.0}]}]} for i in range(n_books)]
    bms.append({"key": "betfair_ex_uk", "markets": [{"key": "h2h", "outcomes": [{"name": "Boston Celtics", "price": 9.0},
                                                                                {"name": "Detroit Pistons", "price": 1.1}]}]})
    return {"id": "nba1", "home_team": "Boston Celtics", "away_team": "Detroit Pistons",
            "commence_time": (datetime(2026, 10, 21, 12, tzinfo=timezone.utc) + timedelta(minutes=minutes)).isoformat()}, bms


def test_nba_ingestion_frozen_method(reg):
    now = datetime(2026, 10, 21, 12, tzinfo=timezone.utc)
    ev, bms = nba_event()
    preds, _ = A.nba_from_odds([{**ev, "bookmakers": bms}], reg, CTX, now, "t")
    assert len(preds) == 1 and preds[0].selection == "Boston Celtics"
    assert preds[0].estimated_probability == pytest.approx((1 / 1.25) / (1 / 1.25 + 1 / 4.0))   # exchange ignored
    ev2, bms2 = nba_event(n_books=2)
    assert A.nba_from_odds([{**ev2, "bookmakers": bms2}], reg, CTX, now, "t")[0] == []
    ev3, bms3 = nba_event(minutes=40 * 60)
    assert A.nba_from_odds([{**ev3, "bookmakers": bms3}], reg, CTX, now, "t")[0] == []
    assert A.nba_from_odds([{**ev, "bookmakers": bms}], reg, CTX, datetime(2026, 10, 1, tzinfo=timezone.utc), "t")[0] == []


# ---------------- ledger append / duplicates / immutability
def test_ledger_append_duplicates_and_immutability(reg, tmp_path):
    preds, _ = A.football_from_card(card(), reg, CTX, NOW, "t")
    path = tmp_path / "l.csv"
    assert append_unique(path, [to_row(p) for p in preds], PREDICTION_FIELDS) == (len(preds), 0)
    before = path.read_bytes()
    later = [replace(p, estimated_probability=0.99, fair_odds=1 / 0.99, probability_band=band_of(0.99)) for p in preds]
    assert append_unique(path, [to_row(p) for p in later], PREDICTION_FIELDS) == (0, len(preds))   # retry/later scan: no change
    assert path.read_bytes() == before
    with pytest.raises(LedgerIntegrityError):
        append_unique(path, [to_row(preds[0])], PREDICTION_FIELDS[:-1])


# ---------------- settlement
class R:
    def __init__(self, hg, ag):
        self.home_goals, self.away_goals = hg, ag


def test_football_outcomes():
    assert S.football_outcome("double_chance", "1X", 1, 1) == 1 and S.football_outcome("double_chance", "12", 1, 1) == 0
    assert S.football_outcome("double_chance", "X2", 2, 0) == 0
    assert S.football_outcome("1x2", "away", 0, 2) == 1 and S.football_outcome("over_under_2_5", "under", 1, 1) == 1
    with pytest.raises(ValueError):
        S.football_outcome("btts", "yes", 1, 1)


def test_settle_football_end_to_end(reg):
    from prediction_markets_lab.settlement import football_data_results as fd
    aliases = fd.load_settlement_aliases()
    csv_text = "Div,Date,HomeTeam,AwayTeam,FTHG,FTAG,FTR\nE0,26/09/2026,Arsenal,Leeds,1,1,D\n"
    results = fd.parse_fd_csv(csv_text, "E0", aliases)
    preds = [{k: str(v) for k, v in to_row(p).items()} for p in A.football_from_card(card(), reg, CTX, NOW, "t")[0]]
    new, review = S.settle_football(preds, set(), results, aliases, datetime(2026, 9, 27, tzinfo=timezone.utc))
    got = {(n["prediction_id"]): n["correct"] for n in new}
    sel = {p["prediction_id"]: (p["market"], p["selection"]) for p in preds}
    assert {sel[k]: v for k, v in got.items()} == {("1x2", "home"): 0, ("1x2", "draw"): 1, ("1x2", "away"): 0,
                                                   ("double_chance", "1X"): 1, ("double_chance", "X2"): 1,
                                                   ("double_chance", "12"): 0, ("over_under_2_5", "over"): 0}
    assert review == []
    early, _ = S.settle_football(preds, set(), results, aliases, datetime(2026, 9, 26, 15, tzinfo=timezone.utc))
    assert early == []                                                  # not before kickoff + 3h
    none, review = S.settle_football(preds, set(), [], aliases, datetime(2026, 9, 27, tzinfo=timezone.utc))
    assert none == [] and {r["status"] for r in review} == {"NOT_FOUND"}    # never guessed


def test_tennis_mirror_and_nba_scores():
    out = S.mirror_tennis({"a": {"status": "SETTLED_CORRECT", "winner": "X"}, "b": {"status": "PENDING"}}, {"a", "b"}, set())
    assert [o["correct"] for o in out] == [1]
    preds = [{"prediction_id": "p", "sport": "basketball", "event_id": "e", "selection": "Home"}]
    sc = [{"id": "e", "completed": True, "scores": [{"name": "Home", "score": "101"}, {"name": "Away", "score": "99"}]}]
    assert S.settle_from_odds_api_scores(preds, set(), sc, NOW)[0]["correct"] == 1


# ---------------- performance / maturity / board / health
def test_performance_pooled_and_decomposed(reg):
    preds = [{k: str(v) for k, v in to_row(p).items()} for p in A.football_from_card(card(), reg, CTX, NOW, "t")[0]]
    sets = {p["prediction_id"]: {"settlement_status": "SETTLED", "correct": "1"} for p in preds}
    rep = P.report(preds, sets)
    assert rep["pooled"]["n"] == len(preds)
    assert set(rep["ge80_decomposition"]["by_engine"]) == {A.FOOTBALL_DC}
    assert rep["engines"][A.FOOTBALL_DC]["settled_events"] == 1           # 3 DC rows = 1 match
    assert P.maturity(49, 0) == "COLLECTING" and P.maturity(300, 100) == "INTERMEDIATE" and P.maturity(1000, 300) == "MATURE"


def test_health_stale_and_board(tmp_path, reg):
    (tmp_path / "status").mkdir()
    old = (NOW - timedelta(hours=40)).isoformat()
    (tmp_path / "status/latest.json").write_text(json.dumps({"last_scan": {"at": old, "status": "success"},
                                                              "last_settlement": {"at": NOW.isoformat(), "status": "success"}}))
    h = H.evaluate(tmp_path, NOW, {"last_ci_pass": NOW.isoformat()})
    assert h["overall"] == "DEGRADED" and h["components"]["daily_scan"]["flag"] == "STALE" and h["stale_data_warning"]
    preds = [{k: str(v) for k, v in to_row(p).items()} for p in A.football_from_card(card(), reg, CTX, NOW, "t")[0]]
    b = B.build(preds, {}, reg.engines, ["x"], h, P.report(preds, {}), {}, NOW)
    ps = [float(p["estimated_probability"]) for p in b["predictions"]]
    assert ps == sorted(ps, reverse=True) and b["summary"]["threshold_counts"][">=80"] == 2
    md = B.render_md(b)
    assert "SYSTEM DEGRADED" in md and "not a betting card" in md.lower()
    B.write(b, tmp_path / "r")
    with (tmp_path / "r/latest_prediction_board.csv").open() as f:
        assert len(list(csv.DictReader(f))) == len(preds)


def test_settlement_fields_are_separate():
    assert "correct" in SETTLEMENT_FIELDS and "correct" not in PREDICTION_FIELDS


def test_money_layer_separation():
    """The Prediction Board must not import staking / grading / money-qualification code."""
    import ast
    pkg = Path(__file__).resolve().parents[2] / "src/prediction_markets_lab/prediction_platform"
    banned = ("prediction_markets_lab.decisions", "prediction_markets_lab.risk", "prediction_markets_lab.ev")
    for f in pkg.glob("*.py"):
        for node in ast.walk(ast.parse(f.read_text())):
            if isinstance(node, ast.ImportFrom) and node.module:
                assert not node.module.startswith(banned), f"{f.name} imports {node.module}"
