"""Tests for ingestion.the_odds_api_loader (2026-09-19 build).

All tests exercise parsing/transformation logic against constructed
fixture JSON matching The Odds API's documented schema -- no network
call is made or mocked, since no live API key was available this
session (see the module's own docstring and the implementation
checkpoint). fetch_odds_raw's credential-gate behaviour is tested
without touching the network, since resolve_api_key() is checked before
any request is made.
"""

from __future__ import annotations

import os

import pytest

from prediction_markets_lab.ingestion.the_odds_api_loader import (
    TheOddsApiConfig,
    TheOddsApiCredentialError,
    TheOddsApiResponseError,
    build_canonical_odds_and_metadata,
    fetch_odds_raw,
    parse_odds_response,
)


def _sample_event(**overrides) -> dict:
    event = {
        "id": "evt-001",
        "sport_key": "soccer_epl",
        "commence_time": "2026-09-19T19:00:00Z",
        "home_team": "Team A",
        "away_team": "Team B",
        "bookmakers": [
            {
                "key": "williamhill",
                "title": "William Hill",
                "last_update": "2026-09-19T09:00:00Z",
                "markets": [
                    {
                        "key": "h2h",
                        "outcomes": [
                            {"name": "Team A", "price": 2.10},
                            {"name": "Draw", "price": 3.40},
                            {"name": "Team B", "price": 3.60},
                        ],
                    },
                    {
                        "key": "totals",
                        "outcomes": [
                            {"name": "Over", "price": 1.90, "point": 2.5},
                            {"name": "Under", "price": 1.95, "point": 2.5},
                        ],
                    },
                ],
            },
            {
                "key": "ladbrokes",
                "title": "Ladbrokes",
                "last_update": "2026-09-19T09:01:00Z",
                "markets": [
                    {
                        "key": "h2h",
                        "outcomes": [
                            {"name": "Team A", "price": 2.05},
                            {"name": "Draw", "price": 3.50},
                            {"name": "Team B", "price": 3.70},
                        ],
                    },
                    {
                        "key": "totals",
                        "outcomes": [
                            {"name": "Over", "price": 1.87, "point": 2.5},
                            {"name": "Under", "price": 2.00, "point": 2.5},
                        ],
                    },
                ],
            },
        ],
    }
    event.update(overrides)
    return event


def test_parse_odds_response_valid_payload():
    events = parse_odds_response([_sample_event()], sport_key="soccer_epl")
    assert len(events) == 1
    assert events[0].id == "evt-001"
    assert len(events[0].bookmakers) == 2
    assert events[0].bookmakers[0].markets[0].key == "h2h"
    assert events[0].bookmakers[0].markets[1].outcomes[0].point == 2.5


def test_parse_odds_response_rejects_non_list_payload():
    with pytest.raises(TheOddsApiResponseError, match="expected a JSON list"):
        parse_odds_response({"message": "invalid api key"}, sport_key="soccer_epl")


def test_parse_odds_response_rejects_missing_required_field():
    bad_event = _sample_event()
    del bad_event["home_team"]
    with pytest.raises(TheOddsApiResponseError, match="home_team"):
        parse_odds_response([bad_event], sport_key="soccer_epl")


def test_parse_odds_response_rejects_non_numeric_price():
    bad_event = _sample_event()
    bad_event["bookmakers"][0]["markets"][0]["outcomes"][0]["price"] = "not_a_number"
    with pytest.raises(TheOddsApiResponseError, match="not numeric"):
        parse_odds_response([bad_event], sport_key="soccer_epl")


def test_build_canonical_maps_h2h_and_totals_correctly():
    events = parse_odds_response([_sample_event()], sport_key="soccer_epl")
    config = TheOddsApiConfig()
    odds, metadata, warnings = build_canonical_odds_and_metadata(events, config)

    market_id_1x2 = "soccer_epl-evt-001-1x2"
    market_id_ou = "soccer_epl-evt-001-ou25"

    assert odds[market_id_1x2]["William Hill"] == {"home": 2.10, "draw": 3.40, "away": 3.60}
    assert odds[market_id_1x2]["Ladbrokes"] == {"home": 2.05, "draw": 3.50, "away": 3.70}
    assert odds[market_id_ou]["William Hill"] == {"over": 1.90, "under": 1.95}

    assert metadata[market_id_1x2]["competition"] == "Premier League"
    assert metadata[market_id_1x2]["event"] == "Team A v Team B"
    assert metadata[market_id_1x2]["market_type"] == "1x2"
    assert metadata[market_id_ou]["market_type"] == "over_under_2_5"
    assert warnings == []


def test_totals_off_target_line_is_skipped_with_warning():
    event = _sample_event()
    # This bookmaker only offers the 3.5 line, not 2.5.
    event["bookmakers"][0]["markets"][1]["outcomes"] = [
        {"name": "Over", "price": 1.50, "point": 3.5},
        {"name": "Under", "price": 2.60, "point": 3.5},
    ]
    events = parse_odds_response([event], sport_key="soccer_epl")
    odds, _, warnings = build_canonical_odds_and_metadata(events, TheOddsApiConfig())

    market_id_ou = "soccer_epl-evt-001-ou25"
    assert "William Hill" not in odds.get(market_id_ou, {})
    assert any("2.5" in w and "William Hill" in w for w in warnings)


def test_incomplete_h2h_outcome_set_is_skipped_with_warning():
    event = _sample_event()
    # Missing the draw outcome entirely.
    event["bookmakers"][0]["markets"][0]["outcomes"] = [
        {"name": "Team A", "price": 2.10},
        {"name": "Team B", "price": 3.60},
    ]
    events = parse_odds_response([event], sport_key="soccer_epl")
    odds, _, warnings = build_canonical_odds_and_metadata(events, TheOddsApiConfig())

    market_id_1x2 = "soccer_epl-evt-001-1x2"
    assert "William Hill" not in odds.get(market_id_1x2, {})
    assert any("William Hill" in w and "home/draw/away" in w for w in warnings)


def test_unrecognised_h2h_outcome_name_is_skipped_with_warning():
    event = _sample_event()
    event["bookmakers"][0]["markets"][0]["outcomes"] = [
        {"name": "Some Other Name", "price": 2.10},
        {"name": "Draw", "price": 3.40},
        {"name": "Team B", "price": 3.60},
    ]
    events = parse_odds_response([event], sport_key="soccer_epl")
    odds, _, warnings = build_canonical_odds_and_metadata(events, TheOddsApiConfig())

    market_id_1x2 = "soccer_epl-evt-001-1x2"
    assert "William Hill" not in odds.get(market_id_1x2, {})
    assert any("did not match either team name" in w for w in warnings)


def test_event_with_no_usable_quotes_is_warned_and_skipped():
    event = _sample_event(bookmakers=[])
    events = parse_odds_response([event], sport_key="soccer_epl")
    odds, metadata, warnings = build_canonical_odds_and_metadata(events, TheOddsApiConfig())
    assert odds == {}
    assert metadata == {}
    assert any("no usable h2h or totals quotes" in w for w in warnings)


def test_resolve_api_key_raises_clear_error_when_unset(monkeypatch):
    monkeypatch.delenv("THE_ODDS_API_KEY", raising=False)
    config = TheOddsApiConfig()
    with pytest.raises(TheOddsApiCredentialError, match="THE_ODDS_API_KEY"):
        config.resolve_api_key()


def test_resolve_api_key_succeeds_when_set(monkeypatch):
    monkeypatch.setenv("THE_ODDS_API_KEY", "test-key-123")
    config = TheOddsApiConfig()
    assert config.resolve_api_key() == "test-key-123"


def test_fetch_odds_raw_stops_at_credential_gate_without_any_network_call(monkeypatch):
    monkeypatch.delenv("THE_ODDS_API_KEY", raising=False)
    config = TheOddsApiConfig()
    with pytest.raises(TheOddsApiCredentialError):
        fetch_odds_raw("soccer_epl", config)
