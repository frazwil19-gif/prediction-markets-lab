import json
from datetime import datetime, timezone

import pytest

from prediction_markets_lab.ingestion.betfair_historical_schema import (
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
