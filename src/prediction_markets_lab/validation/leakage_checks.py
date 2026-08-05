"""Generic data-leakage guards, usable by any future rolling-feature or
rating-update code (e.g. the Elo model planned for Stage 3B).

This module deliberately does not implement Elo/Poisson itself (out of
scope for Stage 3A per project instructions section 20) -- it provides
the reusable checks that any such future model must pass, so leakage
prevention is enforced once, centrally, rather than re-implemented
(and potentially forgotten) inside each model.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True)
class DatedRecord:
    """A minimal (id, date) pair for chronological-order checking."""

    record_id: str
    record_date: date


def check_chronological_order(records: list[DatedRecord]) -> list[str]:
    """Check that a sequence of records is in non-decreasing date order.

    Args:
        records: The records in the order they would be processed
            (e.g. fed into a rolling rating update).

    Returns:
        A list of human-readable violation messages. Empty if the
        sequence is fully chronological.
    """
    violations = []
    for i in range(1, len(records)):
        if records[i].record_date < records[i - 1].record_date:
            violations.append(
                f"record {records[i].record_id!r} (date {records[i].record_date}) "
                f"appears after {records[i - 1].record_id!r} (date {records[i - 1].record_date}) "
                "-- out of chronological order"
            )
    return violations


def check_rolling_window_uses_only_past_data(
    as_of_date: date, window_record_dates: list[date]
) -> list[str]:
    """Check that every date feeding a rolling window is strictly before as_of_date.

    Args:
        as_of_date: The date a feature/rating is being computed for
            (i.e. the date of the match being predicted).
        window_record_dates: The dates of the historical records used
            to compute the rolling feature/rating.

    Returns:
        A list of violation messages, one per record dated on or after
        as_of_date (which would leak future information into a
        pre-match feature). Empty if clean.
    """
    return [
        f"record dated {d} is not strictly before as_of_date {as_of_date} -- "
        "this would leak future information into a pre-match feature"
        for d in window_record_dates
        if d >= as_of_date
    ]


def check_no_test_period_in_development(
    development_dates: list[date], test_period_start: date
) -> list[str]:
    """Check that no development-phase record falls within the test period.

    Args:
        development_dates: Dates of every record used during model
            fitting, threshold tuning, or hypothesis refinement.
        test_period_start: The first date of the frozen final test
            period.

    Returns:
        A list of violation messages for any development record dated
        on or after test_period_start.
    """
    return [
        f"development record dated {d} falls on/after the frozen test "
        f"period start ({test_period_start}) -- test period has been touched"
        for d in development_dates
        if d >= test_period_start
    ]
