from datetime import date

import pytest

from prediction_markets_lab.settlement import football_data_results as fd
from prediction_markets_lab.settlement.market_settlement import determine_1x2_result

CSV = """﻿Div,Date,Time,HomeTeam,AwayTeam,FTHG,FTAG,FTR
E0,20/09/2026,15:00,Man City,Sunderland,3,0,H
E0,20/09/2026,15:00,Leeds,Crystal Palace,1,1,D
E0,21/09/2026,16:30,Nott'm Forest,Arsenal,0,2,A
E0,27/09/2026,15:00,Arsenal,Leeds,,,
E1,20/09/2026,12:30,Norwich,Bolton,2,1,H
"""


@pytest.fixture(scope="module")
def aliases():
    return fd.load_settlement_aliases()


def test_season_code_and_url():
    assert fd.season_code(date(2026, 9, 24)) == "2627"
    assert fd.season_code(date(2027, 5, 1)) == "2627"
    assert fd.fd_url("E0", date(2026, 9, 24)).endswith("/mmz4281/2627/E0.csv")


def test_parse_skips_unplayed_and_maps_aliases(aliases):
    rows = fd.parse_fd_csv(CSV, "E0", aliases)
    assert len(rows) == 4  # the unplayed Arsenal v Leeds row is skipped
    assert rows[0].home == "Manchester City" and rows[2].home == "Nottingham Forest"
    assert all(fd.fd_consistent(r) for r in rows)


def test_matched_with_odds_api_names_and_winner_draw(aliases):
    rows = fd.parse_fd_csv(CSV, "E0", aliases)
    m = fd.match_fixture("E0", "Manchester City", "Sunderland", date(2026, 9, 20), rows, aliases)
    assert m.status == "MATCHED" and determine_1x2_result(m.result.home_goals, m.result.away_goals) == "home"
    d = fd.match_fixture("E0", "Leeds United", "Crystal Palace", date(2026, 9, 20), rows, aliases)
    assert d.status == "MATCHED" and determine_1x2_result(d.result.home_goals, d.result.away_goals) == "draw"


def test_small_reschedule_within_window(aliases):
    rows = fd.parse_fd_csv(CSV, "E0", aliases)
    assert fd.match_fixture("E0", "Nottingham Forest", "Arsenal", date(2026, 9, 20), rows, aliases).status == "MATCHED"


def test_postponed_or_future_is_not_found(aliases):
    rows = fd.parse_fd_csv(CSV, "E0", aliases)
    assert fd.match_fixture("E0", "Arsenal", "Leeds United", date(2026, 9, 27), rows, aliases).status == "NOT_FOUND"
    assert fd.match_fixture("E0", "Manchester City", "Sunderland", date(2026, 10, 20), rows, aliases).status == "NOT_FOUND"


def test_reversed_fixture_is_not_matched(aliases):
    rows = fd.parse_fd_csv(CSV, "E0", aliases)
    assert fd.match_fixture("E0", "Sunderland", "Manchester City", date(2026, 9, 20), rows, aliases).status == "NOT_FOUND"


def test_unresolved_name_never_guessed(aliases):
    rows = fd.parse_fd_csv(CSV, "E1", aliases)
    m = fd.match_fixture("E1", "Norwich City", "Bolton Wanderers", date(2026, 9, 20), rows, aliases)
    assert m.status == "UNRESOLVED_NAME" and "Bolton" in m.detail


def test_duplicate_results_are_ambiguous(aliases):
    rows = fd.parse_fd_csv(CSV + "E0,22/09/2026,20:00,Man City,Sunderland,1,0,H\n", "E0", aliases)
    assert fd.match_fixture("E0", "Manchester City", "Sunderland", date(2026, 9, 21), rows, aliases).status == "AMBIGUOUS"


def test_wrong_competition_not_matched(aliases):
    rows = fd.parse_fd_csv(CSV, "E0", aliases)
    assert fd.match_fixture("E1", "Manchester City", "Sunderland", date(2026, 9, 20), rows, aliases).status == "NOT_FOUND"


def test_inconsistent_ftr_detected(aliases):
    rows = fd.parse_fd_csv("Div,Date,HomeTeam,AwayTeam,FTHG,FTAG,FTR\nE0,20/09/2026,Arsenal,Chelsea,2,0,A\n", "E0", aliases)
    assert not fd.fd_consistent(rows[0])


def test_bad_dates_skipped(aliases):
    assert fd.parse_fd_csv("Div,Date,HomeTeam,AwayTeam,FTHG,FTAG,FTR\nE0,nonsense,Arsenal,Chelsea,2,0,H\n", "E0", aliases) == []


def test_overlay_extends_frozen_table_and_rejects_conflicts(tmp_path):
    t = fd.load_settlement_aliases()
    assert t["Charlton"] == "Charlton Athletic" and t["Dundee FC"] == "Dundee"
    bad = tmp_path / "o.yaml"
    bad.write_text("Charlton Athletic: [Dundee]\n")
    with pytest.raises(ValueError):
        fd.load_settlement_aliases(bad)
