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


@dataclass(frozen=True)
class WalkForwardFold:
    """One expanding-window walk-forward development fold.

    Season labels only (e.g. "2020_21"), not dates -- competitions
    within the same nominal season run slightly different actual date
    ranges (see research/cycles/CYCLE_001/STAGE_3B_PLAN.md), so the
    season label is the ground-truth partition already used throughout
    the data pipeline (config/cycle_001_data.yaml, cycle_001_matches_full.csv's
    'season' column), not a derived date boundary.
    """

    fold_id: str
    train_seasons: tuple[str, ...]
    evaluate_season: str


def generate_expanding_walk_forward_folds(seasons_in_order: list[str]) -> list[WalkForwardFold]:
    """Build expanding-window walk-forward folds from ordered season labels.

    Fold i trains on seasons[0..i] and evaluates on seasons[i+1] --
    e.g. for ["2020_21", "2021_22", "2022_23", "2023_24"] this produces
    3 folds: train on 2020_21 -> eval 2021_22; train on 2020_21+2021_22
    -> eval 2022_23; train on 2020_21+2021_22+2022_23 -> eval 2023_24.

    Args:
        seasons_in_order: season labels in genuine chronological order,
            oldest first (not verified against real dates here -- the
            caller is responsible for passing them in true order; see
            leakage_checks.check_chronological_order for verifying
            individual match dates within a season).

    Returns:
        One WalkForwardFold per evaluation season (len(seasons_in_order) - 1
        folds in total).

    Raises:
        ValueError: if fewer than 2 seasons are given, or a season
            label is repeated.
    """
    if len(seasons_in_order) < 2:
        raise ValueError("need at least 2 seasons to form a walk-forward fold")
    if len(seasons_in_order) != len(set(seasons_in_order)):
        raise ValueError(f"seasons_in_order must not contain duplicates: {seasons_in_order}")

    folds = []
    for i in range(len(seasons_in_order) - 1):
        train_seasons = tuple(seasons_in_order[: i + 1])
        evaluate_season = seasons_in_order[i + 1]
        folds.append(
            WalkForwardFold(
                fold_id=f"train_through_{train_seasons[-1]}_eval_{evaluate_season}",
                train_seasons=train_seasons,
                evaluate_season=evaluate_season,
            )
        )
    return folds
