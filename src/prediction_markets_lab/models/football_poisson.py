"""Leakage-safe football Poisson scoring model (Stage 3B Model 2).

Classic independent-Poisson attack/defence model (Maher 1982-style):
each team has a home-attack, home-defence, away-attack and
away-defence ratio relative to the competition's running league
averages, estimated purely from strictly-prior matches (an expanding
window, per competition -- unlike Elo, Poisson strength is tracked
PER COMPETITION here, since goal-scoring rates differ substantially
between e.g. the Premier League and the Scottish Premiership, and
there is no natural way to carry a goals-based rate across leagues; a
team new to a competition -- including a promoted team -- starts at
the league-average ratio, shrinking toward its own observed rate as
matches accumulate).

Deliberately no time-decay weighting, no Dixon-Coles low-score
correlation adjustment, no joint maximum-likelihood fit across all
teams simultaneously -- all of those are legitimate future
refinements, but add complexity this project has no evidence yet
justifies (project instructions: do not add complexity without
evidence; keep the first implementation simple).
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import date

from prediction_markets_lab.validation.leakage_checks import (
    DatedRecord,
    check_chronological_order,
)

RESULT_TO_OUTCOME = {"H": "home", "D": "draw", "A": "away"}


@dataclass(frozen=True)
class PoissonConfig:
    """All Poisson hyperparameters in one place -- no magic numbers in the model code.

    max_goals bounds the scoreline grid summed over. 15 keeps truncated
    mass above 0.999999 even for an unusually one-sided fixture
    (lambda as high as ~3.5-4.0 for the stronger side) -- see
    test_truncation_error_is_negligible_for_realistic_lambdas, which
    checks this directly rather than assuming it. The remaining
    truncated mass is corrected by renormalising the 3 summed outcome
    probabilities in scoreline_probabilities_to_1x2, so the returned
    probabilities always sum to exactly 1.0 regardless.
    shrinkage_matches is the number of "average team" pseudo-matches
    blended into every team ratio -- simple, closed-form regularisation
    so a team with 0-2 observed matches (most importantly, a team new
    to a competition -- promoted or freshly acquired data) is not
    driven by a tiny, noisy sample. default_league_avg_home_goals/
    default_league_avg_away_goals seed a competition's very first
    match, before any matches exist to average.
    """

    max_goals: int = 15
    shrinkage_matches: float = 4.0
    default_league_avg_home_goals: float = 1.5
    default_league_avg_away_goals: float = 1.1

    def __post_init__(self) -> None:
        if self.max_goals < 1:
            raise ValueError(f"max_goals must be >= 1, got {self.max_goals}")
        if self.shrinkage_matches < 0:
            raise ValueError(f"shrinkage_matches must be >= 0, got {self.shrinkage_matches}")
        if self.default_league_avg_home_goals <= 0 or self.default_league_avg_away_goals <= 0:
            raise ValueError("default league averages must be positive")


@dataclass(frozen=True)
class PoissonMatchInput:
    match_id: str
    season: str
    match_date: date
    competition_code: str
    home_team: str
    away_team: str
    home_goals: int
    away_goals: int
    full_time_result: str  # "H", "D", or "A"


@dataclass(frozen=True)
class PoissonPrediction:
    match_id: str
    p_home: float
    p_draw: float
    p_away: float
    lambda_home: float
    lambda_away: float


def _poisson_pmf(k: int, lam: float) -> float:
    return math.exp(-lam) * (lam**k) / math.factorial(k)


def scoreline_probabilities_to_1x2(
    lambda_home: float, lambda_away: float, max_goals: int
) -> dict[str, float]:
    """Sum independent-Poisson scoreline mass into P(home)/P(draw)/P(away).

    Renormalises by the total summed mass (>0.999999 for any realistic
    lambda within max_goals=10 -- see test_truncation_error_is_negligible)
    so the three returned probabilities sum to exactly 1.0 despite the
    grid truncation.
    """
    home_pmf = [_poisson_pmf(x, lambda_home) for x in range(max_goals + 1)]
    away_pmf = [_poisson_pmf(y, lambda_away) for y in range(max_goals + 1)]

    p_home = p_draw = p_away = 0.0
    for x in range(max_goals + 1):
        for y in range(max_goals + 1):
            mass = home_pmf[x] * away_pmf[y]
            if x > y:
                p_home += mass
            elif x == y:
                p_draw += mass
            else:
                p_away += mass

    total = p_home + p_draw + p_away
    return {"home": p_home / total, "draw": p_draw / total, "away": p_away / total}


def _shrunk_ratio(goals_sum: float, matches_played: int, league_avg: float, shrinkage_matches: float) -> float:
    """Blend a team's observed goals-per-match ratio (vs. league_avg)
    with 1.0 (an average team), weighted by shrinkage_matches pseudo-observations."""
    raw_ratio = 1.0 if matches_played == 0 else (goals_sum / matches_played) / league_avg
    return (matches_played * raw_ratio + shrinkage_matches * 1.0) / (matches_played + shrinkage_matches)


@dataclass
class _CompetitionState:
    total_home_goals: float = 0.0
    total_away_goals: float = 0.0
    total_matches: int = 0
    home_goals_scored: dict[str, float] = None
    home_goals_conceded: dict[str, float] = None
    home_matches: dict[str, int] = None
    away_goals_scored: dict[str, float] = None
    away_goals_conceded: dict[str, float] = None
    away_matches: dict[str, int] = None

    def __post_init__(self) -> None:
        self.home_goals_scored = {}
        self.home_goals_conceded = {}
        self.home_matches = {}
        self.away_goals_scored = {}
        self.away_goals_conceded = {}
        self.away_matches = {}


class PoissonRatingBook:
    """Per-competition, leakage-safe expanding-window goal-rate tracker."""

    def __init__(self, config: PoissonConfig):
        self.config = config
        self._competitions: dict[str, _CompetitionState] = {}

    def _state(self, competition_code: str) -> _CompetitionState:
        return self._competitions.setdefault(competition_code, _CompetitionState())

    def league_averages(self, competition_code: str) -> tuple[float, float]:
        """Return (avg_home_goals, avg_away_goals) from strictly-prior matches.

        Falls back to the configured defaults not only when zero prior
        matches exist, but also in the degenerate edge case where the
        computed average itself is exactly 0 (e.g. a tiny early-window
        sample in which every away team happened to score 0) -- an
        average of 0 would make every team's shrunk ratio undefined
        (division by zero), so it is treated the same as "no data yet."
        """
        state = self._state(competition_code)
        if state.total_matches == 0:
            return self.config.default_league_avg_home_goals, self.config.default_league_avg_away_goals
        avg_home = state.total_home_goals / state.total_matches
        avg_away = state.total_away_goals / state.total_matches
        if avg_home <= 0:
            avg_home = self.config.default_league_avg_home_goals
        if avg_away <= 0:
            avg_away = self.config.default_league_avg_away_goals
        return avg_home, avg_away

    def predict(self, competition_code: str, home_team: str, away_team: str) -> tuple[float, float]:
        """Return (lambda_home, lambda_away) from PRE-MATCH team state."""
        state = self._state(competition_code)
        avg_home, avg_away = self.league_averages(competition_code)
        s = self.config.shrinkage_matches

        attack_home = _shrunk_ratio(
            state.home_goals_scored.get(home_team, 0.0), state.home_matches.get(home_team, 0), avg_home, s
        )
        defence_home = _shrunk_ratio(
            state.home_goals_conceded.get(home_team, 0.0), state.home_matches.get(home_team, 0), avg_away, s
        )
        attack_away = _shrunk_ratio(
            state.away_goals_scored.get(away_team, 0.0), state.away_matches.get(away_team, 0), avg_away, s
        )
        defence_away = _shrunk_ratio(
            state.away_goals_conceded.get(away_team, 0.0), state.away_matches.get(away_team, 0), avg_home, s
        )

        lambda_home = avg_home * attack_home * defence_away
        lambda_away = avg_away * attack_away * defence_home
        return lambda_home, lambda_away

    def update(self, competition_code: str, home_team: str, away_team: str, home_goals: int, away_goals: int) -> None:
        state = self._state(competition_code)
        state.total_home_goals += home_goals
        state.total_away_goals += away_goals
        state.total_matches += 1

        state.home_goals_scored[home_team] = state.home_goals_scored.get(home_team, 0.0) + home_goals
        state.home_goals_conceded[home_team] = state.home_goals_conceded.get(home_team, 0.0) + away_goals
        state.home_matches[home_team] = state.home_matches.get(home_team, 0) + 1

        state.away_goals_scored[away_team] = state.away_goals_scored.get(away_team, 0.0) + away_goals
        state.away_goals_conceded[away_team] = state.away_goals_conceded.get(away_team, 0.0) + home_goals
        state.away_matches[away_team] = state.away_matches.get(away_team, 0) + 1


def simulate_pre_match_lambdas(
    matches: list[PoissonMatchInput], config: PoissonConfig
) -> list[tuple[PoissonMatchInput, float, float]]:
    """Replay matches in order, returning each match's PRE-MATCH (lambda_home, lambda_away).

    Leakage-safe by construction: predict() is called before update()
    for each match, so a match's own goals (and any later match's
    goals) can never influence its own pre-match lambdas.

    Args:
        matches: matches for one fold's training+evaluation span,
            already sorted in genuine global chronological order.
        config: Poisson hyperparameters.

    Returns:
        One (match, lambda_home, lambda_away) tuple per input match.

    Raises:
        ValueError: if matches is empty or not chronologically sorted.
    """
    if not matches:
        raise ValueError("cannot simulate Poisson lambdas over zero matches")

    order_violations = check_chronological_order(
        [DatedRecord(m.match_id, m.match_date) for m in matches]
    )
    if order_violations:
        raise ValueError(
            "matches must be pre-sorted chronologically for Poisson simulation to be "
            f"leakage-safe: {order_violations[0]}"
        )

    book = PoissonRatingBook(config)
    results: list[tuple[PoissonMatchInput, float, float]] = []

    for m in matches:
        if m.full_time_result not in RESULT_TO_OUTCOME:
            raise ValueError(
                f"match {m.match_id!r} has invalid full_time_result {m.full_time_result!r}"
            )
        lambda_home, lambda_away = book.predict(m.competition_code, m.home_team, m.away_team)
        results.append((m, lambda_home, lambda_away))
        book.update(m.competition_code, m.home_team, m.away_team, m.home_goals, m.away_goals)

    return results


def run_poisson_over_matches(matches: list[PoissonMatchInput], config: PoissonConfig) -> list[PoissonPrediction]:
    """Full Poisson pipeline: simulate pre-match lambdas, then convert each to a 3-way prediction."""
    simulated = simulate_pre_match_lambdas(matches, config)
    predictions = []
    for m, lambda_home, lambda_away in simulated:
        probs = scoreline_probabilities_to_1x2(lambda_home, lambda_away, config.max_goals)
        predictions.append(
            PoissonPrediction(
                match_id=m.match_id,
                p_home=probs["home"],
                p_draw=probs["draw"],
                p_away=probs["away"],
                lambda_home=lambda_home,
                lambda_away=lambda_away,
            )
        )
    return predictions
