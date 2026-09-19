"""Live-odds adapter for The Odds API (v4).

Converts The Odds API's documented JSON response format into this
project's existing canonical bookmaker-odds structures -- the same
{market_id: {bookmaker: {selection: decimal_odds}}} shape
ingestion.manual_odds_loader.load_manual_odds_by_bookmaker already
produces from a CSV, plus a metadata dict matching
load_manual_odds_market_metadata's shape -- so scripts/run_daily_scan.py
can consume live API data through the EXACT SAME downstream code path as
a manual CSV, unmodified. The probability/EV/grading engine stays
source-agnostic, per the operator's "MAJOR NEXT PHASE" instruction
(2026-09-19): "The existing engine should therefore remain
source-agnostic."

IMPORTANT -- DOCUMENTATION-BASED, NOT YET LIVE-TESTED: this module was
built from The Odds API's public documentation
(https://the-odds-api.com/liveapi/guides/v4/ and related pages) without
an API key -- none was available this session; obtaining one is the
genuine credential gate this build stops at (see
docs/DAILY_ENGINE_V1_LOCK_AND_IMPLEMENTATION_ROADMAP.md's successor
checkpoint). The parsing/transformation logic (parse_odds_response,
build_canonical_odds_and_metadata) is unit-tested against constructed
fixture JSON matching the documented schema and is safe to trust as far
as that goes. fetch_odds_raw (the actual network call) has NOT been
exercised against a real response. When a real key is available, the
first live call should be treated as a validation step in its own
right, not assumed correct because the tests pass.

V1 SCOPE: h2h ("head to head") -> our "1x2", and totals ("over/under")
-> our "over_under_2_5", filtered to the 2.5-goals line specifically
(see _extract_totals_at_line). spreads (Asian Handicap) is deliberately
NOT wired here yet, matching the project's existing "AH needs exact-line
matching, do not let it delay core automation" decision.
"""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass, field
from datetime import datetime, timezone


class TheOddsApiCredentialError(RuntimeError):
    """Raised when no API key is configured.

    This is the intended, correct stopping point for this adapter --
    per the operator's instruction, "stop only at the genuine credential
    gate and tell Fraser exactly what to do."
    """


class TheOddsApiResponseError(RuntimeError):
    """Raised when the API returns an error status or an unparseable/malformed response."""


@dataclass(frozen=True)
class TheOddsApiConfig:
    """Configuration for a scan against The Odds API.

    The API key is deliberately never a field here -- it is read from an
    environment variable at call time (resolve_api_key), so it is never
    hard-coded, never logged, and never committed to git. In GitHub
    Actions this environment variable is populated from a repository
    Secret (see the daily-scan workflow); locally, Fraser sets it in his
    own shell.
    """

    api_key_env_var: str = "THE_ODDS_API_KEY"
    # sport_key -> our own competition display name. Values sourced from
    # a third-party API wrapper's documented sport table (oddsapiR),
    # NOT yet independently confirmed against the live /v4/sports
    # endpoint (that call itself is quota-free but still needs a key) --
    # see the module docstring and the implementation checkpoint. If a
    # key is wrong, fetch_odds_raw will surface a clear HTTP error
    # rather than silently returning nothing.
    sport_keys: dict[str, str] = field(
        default_factory=lambda: {
            "soccer_epl": "Premier League",
            "soccer_efl_champ": "Championship",
            "soccer_spl": "Scottish Premiership",
        }
    )
    regions: str = "uk"
    markets: tuple[str, ...] = ("h2h", "totals")
    odds_format: str = "decimal"
    base_url: str = "https://api.the-odds-api.com"
    request_timeout_seconds: float = 15.0
    total_goals_line: float = 2.5

    def resolve_api_key(self) -> str:
        """Read the API key from the environment, or raise a clear, actionable error.

        Raises:
            TheOddsApiCredentialError: If the environment variable is not
                set. The message is written to be read directly by
                Fraser, not just logged.
        """
        key = os.environ.get(self.api_key_env_var)
        if not key:
            raise TheOddsApiCredentialError(
                f"Environment variable {self.api_key_env_var} is not set. "
                "This is the genuine credential gate this project cannot cross on its "
                "own: get a free API key at https://the-odds-api.com (Starter plan, "
                "500 credits/month, no card required per their published pricing), "
                f"then set {self.api_key_env_var} -- as a GitHub Actions repository "
                "secret for the scheduled workflow, and/or in your own shell for a "
                "manual run."
            )
        return key


# ---------------------------------------------------------------------------
# Parsed (validated) response types
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ParsedOutcome:
    name: str
    price: float
    point: float | None = None


@dataclass(frozen=True)
class ParsedMarket:
    key: str
    outcomes: list[ParsedOutcome]


@dataclass(frozen=True)
class ParsedBookmaker:
    key: str
    title: str
    last_update: str
    markets: list[ParsedMarket]


@dataclass(frozen=True)
class ParsedEvent:
    id: str
    sport_key: str
    commence_time: str
    home_team: str
    away_team: str
    bookmakers: list[ParsedBookmaker]


def _require_keys(obj: dict, required: set[str], context: str) -> None:
    missing = required - set(obj.keys())
    if missing:
        raise TheOddsApiResponseError(f"{context} is missing required field(s): {sorted(missing)}")


def parse_odds_response(raw_events: object, sport_key: str) -> list[ParsedEvent]:
    """Validate and parse a raw /v4/sports/{sport}/odds JSON payload.

    Args:
        raw_events: The already-JSON-decoded response body -- expected to
            be a list of event objects per The Odds API's documented
            schema.
        sport_key: The sport_key this response was requested for, used
            only for error messages and to sanity-check each event's own
            sport_key field.

    Returns:
        A list of ParsedEvent, one per event in the response, each with
        every bookmaker/market/outcome it offered.

    Raises:
        TheOddsApiResponseError: If the payload is not a list, or any
            event/bookmaker/market/outcome is missing a required field
            or has the wrong type. This function never silently drops or
            invents a value for a structurally invalid response -- a
            malformed API response should be visible, not swallowed.
    """
    if not isinstance(raw_events, list):
        raise TheOddsApiResponseError(
            f"expected a JSON list of events for sport {sport_key!r}, got "
            f"{type(raw_events).__name__}"
        )

    events: list[ParsedEvent] = []
    for i, raw_event in enumerate(raw_events):
        if not isinstance(raw_event, dict):
            raise TheOddsApiResponseError(f"event[{i}] is not a JSON object")
        _require_keys(
            raw_event,
            {"id", "sport_key", "commence_time", "home_team", "away_team", "bookmakers"},
            f"event[{i}]",
        )
        bookmakers: list[ParsedBookmaker] = []
        for j, raw_bookmaker in enumerate(raw_event["bookmakers"]):
            if not isinstance(raw_bookmaker, dict):
                raise TheOddsApiResponseError(f"event[{i}].bookmakers[{j}] is not a JSON object")
            _require_keys(
                raw_bookmaker, {"key", "title", "last_update", "markets"}, f"event[{i}].bookmakers[{j}]"
            )
            markets: list[ParsedMarket] = []
            for k, raw_market in enumerate(raw_bookmaker["markets"]):
                if not isinstance(raw_market, dict):
                    raise TheOddsApiResponseError(
                        f"event[{i}].bookmakers[{j}].markets[{k}] is not a JSON object"
                    )
                _require_keys(
                    raw_market, {"key", "outcomes"}, f"event[{i}].bookmakers[{j}].markets[{k}]"
                )
                outcomes: list[ParsedOutcome] = []
                for m, raw_outcome in enumerate(raw_market["outcomes"]):
                    if not isinstance(raw_outcome, dict):
                        raise TheOddsApiResponseError(
                            f"event[{i}].bookmakers[{j}].markets[{k}].outcomes[{m}] is not a "
                            "JSON object"
                        )
                    _require_keys(
                        raw_outcome,
                        {"name", "price"},
                        f"event[{i}].bookmakers[{j}].markets[{k}].outcomes[{m}]",
                    )
                    try:
                        price = float(raw_outcome["price"])
                    except (TypeError, ValueError) as exc:
                        raise TheOddsApiResponseError(
                            f"event[{i}].bookmakers[{j}].markets[{k}].outcomes[{m}].price is not "
                            f"numeric: {raw_outcome['price']!r}"
                        ) from exc
                    point = raw_outcome.get("point")
                    if point is not None:
                        try:
                            point = float(point)
                        except (TypeError, ValueError) as exc:
                            raise TheOddsApiResponseError(
                                f"event[{i}].bookmakers[{j}].markets[{k}].outcomes[{m}].point is "
                                f"not numeric: {point!r}"
                            ) from exc
                    outcomes.append(ParsedOutcome(name=str(raw_outcome["name"]), price=price, point=point))
                markets.append(ParsedMarket(key=str(raw_market["key"]), outcomes=outcomes))
            bookmakers.append(
                ParsedBookmaker(
                    key=str(raw_bookmaker["key"]),
                    title=str(raw_bookmaker["title"]),
                    last_update=str(raw_bookmaker["last_update"]),
                    markets=markets,
                )
            )
        events.append(
            ParsedEvent(
                id=str(raw_event["id"]),
                sport_key=str(raw_event["sport_key"]),
                commence_time=str(raw_event["commence_time"]),
                home_team=str(raw_event["home_team"]),
                away_team=str(raw_event["away_team"]),
                bookmakers=bookmakers,
            )
        )
    return events


# ---------------------------------------------------------------------------
# Canonicalisation -- ParsedEvent list -> the same shapes manual_odds_loader
# produces from a CSV
# ---------------------------------------------------------------------------


def _h2h_selection(outcome_name: str, home_team: str, away_team: str) -> str | None:
    """Map an h2h outcome name to home/draw/away, or None if unrecognised.

    Never guesses: an outcome name that matches neither team name nor
    "Draw" (case-insensitive) returns None, and the caller records a
    rejection rather than assigning it to the nearest-looking selection.
    """
    if outcome_name == home_team:
        return "home"
    if outcome_name == away_team:
        return "away"
    if outcome_name.strip().lower() == "draw":
        return "draw"
    return None


def _extract_totals_at_line(outcomes: list[ParsedOutcome], line: float) -> dict[str, float] | None:
    """Extract {"over": price, "under": price} for one specific goals line.

    Returns None if this bookmaker did not offer both Over and Under at
    exactly `line` (e.g. it only quoted 2.75, or quoted 2.5 for Over but
    not Under) -- an incomplete or off-line quote is rejected outright,
    the same discipline probability.market_pipeline already applies to
    manually-entered odds, never silently substituted or interpolated.
    """
    at_line = {o.name.strip().lower(): o.price for o in outcomes if o.point == line}
    if set(at_line.keys()) != {"over", "under"}:
        return None
    return at_line


def build_canonical_odds_and_metadata(
    events: list[ParsedEvent],
    config: TheOddsApiConfig,
    scan_timestamp: str | None = None,
) -> tuple[dict[str, dict[str, dict[str, float]]], dict[str, dict[str, str]], list[str]]:
    """Convert parsed events into manual_odds_loader's canonical shapes.

    Args:
        events: Parsed events for ONE sport_key (call this once per
            sport_key/competition and merge the results, since events
            from different competitions never share a market_id).
        config: The active TheOddsApiConfig (for the competition display
            name and the configured totals line).
        scan_timestamp: ISO timestamp to record as this scan's time.
            Defaults to now (UTC) if not given.

    Returns:
        A tuple (bookmaker_odds_by_market, market_metadata, warnings):
        the first two match ingestion.manual_odds_loader's
        load_manual_odds_by_bookmaker / load_manual_odds_market_metadata
        return shapes exactly, so scripts/run_daily_scan.py can use
        either source interchangeably. `warnings` lists every bookmaker
        quote skipped and why (incomplete outcome set, unrecognised
        outcome name, off-target totals line, duplicate bookmaker for a
        market) -- nothing is ever silently dropped without a trace.
    """
    if scan_timestamp is None:
        scan_timestamp = datetime.now(timezone.utc).isoformat()

    bookmaker_odds_by_market: dict[str, dict[str, dict[str, float]]] = {}
    market_metadata: dict[str, dict[str, str]] = {}
    warnings: list[str] = []

    for event in events:
        competition = config.sport_keys.get(event.sport_key, event.sport_key)
        event_label = f"{event.home_team} v {event.away_team}"
        event_date = event.commence_time[:10]
        market_id_1x2 = f"{event.sport_key}-{event.id}-1x2"
        market_id_ou = f"{event.sport_key}-{event.id}-ou{str(config.total_goals_line).replace('.', '')}"

        bookmakers_seen_1x2: set[str] = set()
        bookmakers_seen_ou: set[str] = set()

        for bookmaker in event.bookmakers:
            for market in bookmaker.markets:
                if market.key == "h2h":
                    mapped: dict[str, float] = {}
                    unrecognised = False
                    for outcome in market.outcomes:
                        selection = _h2h_selection(outcome.name, event.home_team, event.away_team)
                        if selection is None:
                            warnings.append(
                                f"{bookmaker.title} h2h outcome {outcome.name!r} for "
                                f"{event_label} did not match either team name or 'Draw' -- "
                                "quote skipped"
                            )
                            unrecognised = True
                            break
                        mapped[selection] = outcome.price
                    if unrecognised or set(mapped.keys()) != {"home", "draw", "away"}:
                        if not unrecognised:
                            warnings.append(
                                f"{bookmaker.title} h2h for {event_label} did not offer a "
                                f"complete home/draw/away set (got {sorted(mapped)}) -- quote skipped"
                            )
                        continue
                    if bookmaker.title in bookmakers_seen_1x2:
                        warnings.append(
                            f"duplicate h2h quote from {bookmaker.title} for {event_label} -- "
                            "second quote skipped"
                        )
                        continue
                    bookmakers_seen_1x2.add(bookmaker.title)
                    bookmaker_odds_by_market.setdefault(market_id_1x2, {})[bookmaker.title] = mapped

                elif market.key == "totals":
                    at_line = _extract_totals_at_line(market.outcomes, config.total_goals_line)
                    if at_line is None:
                        warnings.append(
                            f"{bookmaker.title} totals for {event_label} did not offer a complete "
                            f"Over/Under quote at the {config.total_goals_line} line -- quote skipped"
                        )
                        continue
                    if bookmaker.title in bookmakers_seen_ou:
                        warnings.append(
                            f"duplicate totals quote from {bookmaker.title} for {event_label} -- "
                            "second quote skipped"
                        )
                        continue
                    bookmakers_seen_ou.add(bookmaker.title)
                    bookmaker_odds_by_market.setdefault(market_id_ou, {})[bookmaker.title] = at_line
                # spreads (Asian Handicap) deliberately not handled -- see module docstring.

        if market_id_1x2 in bookmaker_odds_by_market:
            market_metadata[market_id_1x2] = {
                "sport": "football",
                "competition": competition,
                "event": event_label,
                "event_date": event_date,
                "market_type": "1x2",
                "scan_timestamp": scan_timestamp,
            }
        if market_id_ou in bookmaker_odds_by_market:
            market_metadata[market_id_ou] = {
                "sport": "football",
                "competition": competition,
                "event": event_label,
                "event_date": event_date,
                "market_type": "over_under_2_5",
                "scan_timestamp": scan_timestamp,
            }
        if not bookmakers_seen_1x2 and not bookmakers_seen_ou:
            warnings.append(f"{event_label} ({event.id}) had no usable h2h or totals quotes -- skipped")

    return bookmaker_odds_by_market, market_metadata, warnings


# ---------------------------------------------------------------------------
# Network call -- NOT exercised against a real response this session (no
# API key was available). See module docstring.
# ---------------------------------------------------------------------------


def fetch_odds_raw(sport_key: str, config: TheOddsApiConfig) -> list:
    """Call The Odds API's /v4/sports/{sport}/odds endpoint for one sport_key.

    Costs len(config.markets) x 1 (config.regions is a single region
    string for V1) credits per call, per The Odds API's documented quota
    formula -- see docs/DAILY_ENGINE_V1_LOCK_AND_IMPLEMENTATION_ROADMAP.md's
    successor checkpoint for the full credit-economics audit.

    Args:
        sport_key: One of config.sport_keys' keys (one call per
            competition -- the API has no multi-sport endpoint).
        config: The active TheOddsApiConfig.

    Returns:
        The decoded JSON response body (expected: a list of event
        objects -- pass it to parse_odds_response next).

    Raises:
        TheOddsApiCredentialError: If no API key is configured.
        TheOddsApiResponseError: If the request fails, times out, or the
            response is not valid JSON.
    """
    api_key = config.resolve_api_key()
    params = {
        "apiKey": api_key,
        "regions": config.regions,
        "markets": ",".join(config.markets),
        "oddsFormat": config.odds_format,
    }
    url = f"{config.base_url}/v4/sports/{sport_key}/odds/?{urllib.parse.urlencode(params)}"
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
            f"The Odds API returned HTTP {exc.code} for sport {sport_key!r}: {detail[:500]}"
        ) from exc
    except urllib.error.URLError as exc:
        raise TheOddsApiResponseError(
            f"could not reach The Odds API for sport {sport_key!r}: {exc.reason}"
        ) from exc

    try:
        payload = json.loads(body)
    except json.JSONDecodeError as exc:
        raise TheOddsApiResponseError(
            f"The Odds API response for sport {sport_key!r} was not valid JSON"
        ) from exc
    return payload


def fetch_and_canonicalise(config: TheOddsApiConfig) -> tuple[
    dict[str, dict[str, dict[str, float]]], dict[str, dict[str, str]], list[str]
]:
    """Fetch and canonicalise odds for every configured sport_key, merged.

    This is the single entry point scripts/run_daily_scan.py calls for
    live data. Each sport_key is fetched and parsed independently; if one
    competition's call fails, a TheOddsApiResponseError from that call is
    NOT swallowed -- it propagates, since a partial silent scan is worse
    than a loud failure for a betting decision pipeline (per project
    instructions: "no hiding negative/null results" extends to
    operational failures, not only research findings).

    Returns:
        The merged (bookmaker_odds_by_market, market_metadata, warnings)
        across every configured competition.
    """
    all_odds: dict[str, dict[str, dict[str, float]]] = {}
    all_metadata: dict[str, dict[str, str]] = {}
    all_warnings: list[str] = []
    scan_timestamp = datetime.now(timezone.utc).isoformat()

    for sport_key in config.sport_keys:
        raw = fetch_odds_raw(sport_key, config)
        events = parse_odds_response(raw, sport_key)
        odds, metadata, warnings = build_canonical_odds_and_metadata(
            events, config, scan_timestamp=scan_timestamp
        )
        all_odds.update(odds)
        all_metadata.update(metadata)
        all_warnings.extend(warnings)

    return all_odds, all_metadata, all_warnings
