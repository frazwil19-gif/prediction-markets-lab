import csv
from pathlib import Path

import pytest

from prediction_markets_lab.backtesting import historical_loader as hl


@pytest.fixture()
def fake_repo(tmp_path, monkeypatch):
    """A tiny synthetic repo layout mirroring the real one, so the loader's
    join/parsing logic can be tested without depending on the real
    multi-thousand-row dataset."""
    processed_dir = tmp_path / "data" / "processed" / "football"
    processed_dir.mkdir(parents=True)
    raw_dir = tmp_path / "data" / "raw" / "football" / "football_data_co_uk" / "E0" / "2020_21"
    raw_dir.mkdir(parents=True)

    matches_csv = processed_dir / "cycle_001_matches_full.csv"
    with open(matches_csv, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(
            [
                "match_id", "source_id", "competition_code", "competition_name", "season",
                "match_date", "home_team_raw", "away_team_raw", "home_team_normalised",
                "away_team_normalised", "full_time_result", "bookmaker_count_opening",
                "bookmaker_count_closing", "eligible_outcome_model", "eligible_consensus_model",
                "normalisation_status", "processed_at", "data_version",
            ]
        )
        writer.writerow(
            [
                "m1", "E0_2020_21", "E0", "Premier League", "2020_21", "2020-09-12",
                "Fulham", "Arsenal", "Fulham", "Arsenal", "A", "4", "4", "True", "True",
                "resolved", "2026-01-01T00:00:00+00:00", "test_v1",
            ]
        )
        # This one is ineligible and must be excluded.
        writer.writerow(
            [
                "m2", "E0_2020_21", "E0", "Premier League", "2020_21", "2020-09-13",
                "Leeds", "Liverpool", "Leeds", "Liverpool", "H", "1", "1", "True", "False",
                "resolved", "2026-01-01T00:00:00+00:00", "test_v1",
            ]
        )
        # This one has no bookmaker panel at all and must be excluded.
        writer.writerow(
            [
                "m3", "E0_2020_21", "E0", "Premier League", "2020_21", "2020-09-14",
                "Chelsea", "Everton", "Chelsea", "Everton", "D", "0", "0", "True", "True",
                "resolved", "2026-01-01T00:00:00+00:00", "test_v1",
            ]
        )
        # This one will fail the raw kickoff join (no matching raw row).
        writer.writerow(
            [
                "m4", "E0_2020_21", "E0", "Premier League", "2020_21", "2020-09-15",
                "NoSuchHome", "NoSuchAway", "NoSuchHome", "NoSuchAway", "H", "4", "4", "True", "True",
                "resolved", "2026-01-01T00:00:00+00:00", "test_v1",
            ]
        )

    bookmakers_csv = processed_dir / "cycle_001_bookmaker_markets_full.csv"
    with open(bookmakers_csv, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(
            ["match_id", "bookmaker", "price_timing", "home_odds", "draw_odds", "away_odds",
             "fair_home_probability", "fair_draw_probability", "fair_away_probability",
             "processed_at", "data_version"]
        )
        writer.writerow(["m1", "B365", "closing", "5.0", "4.0", "1.66", "", "", "", "t", "v"])
        writer.writerow(["m1", "PS", "closing", "5.48", "3.98", "1.69", "", "", "", "t", "v"])
        writer.writerow(["m1", "B365", "opening", "6.0", "4.33", "1.53", "", "", "", "t", "v"])
        writer.writerow(["m4", "B365", "closing", "2.0", "3.2", "3.5", "", "", "", "t", "v"])

    raw_csv = raw_dir / "E0.csv"
    with open(raw_csv, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["Div", "Date", "Time", "HomeTeam", "AwayTeam", "FTHG", "FTAG"])
        writer.writerow(["E0", "12/09/2020", "12:30", "Fulham", "Arsenal", "0", "3"])
        # m4's teams are deliberately absent from the raw file.

    monkeypatch.setattr(hl, "CYCLE_001_MATCHES", matches_csv)
    monkeypatch.setattr(hl, "CYCLE_001_BOOKMAKER_MARKETS", bookmakers_csv)
    monkeypatch.setattr(hl, "RAW_DATA_ROOT", tmp_path / "data" / "raw" / "football" / "football_data_co_uk")
    return tmp_path


def test_ineligible_and_missing_panel_matches_are_excluded_not_silently_dropped(fake_repo):
    matches, report = hl.load_matches_for_replay("closing")
    match_ids = {m.match_id for m in matches}
    assert "m2" not in match_ids  # ineligible_consensus_model
    assert "m3" not in match_ids  # no bookmaker panel
    assert report.excluded_ineligible_consensus_model == 1
    assert report.excluded_missing_complete_bookmaker_panel == 1
    assert report.total_rows_in_matches_file == 4


def test_kickoff_recovered_correctly_for_a_real_join(fake_repo):
    matches, _ = hl.load_matches_for_replay("closing")
    m1 = next(m for m in matches if m.match_id == "m1")
    # 12:30 BST (12 Sep 2020 is within British Summer Time) -> 11:30 UTC.
    assert m1.kickoff_iso == "2020-09-12T11:30:00+00:00"
    assert m1.kickoff_join_failure_reason is None


def test_kickoff_join_failure_is_recorded_not_fabricated(fake_repo):
    matches, report = hl.load_matches_for_replay("closing")
    m4 = next(m for m in matches if m.match_id == "m4")
    assert m4.kickoff_iso is None
    assert m4.kickoff_join_failure_reason is not None
    assert report.excluded_kickoff_join_failed == 1


def test_price_timing_never_mixed(fake_repo):
    """A single load call must use exactly one price_timing for every
    bookmaker odds value -- m1 has both opening and closing rows for B365,
    and the closing call must never surface the opening odds."""
    matches, _ = hl.load_matches_for_replay("closing")
    m1 = next(m for m in matches if m.match_id == "m1")
    assert m1.bookmaker_odds["B365"]["home"] == 5.0  # closing value
    assert m1.bookmaker_odds["B365"]["home"] != 6.0  # opening value must not appear

    matches_opening, _ = hl.load_matches_for_replay("opening")
    m1_opening = next(m for m in matches_opening if m.match_id == "m1")
    assert m1_opening.bookmaker_odds["B365"]["home"] == 6.0
    # PS never quoted an opening price in the fixture -- must not appear.
    assert "PS" not in m1_opening.bookmaker_odds


def test_invalid_price_timing_rejected(fake_repo):
    with pytest.raises(ValueError):
        hl.load_matches_for_replay("closing_and_opening_mixed")


def test_simulated_scan_timestamp_is_before_kickoff_by_fixed_offset(fake_repo):
    matches, _ = hl.load_matches_for_replay("closing")
    m1 = next(m for m in matches if m.match_id == "m1")
    scan_ts = hl.simulated_scan_timestamp_iso(m1)
    from datetime import datetime

    kickoff_dt = datetime.fromisoformat(m1.kickoff_iso)
    scan_dt = datetime.fromisoformat(scan_ts)
    assert kickoff_dt > scan_dt
    assert (kickoff_dt - scan_dt) == hl.SIMULATED_SCAN_OFFSET_BEFORE_KICKOFF


def test_simulated_scan_timestamp_is_none_when_kickoff_unknown(fake_repo):
    matches, _ = hl.load_matches_for_replay("closing")
    m4 = next(m for m in matches if m.match_id == "m4")
    assert hl.simulated_scan_timestamp_iso(m4) is None


def test_actual_result_letter_matches():
    assert hl.actual_result_letter_matches("home", "H") is True
    assert hl.actual_result_letter_matches("home", "A") is False
    assert hl.actual_result_letter_matches("draw", "D") is True
    assert hl.actual_result_letter_matches("away", "A") is True


def test_real_cycle_001_data_join_succeeds_for_almost_every_eligible_match():
    """Integration-style sanity check against the actual repository data
    (not synthetic) -- guards against the join silently regressing to a
    near-0% success rate without anyone noticing. Threshold is generous
    (95%) rather than exact, since this reads real, occasionally messy
    source data rather than a controlled fixture."""
    matches, report = hl.load_matches_for_replay("closing")
    assert report.included > 5000
    failure_rate = report.excluded_kickoff_join_failed / report.total_rows_in_matches_file
    assert failure_rate < 0.05
