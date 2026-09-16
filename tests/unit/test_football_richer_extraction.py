"""Tests for football_richer_extraction.py (Football Cycle 2)."""

from prediction_markets_lab.ingestion.football_richer_extraction import (
    BFE_ONLY_PREFIX,
    extract_asian_handicap_line,
    extract_market_summary_two_way,
    extract_match_statistics,
    extract_two_way_market,
)


def test_extract_match_statistics_all_present():
    row = {
        "HS": "12", "AS": "8", "HST": "5", "AST": "3",
        "HC": "6", "AC": "4", "HF": "10", "AF": "11",
        "HY": "2", "AY": "1", "HR": "0", "AR": "0",
        "Referee": "M Oliver",
    }
    stats = extract_match_statistics(row)
    assert stats.home_shots == 12
    assert stats.away_shots == 8
    assert stats.home_shots_on_target == 5
    assert stats.away_corners == 4
    assert stats.home_red_cards == 0
    assert stats.referee == "M Oliver"


def test_extract_match_statistics_missing_column_is_none_not_zero():
    row = {"HS": "12"}
    stats = extract_match_statistics(row)
    assert stats.home_shots == 12
    assert stats.away_shots is None
    assert stats.referee is None


def test_extract_match_statistics_blank_string_is_none():
    row = {"HS": "", "Referee": "   "}
    stats = extract_match_statistics(row)
    assert stats.home_shots is None
    assert stats.referee is None


def test_extract_match_statistics_negative_is_rejected():
    row = {"HS": "-1"}
    stats = extract_match_statistics(row)
    assert stats.home_shots is None


def test_extract_two_way_market_over_under_opening_and_closing():
    row = {
        "B365>2.5": "1.90", "B365<2.5": "1.95",
        "B365C>2.5": "1.85", "B365C<2.5": "2.00",
    }
    result = extract_two_way_market(row, ">2.5", "<2.5")
    assert len(result.complete_prices) == 2
    opening = [p for p in result.complete_prices if p.price_timing == "opening"][0]
    closing = [p for p in result.complete_prices if p.price_timing == "closing"][0]
    assert opening.bookmaker == "B365"
    assert opening.side_a_odds == 1.90
    assert opening.side_b_odds == 1.95
    assert closing.side_a_odds == 1.85
    assert closing.side_b_odds == 2.00


def test_extract_two_way_market_asian_handicap_closing_column_naming():
    # AH's closing convention inserts "C" right after the prefix, before "AH".
    row = {
        "B365AHH": "1.95", "B365AHA": "1.87",
        "B365CAHH": "2.05", "B365CAHA": "1.78",
    }
    result = extract_two_way_market(row, "AHH", "AHA")
    assert len(result.complete_prices) == 2
    timings = {p.price_timing for p in result.complete_prices}
    assert timings == {"opening", "closing"}


def test_extract_two_way_market_missing_bookmaker_skipped_silently():
    row = {}
    result = extract_two_way_market(row, ">2.5", "<2.5")
    assert result.complete_prices == []
    assert result.rejected_bookmakers == []


def test_extract_two_way_market_incomplete_pair_is_rejected():
    row = {"B365>2.5": "1.90"}  # side_b missing
    result = extract_two_way_market(row, ">2.5", "<2.5")
    assert result.complete_prices == []
    assert result.rejected_bookmakers == ["B365 (opening)"]


def test_extract_two_way_market_invalid_odds_rejected():
    row = {"B365>2.5": "0.50", "B365<2.5": "1.95"}  # 0.50 is not valid decimal odds
    result = extract_two_way_market(row, ">2.5", "<2.5")
    assert result.complete_prices == []
    assert result.rejected_bookmakers == ["B365 (opening)"]


def test_extract_asian_handicap_line_present():
    row = {"AHh": "-0.25", "AHCh": "-0.5"}
    lines = extract_asian_handicap_line(row)
    assert lines["opening_line"] == -0.25
    assert lines["closing_line"] == -0.5


def test_extract_asian_handicap_line_missing_is_none():
    row = {}
    lines = extract_asian_handicap_line(row)
    assert lines["opening_line"] is None
    assert lines["closing_line"] is None


def test_extract_asian_handicap_line_zero_is_valid_not_missing():
    row = {"AHh": "0"}
    lines = extract_asian_handicap_line(row)
    assert lines["opening_line"] == 0.0


def test_extract_two_way_market_default_prefixes_are_b365_and_pinnacle():
    # Corpus-wide coverage sweep confirmed only B365 and P (Pinnacle)
    # publish O/U 2.5 and AH odds across every season/competition --
    # the 1X2 six-bookmaker panel does NOT extend to these markets.
    row = {
        "B365>2.5": "1.90", "B365<2.5": "1.95",
        "P>2.5": "1.92", "P<2.5": "1.93",
        # A bookmaker from the 1X2 panel that does NOT quote O/U in
        # this source -- must be ignored by the default prefix set.
        "BW>2.5": "1.80", "BW<2.5": "2.10",
    }
    result = extract_two_way_market(row, ">2.5", "<2.5")
    bookmakers = {p.bookmaker for p in result.complete_prices}
    assert bookmakers == {"B365", "P"}


def test_extract_two_way_market_bfe_only_prefix_is_separate():
    row = {"BFE>2.5": "1.88", "BFE<2.5": "1.98"}
    result = extract_two_way_market(row, ">2.5", "<2.5", bookmaker_prefixes=BFE_ONLY_PREFIX)
    assert len(result.complete_prices) == 1
    assert result.complete_prices[0].bookmaker == "BFE"


def test_extract_market_summary_two_way_max_and_avg_opening_and_closing():
    row = {
        "Max>2.5": "1.95", "Max<2.5": "2.05",
        "Avg>2.5": "1.88", "Avg<2.5": "1.96",
        "MaxC>2.5": "1.93", "MaxC<2.5": "2.02",
        "AvgC>2.5": "1.87", "AvgC<2.5": "1.94",
    }
    results = extract_market_summary_two_way(row, ">2.5", "<2.5")
    assert len(results) == 4
    by_key = {(r.summary_type, r.price_timing): r for r in results}
    assert by_key[("max", "opening")].side_a_odds == 1.95
    assert by_key[("avg", "closing")].side_b_odds == 1.94


def test_extract_market_summary_two_way_missing_is_omitted_not_zero():
    row = {"Avg>2.5": "1.88", "Avg<2.5": "1.96"}
    results = extract_market_summary_two_way(row, ">2.5", "<2.5")
    # Only avg opening present -- max (both timings) and avg closing
    # must not appear as spurious all-None rows.
    assert len(results) == 1
    assert results[0].summary_type == "avg"
    assert results[0].price_timing == "opening"


def test_extract_market_summary_two_way_one_side_only_kept_as_partial():
    # Max/Avg sides are independent draws across the panel -- a single
    # valid side is still meaningful and must not be discarded.
    row = {"Max>2.5": "1.95"}  # Max<2.5 absent
    results = extract_market_summary_two_way(row, ">2.5", "<2.5")
    assert len(results) == 1
    assert results[0].side_a_odds == 1.95
    assert results[0].side_b_odds is None
