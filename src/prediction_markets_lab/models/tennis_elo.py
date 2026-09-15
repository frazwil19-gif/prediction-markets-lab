"""Leakage-safe tennis Elo rating model (Workstream A4, Cycle 2).

Mirrors prediction_markets_lab.models.football_elo's structure and
leakage-safety discipline (pre-match rating captured via get_rating()
strictly BEFORE update() is called for that same match -- see
simulate_pre_match_ratings), adapted for tennis's genuinely binary
Match Winner outcome: no draw, so no three-way probability construction
is needed, only the standard two-outcome logistic Elo expected-score
curve.

One rating engine, two uses, via a pluggable rating_key function:
- GLOBAL Elo: one rating per player, updated by every match regardless
  of surface (`global_rating_key`).
- SURFACE Elo: one independent rating per (player, surface) pair, updated
  only by matches on that specific surface (`surface_rating_key`) -- a
  standalone comparison against global Elo, not a blend of the two. Per
  the operating instructions: "test whether surface information adds
  incremental predictive value over global Elo" is answered by comparing
  this model's out-of-sample metrics against global Elo's, not by mixing
  them into one number.

No home-court-advantage term (ATP tour matches are overwhelmingly at
neutral venues; the rare home-country event is not modelled specially,
per "robust baselines, not complexity" -- an explicit simplification, not
an oversight).
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Callable, Hashable

from prediction_markets_lab.performance.binary_classification import binary_log_loss
from prediction_markets_lab.validation.leakage_checks import (
    DatedRecord,
    check_chronological_order,
)

RatingKeyFn = Callable[[str, str], Hashable]


@dataclass(frozen=True)
class EloConfig:
    """All Elo hyperparameters in one place -- no magic numbers in the
    model code. initial_rating=1500 is the standard chess/Elo convention
    default. k_factor's default of 32 is a commonly cited individual-sport
    Elo value (FIDE's standard rate for regularly-rated players); it is
    the ONE parameter this project actually calibrates on the training
    period per Workstream A4's protocol (see calibrate_k_factor) -- this
    default is only a fallback, exactly mirroring how football_elo.py
    treats draw_margin."""

    initial_rating: float = 1500.0
    k_factor: float = 32.0

    def __post_init__(self) -> None:
        if self.k_factor <= 0:
            raise ValueError(f"k_factor must be positive, got {self.k_factor}")


@dataclass(frozen=True)
class EloMatchInput:
    match_id: str
    match_date: date
    surface: str
    player_a_id: str
    player_b_id: str
    outcome_a_won: int  # 1 or 0


@dataclass(frozen=True)
class EloPrediction:
    match_id: str
    p_a_win: float
    pre_match_a_rating: float
    pre_match_b_rating: float


def global_rating_key(player_id: str, surface: str) -> Hashable:
    return player_id


def surface_rating_key(player_id: str, surface: str) -> Hashable:
    return (player_id, surface)


def _expected_score(rating_edge: float) -> float:
    """Standard logistic Elo expected-score curve, base-10/400 convention
    -- identical formula to football_elo._expected_score, duplicated
    rather than imported since these are two independent, differently-
    scoped models (football's is 3-outcome-aware at the call site; this
    one is not) and importing across sport-specific model modules would
    create an unnecessary coupling."""
    return 1.0 / (1.0 + 10.0 ** (-rating_edge / 400.0))


class EloRatingBook:
    """Mutable rating state for every rating_key seen so far, plus the
    update rule. Which entities get their own rating (players only, or
    (player, surface) pairs) is entirely determined by rating_key_fn --
    the update/lookup logic itself doesn't know or care."""

    def __init__(self, config: EloConfig, rating_key_fn: RatingKeyFn):
        self.config = config
        self.rating_key_fn = rating_key_fn
        self.ratings: dict[Hashable, float] = {}

    def get_rating(self, player_id: str, surface: str) -> float:
        key = self.rating_key_fn(player_id, surface)
        return self.ratings.get(key, self.config.initial_rating)

    def update(self, player_a_id: str, player_b_id: str, surface: str, outcome_a_won: int) -> None:
        if outcome_a_won not in (0, 1):
            raise ValueError(f"outcome_a_won must be 0 or 1, got {outcome_a_won!r}")
        key_a = self.rating_key_fn(player_a_id, surface)
        key_b = self.rating_key_fn(player_b_id, surface)
        r_a = self.ratings.get(key_a, self.config.initial_rating)
        r_b = self.ratings.get(key_b, self.config.initial_rating)
        e_a = _expected_score(r_a - r_b)
        delta = self.config.k_factor * (float(outcome_a_won) - e_a)
        self.ratings[key_a] = r_a + delta
        self.ratings[key_b] = r_b - delta


def simulate_pre_match_ratings(
    matches: list[EloMatchInput], config: EloConfig, rating_key_fn: RatingKeyFn
) -> list[tuple[EloMatchInput, float, float]]:
    """Replay matches in order, returning each match's PRE-MATCH ratings.

    Leakage-safe core, identical discipline to football_elo's version:
    for match i, get_rating() (recording pre-match state) is called
    BEFORE update() for that same match, so no match's own result can
    influence its own pre-match rating, and no later match can reach
    backwards into an earlier one.

    Raises:
        ValueError: if matches is empty or not chronologically sorted.
    """
    if not matches:
        raise ValueError("cannot simulate Elo ratings over zero matches")

    order_violations = check_chronological_order(
        [DatedRecord(m.match_id, m.match_date) for m in matches]
    )
    if order_violations:
        raise ValueError(
            "matches must be pre-sorted chronologically for Elo simulation to be "
            f"leakage-safe: {order_violations[0]}"
        )

    book = EloRatingBook(config, rating_key_fn)
    results: list[tuple[EloMatchInput, float, float]] = []
    for m in matches:
        pre_a = book.get_rating(m.player_a_id, m.surface)
        pre_b = book.get_rating(m.player_b_id, m.surface)
        results.append((m, pre_a, pre_b))
        book.update(m.player_a_id, m.player_b_id, m.surface, m.outcome_a_won)
    return results


def run_elo_over_matches(
    matches: list[EloMatchInput], config: EloConfig, rating_key_fn: RatingKeyFn
) -> list[EloPrediction]:
    """Full Elo pipeline: simulate pre-match ratings, convert each to a
    P(player_a wins) prediction via the standard logistic curve."""
    simulated = simulate_pre_match_ratings(matches, config, rating_key_fn)
    predictions = []
    for m, pre_a, pre_b in simulated:
        p_a_win = _expected_score(pre_a - pre_b)
        predictions.append(EloPrediction(
            match_id=m.match_id, p_a_win=p_a_win,
            pre_match_a_rating=pre_a, pre_match_b_rating=pre_b,
        ))
    return predictions


def calibrate_k_factor(
    training_matches: list[EloMatchInput], config: EloConfig,
    candidates: list[float], rating_key_fn: RatingKeyFn,
) -> float:
    """Grid-search k_factor on TRAINING-period matches only, minimising
    log loss -- mirrors football_elo.calibrate_draw_margin's protocol
    exactly (small predeclared candidate set, never touching the
    evaluation/validation/sealed-holdout periods).

    Args:
        training_matches: ONLY the training-period matches -- the caller
            is responsible for this restriction.
        candidates: a small fixed set of k_factor values to try, not an
            open-ended search (per "robust baselines, not a Kaggle
            competition").

    Returns:
        The candidate from `candidates` with the lowest in-sample log
        loss on training_matches.

    Raises:
        ValueError: if candidates is empty or contains a non-positive value.
    """
    if not candidates:
        raise ValueError("candidates must not be empty")
    if any(c <= 0 for c in candidates):
        raise ValueError(f"all k_factor candidates must be positive, got {candidates}")

    best_candidate = candidates[0]
    best_log_loss = float("inf")
    for candidate in candidates:
        trial_config = EloConfig(initial_rating=config.initial_rating, k_factor=candidate)
        predictions = run_elo_over_matches(training_matches, trial_config, rating_key_fn)
        preds = [p.p_a_win for p in predictions]
        actuals = [m.outcome_a_won for m in training_matches]
        loss = binary_log_loss(preds, actuals)
        if loss < best_log_loss:
            best_log_loss = loss
            best_candidate = candidate

    return best_candidate
