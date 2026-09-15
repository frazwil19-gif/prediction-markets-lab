"""Ranking-only baseline model for tennis Match Winner prediction
(Workstream A4, Cycle 2, baseline A).

The zero-th baseline in the approved A4 sequence (A. ranking baseline ->
B. global Elo -> C. surface Elo -> D. incremental feature models): before
building any custom rating system, check how well the ATP's OWN
player-strength measure -- ranking points, already computed by the tour
every week -- predicts Match Winner on its own. If global/surface Elo
cannot beat this, something is wrong with those models; if they can beat
it, that is only the first hint they carry information beyond what the
tour's own ranking process already captures (the actual A4 comparison
this cycle needs). This is a modelling sanity floor, not a market
comparison -- no price data of any kind is used here or anywhere else in
Cycle 2 so far, so every result from this module is PREDICTIVE
PERFORMANCE ONLY -- NO BETTING EDGE ESTABLISHED.

Feature construction: ATP ranking POINTS (not ordinal rank position) are
used, log-transformed. Points are the tour's actual strength measure;
ordinal rank compresses huge points gaps at the top of the ranking (rank 1
vs rank 2 can be an enormous points gap) and expands tiny ones further
down (rank 301 vs 302 is usually a handful of points) onto the same
linear 1-2-3 scale, which does not reflect either fact. The single
feature fed to logistic regression is
log(player_a_rank_points) - log(player_b_rank_points).

Missing ranking points (player_a_rank_missing / player_b_rank_missing in
the canonical data -- unranked players, mostly qualifiers/wildcards) are
EXCLUDED, never imputed, matching Workstream A2's canonicalisation policy
(see canonicalise_cycle_002_tennis_match_data.py: "never imputes missing
rank"). fit_ranking_baseline and predict_ranking_baseline both raise if
handed a match with missing/non-positive ranking points -- callers must
filter with has_usable_ranking() first, so an unranked-player match can
never silently get an invented feature value.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from math import log

import numpy as np

from prediction_markets_lab.models.logistic_regression import (
    FittedLogisticModel,
    fit_logistic_regression,
)

FEATURE_NAME = "log_rank_points_ratio"


@dataclass(frozen=True)
class RankingBaselineMatchInput:
    match_id: str
    match_date: date
    player_a_rank_points: float | None
    player_b_rank_points: float | None
    outcome_a_won: int  # 1 or 0


@dataclass(frozen=True)
class RankingBaselinePrediction:
    match_id: str
    p_a_win: float


def has_usable_ranking(match: RankingBaselineMatchInput) -> bool:
    """True if both players have a known, positive ranking-points value --
    i.e. this match can be fed to the ranking baseline at all. A match
    with missing or non-positive ranking points (an unranked player) must
    be excluded upstream rather than imputed -- see module docstring."""
    return (
        match.player_a_rank_points is not None
        and match.player_b_rank_points is not None
        and not (isinstance(match.player_a_rank_points, float) and np.isnan(match.player_a_rank_points))
        and not (isinstance(match.player_b_rank_points, float) and np.isnan(match.player_b_rank_points))
        and match.player_a_rank_points > 0
        and match.player_b_rank_points > 0
    )


def _log_rank_points_ratio(a_points: float, b_points: float) -> float:
    return log(a_points) - log(b_points)


def _require_usable(matches: list[RankingBaselineMatchInput]) -> None:
    unusable = [m.match_id for m in matches if not has_usable_ranking(m)]
    if unusable:
        preview = unusable[:5]
        suffix = " ..." if len(unusable) > 5 else ""
        raise ValueError(
            "matches contains entries with missing/non-positive ranking points -- "
            f"filter with has_usable_ranking() first: {preview}{suffix}"
        )


def _feature_matrix(matches: list[RankingBaselineMatchInput]) -> np.ndarray:
    return np.array(
        [[_log_rank_points_ratio(m.player_a_rank_points, m.player_b_rank_points)] for m in matches]
    )


def fit_ranking_baseline(
    training_matches: list[RankingBaselineMatchInput], l2_penalty: float = 1e-6
) -> FittedLogisticModel:
    """Fit the single-feature logistic regression on TRAINING matches only.

    Args:
        training_matches: only matches with usable ranking points (see
            has_usable_ranking) -- this raises rather than silently
            dropping or imputing any that are not.
        l2_penalty: forwarded to fit_logistic_regression.

    Raises:
        ValueError: if training_matches is empty, or any match has
            missing/non-positive ranking points.
    """
    if not training_matches:
        raise ValueError("cannot fit ranking baseline on zero matches")
    _require_usable(training_matches)

    features = _feature_matrix(training_matches)
    outcomes = [m.outcome_a_won for m in training_matches]
    return fit_logistic_regression(features, outcomes, [FEATURE_NAME], l2_penalty=l2_penalty)


def predict_ranking_baseline(
    model: FittedLogisticModel, matches: list[RankingBaselineMatchInput]
) -> list[RankingBaselinePrediction]:
    """Apply a fitted ranking baseline model to (usually held-out) matches.

    Raises:
        ValueError: if matches is empty, or any match has missing/
            non-positive ranking points (same discipline as fitting).
    """
    if not matches:
        raise ValueError("cannot predict ranking baseline over zero matches")
    _require_usable(matches)

    features = _feature_matrix(matches)
    probs = model.predict_proba(features)
    return [
        RankingBaselinePrediction(match_id=m.match_id, p_a_win=float(p))
        for m, p in zip(matches, probs)
    ]
