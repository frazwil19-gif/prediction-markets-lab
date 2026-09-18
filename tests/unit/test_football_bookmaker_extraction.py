"""Tests for football_bookmaker_extraction, including real rows drawn
from the Stage 3A feasibility fetches (see
data/raw/football/football_data_co_uk/*/2024_25/*_excerpt.csv)."""

import csv
from pathlib import Path

from prediction_markets_lab.ingestion.football_bookmaker_extraction import (
    BOOKMAKER_PREFIXES_2025_26,
    KNOWN_BOOKMAKER_PREFIXES,
    bookmaker_count_by_timing,
    extract_bookmaker_triplets,
)

REPO_ROOT = Path(__file__).resolve().parent.parent.parent


def load_real_row(relative_csv_path: str, row_index: int) -> dict[str, str]:
    path = REPO_ROOT / relative_csv_path
    with open(path, newline="") as f:
        rows = list(csv.DictReader(f))
    return rows[row_index]


def test_complete_synthetic_row_extracts_all_bookmakers():
    row = {
        "B365H": "1.6", "B365D": "4.2", "B365A": "5.25",
        "B365CH": "1.66", "B365CD": "4.5", "B365CA": "5.6",
        "BWH": "1.6", "BWD": "4.4", "BWA": "5.25",
    }
    result = extract_bookmaker_triplets(row, bookmaker_prefixes=("B365", "BW"))
    counts = bookmaker_count_by_timing(result)
    assert counts["opening"] == 2  # B365, BW
    assert counts["closing"] == 1  # B365 only (BW closing not in row)
    assert result.rejected_bookmakers == []


def test_incomplete_triplet_rejected_not_silently_dropped_as_valid():
    row = {"B365H": "1.6", "B365D": "4.2", "B365A": ""}  # away missing
    result = extract_bookmaker_triplets(row, bookmaker_prefixes=("B365",))
    assert result.complete_triplets == []
    assert "B365 (opening)" in result.rejected_bookmakers


def test_fully_blank_bookmaker_is_skipped_not_rejected():
    """A bookmaker that simply didn't quote at all (all three blank)
    is absent, not an error -- must not appear in either list."""
    row = {"B365H": "", "B365D": "", "B365A": ""}
    result = extract_bookmaker_triplets(row, bookmaker_prefixes=("B365",))
    assert result.complete_triplets == []
    assert result.rejected_bookmakers == []


def test_zero_or_negative_odds_rejected():
    row = {"B365H": "0", "B365D": "4.2", "B365A": "5.25"}
    result = extract_bookmaker_triplets(row, bookmaker_prefixes=("B365",))
    assert result.complete_triplets == []
    assert "B365 (opening)" in result.rejected_bookmakers


def test_non_numeric_odds_rejected():
    row = {"B365H": "N/A", "B365D": "4.2", "B365A": "5.25"}
    result = extract_bookmaker_triplets(row, bookmaker_prefixes=("B365",))
    assert result.complete_triplets == []
    assert "B365 (opening)" in result.rejected_bookmakers


def test_does_not_mix_bookmakers_home_with_another_bookmakers_draw():
    """Each triplet's home/draw/away must come from the SAME bookmaker prefix."""
    row = {
        "B365H": "1.5", "B365D": "4.0", "B365A": "6.0",
        "BWH": "1.6", "BWD": "4.2", "BWA": "5.5",
    }
    result = extract_bookmaker_triplets(row, bookmaker_prefixes=("B365", "BW"))
    b365 = next(t for t in result.complete_triplets if t.bookmaker == "B365")
    bw = next(t for t in result.complete_triplets if t.bookmaker == "BW")
    assert (b365.home_odds, b365.draw_odds, b365.away_odds) == (1.5, 4.0, 6.0)
    assert (bw.home_odds, bw.draw_odds, bw.away_odds) == (1.6, 4.2, 5.5)


def test_average_and_max_columns_never_counted_as_bookmakers():
    row = {
        "B365H": "1.6", "B365D": "4.2", "B365A": "5.25",
        "MaxH": "1.68", "MaxD": "4.5", "MaxA": "5.6",
        "AvgH": "1.62", "AvgD": "4.36", "AvgA": "5.15",
    }
    # Default KNOWN_BOOKMAKER_PREFIXES excludes Max/Avg entirely.
    result = extract_bookmaker_triplets(row)
    bookmakers_seen = {t.bookmaker for t in result.complete_triplets}
    assert "Max" not in bookmakers_seen
    assert "Avg" not in bookmakers_seen
    assert "B365" in bookmakers_seen


def test_real_e0_row_extracts_six_bookmakers_opening_and_closing():
    row = load_real_row(
        "data/raw/football/football_data_co_uk/E0/2024_25/E0_excerpt.csv", 0
    )  # Man United vs Fulham, 16/08/2024
    result = extract_bookmaker_triplets(row)
    counts = bookmaker_count_by_timing(result)
    # All 6 known bookmakers (B365, BW, BF, PS, WH, 1XB) quote both
    # opening and closing for this real, complete-season match.
    assert counts["opening"] == 6
    assert counts["closing"] == 6
    assert result.rejected_bookmakers == []


def test_real_e1_row_matches_same_schema_as_e0():
    row = load_real_row(
        "data/raw/football/football_data_co_uk/E1/2024_25/E1_excerpt.csv", 0
    )  # Blackburn vs Derby, 09/08/2024
    result = extract_bookmaker_triplets(row)
    counts = bookmaker_count_by_timing(result)
    assert counts["opening"] == 6
    assert counts["closing"] == 6


def test_real_sc0_row_with_a_genuinely_missing_bookmaker():
    """St Mirren vs Hibernian (04/08/2024) has a blank WH closing
    triplet in the real SC0 data -- proving blanks are handled
    correctly on genuine historical data, not just synthetic tests."""
    row = load_real_row(
        "data/raw/football/football_data_co_uk/SC0/2024_25/SC0_excerpt.csv", 3
    )
    result = extract_bookmaker_triplets(row)
    counts = bookmaker_count_by_timing(result)
    # Opening should still have all bookmakers; closing has one missing.
    assert counts["opening"] == 6
    assert counts["closing"] <= 6
    assert result.rejected_bookmakers == []  # missing, not invalid -- correctly skipped


def test_real_2025_26_row_has_a_different_bookmaker_panel_than_2024_25():
    """Regression test for the real 2025/26 schema-drift defect found
    2026-09-17 while running H-FB2-002's sealed OOS evaluation: the
    historical KNOWN_BOOKMAKER_PREFIXES panel (B365, BW, BF, PS, WH,
    1XB) silently yields only 3 usable bookmakers (B365, BW, PS) on
    real 2025/26 data -- BF, WH and 1XB are gone -- below
    MIN_BOOKMAKERS_FOR_CONSENSUS (4), confirmed directly, not assumed,
    against the real downloaded E0 file."""
    row = load_real_row(
        "data/raw/football/football_data_co_uk/E0/2025_26/E0_excerpt.csv", 0
    )  # Liverpool vs Bournemouth, 15/08/2025

    old_panel_result = extract_bookmaker_triplets(row, bookmaker_prefixes=KNOWN_BOOKMAKER_PREFIXES)
    old_panel_counts = bookmaker_count_by_timing(old_panel_result)
    old_panel_bookmakers = {t.bookmaker for t in old_panel_result.complete_triplets}
    assert old_panel_bookmakers == {"B365", "BW", "PS"}  # BF/WH/1XB are gone from 2025/26
    assert old_panel_counts["opening"] == 3
    assert old_panel_counts["opening"] < 4  # below MIN_BOOKMAKERS_FOR_CONSENSUS -- this is the defect

    new_panel_result = extract_bookmaker_triplets(row, bookmaker_prefixes=BOOKMAKER_PREFIXES_2025_26)
    new_panel_counts = bookmaker_count_by_timing(new_panel_result)
    assert new_panel_counts["opening"] == 8  # B365, BFD, BMGM, BV, BW, CL, LB, PS all quote this real match
    assert new_panel_counts["closing"] == 8
    assert new_panel_result.rejected_bookmakers == []


def test_real_2025_26_row_new_panel_still_excludes_aggregate_columns():
    """Max/Avg/BFE must still never be counted as individual bookmakers
    under the new 2025/26 panel, exactly as under the historical one."""
    row = load_real_row(
        "data/raw/football/football_data_co_uk/E0/2025_26/E0_excerpt.csv", 0
    )
    result = extract_bookmaker_triplets(row, bookmaker_prefixes=BOOKMAKER_PREFIXES_2025_26)
    bookmakers_seen = {t.bookmaker for t in result.complete_triplets}
    assert "Max" not in bookmakers_seen
    assert "Avg" not in bookmakers_seen
    assert "BFE" not in bookmakers_seen


def test_historical_default_panel_is_unchanged_by_the_2025_26_addition():
    """The fix adds a NEW constant; it must not alter
    KNOWN_BOOKMAKER_PREFIXES, which Cycle 1's already-committed
    2020/21-2024/25 processed files were built against."""
    assert KNOWN_BOOKMAKER_PREFIXES == ("B365", "BW", "BF", "PS", "WH", "1XB")
