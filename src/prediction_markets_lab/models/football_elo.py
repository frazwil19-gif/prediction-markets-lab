"""Leakage-safe football Elo rating model (Stage 3B Model 1).

Two deliberately separate mechanisms, documented explicitly per the
Stage 3B directive's requirement to state exactly how the draw
probability is generated:

1. RATING UPDATE uses the standard two-outcome Elo expected/actual
   score convention (win=1, draw=0.5, loss=0) -- identical to chess
   Elo and every football club-Elo system. This never sees a draw
   probability; it only asks "how much better/worse did the home side
   do than the rating difference predicted."

2. 3-WAY PREDICTION (what is actually scored by log loss/Brier) is a
   SEPARATE, closed-form transform of the same underlying ratings,
   using one additional parameter, draw_margin: the home side's
   "no-loss" probability (win-or-draw) is computed with a positive
   margin added to its effective rating edge, and its "win" probability
   with the same margin subtracted. The gap between the two is the
   draw probability. This guarantees P(home)+P(draw)+P(away) == 1 and
   P(draw) >= 0 by construction (for draw_margin >= 0), with no
   separate fitting of P(draw) as its own model.

No fuzzy machine-learned draw model, no season-specific tuning beyond
draw_margin (calibrated per walk-forward fold, on that fold's training
period only -- see calibrate_draw_margin). Kept deliberately simple
per project instructions: do not add complexity without evidence.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import date

from prediction_markets_lab.validation.leakage_checks import (
    DatedRecord,
    check_chronological_order,
)

RESULT_TO_OUTCOME = {"H": "home", "D": "draw", "A": "away"}


@dataclass(frozen=True)
class EloConfig:
    """All Elo hyperparameters in one place -- no magic numbers in the model code.

    Defaults are standard literature/convention values, not fit to this
    dataset: initial_rating=1500 and k_factor=20 are the common chess/
    football-Elo defaults; home_advantage=100 rating points is a
    commonly cited football home-advantage magnitude; a 25% season
    reversion toward the mean is a conventional choice used by public
    football-Elo systems (e.g. club Elo ratings) to avoid ratings
    drifting unboundedly across many seasons. draw_margin is the one
    parameter this project actually calibrates per fold (see
    calibrate_draw_margin) -- its default here is only a fallback.
    """

    initial_rating: float = 1500.0
    k_factor: float = 20.0
    home_advantage: float = 100.0
    season_reversion_fraction: float = 0.25
    draw_margin: float = 100.0

    def __post_init__(self) -> None:
        if self.k_factor <= 0:
            raise ValueError(f"k_factor must be positive, got {self.k_factor}")
        if not (0.0 <= self.season_reversion_fraction <= 1.0):
            raise ValueError(
                f"season_reversion_fraction must be in [0, 1], got {self.season_reversion_fraction}"
            )
        if self.draw_margin < 0:
            raise ValueError(f"draw_margin must be >= 0 (would produce negative P(draw) otherwise), got {self.draw_margin}")


@dataclass(frozen=True)
class EloMatchInput:
    match_id: str
    season: str
    match_date: date
    home_team: str
    away_team: str
    full_time_result: str  # "H", "D", or "A"


@dataclass(frozen=True)
class EloPrediction:
    match_id: str
    p_home: float
    p_draw: float
    p_away: float
    pre_match_home_rating: float
    pre_match_away_rating: float


def _expected_score(rating_edge: float) -> float:
    """Standard logistic Elo expected-score curve, base-10/400 convention."""
    return 1.0 / (1.0 + 10.0 ** (-rating_edge / 400.0))


def three_way_probabilities(
    home_rating: float, away_rating: float, home_advantage: float, draw_margin: float
) -> dict[str, float]:
    """Convert two ratings into genuine P(home)/P(draw)/P(away).

    See module docstring for the exact construction. Always sums to
    1.0 exactly and is non-negative for every outcome when
    draw_margin >= 0.
    """
    if draw_margin < 0:
        raise ValueError(f"draw_margin must be >= 0, got {draw_margin}")
    edge = (home_rating + home_advantage) - away_rating
    e_home_or_draw = _expected_score(edge + draw_margin)
    e_home_win = _expected_score(edge - draw_margin)
    p_home = e_home_win
    p_away = 1.0 - e_home_or_draw
    p_draw = e_home_or_draw - e_home_win
    return {"home": p_home, "draw": p_draw, "away": p_away}


class EloRatingBook:
    """Mutable rating state for every team seen so far, plus the update rule.

    Ratings are tracked globally per team (not per-competition): a team
    promoted or relegated between competitions carries its existing
    rating forward rather than resetting to initial_rating, which is
    this project's documented, deliberately simple answer to
    "promoted-team initialisation" (no separate discount/boost applied
    in this version).
    """

    def __init__(self, config: EloConfig):
        self.config = config
        self.ratings: dict[str, float] = {}

    def get_rating(self, team: str) -> float:
        return self.ratings.get(team, self.config.initial_rating)

    def update(self, home_team: str, away_team: str, full_time_result: str) -> None:
        if full_time_result not in RESULT_TO_OUTCOME:
            raise ValueError(f"full_time_result must be 'H', 'D', or 'A', got {full_time_result!r}")
        r_home = self.get_rating(home_team)
        r_away = self.get_rating(away_team)
        e_home = _expected_score((r_home + self.config.home_advantage) - r_away)
        s_home = {"H": 1.0, "D": 0.5, "A": 0.0}[full_time_result]
        delta = self.config.k_factor * (s_home - e_home)
        self.ratings[home_team] = r_home + delta
        self.ratings[away_team] = r_away - delta

    def apply_season_reversion(self) -> None:
        """Pull every known team's rating a fixed fraction back toward
        initial_rating. Called once between seasons, never mid-season."""
        frac = self.config.season_reversion_fraction
        for team in list(self.ratings.keys()):
            self.ratings[team] = (1 - frac) * self.ratings[team] + frac * self.config.initial_rating


def simulate_pre_match_ratings(
    matches: list[EloMatchInput], config: EloConfig
) -> list[tuple[EloMatchInput, float, float]]:
    """Replay matches in order, returning each match's PRE-MATCH ratings.

    This is the leakage-safe core: for match i, get_rating() is called
    (recording the pre-match state) BEFORE update() is called for that
    same match, so match i's own result can never influence its own
    pre-match rating, and no later match's result can ever reach
    backwards into an earlier pre-match rating. Independent of
    draw_margin (rating updates never use it -- see module docstring),
    so this can be computed once and reused across a draw_margin grid
    search (see calibrate_draw_margin).

    Args:
        matches: matches for one fold's training+evaluation span,
            already sorted in genuine global chronological order
            (across all competitions together).
        config: Elo hyperparameters (draw_margin is unused here).

    Returns:
        One (match, pre_match_home_rating, pre_match_away_rating) tuple
        per input match, same order.

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

    book = EloRatingBook(config)
    results: list[tuple[EloMatchInput, float, float]] = []
    current_season: str | None = None

    for m in matches:
        if current_season is not None and m.season != current_season:
            book.apply_season_reversion()
        current_season = m.season

        pre_home = book.get_rating(m.home_team)
        pre_away = book.get_rating(m.away_team)
        results.append((m, pre_home, pre_away))

        book.update(m.home_team, m.away_team, m.full_time_result)

    return results


def run_elo_over_matches(matches: list[EloMatchInput], config: EloConfig) -> list[EloPrediction]:
    """Full Elo pipeline: simulate pre-match ratings, then convert each to a 3-way prediction."""
    simulated = simulate_pre_match_ratings(matches, config)
    predictions = []
    for m, pre_home, pre_away in simulated:
        probs = three_way_probabilities(pre_home, pre_away, config.home_advantage, config.draw_margin)
        predictions.append(
            EloPrediction(
                match_id=m.match_id,
                p_home=probs["home"],
                p_draw=probs["draw"],
                p_away=probs["away"],
                pre_match_home_rating=pre_home,
                pre_match_away_rating=pre_away,
            )
        )
    return predictions


def calibrate_draw_margin(
    training_matches: list[EloMatchInput], config: EloConfig, candidates: list[float]
) -> float:
    """Grid-search draw_margin on TRAINING-period matches only, minimising log loss.

    The rating trajectory itself does not depend on draw_margin (see
    simulate_pre_match_ratings), so this simulates ratings exactly
    once, then scores each candidate's resulting 3-way predictions
    retrospectively over the same training matches -- never touching
    the fold's evaluation season, per the walk-forward protocol.

    Args:
        training_matches: ONLY a fold's training-period matches (the
            caller is responsible for this -- see
            research/cycles/CYCLE_001/STAGE_3B_PLAN.md).
        config: base Elo config; every candidate reuses config's other
            fields and only draw_margin varies.
        candidates: predeclared draw_margin values (Elo points) to try
            -- a small fixed set, not an open-ended search, per project
            instructions.

    Returns:
        The candidate from `candidates` with the lowest in-sample log
        loss on training_matches.

    Raises:
        ValueError: if candidates is empty or contains a negative value.
    """
    from prediction_markets_lab.performance.log_loss import multiclass_log_loss

    if not candidates:
        raise ValueError("candidates must not be empty")
    if any(c < 0 for c in candidates):
        raise ValueError(f"all draw_margin candidates must be >= 0, got {candidates}")

    simulated = simulate_pre_match_ratings(training_matches, config)
    actuals = [RESULT_TO_OUTCOME[m.full_time_result] for m, _, _ in simulated]

    best_candidate = candidates[0]
    best_log_loss = float("inf")
    for candidate in candidates:
        preds = [
            three_way_probabilities(pre_home, pre_away, config.home_advantage, candidate)
            for _, pre_home, pre_away in simulated
        ]
        loss = multiclass_log_loss(preds, actuals)
        if loss < best_log_loss:
            best_log_loss = loss
            best_candidate = candidate

    return best_candidate
