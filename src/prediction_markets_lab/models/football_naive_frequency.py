"""Naive leakage-safe historical-frequency baseline (Stage 3B BASELINE 0).

For each match, estimates P(home)/P(draw)/P(away) purely from the
expanding, strictly-prior history of matches in the same competition
-- no bookmaker data, no Elo/Poisson modelling. Purpose: a sanity
floor. If Elo/Poisson/blend cannot meaningfully improve on this,
something is wrong with those models or they contain very little
signal (see research/cycles/CYCLE_001/STAGE_3B_PLAN.md, Baseline 0).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from prediction_markets_lab.validation.leakage_checks import (
    DatedRecord,
    check_chronological_order,
)

RESULT_TO_OUTCOME = {"H": "home", "D": "draw", "A": "away"}


@dataclass(frozen=True)
class NaiveFrequencyMatchInput:
    """One match's minimal inputs for the naive baseline."""

    match_id: str
    competition_code: str
    match_date: date
    full_time_result: str  # "H", "D", or "A"


@dataclass(frozen=True)
class NaiveFrequencyPrediction:
    match_id: str
    p_home: float
    p_draw: float
    p_away: float
    n_prior_matches: int  # how many strictly-earlier same-competition matches informed this prediction


def compute_naive_frequency_predictions(
    matches: list[NaiveFrequencyMatchInput], laplace_alpha: float = 1.0
) -> list[NaiveFrequencyPrediction]:
    """Compute expanding-window naive frequency predictions.

    Args:
        matches: matches for ONE walk-forward fold's training+evaluation
            span, already sorted chronologically (ties broken by the
            caller in a stable, documented way). This function verifies
            the ordering itself and raises rather than silently
            re-sorting, so a caller bug cannot silently produce a
            leakage-unsafe result.
        laplace_alpha: additive (Laplace) smoothing per outcome, so the
            very first matches of a competition's history -- before any
            prior result exists -- get a well-defined, non-degenerate
            prediction instead of a 0/0 division. Default 1.0 (add-one
            smoothing), deliberately simple per project instructions
            (avoid overfitting a 5,800-row dataset with an elaborate
            prior).

    Returns:
        One NaiveFrequencyPrediction per input match, same order.

    Raises:
        ValueError: if matches is empty, not in chronological order, or
            contains a full_time_result other than "H"/"D"/"A".
    """
    if not matches:
        raise ValueError("cannot compute naive frequency predictions over zero matches")

    order_violations = check_chronological_order(
        [DatedRecord(m.match_id, m.match_date) for m in matches]
    )
    if order_violations:
        raise ValueError(
            "matches must be pre-sorted chronologically -- naive frequency counts are "
            f"updated in input order and cannot be leakage-safe otherwise: {order_violations[0]}"
        )

    counts: dict[str, dict[str, int]] = {}
    predictions: list[NaiveFrequencyPrediction] = []

    for m in matches:
        if m.full_time_result not in RESULT_TO_OUTCOME:
            raise ValueError(
                f"match {m.match_id!r} has invalid full_time_result {m.full_time_result!r}, "
                "must be 'H', 'D', or 'A'"
            )

        c = counts.setdefault(m.competition_code, {"H": 0, "D": 0, "A": 0})
        n_prior = c["H"] + c["D"] + c["A"]
        denom = n_prior + 3 * laplace_alpha

        predictions.append(
            NaiveFrequencyPrediction(
                match_id=m.match_id,
                p_home=(c["H"] + laplace_alpha) / denom,
                p_draw=(c["D"] + laplace_alpha) / denom,
                p_away=(c["A"] + laplace_alpha) / denom,
                n_prior_matches=n_prior,
            )
        )

        # Only now -- after this match's prediction has been recorded --
        # does its own result become visible to future matches.
        c[m.full_time_result] += 1

    return predictions
