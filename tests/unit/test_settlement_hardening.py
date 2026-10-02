"""Settlement hardening (2026-10-02): completeness monitor, football-data fallback for legacy rows, alias derivation."""
from __future__ import annotations

import csv
import importlib.util
from datetime import datetime, timedelta, timezone
from pathlib import Path

from prediction_markets_lab.settlement import alias_derivation as AD
from prediction_markets_lab.settlement import completeness as C
from prediction_markets_lab.settlement import football_data_results as fd
from prediction_markets_lab.settlement.settle_paper_ledger import fallback_reason, settle_with_football_data_fallback
from prediction_markets_lab.storage.paper_ledger import load_paper_bets

REPO = Path(__file__).resolve().parents[2]
NOW = datetime(2026, 10, 2, 22, 0, tzinfo=timezone.utc)
LAG = {"football_data_co_uk": 120, "tennis_court_log": 240, "odds_api_scores": 96}


# ------------------------------------------------------------------ completeness
def rec(start, settled=False, source="tennis_court_log"):
    return C.Record("l", "id", "tennis", "X", "e", start, settled, source)


def test_completeness_statuses():
    assert C.classify(rec(NOW + timedelta(hours=1)), NOW, LAG) == "NOT_STARTED"
    assert C.classify(rec(NOW - timedelta(days=30), settled=True), NOW, LAG) == "SETTLED"
    assert C.classify(rec(NOW - timedelta(hours=200)), NOW, LAG) == "NORMAL_SOURCE_LAG"
    assert C.classify(rec(NOW - timedelta(hours=241)), NOW, LAG) == "UNRESOLVED_AFTER_EXPECTED_LAG"
    assert C.classify(rec(NOW - timedelta(hours=1), source=None), NOW, LAG) == "SOURCE_UNAVAILABLE"
    s = C.summarise([rec(NOW - timedelta(hours=241)), rec(NOW - timedelta(hours=1), settled=True)], NOW, LAG)
    assert s["totals"]["UNRESOLVED_AFTER_EXPECTED_LAG"] == 1 and not s["healthy"] and len(s["flagged"]) == 1


def test_completeness_config_has_every_source():
    cfg = C.load_config()
    assert set(cfg["sources"].values()) | {cfg["legacy_paper_ledger_source"]} <= set(cfg["expected_lag_hours"])


# ------------------------------------------------------------------ legacy football-data fallback
HEADER = (REPO / "paper_ledger/paper_bets.csv").read_text().splitlines()[0].split(",")


def ledger(tmp_path, rows):
    p = tmp_path / "paper_bets.csv"
    with open(p, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=HEADER)
        w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k, "") for k in HEADER})
    return p


def bet(bet_id, event_id, event, kickoff, market="1x2", selection="away", comp="Premier League"):
    return {"bet_id": bet_id, "event_id": event_id, "event": event, "kickoff": kickoff, "sport": "football", "competition": comp,
            "market": market, "selection": selection, "quoted_odds": "5.0", "recommended_stake": "1.0", "status": "pending"}


def fdres(h, a, hg, ag, d="2026-09-20", comp="E0"):
    return fd.FDResult(comp, datetime.fromisoformat(d).date(), h, a, h, a, hg, ag, "")


def test_fallback_settles_only_unsettleable_rows_and_audits(tmp_path):
    p = ledger(tmp_path, [
        bet("A", "Leeds United v Crystal Palace::1x2::away", "Leeds United v Crystal Palace", "2026-09-20"),          # no provider id
        bet("B", "Leeds United v Crystal Palace::ou::under", "Leeds United v Crystal Palace", "2026-09-20", "over_under_2_5", "under"),
        bet("C", "soccer_epl-abc-1x2", "Arsenal v Chelsea", (NOW - timedelta(days=1)).date().isoformat()),          # scores API can still settle
        bet("D", "soccer_epl-def-1x2", "Fulham v Everton", "2026-09-21"),                                            # outside scores window
        bet("E", "x::y", "Unknown FC v Arsenal", "2026-09-20"),                                                      # unresolved name
        bet("F", "x::z", "Arsenal v Chelsea", "2026-10-30"),                                                         # not started
    ])
    aliases = {n: n for n in ("Leeds United", "Crystal Palace", "Arsenal", "Chelsea", "Fulham", "Everton")}
    results = [fdres("Leeds United", "Crystal Palace", 0, 0), fdres("Fulham", "Everton", 2, 1, "2026-09-21")]
    assert [fallback_reason(r, NOW) for r in load_paper_bets(p)] == ["NO_PROVIDER_ID", "NO_PROVIDER_ID", None, "OUTSIDE_SCORES_WINDOW", "NO_PROVIDER_ID", None]
    audit = tmp_path / "audit.csv"
    res = settle_with_football_data_fallback(p, 100.0, results, aliases, {"Premier League": "E0"}, NOW, audit)
    assert sorted(res.settled) == ["A", "B", "D"] and res.left_pending == [("E", "UNRESOLVED_NAME")]
    rows = {r["bet_id"]: r for r in load_paper_bets(p)}
    assert (rows["A"]["result"], rows["B"]["result"], rows["D"]["result"]) == ("lost", "won", "lost")
    assert rows["C"]["status"] == rows["E"]["status"] == rows["F"]["status"] == "pending"
    assert rows["B"]["actual_pnl"] == "4.00"
    a = list(csv.DictReader(open(audit)))
    assert [x["bet_id"] for x in a] == ["A", "B", "D"] and {x["settlement_source"] for x in a} == {"football_data_co_uk"}
    again = settle_with_football_data_fallback(p, 100.0, results, aliases, {"Premier League": "E0"}, NOW, audit)
    assert again.settled == []                                  # idempotent: settled rows are never touched again


# ------------------------------------------------------------------ shadow coverage
def test_shadow_covers_every_observed_league_including_f1():
    spec = importlib.util.spec_from_file_location("shadow", REPO / "scripts/run_football_settlement_shadow.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    assert m.SPORT_TO_FD["soccer_france_ligue_one"] == "F1" and {"E0", "E1", "SC0", "N1", "D1"} <= set(m.SPORT_TO_FD.values())


# ------------------------------------------------------------------ alias derivation
T = datetime(2026, 10, 17, 13, 30, tzinfo=timezone.utc)


def fx(h, a, t=T, c="D1"):
    return AD.Fixture(c, t, h, a)


def test_unique_slots_map_by_fixture_identity():
    fdl = [fx("Ein Frankfurt", "M'gladbach"), fx("Hamburg", "Mainz", T + timedelta(hours=3))]
    odd = [fx("Eintracht Frankfurt", "Borussia Monchengladbach"), fx("Hamburger SV", "FSV Mainz 05", T + timedelta(hours=3))]
    d = AD.derive(fdl, odd)
    assert d.aliases == {"Ein Frankfurt": "Eintracht Frankfurt", "M'gladbach": "Borussia Monchengladbach", "Hamburg": "Hamburger SV", "Mainz": "FSV Mainz 05"}
    assert set(d.method.values()) == {"FIXTURE_IDENTITY"} and not d.unresolved and not d.rejected


def test_shared_slot_uses_name_tokens_then_elimination_and_never_guesses():
    fdl = [fx("Ein Frankfurt", "Mainz"), fx("Hamburg", "M'gladbach")]
    odd = [fx("Hamburger SV", "Borussia Monchengladbach"), fx("Eintracht Frankfurt", "FSV Mainz 05")]
    d = AD.derive(fdl, odd)
    assert d.aliases["Ein Frankfurt"] == "Eintracht Frankfurt" and d.method["Ein Frankfurt"] == "FIXTURE_IDENTITY+NAME_TOKEN"
    assert d.aliases["Hamburg"] == "Hamburger SV" and d.aliases["M'gladbach"] == "Borussia Monchengladbach"
    # no token evidence anywhere in a shared slot -> stays unresolved
    d2 = AD.derive([fx("Aaa", "Bbb"), fx("Ccc", "Ddd")], [fx("Xxx", "Yyy"), fx("Zzz", "Www")])
    assert d2.aliases == {} and set(d2.unresolved) == {"Aaa", "Bbb", "Ccc", "Ddd"}


def test_known_aliases_and_cross_round_intersection():
    r1 = [fx("Aaa", "Bbb"), fx("Ccc", "Ddd")]
    o1 = [fx("Xxx", "Yyy"), fx("Zzz", "Www")]
    t2 = T + timedelta(days=7)
    r2 = [fx("Aaa", "Ddd", t2), fx("Ccc", "Bbb", t2 + timedelta(hours=2))]
    o2 = [fx("Xxx", "Www", t2), fx("Zzz", "Yyy", t2 + timedelta(hours=2))]
    d = AD.derive(r1 + r2, o1 + o2)
    assert d.aliases == {"Aaa": "Xxx", "Bbb": "Yyy", "Ccc": "Zzz", "Ddd": "Www"}
    d3 = AD.derive(r1, o1, known={"Aaa": "Xxx"})
    assert d3.aliases == {"Bbb": "Yyy", "Ccc": "Zzz", "Ddd": "Www"}


def test_missing_slot_and_contradiction_fail_closed():
    d = AD.derive([fx("Aaa", "Bbb", T + timedelta(hours=5))], [fx("Xxx", "Yyy")])
    assert d.aliases == {} and len(d.fixtures_without_slot) == 1
    bad = AD.derive([fx("Aaa", "Bbb"), fx("Aaa", "Ccc", T + timedelta(days=7))], [fx("Xxx", "Yyy"), fx("Zzz", "Www", T + timedelta(days=7))])
    assert bad.rejected and bad.aliases == {}
