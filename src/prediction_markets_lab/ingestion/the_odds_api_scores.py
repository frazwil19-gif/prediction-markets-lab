"""Live results ("scores") adapter for The Odds API v4 -- feeds automated
settlement (Section 7, Production Infrastructure Build, 2026-09-20).

Companion to ingestion.the_odds_api_loader (odds), same project, same
API, same credential handling (THE_ODDS_API_KEY from the environment
only -- see that module's resolve_api_key, reused here rather than
duplicated). The /v4/sports/{sport}/scores endpoint returns each event's
current score and whether it has completed; this module parses that
response into a small typed structure settlement.settle_paper_ledger
consumes to determine 1X2 / Over-Under results without any manual result
entry.

NOT YET LIVE-TESTED against a real response at the time this module was
written (same honesty discipline as the_odds_api_loader's own original
build) -- parsing is unit-tested against constructed fixture JSON
matching the documented schema; the first live call should be treated as
its own validation step, not assumed correct because the tests pass.
"""

from __future__ import annotations

import json
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass

from prediction_markets_lab.ingestion.the_odds_api_loader import (
    TheOddsApiConfig,
    TheOddsApiResponseError,
)


@dataclass(frozen=True)
class ParsedScore:
    """One event's result status, as reported by /v4/sports/{sport}/scores."""

    event_id: str
    sport_key: str
    commence_time: str
    completed: bool
    home_team: str
    away_team: str
    home_score: int | None
    away_score: int | None


def _parse_score_value(raw: object) -> int | None:
    if raw is None:
        return None
    try:
        return int(raw)
    except (TypeError, ValueError):
        return None


def parse_scores_response(raw_events: object, sport_key: str) -> list[ParsedScore]:
    """Validate and parse a raw /v4/sports/{sport}/scores JSON payload.

    Args:
        raw_events: The already-JSON-decoded response body -- a list of
            event objects per The Odds API's documented scores schema.
        sport_key: The sport_key this response was requested for, used
            for error messages only.

    Returns:
        A list of ParsedScore, one per event. An event with a null
        `scores` field (not yet started, or a provider outage) is still
        returned, with home_score/away_score both None and completed
        taken from the response's own `completed` flag -- never guessed.

    Raises:
        TheOddsApiResponseError: If the payload is not a list, or an
            event is missing a required field.
    """
    if not isinstance(raw_events, list):
        raise TheOddsApiResponseError(
            f"expected a JSON list of events for sport {sport_key!r} scores, got "
            f"{type(raw_events).__name__}"
        )

    parsed: list[ParsedScore] = []
    for i, raw_event in enumerate(raw_events):
        if not isinstance(raw_event, dict):
            raise TheOddsApiResponseError(f"scores event[{i}] is not a JSON object")
        missing = {"id", "sport_key", "commence_time", "completed", "home_team", "away_team"} - set(
            raw_event.keys()
        )
        if missing:
            raise TheOddsApiResponseError(f"scores event[{i}] is missing required field(s): {sorted(missing)}")

        home_score: int | None = None
        away_score: int | None = None
        scores = raw_event.get("scores")
        if scores:
            by_team = {s.get("name"): _parse_score_value(s.get("score")) for s in scores if isinstance(s, dict)}
            home_score = by_team.get(raw_event["home_team"])
            away_score = by_team.get(raw_event["away_team"])

        parsed.append(
            ParsedScore(
                event_id=str(raw_event["id"]),
                sport_key=str(raw_event["sport_key"]),
                commence_time=str(raw_event["commence_time"]),
                completed=bool(raw_event["completed"]),
                home_team=str(raw_event["home_team"]),
                away_team=str(raw_event["away_team"]),
                home_score=home_score,
                away_score=away_score,
            )
        )
    return parsed


def fetch_scores_raw(sport_key: str, config: TheOddsApiConfig, days_from: int = 3) -> list:
    """Call The Odds API's /v4/sports/{sport}/scores endpoint for one sport_key.

    Args:
        sport_key: One of config.sport_keys' keys.
        config: The active TheOddsApiConfig (reused from the odds
            adapter -- same api_key_env_var, base_url, timeout).
        days_from: How many days back to include completed events for
            (The Odds API's documented `daysFrom` parameter, 1-3). 3 is
            used as the default so a settlement run always covers the
            weekend/short gap case without needing to be re-tuned daily.

    Returns:
        The decoded JSON response body (a list of event score objects).

    Raises:
        TheOddsApiCredentialError: If no API key is configured.
        TheOddsApiResponseError: If the request fails or is not valid JSON.
    """
    api_key = config.resolve_api_key()
    params = {"apiKey": api_key, "daysFrom": str(days_from)}
    url = f"{config.base_url}/v4/sports/{sport_key}/scores/?{urllib.parse.urlencode(params)}"
    request = urllib.request.Request(url, headers={"Accept": "application/json"})
    try:
        with urllib.request.urlopen(request, timeout=config.request_timeout_seconds) as response:
            body = response.read()
    except urllib.error.HTTPError as exc:
        detail = ""
        try:
            detail = exc.read().decode("utf-8", errors="replace")
        except Exception:
            pass
        raise TheOddsApiResponseError(
            f"The Odds API scores request returned HTTP {exc.code} for sport {sport_key!r}: {detail[:500]}"
        ) from exc
    except urllib.error.URLError as exc:
        raise TheOddsApiResponseError(
            f"could not reach The Odds API scores endpoint for sport {sport_key!r}: {exc.reason}"
        ) from exc

    try:
        payload = json.loads(body)
    except json.JSONDecodeError as exc:
        raise TheOddsApiResponseError(
            f"The Odds API scores response for sport {sport_key!r} was not valid JSON"
        ) from exc
    return payload
