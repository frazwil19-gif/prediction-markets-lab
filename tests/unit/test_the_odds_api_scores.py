"""Tests for ingestion.the_odds_api_scores (Production Infrastructure Build, 2026-09-20)."""

from __future__ import annotations

import pytest

from prediction_markets_lab.ingestion.the_odds_api_loader import TheOddsApiResponseError
from prediction_markets_lab.ingestion.the_odds_api_scores import parse_scores_response


def _completed_event() -> dict:
    return {
        "id": "abc123",
        "sport_key": "soccer_epl",
        "commence_time": "2026-09-19T14:00:00Z",
        "completed": True,
        "home_team": "Team A",
        "away_team": "Team B",
        "scores": [
            {"name": "Team A", "score": "2"},
            {"name": "Team B", "score": "1"},
        ],
    }


def test_parse_completed_event_with_scores():
    parsed = parse_scores_response([_completed_event()], sport_key="soccer_epl")
    assert len(parsed) == 1
    assert parsed[0].completed is True
    assert parsed[0].home_score == 2
    assert parsed[0].away_score == 1


def test_parse_not_yet_started_event_has_null_scores():
    event = _completed_event()
    event["completed"] = False
    event["scores"] = None
    parsed = parse_scores_response([event], sport_key="soccer_epl")
    assert parsed[0].completed is False
    assert parsed[0].home_score is None
    assert parsed[0].away_score is None


def test_missing_required_field_raises():
    event = _completed_event()
    del event["home_team"]
    with pytest.raises(TheOddsApiResponseError):
        parse_scores_response([event], sport_key="soccer_epl")


def test_non_list_payload_raises():
    with pytest.raises(TheOddsApiResponseError):
        parse_scores_response({"not": "a list"}, sport_key="soccer_epl")
