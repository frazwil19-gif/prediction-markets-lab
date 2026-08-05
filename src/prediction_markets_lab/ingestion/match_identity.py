"""Deterministic match identity and duplicate classification.

A match_id is derived from stable, meaningful fields so the same
fixture always gets the same ID across re-downloads, rather than a
row number or hash of the whole row (which would change if a
bookmaker's odds were corrected upstream).
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from enum import Enum


def build_match_id(
    competition_code: str, season: str, match_date: str, home_team_normalised: str, away_team_normalised: str
) -> str:
    """Build a deterministic match ID.

    Args:
        competition_code: e.g. "E0".
        season: Human-readable season, e.g. "2024_25".
        match_date: ISO date string, e.g. "2024-08-16".
        home_team_normalised: Canonical home team name.
        away_team_normalised: Canonical away team name.

    Returns:
        A short, deterministic, collision-resistant ID (first 16 hex
        chars of a SHA-256 digest of the concatenated fields).
    """
    key = f"{competition_code}|{season}|{match_date}|{home_team_normalised}|{away_team_normalised}"
    return hashlib.sha256(key.encode("utf-8")).hexdigest()[:16]


class DuplicateClassification(str, Enum):
    EXACT_DUPLICATE = "EXACT_DUPLICATE"
    CONFLICTING_DUPLICATE = "CONFLICTING_DUPLICATE"
    POSSIBLE_RESCHEDULE = "POSSIBLE_RESCHEDULE"
    DISTINCT_FIXTURE = "DISTINCT_FIXTURE"
    MANUAL_REVIEW = "MANUAL_REVIEW"


@dataclass(frozen=True)
class MatchRow:
    """The minimal fields needed to classify two candidate-duplicate rows."""

    match_id: str
    match_date: str
    home_team_normalised: str
    away_team_normalised: str
    full_time_home_goals: int | None
    full_time_away_goals: int | None
    raw_row_hash: str


def classify_duplicate(a: MatchRow, b: MatchRow) -> DuplicateClassification:
    """Classify a pair of rows that share the same match_id.

    Args:
        a: The first row.
        b: The second row (assumed to share a.match_id).

    Returns:
        A DuplicateClassification. Never silently discards either row
        -- callers must record the classification and keep both rows
        for manual review where the classification is anything other
        than EXACT_DUPLICATE.
    """
    if a.match_id != b.match_id:
        # Same date/teams but somehow different IDs shouldn't happen if
        # callers group by match_id first; treat defensively.
        return DuplicateClassification.MANUAL_REVIEW

    if a.raw_row_hash == b.raw_row_hash:
        return DuplicateClassification.EXACT_DUPLICATE

    if (
        a.full_time_home_goals is not None
        and a.full_time_away_goals is not None
        and b.full_time_home_goals is not None
        and b.full_time_away_goals is not None
        and (a.full_time_home_goals, a.full_time_away_goals) != (b.full_time_home_goals, b.full_time_away_goals)
    ):
        return DuplicateClassification.CONFLICTING_DUPLICATE

    if a.match_date != b.match_date:
        return DuplicateClassification.POSSIBLE_RESCHEDULE

    # Same match_id, same date, same result, but different raw content
    # (e.g. odds differ) -- needs a human to decide which row is
    # authoritative rather than the pipeline guessing.
    return DuplicateClassification.MANUAL_REVIEW
