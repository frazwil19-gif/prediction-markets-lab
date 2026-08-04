"""Date and timestamp helpers for manual data entry.

All timestamps in this project are stored as timezone-aware UTC ISO
8601 strings, so that manually entered prices, opinions and results
always carry an unambiguous, comparable timestamp (project
instructions section 7: "all manually entered information must retain
its source and timestamp where practical").
"""

from __future__ import annotations

from datetime import datetime, timezone


def now_utc_iso() -> str:
    """Return the current UTC time as an ISO 8601 string.

    Returns:
        A string like "2026-08-03T14:05:00+00:00".
    """
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def parse_iso_timestamp(value: str) -> datetime:
    """Parse an ISO 8601 timestamp string into a timezone-aware datetime.

    Args:
        value: An ISO 8601 timestamp string, e.g. "2026-08-03T14:05:00+00:00".

    Returns:
        A timezone-aware datetime object. Naive strings (no offset) are
        assumed to be UTC.

    Raises:
        ValueError: If value cannot be parsed as an ISO 8601 timestamp.
    """
    dt = datetime.fromisoformat(value)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


def is_stale(timestamp: str, max_age_seconds: float, reference: datetime | None = None) -> bool:
    """Check whether a timestamp is older than a maximum allowed age.

    Used to enforce the "exchange price is no longer current" safety
    gate (project instructions section 21) before grading an
    opportunity.

    Args:
        timestamp: ISO 8601 timestamp string when the price/data was
            captured.
        max_age_seconds: Maximum allowed age, in seconds.
        reference: The "now" to compare against. Defaults to the
            current UTC time; pass an explicit value in tests for
            determinism.

    Returns:
        True if the timestamp is older than max_age_seconds.
    """
    parsed = parse_iso_timestamp(timestamp)
    now = reference if reference is not None else datetime.now(timezone.utc)
    age_seconds = (now - parsed).total_seconds()
    return age_seconds > max_age_seconds
