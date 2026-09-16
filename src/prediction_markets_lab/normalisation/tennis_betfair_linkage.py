"""Deterministic linkage between TML-Database matches and Betfair
historical Match Odds events/markets (Workstream B, Tennis Cycle 1
market-aware research, per
research/cycles/CYCLE_002_TENNIS/WORKSTREAM_B_MARKET_AWARE_RESEARCH_PROTOCOL.md).

This module answers exactly one question per TML match: which Betfair
event/market (if any) covers the same real-world match? It NEVER
silently guesses -- per project instructions section 9 (no fuzzy
matching applied silently) and the same philosophy already used for
Tennis-data.co.uk name matching in normalisation/player_names.py, every
result is one of MATCHED, AMBIGUOUS, or UNMATCHED, and callers must
handle all three distinctly.

Matching uses two independent signals, both required:
    1. Date proximity: the Betfair event's scheduled open date is
       within `date_tolerance_days` of the TML match's tourney_date
       (matches can be scheduled the day before or after the nominal
       tournament date in different feeds' conventions).
    2. Player-pair identity: the event's two runner names correspond,
       as an unordered pair, to the TML match's two player names, via
       `names_are_equivalent` below.

`names_are_equivalent` tries three known real-world tennis-name
conventions in order (exact full-name match; Tennis-data.co.uk-style
"Surname I." abbreviation, reusing player_names.py's already-tested
logic; and "Surname, First" comma-inverted form) and returns False, not
a guess, if none apply. The real Betfair runner-name convention for
tennis has NOT yet been confirmed against a real downloaded file (see
the protocol doc's audit-first requirement) -- this module is built and
tested against the documented/found sample and synthetic data
reflecting these three conventions, and must be re-validated against
Fraser's real Betfair sample before being trusted on live data, exactly
as player_names.py was built and tested against mocks before ever
touching a real network connection.
"""

from __future__ import annotations

import unicodedata
from dataclasses import dataclass
from datetime import date, timedelta
from typing import Literal, Sequence

from prediction_markets_lab.normalisation.player_names import (
    full_name_matches_abbreviated,
    parse_abbreviated_name,
)

LinkageStatus = Literal["MATCHED", "AMBIGUOUS", "UNMATCHED"]


def _fold(text: str) -> str:
    """Casefold, strip diacritics, and normalise hyphens to spaces for
    tolerant comparison.

    **Real-data discovery (2026-09-16, Fraser's first Betfair BASIC
    sample):** Betfair renders "Felix Auger-Aliassime" as the
    unhyphenated "Felix Auger Aliassime". This was the only name-format
    mismatch found across 137 real ATP matches tested against a real
    Betfair sample (136/137 matched without it; this one player's
    hyphenated surname was the sole miss) -- it is exactly the kind of
    formatting difference the "never silently guess" discipline still
    wants handled explicitly rather than accepted as an unmatched loss,
    since it is a deterministic, unconditional string transform, not a
    fuzzy guess.
    """
    normalised = unicodedata.normalize("NFKD", text)
    without_marks = "".join(ch for ch in normalised if not unicodedata.combining(ch))
    without_hyphens = without_marks.replace("-", " ")
    collapsed = " ".join(without_hyphens.split())
    return collapsed.casefold().strip()


@dataclass(frozen=True)
class TMLMatchRecord:
    """The minimal TML-Database fields needed to look up a Betfair event."""

    match_id: str
    match_date: date
    player_a_name: str
    player_b_name: str


@dataclass(frozen=True)
class BetfairEventCandidate:
    """The minimal Betfair historical-stream fields needed to identify
    an ATP Match Odds market as covering a specific real-world match.

    event_open_date is the scheduled market/event start date (a date,
    not a full timestamp -- the linkage step only needs day-level
    proximity; price-time snapshot alignment is a separate, later step
    per the protocol doc).
    """

    market_id: str
    event_id: str
    event_open_date: date
    runner_names: tuple[str, str]


@dataclass(frozen=True)
class LinkageResult:
    """The outcome of matching one TML match against a set of Betfair
    event candidates. Exactly one of matched_market_id (MATCHED) or
    ambiguous_market_ids (AMBIGUOUS, 2+) is populated; both empty means
    UNMATCHED. Callers must branch on `status`, never assume MATCHED."""

    tml_match_id: str
    status: LinkageStatus
    matched_market_id: str | None
    ambiguous_market_ids: tuple[str, ...]
    candidates_in_date_window: int


def _full_name_equivalent(full_a: str, full_b: str) -> bool:
    return _fold(full_a) == _fold(full_b)


def _comma_inverted_equivalent(full_name: str, comma_form: str) -> bool:
    """"Djokovic, Novak" == "Novak Djokovic" -- a convention seen in
    some exchange/scraped feeds alongside "Surname I." and full-name
    forms. Requires exactly one comma; anything else is not this form."""
    if comma_form.count(",") != 1:
        return False
    surname, _, given = comma_form.partition(",")
    inverted = f"{given.strip()} {surname.strip()}"
    return _full_name_equivalent(full_name, inverted)


def names_are_equivalent(tml_full_name: str, other_name: str) -> bool:
    """True if `other_name` (in any of three known conventions) refers
    to the same player as `tml_full_name` (a TML-Database full name).

    Tries, in order: (1) exact full-name match; (2) Tennis-data.co.uk
    "Surname I." abbreviation (reusing player_names.py, already tested
    against that source's documented convention); (3) "Surname, First"
    comma-inverted form. Returns False -- never a guess -- if none of
    the three apply.
    """
    if _full_name_equivalent(tml_full_name, other_name):
        return True
    try:
        parsed = parse_abbreviated_name(other_name)
    except ValueError:
        pass
    else:
        if full_name_matches_abbreviated(tml_full_name, parsed):
            return True
    if _comma_inverted_equivalent(tml_full_name, other_name):
        return True
    return False


def _runner_pair_matches_players(
    runner_names: tuple[str, str], player_a_name: str, player_b_name: str
) -> bool:
    """True iff the two runner names correspond, as an unordered pair,
    to the two player names -- either assignment direction counts,
    since Betfair's runner order need not match TML's player_a/player_b
    convention (which itself carries no outcome information, per
    Workstream A2)."""
    r1, r2 = runner_names
    direct = names_are_equivalent(player_a_name, r1) and names_are_equivalent(player_b_name, r2)
    swapped = names_are_equivalent(player_a_name, r2) and names_are_equivalent(player_b_name, r1)
    return direct or swapped


def classify_tennis_betfair_match(
    tml_match: TMLMatchRecord,
    betfair_candidates: Sequence[BetfairEventCandidate],
    date_tolerance_days: int = 1,
) -> LinkageResult:
    """Classify a single TML match against a pool of Betfair event
    candidates as MATCHED, AMBIGUOUS, or UNMATCHED.

    Args:
        tml_match: The TML match to link.
        betfair_candidates: Candidate Betfair events to search (in
            real use, callers should narrow this to the relevant
            tournament/date window for performance -- this function
            does not assume any pre-filtering beyond what it does
            itself).
        date_tolerance_days: Maximum absolute difference, in days,
            between tml_match.match_date and a candidate's
            event_open_date to be considered at all.

    Returns:
        A LinkageResult. MATCHED only when exactly one candidate in
        the date window has a runner pair matching both players;
        AMBIGUOUS when two or more do (this is reported, never
        resolved by picking one); UNMATCHED when none do.
    """
    in_window = [
        c for c in betfair_candidates
        if abs((c.event_open_date - tml_match.match_date).days) <= date_tolerance_days
    ]
    matches = [
        c for c in in_window
        if _runner_pair_matches_players(c.runner_names, tml_match.player_a_name, tml_match.player_b_name)
    ]
    unique_market_ids = sorted({c.market_id for c in matches})

    if len(unique_market_ids) == 1:
        return LinkageResult(
            tml_match_id=tml_match.match_id,
            status="MATCHED",
            matched_market_id=unique_market_ids[0],
            ambiguous_market_ids=(),
            candidates_in_date_window=len(in_window),
        )
    if len(unique_market_ids) > 1:
        return LinkageResult(
            tml_match_id=tml_match.match_id,
            status="AMBIGUOUS",
            matched_market_id=None,
            ambiguous_market_ids=tuple(unique_market_ids),
            candidates_in_date_window=len(in_window),
        )
    return LinkageResult(
        tml_match_id=tml_match.match_id,
        status="UNMATCHED",
        matched_market_id=None,
        ambiguous_market_ids=(),
        candidates_in_date_window=len(in_window),
    )


def classify_all(
    tml_matches: Sequence[TMLMatchRecord],
    betfair_candidates: Sequence[BetfairEventCandidate],
    date_tolerance_days: int = 1,
) -> dict[LinkageStatus, list[LinkageResult]]:
    """Classify every TML match, grouped by status, for a coverage report.

    Returns:
        A dict with keys "MATCHED", "AMBIGUOUS", "UNMATCHED", each a
        list of LinkageResult in tml_matches order. A coverage report
        should always print all three counts, per the protocol doc's
        requirement that unmatched/ambiguous rates be reported, not
        just the matched count.
    """
    grouped: dict[LinkageStatus, list[LinkageResult]] = {"MATCHED": [], "AMBIGUOUS": [], "UNMATCHED": []}
    for tml_match in tml_matches:
        result = classify_tennis_betfair_match(tml_match, betfair_candidates, date_tolerance_days)
        grouped[result.status].append(result)
    return grouped
