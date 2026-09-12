"""Tennis player name matching across data sources (Tennis Cycle 2,
Checkpoint 2).

Two source families use two different name conventions and must be
reconciled without silently guessing, per project instructions section 9
(no fuzzy matching applied silently -- team_names.py's explicit alias
table follows the same rule for football's much smaller, fixed team
set). Tennis has thousands of players across decades, so a static alias
table doesn't scale the way it does for football; instead this module
matches structurally (surname + first-initial) and always surfaces an
ambiguous or failed match to the caller rather than picking a guess.

- Tennismylife/TML-Database (github.com/Tennismylife/TML-Database):
  full names, e.g. "Novak Djokovic" (the same convention Jeff
  Sackmann's original tennis_atp repo used).
- Tennis-data.co.uk: abbreviated "Surname I." strings, e.g.
  "Djokovic N." -- a long-established, widely-documented convention in
  public tennis-betting-data circles, but NOT yet verified against a
  real downloaded file in this environment (Tennis-data.co.uk has
  failed every automated fetch attempt so far -- see
  research/cycles/CYCLE_002_TENNIS/PLAN.md). This module is built to
  the documented convention and tested with synthetic data reflecting
  it; the real convention (multi-part surnames, accented characters,
  double initials for compound first names, etc.) must be confirmed
  against Checkpoint 1's actual acquired odds files before this module
  is trusted on live data, exactly as tennis_data_loader.py's HTTP
  primitives were built and tested against mocks before ever touching
  a real network connection.

Matching rule: a full name "matches" an abbreviated "Surname I." string
if the full name ends with the surname (case/diacritic-insensitive,
so multi-word surnames like "del Potro" or hyphenated ones like
"Auger-Aliassime" work without special-casing) AND the remaining
prefix's first letter equals the initial. When more than one candidate
full name matches, or none do, the result says so explicitly --
disambiguation by tournament/date/round (per
research/cycles/CYCLE_002_TENNIS/PLAN.md section 4) is Checkpoint 2's
job, using real match-level context this module deliberately does not
have.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from typing import Sequence

_ABBREVIATED_NAME_PATTERN = re.compile(r"^(?P<surname>.+?)\s+(?P<initial>[A-Za-z])\.?\s*$")


def _fold(text: str) -> str:
    """Casefold and strip diacritics for tolerant comparison (so
    "Djokovic" matches "Djoković", "Cilic" matches "Čilić", etc.) --
    tennis player names routinely appear both ways across sources."""
    normalised = unicodedata.normalize("NFKD", text)
    without_marks = "".join(ch for ch in normalised if not unicodedata.combining(ch))
    return without_marks.casefold().strip()


@dataclass(frozen=True)
class ParsedAbbreviatedName:
    """A Tennis-data.co.uk "Surname I." string, split into parts."""

    surname: str
    initial: str
    raw: str


def parse_abbreviated_name(name: str) -> ParsedAbbreviatedName:
    """Parse a Tennis-data.co.uk-style abbreviated name, e.g. "Djokovic N."
    or "Del Potro J" (the trailing "." is optional).

    Args:
        name: The abbreviated name string as it appears in the source.

    Returns:
        A ParsedAbbreviatedName with the surname and initial split out.

    Raises:
        ValueError: If `name` does not look like "Surname I[.]" at all
            (loud failure rather than a silent, possibly wrong, guess).
    """
    stripped = name.strip()
    match = _ABBREVIATED_NAME_PATTERN.match(stripped)
    if match is None:
        raise ValueError(
            f"{name!r} does not look like a 'Surname I.' abbreviated tennis "
            "name -- refusing to guess"
        )
    return ParsedAbbreviatedName(
        surname=match.group("surname").strip(),
        initial=match.group("initial").upper(),
        raw=name,
    )


def full_name_matches_abbreviated(full_name: str, parsed: ParsedAbbreviatedName) -> bool:
    """True if `full_name` (e.g. "Novak Djokovic") is structurally
    consistent with `parsed` (surname + first initial).

    Args:
        full_name: A full "First [Middle] Last" name, e.g. from
            TML-Database's winner_name/loser_name columns.
        parsed: The abbreviated name to compare against.

    Returns:
        True if the folded full name ends with the folded surname and
        the character immediately before that (the first letter of
        whatever precedes the surname) equals the initial. A full name
        that IS just the surname with nothing before it (no first-name
        information to check) never matches -- that would be
        indistinguishable from a coincidental substring match.
    """
    folded_full = _fold(full_name)
    folded_surname = _fold(parsed.surname)
    if not folded_full.endswith(folded_surname):
        return False
    prefix = folded_full[: len(folded_full) - len(folded_surname)].rstrip()
    if not prefix:
        return False
    return prefix[0] == parsed.initial.casefold()


@dataclass(frozen=True)
class NameMatchResult:
    """Outcome of matching one abbreviated name against a set of
    candidate full names."""

    abbreviated_raw: str
    matched_full_name: str | None
    candidates_considered: tuple[str, ...]
    ambiguous_matches: tuple[str, ...]

    @property
    def is_unique_match(self) -> bool:
        return self.matched_full_name is not None

    @property
    def is_ambiguous(self) -> bool:
        return len(self.ambiguous_matches) > 1

    @property
    def is_unmatched(self) -> bool:
        return self.matched_full_name is None and len(self.ambiguous_matches) == 0


def match_abbreviated_name_to_candidates(
    abbreviated: str, candidate_full_names: Sequence[str]
) -> NameMatchResult:
    """Match one Tennis-data.co.uk abbreviated name against a list of
    candidate TML-Database full names, never guessing when more than
    one candidate is structurally consistent.

    Args:
        abbreviated: The "Surname I." string to resolve.
        candidate_full_names: Full names to check against -- in real
            use, callers should narrow this to players who plausibly
            played the specific tournament/date/round in question
            (see research/cycles/CYCLE_002_TENNIS/PLAN.md section 4),
            not the entire multi-decade player pool, both for
            performance and because a narrower candidate set is itself
            part of how collisions get disambiguated.

    Returns:
        A NameMatchResult. Exactly one of matched_full_name (a unique
        match) or ambiguous_matches (two or more consistent candidates)
        is populated; both are empty/None if no candidate matches at
        all -- callers must treat all three outcomes as distinct and
        must not fall back to guessing on ambiguous or unmatched cases.

    Raises:
        ValueError: If `abbreviated` does not parse (see
            parse_abbreviated_name).
    """
    parsed = parse_abbreviated_name(abbreviated)
    matches = [
        candidate
        for candidate in candidate_full_names
        if full_name_matches_abbreviated(candidate, parsed)
    ]
    unique_matches = sorted(set(matches))

    if len(unique_matches) == 1:
        return NameMatchResult(
            abbreviated_raw=abbreviated,
            matched_full_name=unique_matches[0],
            candidates_considered=tuple(candidate_full_names),
            ambiguous_matches=(),
        )
    return NameMatchResult(
        abbreviated_raw=abbreviated,
        matched_full_name=None,
        candidates_considered=tuple(candidate_full_names),
        ambiguous_matches=tuple(unique_matches),
    )
