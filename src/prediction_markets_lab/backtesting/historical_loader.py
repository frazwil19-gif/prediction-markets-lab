"""Load Cycle 1 historical 1X2 data into the shape the replay harness needs.

See research/backtesting/BACKTEST_DATA_FEASIBILITY_AUDIT.md (sections 2-3)
and LEAKAGE_AUDIT.md for the full reasoning this module implements:

  - Only cycle_001_matches_full.csv / cycle_001_bookmaker_markets_full.csv
    are read (1X2 only -- Over/Under 2.5 and Asian Handicap do not have
    enough independent bookmakers in this repository to clear the
    production data-quality floor; see the feasibility audit).
  - Exactly one price_timing ("opening" or "closing") is used for BOTH
    the consensus and the best-price side of every candidate in a single
    run -- never mixed (leakage audit, "explicitly excluded" section).
  - Kickoff date/time is recovered by joining back to the raw
    football-data.co.uk file for that (competition, season) -- this is
    NOT present in any existing processed table (feasibility audit
    section 3) and is computed fresh here, every run, from real raw
    data (never fabricated).
  - eligible_consensus_model == False rows are excluded, not
    force-included (matches docs/DATA_DICTIONARY.md's flagging
    convention).
"""

from __future__ import annotations

import csv
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
CYCLE_001_MATCHES = REPO_ROOT / "data" / "processed" / "football" / "cycle_001_matches_full.csv"
CYCLE_001_BOOKMAKER_MARKETS = (
    REPO_ROOT / "data" / "processed" / "football" / "cycle_001_bookmaker_markets_full.csv"
)
RAW_DATA_ROOT = REPO_ROOT / "data" / "raw" / "football" / "football_data_co_uk"

# The simulated scan is assumed to happen this long before the recovered
# kickoff timestamp. This is a declared modelling constant, not a
# historical fact -- see BACKTEST_DATA_FEASIBILITY_AUDIT.md section 5 for
# why this makes the money-event-horizon gate trivially always pass in
# this proxy, and why that is disclosed rather than hidden.
SIMULATED_SCAN_OFFSET_BEFORE_KICKOFF = timedelta(minutes=60)

# football-data.co.uk kickoff times are treated as UK local civil time,
# converted to UTC via the IANA tz database (correctly handles the
# GMT/BST boundary per calendar date). Documented as an assumption, not a
# verified fact -- see the feasibility audit section 1.
_UK_TZ = ZoneInfo("Europe/London")

VALID_PRICE_TIMINGS = ("opening", "closing")


@dataclass(frozen=True)
class HistoricalMatch:
    """One historical match, ready for the replay harness.

    bookmaker_odds is keyed by bookmaker name -> {"home":.., "draw":..,
    "away":..} decimal odds, drawn from a SINGLE price_timing only (see
    module docstring). kickoff_iso is None when the raw-file join could
    not resolve a kickoff time for this match (excluded from money
    qualification by the same rule live production applies to any
    candidate with an unknown kickoff).
    """

    match_id: str
    competition_code: str
    competition_name: str
    season: str
    match_date: str  # ISO date, e.g. "2020-09-12"
    home_team_raw: str
    away_team_raw: str
    full_time_result: str  # "H" | "D" | "A"
    bookmaker_odds: dict[str, dict[str, float]]
    kickoff_iso: str | None
    kickoff_join_failure_reason: str | None


@dataclass(frozen=True)
class LoadReport:
    """Coverage/exclusion accounting for one load, so sample size is
    never silently hidden (governing instruction's data-quality/coverage
    requirement)."""

    total_rows_in_matches_file: int
    excluded_ineligible_consensus_model: int
    excluded_missing_complete_bookmaker_panel: int
    excluded_kickoff_join_failed: int
    included: int


_OUTCOME_TO_RESULT_LETTER = {"home": "H", "draw": "D", "away": "A"}


def _competition_dir_name(competition_code: str) -> str:
    # Raw directories are named exactly by competition_code (E0/E1/SC0).
    return competition_code


def _ddmmyyyy(iso_date: str) -> str:
    y, m, d = iso_date.split("-")
    return f"{d}/{m}/{y}"


def _load_raw_kickoff_lookup(competition_code: str, season: str) -> dict[tuple[str, str, str], str]:
    """Build {(DD/MM/YYYY, home, away): "HH:MM"} for one raw season file.

    Returns an empty dict (not an exception) if the raw file cannot be
    found -- the caller records this as a per-match join failure rather
    than aborting the whole load, matching the "never silently discard,
    always report why" convention used throughout this project.
    """
    raw_path = RAW_DATA_ROOT / _competition_dir_name(competition_code) / season / f"{competition_code}.csv"
    lookup: dict[tuple[str, str, str], str] = {}
    if not raw_path.exists():
        return lookup
    with open(raw_path, encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            date = row.get("Date", "")
            time = row.get("Time", "")
            home = row.get("HomeTeam", "")
            away = row.get("AwayTeam", "")
            if date and home and away:
                lookup[(date, home, away)] = time
    return lookup


def _kickoff_iso_from_raw(
    match_date_iso: str, home_team_raw: str, away_team_raw: str, raw_lookup: dict
) -> tuple[str | None, str | None]:
    """Resolve one match's kickoff ISO timestamp (UTC) from the raw lookup.

    Returns (kickoff_iso, failure_reason) -- exactly one is None.
    """
    key = (_ddmmyyyy(match_date_iso), home_team_raw, away_team_raw)
    time_str = raw_lookup.get(key)
    if not time_str:
        return None, f"no raw (Date, HomeTeam, AwayTeam) match for key {key!r}"
    try:
        hour, minute = (int(x) for x in time_str.split(":")[:2])
    except (ValueError, IndexError):
        return None, f"unparseable raw Time value {time_str!r} for key {key!r}"
    year, month, day = (int(x) for x in match_date_iso.split("-"))
    local_dt = datetime(year, month, day, hour, minute, tzinfo=_UK_TZ)
    utc_dt = local_dt.astimezone(timezone.utc)
    return utc_dt.isoformat(), None


def load_matches_for_replay(price_timing: str) -> tuple[list[HistoricalMatch], LoadReport]:
    """Load every eligible Cycle 1 1X2 match, with one bookmaker odds
    panel (single price_timing) and a best-effort recovered kickoff time.

    Args:
        price_timing: "opening" or "closing" -- selects which snapshot's
            bookmaker odds populate every match's bookmaker_odds. Never
            both in the same call (see module docstring).

    Returns:
        (matches, report). matches is NOT necessarily sorted by date --
        callers that need chronological order (the replay harness does)
        must sort explicitly, per this project's convention of never
        silently assuming an input file's row order is meaningful.

    Raises:
        ValueError: if price_timing is not "opening" or "closing".
    """
    if price_timing not in VALID_PRICE_TIMINGS:
        raise ValueError(f"price_timing must be one of {VALID_PRICE_TIMINGS}, got {price_timing!r}")

    with open(CYCLE_001_MATCHES, newline="") as f:
        match_rows = list(csv.DictReader(f))

    # bookmaker_odds_by_match[match_id][bookmaker] = {"home":.., "draw":.., "away":..}
    bookmaker_odds_by_match: dict[str, dict[str, dict[str, float]]] = {}
    with open(CYCLE_001_BOOKMAKER_MARKETS, newline="") as f:
        for row in csv.DictReader(f):
            if row["price_timing"] != price_timing:
                continue
            match_id = row["match_id"]
            bookmaker_odds_by_match.setdefault(match_id, {})[row["bookmaker"]] = {
                "home": float(row["home_odds"]),
                "draw": float(row["draw_odds"]),
                "away": float(row["away_odds"]),
            }

    raw_kickoff_lookup_cache: dict[tuple[str, str], dict] = {}

    matches: list[HistoricalMatch] = []
    excluded_ineligible = 0
    excluded_missing_panel = 0
    excluded_kickoff_join_failed = 0

    for row in match_rows:
        if row["eligible_consensus_model"] != "True":
            excluded_ineligible += 1
            continue

        odds = bookmaker_odds_by_match.get(row["match_id"])
        if not odds:
            excluded_missing_panel += 1
            continue

        cache_key = (row["competition_code"], row["season"])
        if cache_key not in raw_kickoff_lookup_cache:
            raw_kickoff_lookup_cache[cache_key] = _load_raw_kickoff_lookup(*cache_key)
        kickoff_iso, failure_reason = _kickoff_iso_from_raw(
            row["match_date"], row["home_team_raw"], row["away_team_raw"], raw_kickoff_lookup_cache[cache_key]
        )
        if kickoff_iso is None:
            excluded_kickoff_join_failed += 1

        matches.append(
            HistoricalMatch(
                match_id=row["match_id"],
                competition_code=row["competition_code"],
                competition_name=row["competition_name"],
                season=row["season"],
                match_date=row["match_date"],
                home_team_raw=row["home_team_raw"],
                away_team_raw=row["away_team_raw"],
                full_time_result=row["full_time_result"],
                bookmaker_odds=odds,
                kickoff_iso=kickoff_iso,
                kickoff_join_failure_reason=failure_reason,
            )
        )

    report = LoadReport(
        total_rows_in_matches_file=len(match_rows),
        excluded_ineligible_consensus_model=excluded_ineligible,
        excluded_missing_complete_bookmaker_panel=excluded_missing_panel,
        excluded_kickoff_join_failed=excluded_kickoff_join_failed,
        included=len(matches),
    )
    return matches, report


def simulated_scan_timestamp_iso(match: HistoricalMatch) -> str | None:
    """The simulated scan timestamp for one match: kickoff minus the
    fixed, documented offset (see SIMULATED_SCAN_OFFSET_BEFORE_KICKOFF).

    Returns None if this match has no recovered kickoff time -- a
    candidate with no kickoff time gets no scan timestamp either, and
    will fail the money-event-horizon check for exactly that reason (an
    unverifiable kickoff), matching live production's own rule.
    """
    if match.kickoff_iso is None:
        return None
    kickoff_dt = datetime.fromisoformat(match.kickoff_iso)
    scan_dt = kickoff_dt - SIMULATED_SCAN_OFFSET_BEFORE_KICKOFF
    return scan_dt.astimezone(timezone.utc).isoformat()


def actual_result_letter_matches(selection: str, full_time_result: str) -> bool:
    """Whether `selection` ("home"/"draw"/"away") is the realised outcome."""
    return _OUTCOME_TO_RESULT_LETTER[selection] == full_time_result
