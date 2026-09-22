"""Gate 1b -- football Over/Under 2.5 total-goals probability-architecture
comparison (Phase 4, Multi-Market Expansion for Outcome Prediction, 2026-09-22).

Applies Gate 1's own methodology (2026-09-18, football 1X2) to a genuinely
different market family: Over/Under 2.5 total goals is a natively BINARY
occurred/not-occurred target, unlike 1X2's three-way outcome, so this module
deliberately reuses the project's existing BINARY tooling (built for tennis
Match Winner) rather than the 3-outcome multinomial tooling Gate 1 used:

  - prediction_markets_lab.models.logistic_regression.fit_logistic_regression
    (existing binary IRLS fit -- no new model architecture written here)
  - prediction_markets_lab.validation.time_splits.generate_expanding_walk_forward_folds
    (identical fold construction to Gate 1, reused unchanged)
  - prediction_markets_lab.performance.binary_classification (log loss, Brier,
    quantile calibration bins, ECE, AUC -- reused unchanged)
  - prediction_markets_lab.performance.bootstrap.paired_bootstrap_mean_diff
    (same paired bootstrap Gate 1 used for model-vs-market comparisons)

Only the OU2.5-specific pieces are new: target construction from actual full
time goals, the fundamentals feature set relevant to goal-scoring (rather than
match-result), and fixed-probability-band calibration reporting (Section 15 of
the operator's Phase 4 instruction; the existing binary_calibration_bins is
quantile-based, not fixed-band, so it does not cover this reporting need).

This module performs NO file I/O -- see scripts/run_gate1b_ou25_probability_
architecture_comparison.py for loading cycle_002_discovery_features.csv and
writing results.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from prediction_markets_lab.models.logistic_regression import (
    FittedLogisticModel,
    fit_logistic_regression,
)
from prediction_markets_lab.validation.time_splits import (
    WalkForwardFold,
    generate_expanding_walk_forward_folds,
)

# ---------------------------------------------------------------------------
# Feature / field definitions
# ---------------------------------------------------------------------------

# Pre-match rolling fundamentals directly relevant to goal-scoring (Section 7
# of the operator's Phase 4 instruction: rolling goals scored/conceded,
# shots, SOT, attack/defence strength proxies). Deliberately excludes cards
# (weakest, least goal-relevant signal in the Outcome Discovery cycle's own
# winner/loser analysis) and the last5 window (last10 preferred there too, for
# the same reason -- larger, more stable sample). Elo gap is included as a
# single team-strength-mismatch summary feature per Section 7's own listing.
FUNDAMENTALS_FEATURES: tuple[str, ...] = (
    "home_team_overall_last10_avg_goals_for",
    "home_team_overall_last10_avg_goals_against",
    "home_team_overall_last10_avg_shots_for",
    "home_team_overall_last10_avg_shots_against",
    "home_team_overall_last10_avg_sot_for",
    "home_team_overall_last10_avg_sot_against",
    "home_team_overall_last10_avg_corners_for",
    "home_team_overall_last10_avg_corners_against",
    "home_team_overall_last10_points_per_game",
    "away_team_overall_last10_avg_goals_for",
    "away_team_overall_last10_avg_goals_against",
    "away_team_overall_last10_avg_shots_for",
    "away_team_overall_last10_avg_shots_against",
    "away_team_overall_last10_avg_sot_for",
    "away_team_overall_last10_avg_sot_against",
    "away_team_overall_last10_avg_corners_for",
    "away_team_overall_last10_avg_corners_against",
    "away_team_overall_last10_points_per_game",
    "elo_rating_gap_incl_home_advantage",
)

# The existing cycle_002_discovery_features.csv already carries a per-match,
# de-vigged, closing-snapshot Over 2.5 probability averaged across whatever
# bookmakers quoted it (2-3 per match -- confirmed too thin for the
# production min_bookmakers=3 consensus floor, see
# research/data_expansion/EXHAUSTED_VS_OPEN_RESEARCH.md). This is used here
# ONLY as a research-grade "Model A" input, explicitly labelled thin-panel,
# never conflated with a production-grade consensus.
MARKET_PROBABILITY_FIELD = "market_ou25_closing_source_avg_over_probability"
MARKET_BOOKMAKER_COUNT_FIELD = "market_ou25_closing_individual_bookmaker_count"

SEASONS_IN_ORDER: tuple[str, ...] = (
    "2020_21",
    "2021_22",
    "2022_23",
    "2023_24",
    "2024_25",
)
DISCOVERY_SEASONS = {"2020_21", "2021_22", "2022_23"}
VALIDATION_SEASON = "2023_24"
HOLDOUT_SEASON = "2024_25"  # last available season -- see module docstring caveat below

# Section 15's fixed probability bands (distinct from binary_classification's
# quantile-based binary_calibration_bins, which cannot produce these exact,
# operator-specified, comparable-across-models edges).
CALIBRATION_BAND_EDGES: tuple[tuple[float, float, str], ...] = (
    (0.0, 0.50, "<50%"),
    (0.50, 0.55, "50-54.9%"),
    (0.55, 0.60, "55-59.9%"),
    (0.60, 0.65, "60-64.9%"),
    (0.65, 0.70, "65-69.9%"),
    (0.70, 0.80, "70-79.9%"),
    (0.80, 1.0001, "80%+"),
)

DEFAULT_L2_PENALTY = 1e-6


def _to_float(v: object) -> float | None:
    if v is None or v == "":
        return None
    try:
        return float(v)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return None


@dataclass(frozen=True)
class Candidate:
    """One match's Over/Under 2.5 candidate: a single binary target (unlike
    1X2's three per-match candidates), since Over and Under are complements
    of the same event, not independent propositions."""

    match_id: str
    season: str
    match_date: str
    target: int  # 1 if total goals > 2.5, else 0
    total_goals: float
    market_probability: float | None  # research-grade thin-panel P(Over 2.5)
    market_bookmaker_count: int | None
    fundamentals: tuple[float, ...] | None  # None if any listed feature is missing


def build_candidate(row: dict[str, str]) -> Candidate | None:
    """Build one Candidate from a cycle_002_discovery_features.csv row.

    Returns None only if the match's actual result (total goals) is
    missing -- every other field may be individually absent; callers
    filter per-model on that (a candidate with no market quote can still
    be used to fit/evaluate the fundamentals-only model, and vice versa).
    """
    home_goals = _to_float(row.get("outcome_full_time_home_goals"))
    away_goals = _to_float(row.get("outcome_full_time_away_goals"))
    if home_goals is None or away_goals is None:
        return None
    total = home_goals + away_goals
    target = 1 if total > 2.5 else 0

    market_probability = _to_float(row.get(MARKET_PROBABILITY_FIELD))
    market_count_raw = _to_float(row.get(MARKET_BOOKMAKER_COUNT_FIELD))
    market_bookmaker_count = int(market_count_raw) if market_count_raw is not None else None

    feature_values = [_to_float(row.get(name)) for name in FUNDAMENTALS_FEATURES]
    fundamentals = (
        tuple(feature_values) if all(v is not None for v in feature_values) else None  # type: ignore[misc]
    )

    return Candidate(
        match_id=row["match_id"],
        season=row["season"],
        match_date=row["match_date"],
        target=target,
        total_goals=total,
        market_probability=market_probability,
        market_bookmaker_count=market_bookmaker_count,
        fundamentals=fundamentals,
    )


def partition_season(season: str) -> str:
    if season in DISCOVERY_SEASONS:
        return "discovery"
    if season == VALIDATION_SEASON:
        return "validation"
    if season == HOLDOUT_SEASON:
        return "holdout"
    return "unknown"


def calibration_band_for(probability: float) -> str:
    for lo, hi, label in CALIBRATION_BAND_EDGES:
        if lo <= probability < hi:
            return label
    return CALIBRATION_BAND_EDGES[-1][2]


def naive_frequency_baseline(train_candidates: list[Candidate]) -> float:
    """Historical base rate of Over 2.5 among the given (training) candidates."""
    if not train_candidates:
        raise ValueError("cannot compute a naive baseline on zero training candidates")
    return sum(c.target for c in train_candidates) / len(train_candidates)


# ---------------------------------------------------------------------------
# Per-fold model fitting / prediction
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Prediction:
    match_id: str
    season: str
    predicted_probability: float
    actual: int


def predict_naive(train: list[Candidate], evaluate: list[Candidate]) -> list[Prediction]:
    rate = naive_frequency_baseline(train)
    return [Prediction(c.match_id, c.season, rate, c.target) for c in evaluate]


def predict_market(evaluate: list[Candidate]) -> list[Prediction]:
    """Zero-parameter: the market's own thin-panel probability, used directly
    (no fitting/recalibration) -- exactly how Gate 1 used market consensus."""
    return [
        Prediction(c.match_id, c.season, c.market_probability, c.target)
        for c in evaluate
        if c.market_probability is not None
    ]


def _fit_and_predict(
    train: list[Candidate],
    evaluate: list[Candidate],
    feature_of: "callable[[Candidate], tuple[float, ...] | None]",
    l2_penalty: float,
) -> tuple[FittedLogisticModel, list[Prediction]]:
    train_rows = [(feature_of(c), c.target) for c in train]
    train_rows = [(f, t) for f, t in train_rows if f is not None]
    if not train_rows:
        raise ValueError("no training rows with complete features")
    X_train = np.array([f for f, _ in train_rows], dtype=float)
    y_train = [t for _, t in train_rows]
    n_features = X_train.shape[1]
    feature_names = [f"f{i}" for i in range(n_features)]
    model = fit_logistic_regression(
        X_train, y_train, feature_names, l2_penalty=l2_penalty
    )

    preds = []
    for c in evaluate:
        f = feature_of(c)
        if f is None:
            continue
        p = float(model.predict_proba(np.array(f, dtype=float))[0])
        preds.append(Prediction(c.match_id, c.season, p, c.target))
    return model, preds


def predict_fundamentals(
    train: list[Candidate], evaluate: list[Candidate], l2_penalty: float = DEFAULT_L2_PENALTY
) -> tuple[FittedLogisticModel, list[Prediction]]:
    return _fit_and_predict(train, evaluate, lambda c: c.fundamentals, l2_penalty)


def predict_market_fundamentals(
    train: list[Candidate], evaluate: list[Candidate], l2_penalty: float = DEFAULT_L2_PENALTY
) -> tuple[FittedLogisticModel, list[Prediction]]:
    def feature_of(c: Candidate) -> tuple[float, ...] | None:
        if c.fundamentals is None or c.market_probability is None:
            return None
        return c.fundamentals + (c.market_probability,)

    return _fit_and_predict(train, evaluate, feature_of, l2_penalty)


@dataclass(frozen=True)
class WalkForwardResults:
    folds: tuple[WalkForwardFold, ...]
    pooled_predictions: dict[str, list[Prediction]]  # model_key -> pooled OOS predictions


MODEL_KEYS = ("naive", "market", "fundamentals", "market_fundamentals")


def run_walk_forward_comparison(
    candidates: list[Candidate],
    seasons_in_order: tuple[str, ...] = SEASONS_IN_ORDER,
    l2_penalty: float = DEFAULT_L2_PENALTY,
) -> WalkForwardResults:
    """Expanding walk-forward comparison across all four models, pooling
    out-of-sample predictions across every fold (Gate 1's own pooling
    convention). Each model is filtered to the candidates it can actually
    score (e.g. "market" only scores candidates with a market quote) --
    pooled counts can therefore differ slightly between models, exactly the
    situation Gate 1 also had for its market-vs-fundamentals comparison."""
    folds = generate_expanding_walk_forward_folds(list(seasons_in_order))
    by_season: dict[str, list[Candidate]] = {}
    for c in candidates:
        by_season.setdefault(c.season, []).append(c)

    pooled: dict[str, list[Prediction]] = {k: [] for k in MODEL_KEYS}
    for fold in folds:
        train = [c for s in fold.train_seasons for c in by_season.get(s, [])]
        evaluate = by_season.get(fold.evaluate_season, [])
        if not train or not evaluate:
            continue
        pooled["naive"].extend(predict_naive(train, evaluate))
        pooled["market"].extend(predict_market(evaluate))
        _, fpreds = predict_fundamentals(train, evaluate, l2_penalty)
        pooled["fundamentals"].extend(fpreds)
        _, mfpreds = predict_market_fundamentals(train, evaluate, l2_penalty)
        pooled["market_fundamentals"].extend(mfpreds)

    return WalkForwardResults(folds=tuple(folds), pooled_predictions=pooled)


def fixed_band_calibration_report(predictions: list[Prediction]) -> list[dict]:
    """Section 15 fixed-band calibration table: for each band, n, mean
    predicted probability, actual occurrence rate, calibration error.
    Empty bands are reported with n=0, never dropped (mirrors the
    Outcome Discovery cycle's probability_bands_report convention)."""
    buckets: dict[str, list[Prediction]] = {label: [] for _, _, label in CALIBRATION_BAND_EDGES}
    for p in predictions:
        buckets[calibration_band_for(p.predicted_probability)].append(p)

    report = []
    for _, _, label in CALIBRATION_BAND_EDGES:
        bucket = buckets[label]
        if not bucket:
            report.append(
                {
                    "band": label,
                    "n": 0,
                    "mean_predicted_probability": None,
                    "actual_occurrence_rate": None,
                    "calibration_error_pp": None,
                }
            )
            continue
        mean_p = sum(p.predicted_probability for p in bucket) / len(bucket)
        actual_rate = sum(p.actual for p in bucket) / len(bucket)
        report.append(
            {
                "band": label,
                "n": len(bucket),
                "mean_predicted_probability": mean_p,
                "actual_occurrence_rate": actual_rate,
                "calibration_error_pp": (actual_rate - mean_p) * 100.0,
            }
        )
    return report


def top_misses(predictions: list[Prediction], n: int = 20) -> list[dict]:
    """The n highest-confidence WRONG predictions (largest single-prediction
    log loss), for error analysis (Section 17)."""
    from prediction_markets_lab.performance.binary_classification import (
        binary_log_loss_single,
    )

    scored = [
        {
            "match_id": p.match_id,
            "season": p.season,
            "predicted_probability": p.predicted_probability,
            "actual": p.actual,
            "log_loss": binary_log_loss_single(p.predicted_probability, p.actual),
        }
        for p in predictions
    ]
    scored.sort(key=lambda r: r["log_loss"], reverse=True)
    return scored[:n]


def accuracy_at_threshold(predictions: list[Prediction], threshold: float = 0.5) -> float:
    if not predictions:
        raise ValueError("cannot compute accuracy over zero predictions")
    correct = sum(1 for p in predictions if int(p.predicted_probability >= threshold) == p.actual)
    return correct / len(predictions)
