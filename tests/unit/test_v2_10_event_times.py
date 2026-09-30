"""V2-10 fix A regression tests: current start-time semantics (est-1). No outcomes, no network."""
from __future__ import annotations

import copy
import csv
import importlib.util
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from prediction_markets_lab.prediction_platform import event_times as ET

NOW = datetime(2026, 9, 30, 12, 54, tzinfo=timezone.utc)
KEY = "tennis|tennis_atp_japan_open|evt1"
REPO = Path(__file__).resolve().parents[2]


def pred(start="2026-09-30T02:00:00+00:00", made="2026-09-29T08:31:00+00:00", pid="p1", valid="True"):
    return {"prediction_id": pid, "event_key": KEY, "event_name": "Carlos Alcaraz v Alex Michelsen", "event_start": start,
            "prediction_timestamp": made, "prediction_valid": valid}


def idx(*obs):
    i = ET.StartIndex()
    for at, start in obs:
        i.add(KEY, at, start, "tennis_predictions/exchange_probability_snapshots.csv")
    return i


def test_unchanged_start():
    r = ET.resolve(pred(start="2026-10-01T07:00:00+00:00"), idx(("2026-09-30T12:54:00+00:00", "2026-10-01T07:00:00+00:00")))
    assert r.status == ET.UNCHANGED and ET.parse_ts(r.current_start) == ET.parse_ts("2026-10-01T07:00:00+00:00")
    assert ET.exclusion_reason(r, NOW) is None


def test_reschedule_later_is_eligible_and_keeps_original():
    eligible, rows = ET.apply([pred()], idx(("2026-09-29T20:11:00+00:00", "2026-10-01T02:00:00+00:00"),
                                            ("2026-09-30T12:54:00+00:00", "2026-10-01T07:00:00+00:00")), NOW)
    assert len(eligible) == 1
    e = eligible[0]
    assert ET.parse_ts(e["event_start"]) == ET.parse_ts("2026-10-01T07:00:00+00:00")
    assert e["event_start_original"] == "2026-09-30T02:00:00+00:00"
    assert e["start_time_status"] == ET.RESCHEDULED
    assert rows[0]["eligibility"] == ET.ELIGIBLE and rows[0]["exclusion_reason"] == ""


def test_reschedule_earlier_uses_new_start():
    p = pred(start="2026-10-02T09:00:00+00:00")
    r = ET.resolve(p, idx(("2026-09-30T12:00:00+00:00", "2026-10-01T05:00:00+00:00")))
    assert r.status == ET.RESCHEDULED and ET.parse_ts(r.current_start) == ET.parse_ts("2026-10-01T05:00:00+00:00")
    # and an earlier reschedule that is already in the past is excluded as started (never kept as future)
    r2 = ET.resolve(p, idx(("2026-09-30T12:00:00+00:00", "2026-09-30T12:30:00+00:00")))
    assert ET.exclusion_reason(r2, NOW) == ET.EXCL_STARTED


def test_placeholder_replaced_by_confirmed_time():
    # first-seen placeholder 02:00, then the provider confirms 03:10 the next day (V2-9: Nishikori v Tiafoe)
    eligible, rows = ET.apply([pred()], idx(("2026-09-30T12:54:00+00:00", "2026-10-01T03:10:00+00:00")), NOW)
    assert eligible and ET.parse_ts(eligible[0]["event_start"]) == ET.parse_ts("2026-10-01T03:10:00+00:00")


def test_already_started_event_excluded_with_reason():
    eligible, rows = ET.apply([pred(start="2026-09-30T10:00:00+00:00", made="2026-09-30T06:00:00+00:00")],
                              idx(("2026-09-30T08:00:00+00:00", "2026-09-30T10:00:00+00:00")), NOW)
    assert eligible == []
    assert rows[0]["eligibility"] == ET.EXCLUDED and rows[0]["exclusion_reason"] == ET.EXCL_STARTED


def test_conflicting_update_fails_closed():
    i = idx(("2026-09-30T12:54:00+00:00", "2026-10-01T07:00:00+00:00"), ("2026-09-30T12:54:00+00:00", "2026-10-01T09:00:00+00:00"))
    eligible, rows = ET.apply([pred()], i, NOW)
    assert eligible == [] and rows[0]["exclusion_reason"] == ET.EXCL_CONFLICT
    assert rows[0]["start_time_status"] == ET.CONFLICT


def test_invalid_update_ignored_and_counted():
    i = idx(("2026-09-30T12:54:00+00:00", "not-a-time"), ("", "2026-10-01T07:00:00+00:00"),
            ("2026-09-30T11:00:00+00:00", "2026-10-01T06:00:00+00:00"))
    r = ET.resolve(pred(), i)
    assert r.n_invalid == 2
    assert ET.parse_ts(r.current_start) == ET.parse_ts("2026-10-01T06:00:00+00:00")


def test_invalid_ledger_start_without_observations_is_excluded_with_reason():
    eligible, rows = ET.apply([pred(start="garbage")], ET.StartIndex(), NOW)
    assert eligible == [] and rows[0]["exclusion_reason"] == ET.EXCL_INVALID


def test_ledger_only_behaves_exactly_like_before():
    """No provider observation -> identical to the old `event_start > now` filter."""
    fut, past = pred(start="2026-10-01T02:00:00+00:00", pid="a"), pred(start="2026-09-30T02:00:00+00:00", pid="b")
    eligible, rows = ET.apply([fut, past], ET.StartIndex(), NOW)
    assert [e["prediction_id"] for e in eligible] == ["a"]
    assert {r["start_time_status"] for r in rows} == {ET.LEDGER_ONLY}


def test_append_only_history_preserved():
    preds = [pred()]
    before = copy.deepcopy(preds)
    ET.apply(preds, idx(("2026-09-30T12:54:00+00:00", "2026-10-01T07:00:00+00:00")), NOW)
    assert preds == before   # inputs never mutated; the overlay is a copy


def test_no_future_match_excluded_because_of_stale_ledger_start():
    """V2-9 defect: stale first-seen start in the past + later provider start in the future -> must stay eligible."""
    for later in ("2026-10-01T02:00:00+00:00", "2026-10-01T03:10:00+00:00", "2026-10-01T05:40:00+00:00"):
        eligible, _ = ET.apply([pred()], idx(("2026-09-30T12:54:00+00:00", later)), NOW)
        assert len(eligible) == 1, later


def test_ledger_observation_newer_than_scans_wins():
    # a ledger row recorded after the last snapshot carries the newest provider start
    r = ET.resolve(pred(start="2026-10-01T08:00:00+00:00", made="2026-09-30T12:00:00+00:00"),
                   idx(("2026-09-30T06:00:00+00:00", "2026-10-01T02:00:00+00:00")))
    assert ET.parse_ts(r.current_start) == ET.parse_ts("2026-10-01T08:00:00+00:00")


def test_load_index_reads_tennis_snapshot_files(tmp_path):
    d = tmp_path / "tennis_predictions"
    d.mkdir()
    with (d / "exchange_probability_snapshots.csv").open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["scan_timestamp_utc", "sport_key", "event_id", "commence_time"])
        w.writeheader()
        w.writerow({"scan_timestamp_utc": "2026-09-30T12:54:00+00:00", "sport_key": "tennis_atp_japan_open",
                    "event_id": "evt1", "commence_time": "2026-10-01T07:00:00+00:00"})
    i = ET.load_index(tmp_path)
    assert len(i.obs[KEY]) == 1


def test_unified_board_shows_rescheduled_match():
    from prediction_markets_lab.prediction_platform import board as B
    p = {**{k: "" for k in B.PREDICTION_FIELDS}, **pred(), "estimated_probability": "0.85", "fair_odds": "1.18",
         "sport": "tennis", "engine_status": "VALIDATED_HISTORICAL"}
    health = {"overall": "OK", "api_credits": {"remaining": None}, "components": {}, "warnings": []}
    old = B.build([p], {}, {}, [], health, {}, {}, NOW)
    new = B.build([p], {}, {}, [], health, {}, {}, NOW, idx(("2026-09-30T12:54:00+00:00", "2026-10-01T07:00:00+00:00")))
    assert old["predictions"] == []                      # ledger-only: the stale start still hides it (no provider info)
    assert len(new["predictions"]) == 1
    assert new["predictions"][0]["start_time_status"] == ET.RESCHEDULED
    assert new["start_time_resolution"]["eligible_rescheduled"] == 1


def _load_bs_script():
    spec = importlib.util.spec_from_file_location("run_bet_selection_v2_t", REPO / "scripts/run_bet_selection_v2.py")
    m = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = m
    spec.loader.exec_module(m)
    return m


def test_bet_selection_evaluate_includes_rescheduled_and_records_reasons(tmp_path, monkeypatch):
    m = _load_bs_script()
    (tmp_path / "predictions").mkdir()
    (tmp_path / "tennis_predictions").mkdir()
    from prediction_markets_lab.prediction_platform.schema import PREDICTION_FIELDS
    base = {k: "" for k in PREDICTION_FIELDS}
    rows = [{**base, **pred(), "sport": "tennis", "engine_id": "tennis_atp.exchange_mid", "engine_status": "VALIDATED_HISTORICAL",
             "market": "match_winner", "selection": "Carlos Alcaraz", "estimated_probability": "0.85", "event_id": "evt1"},
            {**base, **pred(pid="p2", start="2026-09-30T09:00:00+00:00", made="2026-09-30T06:00:00+00:00"),
             "event_key": "tennis|x|gone", "sport": "tennis", "engine_id": "tennis_atp.exchange_mid",
             "engine_status": "VALIDATED_HISTORICAL", "market": "match_winner", "selection": "Carlos Alcaraz",
             "estimated_probability": "0.85", "event_id": "gone"}]
    with (tmp_path / "predictions/unified_ledger.csv").open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=PREDICTION_FIELDS)
        w.writeheader()
        w.writerows(rows)
    with (tmp_path / "tennis_predictions/exchange_probability_snapshots.csv").open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["scan_timestamp_utc", "sport_key", "event_id", "commence_time"])
        w.writeheader()
        w.writerow({"scan_timestamp_utc": "2026-09-30T12:54:00+00:00", "sport_key": "tennis_atp_japan_open",
                    "event_id": "evt1", "commence_time": "2026-10-01T07:00:00+00:00"})
    monkeypatch.setattr(m, "REPO", tmp_path)
    monkeypatch.setattr(m, "OUT", tmp_path / "paper_betting_v2")
    monkeypatch.setattr(m, "REPORTS", tmp_path / "reports")
    for n in ("SELECTIONS", "SNAPSHOTS", "SETTLEMENTS", "RUNS"):
        monkeypatch.setattr(m, n, tmp_path / "paper_betting_v2" / Path(getattr(m, n)).name)
    out = m.evaluate(m.load_config(), NOW)
    assert [c["prediction_id"] for c in out["decided"]] == ["p1"]
    assert out["decided"][0]["decision"] != m.PAPER_BET      # no price -> never a bet
    res = list(csv.DictReader((tmp_path / "reports/bet_selection_v2_start_time_resolution.csv").open()))
    by = {r["prediction_id"]: r for r in res}
    assert by["p1"]["eligibility"] == ET.ELIGIBLE and by["p1"]["start_time_status"] == ET.RESCHEDULED
    assert by["p2"]["eligibility"] == ET.EXCLUDED and by["p2"]["exclusion_reason"] == ET.EXCL_STARTED
    # the (tmp) ledger is untouched
    assert list(csv.DictReader((tmp_path / "predictions/unified_ledger.csv").open()))[0]["event_start"] == "2026-09-30T02:00:00+00:00"


@pytest.mark.parametrize("path", ["predictions/unified_ledger.csv", "tennis_predictions/ledger_predictions.csv"])
def test_production_code_never_writes_ledgers_during_resolution(path, tmp_path):
    """Resolution is read-only: loading the index over the real repo leaves ledgers byte-identical."""
    p = REPO / path
    before = p.read_bytes() if p.exists() else None
    i = ET.load_index(REPO)
    ET.apply(list(csv.DictReader(p.open())) if p.exists() and "unified" in path else [], i, NOW)
    assert (p.read_bytes() if p.exists() else None) == before
