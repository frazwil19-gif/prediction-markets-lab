import json
from datetime import datetime, timezone

import pytest

from prediction_markets_lab.ingestion.betfair_historical_schema import (
    latest_singles_event_candidates,
    parse_market_change_line,
    to_singles_event_candidate,
)

# A hand-built line matching Betfair's DOCUMENTED market-change-message
# shape (not a real captured file -- see this module's docstring for why).
MARKET_DEFINITION_LINE = json.dumps({
    "op": "mcm",
    "pt": 1741593600000,  # 2025-03-10T08:00:00Z
    "mc": [
        {
            "id": "1.123456789",
            "marketDefinition": {
                "eventId": "31234567",
                "marketTime": "2025-03-10T14:00:00.000Z",
                "marketType": "MATCH_ODDS",
                "status": "OPEN",
                "runners": [
                    {"id": 11111, "name": "Novak Djokovic", "sortPriority": 1},
                    {"id": 22222, "name": "Rafael Nadal", "sortPriority": 2},
                ],
            },
        }
    ],
})

PRICE_UPDATE_LINE = json.dumps({
    "op": "mcm",
    "pt": 1741593660000,
    "mc": [
        {
            "id": "1.123456789",
            "rc": [
                {
                    "id": 11111,
                    "ltp": 1.65,
                    "batb": [[0, 1.64, 120.5], [1, 1.63, 40.0]],
                    "batl": [[0, 1.66, 80.0]],
                },
                {"id": 22222, "ltp": 2.30, "batb": [], "batl": []},
            ],
        }
    ],
})

DOUBLES_MARKET_LINE = json.dumps({
    "op": "mcm",
    "pt": 1741593600000,
    "mc": [
        {
            "id": "1.999999999",
            "marketDefinition": {
                "eventId": "31234568",
                "marketTime": "2025-03-10T14:00:00.000Z",
                "marketType": "MATCH_ODDS",
                "status": "OPEN",
                "runners": [
                    {"id": 1, "name": "A/B", "sortPriority": 1},
                    {"id": 2, "name": "C/D", "sortPriority": 2},
                    {"id": 3, "name": "E/F", "sortPriority": 3},
                ],
            },
        }
    ],
})


def test_parses_market_definition_line():
    messages = parse_market_change_line(MARKET_DEFINITION_LINE)
    assert len(messages) == 1
    msg = messages[0]
    assert msg.market_id == "1.123456789"
    assert msg.published_at == datetime(2025, 3, 10, 8, 0, tzinfo=timezone.utc)
    assert msg.market_definition is not None
    assert msg.market_definition.event_id == "31234567"
    assert msg.market_definition.market_time == datetime(2025, 3, 10, 14, 0, tzinfo=timezone.utc)
    assert msg.market_definition.status == "OPEN"
    names = [r.name for r in msg.market_definition.runners]
    assert names == ["Novak Djokovic", "Rafael Nadal"]
    assert msg.runner_changes == ()


def test_parses_price_update_line_with_ladders():
    messages = parse_market_change_line(PRICE_UPDATE_LINE)
    msg = messages[0]
    assert msg.market_definition is None
    assert len(msg.runner_changes) == 2
    djokovic_rc = msg.runner_changes[0]
    assert djokovic_rc.selection_id == 11111
    assert djokovic_rc.last_traded_price == 1.65
    assert [(lvl.price, lvl.size) for lvl in djokovic_rc.available_to_back] == [(1.64, 120.5), (1.63, 40.0)]
    assert [(lvl.price, lvl.size) for lvl in djokovic_rc.available_to_lay] == [(1.66, 80.0)]


def test_raises_on_missing_mc_key():
    with pytest.raises(KeyError):
        parse_market_change_line(json.dumps({"op": "mcm", "pt": 123}))


def test_raises_on_malformed_ladder_entry_instead_of_silently_misreading_it():
    bad_line = json.dumps({
        "op": "mcm", "pt": 1741593660000,
        "mc": [{"id": "1.1", "rc": [{"id": 1, "ltp": 1.5, "batb": [[1.64, 120.5]], "batl": []}]}],
    })
    with pytest.raises(ValueError):
        parse_market_change_line(bad_line)


def test_raises_on_invalid_json():
    with pytest.raises(ValueError):
        parse_market_change_line("not json at all")


def test_to_singles_event_candidate_from_market_definition():
    messages = parse_market_change_line(MARKET_DEFINITION_LINE)
    candidate = to_singles_event_candidate(messages[0])
    assert candidate is not None
    assert candidate.market_id == "1.123456789"
    assert candidate.event_id == "31234567"
    assert candidate.event_open_date.isoformat() == "2025-03-10"
    assert set(candidate.runner_names) == {"Novak Djokovic", "Rafael Nadal"}


def test_to_singles_event_candidate_none_for_price_only_message():
    messages = parse_market_change_line(PRICE_UPDATE_LINE)
    assert to_singles_event_candidate(messages[0]) is None


def test_to_singles_event_candidate_none_for_non_two_runner_market():
    messages = parse_market_change_line(DOUBLES_MARKET_LINE)
    assert to_singles_event_candidate(messages[0]) is None


# Sanitised, minimal fixture derived from a real discovery in Fraser's
# 2026-09-16 Betfair BASIC sample: a real tennis event carries a
# SET_WINNER market alongside its Match Odds market, with the SAME two
# player names and the same eventId. Real market/selection IDs replaced
# with clearly-fake round numbers; everything else (field shape, the
# fact that SET_WINNER has exactly two runners) matches the real file.
SET_WINNER_MARKET_LINE = json.dumps({
    "op": "mcm",
    "pt": 1741593600000,
    "mc": [
        {
            "id": "1.500000002",
            "marketDefinition": {
                "eventId": "31234567",
                "marketTime": "2025-03-10T14:00:00.000Z",
                "marketType": "SET_WINNER",
                "status": "OPEN",
                "runners": [
                    {"id": 11111, "name": "Novak Djokovic", "sortPriority": 1},
                    {"id": 22222, "name": "Rafael Nadal", "sortPriority": 2},
                ],
            },
        }
    ],
})


def test_to_singles_event_candidate_none_for_non_match_odds_market_type():
    """Regression test for a real bug: a real tennis event carries several
    non-Match-Odds two-runner markets (SET_WINNER here) with the exact
    same player names as the real Match Odds market. Before the
    market_type filter was added, this produced a spurious extra
    "singles candidate" per sibling market, which made
    classify_tennis_betfair_match report a perfectly matchable real
    match as AMBIGUOUS -- not because the match itself was ambiguous,
    but because of this upstream duplication. A SET_WINNER market must
    never produce a candidate, however many runners it has."""
    messages = parse_market_change_line(SET_WINNER_MARKET_LINE)
    assert to_singles_event_candidate(messages[0]) is None


def test_to_singles_event_candidate_ok_for_match_odds_despite_sibling_set_winner_market():
    """The corresponding real Match Odds market for the same event/players
    still produces a candidate -- the filter excludes SET_WINNER
    specifically, not tennis markets with two same-named runners in
    general."""
    match_odds_messages = parse_market_change_line(MARKET_DEFINITION_LINE)
    candidate = to_singles_event_candidate(match_odds_messages[0])
    assert candidate is not None
    assert candidate.event_id == "31234567"



# Sanitised, minimal fixture derived from a real discovery in Fraser's
# 2026-09-16 Betfair BASIC sample: a real market's scheduled date was
# revised across its own message history (postponement), with three
# different marketTime values seen for the same real marketId before
# settling on the actual played date. Real IDs replaced with clearly
# fake round numbers.
REVISED_DATE_LINE_EARLY = json.dumps({
    "op": "mcm", "pt": 1741420800000,
    "mc": [{
        "id": "1.700000001",
        "marketDefinition": {
            "eventId": "39999999", "marketTime": "2025-03-08T14:00:00.000Z",
            "marketType": "MATCH_ODDS", "status": "OPEN",
            "runners": [
                {"id": 1, "name": "Player One", "sortPriority": 1},
                {"id": 2, "name": "Player Two", "sortPriority": 2},
            ],
        },
    }],
})
REVISED_DATE_LINE_LATE = json.dumps({
    "op": "mcm", "pt": 1741593600000,
    "mc": [{
        "id": "1.700000001",
        "marketDefinition": {
            "eventId": "39999999", "marketTime": "2025-03-10T14:00:00.000Z",
            "marketType": "MATCH_ODDS", "status": "OPEN",
            "runners": [
                {"id": 1, "name": "Player One", "sortPriority": 1},
                {"id": 2, "name": "Player Two", "sortPriority": 2},
            ],
        },
    }],
})


def test_latest_singles_event_candidates_uses_last_not_first_definition():
    """Regression test for a real discovery: a market's scheduled date
    can be revised within its own message history. Using the first
    definition would keep the stale 2025-03-08 date; the last one
    (2025-03-10) is what actually applies."""
    messages = (
        parse_market_change_line(REVISED_DATE_LINE_EARLY)
        + parse_market_change_line(REVISED_DATE_LINE_LATE)
    )
    result = latest_singles_event_candidates(messages)
    assert set(result) == {"1.700000001"}
    assert result["1.700000001"].event_open_date.isoformat() == "2025-03-10"


def test_latest_singles_event_candidates_skips_price_only_and_non_match_odds():
    messages = parse_market_change_line(PRICE_UPDATE_LINE) + parse_market_change_line(SET_WINNER_MARKET_LINE)
    assert latest_singles_event_candidates(messages) == {}


def test_latest_singles_event_candidates_one_entry_per_market_id():
    messages = parse_market_change_line(MARKET_DEFINITION_LINE) * 3
    result = latest_singles_event_candidates(messages)
    assert len(result) == 1
