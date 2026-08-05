"""Chronological train/validation/test split helpers.

Implements docs/DATA_LEAKAGE_RULES.md: splits must be assigned by date
ranges fixed in advance, never by random shuffling, and the final test
period must remain untouched during model/threshold development.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True)
class DateRange:
    """An inclusive date range for one split."""

    start: date
    end: date

    def contains(self, d: date) -> bool:
        return self.start <= d <= self.end


@dataclass(frozen=True)
class SplitPlan:
    """A named, ordered set of non-overlapping chronological date ranges."""

    training: DateRange
    validation: DateRange
    test: DateRange

    def __post_init__(self) -> None:
        if self.training.end >= self.validation.start:
            raise ValueError("training range must end strictly before validation range starts")
        if self.validation.end >= self.test.start:
            raise ValueError("validation range must end strictly before test range starts")


def assign_split(match_date: date, plan: SplitPlan) -> str | None:
    """Assign a single match date to training/validation/test.

    Args:
        match_date: The match's date.
        plan: The fixed SplitPlan.

    Returns:
        "training", "validation", or "test", or None if match_date
        falls outside all three ranges (e.g. a gap, or a date before/
        after the whole plan) -- callers must exclude such rows from
        any modelling analysis rather than guessing a split.
    """
    if plan.training.contains(match_date):
        return "training"
    if plan.validation.contains(match_date):
        return "validation"
    if plan.test.contains(match_date):
        return "test"
    return None


def validate_test_period_untouched(plan: SplitPlan, latest_date_used_in_development: date) -> bool:
    """Check that no development activity has touched the test period.

    Args:
        plan: The fixed SplitPlan.
        latest_date_used_in_development: The most recent match date
            that has been used so far for any model fitting, threshold
            tuning, or hypothesis refinement.

    Returns:
        True if latest_date_used_in_development falls strictly before
        the test period begins (i.e. the test period is still
        untouched). False otherwise -- this must halt further test-set
        use.
    """
    return latest_date_used_in_development < plan.test.start
