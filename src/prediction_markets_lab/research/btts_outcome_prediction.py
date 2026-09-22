"""Phase 5 -- Football Both-Teams-To-Score (BTTS) outcome prediction (2026-09-22).

Stage-A outcome-prediction research: how well can P(BTTS YES) be estimated, how
calibrated is it, and how often do strong predictions actually occur? Price/value
is deliberately NOT part of this module (see research/btts_outcome_prediction/
PROBABILITY_ENGINE_ARCHITECTURE.md for the probability-vs-betting separation).

Reused, not reimplemented:
  - models.football_poisson.simulate_pre_match_lambdas / PoissonConfig
    (the project's existing validated, leakage-safe goal model)
  - models.logistic_regression.fit_logistic_regression (binary IRLS)
  - research.ou25_probability_architecture.FUNDAMENTALS_FEATURES (Gate 1b's
    19 pre-match fundamentals, identical list)

New here: BTTS target, leakage-safe rolling scoring / clean-sheet / BTTS-rate
features (date-grouped updates so same-day fixtures never see each other),
independent-Poisson BTTS, market-implied Poisson lambdas solved from 1X2 +
OU2.5 prices, fixed probability-band reporting for BOTH sides with Wilson CIs,
top-prediction and high-probability reports.

No file I/O -- see scripts/run_phase5_btts_outcome_prediction.py.
"""
from __future__ import annotations

import math
from collections import deque
from dataclasses import dataclass, field
from datetime import date
from typing import Callable, Iterable, Sequence

import numpy as np

from prediction_markets_lab.models.football_poisson import (
    PoissonConfig,
    PoissonMatchInput,
    simulate_pre_match_lambdas,
)
from prediction_markets_lab.models.logistic_regression import fit_logistic_regression
from prediction_markets_lab.research.ou25_probability_architecture import (
    FUNDAMENTALS_FEATURES,
)

# ---------------------------------------------------------------------------
# Configuration (all named -- no magic numbers in the logic below)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class BttsConfig:
    rolling_window: int = 10
    shrinkage_pseudo_matches: float = 4.0
    # Seeds used ONLY before a competition has any completed match in the data
    # (i.e. the very first match date of each competition).
    seed_home_scored_rate: float = 0.75
    seed_away_scored_rate: float = 0.68
    seed_btts_rate: float = 0.50
    l2_penalty: float = 1.0
    lambda_grid_min: float = 0.05
    lambda_grid_max: float = 5.0
    lambda_grid_step: float = 0.05
    lambda_refine_step: float = 0.005
    lambda_refine_half_width: float = 0.05
    max_goals: int = 15
    probability_floor: float = 1e-6

    def __post_init__(self) -> None:
        if self.rolling_window < 1:
            raise ValueError("rolling_window must be >= 1")
        if self.shrinkage_pseudo_matches < 0:
            raise ValueError("shrinkage_pseudo_matches must be >= 0")
        if not (0 < self.lambda_grid_min < self.lambda_grid_max):
            raise ValueError("invalid lambda grid")


DEFAULT_CONFIG = BttsConfig()

SEASONS_IN_ORDER: tuple[str, ...] = ("2020_21", "2021_22", "2022_23", "2023_24", "2024_25")
DISCOVERY_SEASONS: tuple[str, ...] = ("2020_21", "2021_22", "2022_23")
DEVELOPMENT_EVAL_SEASONS: tuple[str, ...] = ("2021_22", "2022_23", "2023_24")
VALIDATION_SEASON = "2023_24"
HOLDOUT_SEASON = "2024_25"

PROBABILITY_BANDS: tuple[tuple[float, float, str], ...] = (
    (0.50, 0.55, "50-54.9%"),
    (0.55, 0.60, "55-59.9%"),
    (0.60, 0.65, "60-64.9%"),
    (0.65, 0.70, "65-69.9%"),
    (0.70, 0.75, "70-74.9%"),
    (0.75, 0.80, "75-79.9%"),
    (0.80, 1.0000001, "80%+"),
)
HIGH_PROBABILITY_THRESHOLDS: tuple[float, ...] = (0.60, 0.65, 0.70, 0.75, 0.80)
CALIBRATION_DECILE_EDGES: tuple[float, ...] = tuple(i / 10 for i in range(11))
WILSON_Z_95 = 1.959963984540054

NEW_ROLLING_FEATURES: tuple[str, ...] = (
    "home_scoring_rate_l10",
    "home_clean_sheet_rate_l10",
    "home_btts_rate_l10",
    "away_scoring_rate_l10",
    "away_clean_sheet_rate_l10",
    "away_btts_rate_l10",
    "home_home_scoring_rate_l10",
    "home_home_clean_sheet_rate_l10",
    "away_away_scoring_rate_l10",
    "away_away_clean_sheet_rate_l10",
)
DATA_FEATURES: tuple[str, ...] = tuple(FUNDAMENTALS_FEATURES) + NEW_ROLLING_FEATURES

MODEL_KEYS: tuple[str, ...] = (
    "naive",
    "data_logit",
    "poisson_goal",
    "market_implied_poisson",
    "market_implied_poisson_recal",
    "market_implied_plus_data",
)
SENSITIVITY_MODEL_KEYS: tuple[str, ...] = ("market_implied_poisson_opening",)
MODEL_FITTED_PARAMETERS: dict[str, int] = {
    "naive": 1,
    "data_logit": len(DATA_FEATURES) + 1,
    "poisson_goal": 0,
    "market_implied_poisson": 0,
    "market_implied_poisson_recal": 2,
    "market_implied_plus_data": len(DATA_FEATURES) + 2,
    "market_implied_poisson_opening": 0,
}


# ---------------------------------------------------------------------------
# Target
# ---------------------------------------------------------------------------


def btts_target(home_goals: int | float, away_goals: int | float) -> int:
    """1 = BTTS YES (both teams scored >= 1), 0 = BTTS NO."""
    if home_goals < 0 or away_goals < 0:
        raise ValueError("goals cannot be negative")
    return int(home_goals >= 1 and away_goals >= 1)


def btts_yes_no(p_yes: float) -> tuple[float, float]:
    """Return (P(YES), P(NO)); the pair always sums to exactly 1."""
    if not 0.0 <= p_yes <= 1.0:
        raise ValueError(f"probability out of range: {p_yes}")
    return p_yes, 1.0 - p_yes


# ---------------------------------------------------------------------------
# Poisson helpers
# ---------------------------------------------------------------------------


def btts_probability_independent_poisson(lambda_home: float, lambda_away: float) -> float:
    """P(home>=1 and away>=1) for independent Poisson goal counts (exact closed form)."""
    if lambda_home < 0 or lambda_away < 0:
        raise ValueError("lambdas must be non-negative")
    return (1.0 - math.exp(-lambda_home)) * (1.0 - math.exp(-lambda_away))


def poisson_outcome_probabilities(
    lambda_home: np.ndarray, lambda_away: np.ndarray, max_goals: int
) -> dict[str, np.ndarray]:
    """Vectorised independent-Poisson P(home win), P(draw), P(away win),
    P(total > 2.5), P(BTTS) over a truncated, renormalised scoreline grid."""
    lh = np.atleast_1d(np.asarray(lambda_home, dtype=float))
    la = np.atleast_1d(np.asarray(lambda_away, dtype=float))
    k = np.arange(max_goals + 1, dtype=float)
    log_fact = np.array([math.lgamma(x + 1.0) for x in k])

    def pmf(lam: np.ndarray) -> np.ndarray:
        lam_c = np.clip(lam, 1e-12, None)[:, None]
        return np.exp(-lam_c + k[None, :] * np.log(lam_c) - log_fact[None, :])

    ph, pa = pmf(lh), pmf(la)
    grid = ph[:, :, None] * pa[:, None, :]  # [n, x(home), y(away)]
    total = grid.sum(axis=(1, 2))
    x = k[:, None]
    y = k[None, :]
    home = (grid * (x > y)).sum(axis=(1, 2)) / total
    draw = (grid * (x == y)).sum(axis=(1, 2)) / total
    away = (grid * (x < y)).sum(axis=(1, 2)) / total
    over = (grid * ((x + y) >= 3)).sum(axis=(1, 2)) / total
    btts = (grid * ((x >= 1) & (y >= 1))).sum(axis=(1, 2)) / total
    return {"home": home, "draw": draw, "away": away, "over25": over, "btts": btts}


def fit_market_implied_lambdas(
    p_home: Sequence[float],
    p_away: Sequence[float],
    p_over25: Sequence[float | None],
    config: BttsConfig = DEFAULT_CONFIG,
) -> list[tuple[float, float]]:
    """Solve, per match, the (lambda_home, lambda_away) whose independent-Poisson
    P(home), P(away) and (when given) P(over 2.5) best match the de-vigged market
    probabilities in least squares. Deterministic coarse grid + local refinement.
    A zero-parameter transformation of market prices -- nothing is fitted to outcomes."""
    n = len(p_home)
    if not (len(p_away) == n == len(p_over25)):
        raise ValueError("input lengths differ")
    grid_vals = np.arange(
        config.lambda_grid_min, config.lambda_grid_max + 1e-9, config.lambda_grid_step
    )
    gh, ga = np.meshgrid(grid_vals, grid_vals, indexing="ij")
    gh, ga = gh.ravel(), ga.ravel()
    gp = poisson_outcome_probabilities(gh, ga, config.max_goals)

    offsets = np.arange(
        -config.lambda_refine_half_width,
        config.lambda_refine_half_width + 1e-9,
        config.lambda_refine_step,
    )
    oh, oa = np.meshgrid(offsets, offsets, indexing="ij")
    oh, oa = oh.ravel(), oa.ravel()

    out: list[tuple[float, float]] = []
    for i in range(n):
        th, ta, to = float(p_home[i]), float(p_away[i]), p_over25[i]
        sse = (gp["home"] - th) ** 2 + (gp["away"] - ta) ** 2
        if to is not None:
            sse = sse + (gp["over25"] - float(to)) ** 2
        j = int(np.argmin(sse))
        rh = np.clip(gh[j] + oh, config.lambda_grid_min / 10, None)
        ra = np.clip(ga[j] + oa, config.lambda_grid_min / 10, None)
        rp = poisson_outcome_probabilities(rh, ra, config.max_goals)
        rsse = (rp["home"] - th) ** 2 + (rp["away"] - ta) ** 2
        if to is not None:
            rsse = rsse + (rp["over25"] - float(to)) ** 2
        jj = int(np.argmin(rsse))
        out.append((float(rh[jj]), float(ra[jj])))
    return out


# ---------------------------------------------------------------------------
# Leakage-safe rolling BTTS features
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class RawMatch:
    match_id: str
    season: str
    match_date: date
    competition: str
    home_team: str
    away_team: str
    home_goals: int
    away_goals: int


@dataclass
class _LeagueTotals:
    n: int = 0
    home_scored: int = 0
    away_scored: int = 0
    btts: int = 0


def _shrunk(successes: float, n: int, prior: float, k: float) -> float:
    if n + k == 0:
        return prior  # no history and no shrinkage: fall back to the prior
    return (successes + prior * k) / (n + k)


def build_rolling_btts_features(
    matches: Sequence[RawMatch], config: BttsConfig = DEFAULT_CONFIG
) -> dict[str, dict[str, float | int | bool | None]]:
    """Pre-match rolling scoring / clean-sheet / BTTS-rate features.

    Leakage safety: matches are grouped by calendar date; ALL features for a date
    are computed before ANY result from that date is added to history, so neither
    a match's own result nor a same-day concurrent fixture's result can leak in.
    Rates are shrunk toward the competition's running (strictly prior) league rate
    with `shrinkage_pseudo_matches` pseudo-observations, so a team with little or
    no history (e.g. newly promoted from outside the dataset) gets the league prior
    rather than a missing value -- its history depth is reported separately.
    """
    ordered = sorted(matches, key=lambda m: (m.match_date, m.match_id))
    w, k = config.rolling_window, config.shrinkage_pseudo_matches
    overall: dict[str, deque] = {}
    home_ctx: dict[str, deque] = {}
    away_ctx: dict[str, deque] = {}
    league: dict[str, _LeagueTotals] = {}
    comp_by_team_season: dict[tuple[str, str], str] = {}
    season_matches: dict[tuple[str, str], int] = {}
    seasons_seen = sorted({m.season for m in ordered})
    out: dict[str, dict[str, float | int | bool | None]] = {}

    def league_priors(comp: str) -> tuple[float, float, float]:
        t = league.get(comp)
        if t is None or t.n == 0:
            return config.seed_home_scored_rate, config.seed_away_scored_rate, config.seed_btts_rate
        return t.home_scored / t.n, t.away_scored / t.n, t.btts / t.n

    i = 0
    while i < len(ordered):
        d = ordered[i].match_date
        j = i
        while j < len(ordered) and ordered[j].match_date == d:
            j += 1
        day = ordered[i:j]
        # 1) compute features for every match on this date from prior history only
        for m in day:
            ph, pa, pb = league_priors(m.competition)
            p_overall_scoring = (ph + pa) / 2.0
            hist_h = overall.get(m.home_team, deque(maxlen=w))
            hist_a = overall.get(m.away_team, deque(maxlen=w))
            hh = home_ctx.get(m.home_team, deque(maxlen=w))
            aa = away_ctx.get(m.away_team, deque(maxlen=w))

            def rate(hist: deque, idx: int, prior: float) -> float:
                return _shrunk(sum(r[idx] for r in hist), len(hist), prior, k)

            prev_idx = seasons_seen.index(m.season) - 1
            prev_season = seasons_seen[prev_idx] if prev_idx >= 0 else None

            def new_to_comp(team: str) -> bool | None:
                if prev_season is None:
                    return None
                return comp_by_team_season.get((team, prev_season)) != m.competition

            out[m.match_id] = {
                "home_scoring_rate_l10": rate(hist_h, 0, p_overall_scoring),
                "home_clean_sheet_rate_l10": rate(hist_h, 1, 1.0 - p_overall_scoring),
                "home_btts_rate_l10": rate(hist_h, 2, pb),
                "away_scoring_rate_l10": rate(hist_a, 0, p_overall_scoring),
                "away_clean_sheet_rate_l10": rate(hist_a, 1, 1.0 - p_overall_scoring),
                "away_btts_rate_l10": rate(hist_a, 2, pb),
                "home_home_scoring_rate_l10": rate(hh, 0, ph),
                "home_home_clean_sheet_rate_l10": rate(hh, 1, 1.0 - pa),
                "away_away_scoring_rate_l10": rate(aa, 0, pa),
                "away_away_clean_sheet_rate_l10": rate(aa, 1, 1.0 - ph),
                "home_failed_to_score_rate_l10": 1.0 - rate(hist_h, 0, p_overall_scoring),
                "away_failed_to_score_rate_l10": 1.0 - rate(hist_a, 0, p_overall_scoring),
                "home_history_matches": len(hist_h),
                "away_history_matches": len(hist_a),
                "min_history_matches": min(len(hist_h), len(hist_a)),
                "season_match_number": min(
                    season_matches.get((m.home_team, m.season), 0),
                    season_matches.get((m.away_team, m.season), 0),
                )
                + 1,
                "home_new_to_competition": new_to_comp(m.home_team),
                "away_new_to_competition": new_to_comp(m.away_team),
            }
        # 2) only now add this date's results to history
        for m in day:
            hs, as_ = m.home_goals >= 1, m.away_goals >= 1
            both = hs and as_
            overall.setdefault(m.home_team, deque(maxlen=w)).append((hs, not as_, both))
            overall.setdefault(m.away_team, deque(maxlen=w)).append((as_, not hs, both))
            home_ctx.setdefault(m.home_team, deque(maxlen=w)).append((hs, not as_, both))
            away_ctx.setdefault(m.away_team, deque(maxlen=w)).append((as_, not hs, both))
            t = league.setdefault(m.competition, _LeagueTotals())
            t.n += 1
            t.home_scored += int(hs)
            t.away_scored += int(as_)
            t.btts += int(both)
            comp_by_team_season[(m.home_team, m.season)] = m.competition
            comp_by_team_season[(m.away_team, m.season)] = m.competition
            for team in (m.home_team, m.away_team):
                season_matches[(team, m.season)] = season_matches.get((team, m.season), 0) + 1
        i = j
    return out


# ---------------------------------------------------------------------------
# Canonical dataset
# ---------------------------------------------------------------------------


def _to_float(v: object) -> float | None:
    if v is None or v == "":
        return None
    try:
        f = float(v)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return None
    return None if math.isnan(f) else f


@dataclass
class BttsMatch:
    match_id: str
    season: str
    match_date: date
    competition: str
    home_team: str
    away_team: str
    home_goals: int
    away_goals: int
    target: int
    features: dict[str, float | None] = field(default_factory=dict)
    context: dict[str, float | int | bool | None] = field(default_factory=dict)
    lambda_poisson: tuple[float, float] | None = None
    lambda_market_closing: tuple[float, float] | None = None
    lambda_market_opening: tuple[float, float] | None = None
    p_market_implied_closing: float | None = None
    p_market_implied_opening: float | None = None
    p_poisson: float | None = None

    def data_vector(self) -> tuple[float, ...] | None:
        vals = [self.features.get(f) for f in DATA_FEATURES]
        if any(v is None for v in vals):
            return None
        return tuple(float(v) for v in vals)  # type: ignore[arg-type]


def build_btts_dataset(
    rows: Iterable[dict[str, str]], config: BttsConfig = DEFAULT_CONFIG
) -> list[BttsMatch]:
    """Build the canonical, chronologically ordered BTTS dataset from
    cycle_002_discovery_features.csv rows."""
    raw_rows = []
    for r in rows:
        hg, ag = _to_float(r.get("outcome_full_time_home_goals")), _to_float(
            r.get("outcome_full_time_away_goals")
        )
        if hg is None or ag is None:
            continue
        raw_rows.append((r, int(hg), int(ag)))
    raw_rows.sort(key=lambda t: (t[0]["match_date"], t[0]["match_id"]))

    raws = [
        RawMatch(
            match_id=r["match_id"],
            season=r["season"],
            match_date=date.fromisoformat(r["match_date"]),
            competition=r["competition_code"],
            home_team=r["home_team"],
            away_team=r["away_team"],
            home_goals=hg,
            away_goals=ag,
        )
        for r, hg, ag in raw_rows
    ]
    rolling = build_rolling_btts_features(raws, config)

    poisson_inputs = [
        PoissonMatchInput(
            match_id=m.match_id,
            season=m.season,
            match_date=m.match_date,
            competition_code=m.competition,
            home_team=m.home_team,
            away_team=m.away_team,
            home_goals=m.home_goals,
            away_goals=m.away_goals,
            full_time_result="H" if m.home_goals > m.away_goals else ("D" if m.home_goals == m.away_goals else "A"),
        )
        for m in raws
    ]
    lambdas = {
        m.match_id: (lh, la)
        for m, lh, la in simulate_pre_match_lambdas(poisson_inputs, PoissonConfig(max_goals=config.max_goals))
    }

    out: list[BttsMatch] = []
    for (r, hg, ag), m in zip(raw_rows, raws):
        feats: dict[str, float | None] = {f: _to_float(r.get(f)) for f in FUNDAMENTALS_FEATURES}
        roll = rolling[m.match_id]
        for f in NEW_ROLLING_FEATURES:
            feats[f] = float(roll[f])  # type: ignore[arg-type]
        ctx = {k2: v for k2, v in roll.items() if k2 not in NEW_ROLLING_FEATURES}
        for extra in (
            "home_team_overall_last10_goal_diff_volatility",
            "away_team_overall_last10_goal_diff_volatility",
            "market_1x2_closing_home_probability",
            "market_1x2_closing_draw_probability",
            "market_1x2_closing_away_probability",
            "market_ou25_closing_source_avg_over_probability",
            "market_ou25_opening_source_avg_over_probability",
            "market_1x2_opening_home_probability",
            "market_1x2_opening_away_probability",
        ):
            ctx[extra] = _to_float(r.get(extra))
        elo_gap = _to_float(r.get("elo_rating_gap_incl_home_advantage"))
        ctx["abs_elo_gap"] = abs(elo_gap) if elo_gap is not None else None
        lp = lambdas[m.match_id]
        out.append(
            BttsMatch(
                match_id=m.match_id,
                season=m.season,
                match_date=m.match_date,
                competition=m.competition,
                home_team=m.home_team,
                away_team=m.away_team,
                home_goals=hg,
                away_goals=ag,
                target=btts_target(hg, ag),
                features=feats,
                context=ctx,
                lambda_poisson=lp,
                p_poisson=btts_probability_independent_poisson(*lp),
            )
        )

    for timing in ("closing", "opening"):
        idx, ph, pa, po = [], [], [], []
        for n_i, bm in enumerate(out):
            h = bm.context.get(f"market_1x2_{timing}_home_probability")
            a = bm.context.get(f"market_1x2_{timing}_away_probability")
            o = bm.context.get(f"market_ou25_{timing}_source_avg_over_probability")
            if h is None or a is None:
                continue
            idx.append(n_i)
            ph.append(h)
            pa.append(a)
            po.append(o)
        fitted = fit_market_implied_lambdas(ph, pa, po, config)
        for n_i, lam in zip(idx, fitted):
            p = btts_probability_independent_poisson(*lam)
            if timing == "closing":
                out[n_i].lambda_market_closing = lam
                out[n_i].p_market_implied_closing = p
            else:
                out[n_i].lambda_market_opening = lam
                out[n_i].p_market_implied_opening = p
    return out


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Prediction:
    match_id: str
    season: str
    competition: str
    p_yes: float
    actual: int


def _logit(p: float, floor: float) -> float:
    p = min(max(p, floor), 1.0 - floor)
    return math.log(p / (1.0 - p))


@dataclass(frozen=True)
class StandardisedLogit:
    mean: np.ndarray
    std: np.ndarray
    intercept: float
    coefficients: np.ndarray

    def predict(self, x: Sequence[float]) -> float:
        z = (np.asarray(x, dtype=float) - self.mean) / self.std
        eta = self.intercept + float(z @ self.coefficients)
        return 1.0 / (1.0 + math.exp(-max(min(eta, 35.0), -35.0)))


def fit_standardised_logit(
    X: Sequence[Sequence[float]], y: Sequence[int], l2_penalty: float
) -> StandardisedLogit:
    Xa = np.asarray(X, dtype=float)
    mean = Xa.mean(axis=0)
    std = Xa.std(axis=0)
    std = np.where(std > 0, std, 1.0)
    Z = (Xa - mean) / std
    names = [f"z{i}" for i in range(Z.shape[1])]
    m = fit_logistic_regression(Z, list(y), names, l2_penalty=l2_penalty)
    return StandardisedLogit(mean, std, m.intercept, np.asarray(m.coefficients))


FeatureFn = Callable[[BttsMatch], "tuple[float, ...] | None"]


def _feature_fn(model_key: str, config: BttsConfig) -> FeatureFn | None:
    fl = config.probability_floor
    if model_key == "data_logit":
        return lambda m: m.data_vector()
    if model_key == "market_implied_poisson_recal":
        return lambda m: (
            (_logit(m.p_market_implied_closing, fl),) if m.p_market_implied_closing is not None else None
        )
    if model_key == "market_implied_plus_data":
        def f(m: BttsMatch) -> tuple[float, ...] | None:
            dv = m.data_vector()
            if dv is None or m.p_market_implied_closing is None:
                return None
            return (_logit(m.p_market_implied_closing, fl),) + dv
        return f
    return None


def predict_model(
    model_key: str,
    train: Sequence[BttsMatch],
    evaluate: Sequence[BttsMatch],
    config: BttsConfig = DEFAULT_CONFIG,
) -> list[Prediction]:
    """Fit (if the model has parameters) on `train` only and predict `evaluate`.
    Train and evaluate sets must be disjoint in time -- enforced by the caller's
    fold construction and asserted here."""
    if train and evaluate and max(m.match_date for m in train) >= min(m.match_date for m in evaluate):
        raise ValueError("training data must strictly precede evaluation data")

    def pred(m: BttsMatch, p: float) -> Prediction:
        return Prediction(m.match_id, m.season, m.competition, float(p), m.target)

    if model_key == "naive":
        if not train:
            raise ValueError("naive baseline needs training data")
        rate = sum(m.target for m in train) / len(train)
        return [pred(m, rate) for m in evaluate]
    if model_key == "poisson_goal":
        return [pred(m, m.p_poisson) for m in evaluate if m.p_poisson is not None]
    if model_key == "market_implied_poisson":
        return [pred(m, m.p_market_implied_closing) for m in evaluate if m.p_market_implied_closing is not None]
    if model_key == "market_implied_poisson_opening":
        return [pred(m, m.p_market_implied_opening) for m in evaluate if m.p_market_implied_opening is not None]
    fn = _feature_fn(model_key, config)
    if fn is None:
        raise ValueError(f"unknown model {model_key!r}")
    rows = [(fn(m), m.target) for m in train]
    rows = [(x, t) for x, t in rows if x is not None]
    if not rows:
        raise ValueError(f"no complete training rows for {model_key}")
    fitted = fit_standardised_logit([x for x, _ in rows], [t for _, t in rows], config.l2_penalty)
    out = []
    for m in evaluate:
        x = fn(m)
        if x is not None:
            out.append(pred(m, fitted.predict(x)))
    return out


def run_expanding_walk_forward(
    matches: Sequence[BttsMatch],
    eval_seasons: Sequence[str],
    model_keys: Sequence[str],
    seasons_in_order: Sequence[str] = SEASONS_IN_ORDER,
    config: BttsConfig = DEFAULT_CONFIG,
) -> dict[str, list[Prediction]]:
    """For each evaluation season, train on ALL strictly earlier seasons."""
    by_season: dict[str, list[BttsMatch]] = {}
    for m in matches:
        by_season.setdefault(m.season, []).append(m)
    pooled: dict[str, list[Prediction]] = {k: [] for k in model_keys}
    for s in eval_seasons:
        pos = list(seasons_in_order).index(s)
        train = [m for prior in seasons_in_order[:pos] for m in by_season.get(prior, [])]
        evaluate = by_season.get(s, [])
        for k in model_keys:
            pooled[k].extend(predict_model(k, train, evaluate, config))
    return pooled


def restrict_to_common(preds: dict[str, list[Prediction]]) -> dict[str, list[Prediction]]:
    """Restrict every model to matches every model scored, in identical order."""
    ids = None
    for p in preds.values():
        s = {x.match_id for x in p}
        ids = s if ids is None else ids & s
    ids = ids or set()
    out = {}
    for k, p in preds.items():
        sel = sorted((x for x in p if x.match_id in ids), key=lambda x: x.match_id)
        out[k] = sel
    return out


# ---------------------------------------------------------------------------
# Metrics / reports
# ---------------------------------------------------------------------------


def wilson_interval(successes: int, n: int, z: float = WILSON_Z_95) -> tuple[float | None, float | None]:
    if n == 0:
        return None, None
    ph = successes / n
    denom = 1 + z * z / n
    centre = (ph + z * z / (2 * n)) / denom
    half = z * math.sqrt(ph * (1 - ph) / n + z * z / (4 * n * n)) / denom
    return max(0.0, centre - half), min(1.0, centre + half)


def _band_label(p: float) -> str | None:
    for lo, hi, label in PROBABILITY_BANDS:
        if lo <= p < hi:
            return label
    return None


def probability_band_report(preds: Sequence[Prediction], side: str) -> list[dict]:
    """Bands of the probability assigned to `side` ("YES" or "NO"). For NO the
    probability is 1 - P(YES) and 'occurred' means BTTS did NOT happen."""
    if side not in ("YES", "NO"):
        raise ValueError("side must be YES or NO")
    buckets: dict[str, list[tuple[float, int]]] = {b[2]: [] for b in PROBABILITY_BANDS}
    for p in preds:
        prob = p.p_yes if side == "YES" else 1.0 - p.p_yes
        occ = p.actual if side == "YES" else 1 - p.actual
        lab = _band_label(prob)
        if lab is not None:
            buckets[lab].append((prob, occ))
    rows = []
    for _, _, lab in PROBABILITY_BANDS:
        b = buckets[lab]
        n = len(b)
        occ = sum(o for _, o in b)
        mean_p = sum(p for p, _ in b) / n if n else None
        rate = occ / n if n else None
        lo, hi = wilson_interval(occ, n)
        rows.append(
            {
                "side": side,
                "band": lab,
                "n": n,
                "mean_predicted_probability": mean_p,
                "occurred": occ,
                "actual_rate": rate,
                "calibration_error_pp": (rate - mean_p) * 100 if n else None,
                "wilson95_low": lo,
                "wilson95_high": hi,
            }
        )
    return rows


def top_pick(p_yes: float) -> tuple[str, float]:
    """Pick YES only if P(YES) > P(NO); a tie goes to NO (per the brief's rule)."""
    return ("YES", p_yes) if p_yes > 0.5 else ("NO", 1.0 - p_yes)


def top_prediction_summary(preds: Sequence[Prediction]) -> dict:
    n = len(preds)
    if n == 0:
        return {"n": 0}
    correct = 0
    conf = 0.0
    yes_picks = 0
    for p in preds:
        side, prob = top_pick(p.p_yes)
        conf += prob
        yes_picks += side == "YES"
        correct += int((side == "YES") == (p.actual == 1))
    return {
        "n": n,
        "yes_picks": yes_picks,
        "no_picks": n - yes_picks,
        "correct": correct,
        "incorrect": n - correct,
        "accuracy": correct / n,
        "mean_pick_probability": conf / n,
        "expected_correct": conf,
        "actual_minus_expected": correct - conf,
    }


def high_probability_report(preds: Sequence[Prediction], thresholds: Sequence[float] = HIGH_PROBABILITY_THRESHOLDS) -> list[dict]:
    rows = []
    for t in thresholds:
        for side in ("YES", "NO", "EITHER"):
            sel = []
            for p in preds:
                s, prob = top_pick(p.p_yes)
                if prob >= t and (side == "EITHER" or s == side):
                    sel.append((prob, int((s == "YES") == (p.actual == 1))))
            n = len(sel)
            occ = sum(o for _, o in sel)
            mp = sum(pr for pr, _ in sel) / n if n else None
            lo, hi = wilson_interval(occ, n)
            rows.append(
                {
                    "threshold": t,
                    "side": side,
                    "n": n,
                    "mean_predicted_probability": mp,
                    "occurred": occ,
                    "actual_rate": occ / n if n else None,
                    "calibration_error_pp": (occ / n - mp) * 100 if n else None,
                    "wilson95_low": lo,
                    "wilson95_high": hi,
                }
            )
    return rows


def decile_calibration(preds: Sequence[Prediction]) -> list[dict]:
    edges = CALIBRATION_DECILE_EDGES
    rows = []
    for i in range(len(edges) - 1):
        lo, hi = edges[i], edges[i + 1]
        b = [p for p in preds if (lo <= p.p_yes < hi) or (i == len(edges) - 2 and p.p_yes == hi)]
        n = len(b)
        mp = sum(p.p_yes for p in b) / n if n else None
        ar = sum(p.actual for p in b) / n if n else None
        rows.append({"bin": f"{lo:.1f}-{hi:.1f}", "n": n, "mean_predicted": mp, "actual_rate": ar,
                     "gap_pp": (ar - mp) * 100 if n else None})
    return rows


def cohens_d(x_yes: Sequence[float], x_no: Sequence[float]) -> float | None:
    if len(x_yes) < 2 or len(x_no) < 2:
        return None
    a, b = np.asarray(x_yes, float), np.asarray(x_no, float)
    pooled = math.sqrt(((len(a) - 1) * a.var(ddof=1) + (len(b) - 1) * b.var(ddof=1)) / (len(a) + len(b) - 2))
    if pooled == 0:
        return None
    return float((a.mean() - b.mean()) / pooled)


def univariate_auc(values: Sequence[float], targets: Sequence[int]) -> float | None:
    """Rank-based AUC of a single feature for predicting BTTS YES (ties averaged)."""
    v = np.asarray(values, float)
    t = np.asarray(targets, int)
    n1, n0 = int(t.sum()), int((1 - t).sum())
    if n1 == 0 or n0 == 0:
        return None
    order = v.argsort(kind="mergesort")
    ranks = np.empty(len(v))
    sv = v[order]
    i = 0
    while i < len(v):
        j = i
        while j + 1 < len(v) and sv[j + 1] == sv[i]:
            j += 1
        ranks[order[i : j + 1]] = (i + j) / 2.0 + 1
        i = j + 1
    return float((ranks[t == 1].sum() - n1 * (n1 + 1) / 2) / (n1 * n0))
