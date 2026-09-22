"""Gate 1 football 1X2 probability-architecture comparison -- EXECUTION.

Runs exactly the protocol frozen and committed in
research/cycles/CYCLE_003_FOOTBALL/GATE1_PROBABILITY_ARCHITECTURE_PROTOCOL.md
(commit f960e5e). See that document for the full specification; this
script implements it without introducing any new modelling decision.

Writes data/processed/football/gate1_1x2_architecture_results.json.
"""

from __future__ import annotations

import csv
import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

from prediction_markets_lab.features.football_leakage_safe_features import (
    TeamMatchInput,
    compute_rolling_features,
)
from prediction_markets_lab.models.football_blended import (
    BlendWeights,
    blend_probabilities,
    calibrate_blend_weights,
)
from prediction_markets_lab.models.football_elo import (
    EloConfig,
    EloMatchInput,
    calibrate_draw_margin,
    simulate_pre_match_ratings,
    three_way_probabilities,
)
from prediction_markets_lab.models.football_poisson import (
    PoissonConfig,
    PoissonMatchInput,
    scoreline_probabilities_to_1x2,
    simulate_pre_match_lambdas,
)
from prediction_markets_lab.models.multinomial_logistic_regression import (
    fit_multinomial_logistic_regression,
)
from prediction_markets_lab.performance.binary_classification import (
    binary_auc,
    expected_calibration_error as binary_ece,
    binary_calibration_bins,
    fit_calibration_intercept_slope,
)
from prediction_markets_lab.performance.bootstrap import paired_bootstrap_mean_diff
from prediction_markets_lab.performance.brier import brier_score_single, multiclass_brier_score
from prediction_markets_lab.performance.calibration import compute_outcome_calibration
from prediction_markets_lab.performance.log_loss import OUTCOMES, log_loss_single, multiclass_log_loss
from prediction_markets_lab.validation.time_splits import generate_expanding_walk_forward_folds

REPO_ROOT = Path(__file__).resolve().parents[1]
PROC = REPO_ROOT / "data" / "processed" / "football"

RESULT_TO_OUTCOME = {"H": "home", "D": "draw", "A": "away"}
DRAW_MARGIN_CANDIDATES = [25.0, 50.0, 75.0, 100.0, 125.0, 150.0, 175.0, 200.0]
BLEND_STEP = 0.1
SEASONS_IN_ORDER = ["2020_21", "2021_22", "2022_23", "2023_24", "2024_25", "2025_26"]
MIN_BOOKMAKERS_FOR_CONSENSUS = 4
ROLLING_WINDOW = 10
BOOTSTRAP_SEED = 20260918
BOOTSTRAP_N_RESAMPLES = 2000

MODEL2_FEATURE_NAMES = [
    "elo_rating_gap_incl_home_advantage",
    "diff_avg_goals_for_last10",
    "diff_avg_shots_for_last10",
    "diff_avg_sot_for_last10",
    "diff_avg_corners_for_last10",
    "diff_avg_cards_for_last10",
    "diff_points_per_game_last10",
    "is_E1",
    "is_SC0",
]
MODEL3_FEATURE_NAMES = MODEL2_FEATURE_NAMES + ["market_home_logit", "market_draw_logit"]


def _f(v):
    if v is None or v == "":
        return None
    try:
        return float(v)
    except ValueError:
        return None


def _i(v):
    x = _f(v)
    return int(x) if x is not None else None


def load_csv(path: Path) -> list[dict]:
    with open(path, newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


# =====================================================================
# 1. Load and combine raw sources (nothing new acquired -- all files
#    already exist in the repository, see protocol section 2).
# =====================================================================

matches_old = load_csv(PROC / "cycle_001_matches_full.csv")
matches_new = load_csv(PROC / "h_fb2_002_sealed_oos_2025_26_matches.csv")
all_matches = matches_old + matches_new

stats_by_id = {s["match_id"]: s for s in load_csv(PROC / "cycle_002_match_statistics.csv")}
stats_by_id.update({s["match_id"]: s for s in load_csv(PROC / "h_fb2_002_sealed_oos_2025_26_match_statistics.csv")})

consensus_closing: dict[str, dict] = {}
for row in load_csv(PROC / "cycle_001_consensus_full.csv") + load_csv(PROC / "h_fb2_002_sealed_oos_2025_26_consensus.csv"):
    if row["price_timing"] == "closing":
        consensus_closing[row["match_id"]] = row

print(f"Loaded {len(all_matches)} raw match rows across {sorted(set(m['season'] for m in all_matches))}")

# Sort ALL matches in true global chronological order (required for the
# leakage-safe Elo/Poisson replays, which check this explicitly).
all_matches_sorted = sorted(all_matches, key=lambda m: (m["match_date"], m["match_id"]))


# =====================================================================
# 2. One continuous chronological replay of Elo, Poisson, and rolling
#    match-statistic features across all 6 seasons combined (protocol
#    section 2 -- deliberately NOT split by season, so 2025/26 correctly
#    inherits 2024/25 team state with no reset).
# =====================================================================

def cards_sum(stats: dict | None, side: str) -> int | None:
    if stats is None:
        return None
    y = _i(stats.get(f"{side}_yellow_cards"))
    r = _i(stats.get(f"{side}_red_cards"))
    return (y + r) if (y is not None and r is not None) else None


team_match_inputs: list[TeamMatchInput] = []
elo_inputs: list[EloMatchInput] = []
poisson_inputs: list[PoissonMatchInput] = []
skipped_bad_result = 0

for m in all_matches_sorted:
    ftr = m["full_time_result"]
    if ftr not in RESULT_TO_OUTCOME:
        skipped_bad_result += 1
        continue
    match_date = datetime.strptime(m["match_date"], "%Y-%m-%d").date()
    s = stats_by_id.get(m["match_id"])
    goals_home = _i(s.get("full_time_home_goals")) if s else None
    goals_away = _i(s.get("full_time_away_goals")) if s else None
    shots_home = _i(s.get("home_shots")) if s else None
    shots_away = _i(s.get("away_shots")) if s else None
    sot_home = _i(s.get("home_shots_on_target")) if s else None
    sot_away = _i(s.get("away_shots_on_target")) if s else None
    corners_home = _i(s.get("home_corners")) if s else None
    corners_away = _i(s.get("away_corners")) if s else None
    cards_home = cards_sum(s, "home")
    cards_away = cards_sum(s, "away")
    home_pts, away_pts = {"H": (3, 0), "D": (1, 1), "A": (0, 3)}[ftr]

    team_match_inputs.append(TeamMatchInput(
        match_id=m["match_id"], match_date=match_date, team=m["home_team_normalised"], is_home=True,
        goals_for=goals_home, goals_against=goals_away, shots_for=shots_home, shots_against=shots_away,
        shots_on_target_for=sot_home, shots_on_target_against=sot_away,
        corners_for=corners_home, corners_against=corners_away,
        cards_for=cards_home, cards_against=cards_away, result_points=home_pts,
    ))
    team_match_inputs.append(TeamMatchInput(
        match_id=m["match_id"], match_date=match_date, team=m["away_team_normalised"], is_home=False,
        goals_for=goals_away, goals_against=goals_home, shots_for=shots_away, shots_against=shots_home,
        shots_on_target_for=sot_away, shots_on_target_against=sot_home,
        corners_for=corners_away, corners_against=corners_home,
        cards_for=cards_away, cards_against=cards_home, result_points=away_pts,
    ))

    elo_inputs.append(EloMatchInput(
        match_id=m["match_id"], season=m["season"], match_date=match_date,
        home_team=m["home_team_normalised"], away_team=m["away_team_normalised"], full_time_result=ftr,
    ))

    if goals_home is not None and goals_away is not None:
        poisson_inputs.append(PoissonMatchInput(
            match_id=m["match_id"], season=m["season"], match_date=match_date,
            competition_code=m["competition_code"], home_team=m["home_team_normalised"],
            away_team=m["away_team_normalised"], home_goals=goals_home, away_goals=goals_away,
            full_time_result=ftr,
        ))

print(f"Skipped {skipped_bad_result} rows with an invalid full_time_result")
print(f"Built {len(elo_inputs)} Elo inputs, {len(poisson_inputs)} Poisson inputs (missing-goals rows excluded)")

rolling_features = compute_rolling_features(team_match_inputs, windows=(ROLLING_WINDOW,))
rolling_by_match_team = {(f.match_id, f.team): f for f in rolling_features}

elo_config = EloConfig()  # frozen defaults; draw_margin recalibrated per fold below
elo_replay = simulate_pre_match_ratings(elo_inputs, elo_config)
elo_pre_match = {m.match_id: (pre_home, pre_away) for m, pre_home, pre_away in elo_replay}

poisson_config = PoissonConfig()  # frozen defaults, no per-fold calibration
poisson_replay = simulate_pre_match_lambdas(poisson_inputs, poisson_config)
poisson_pre_match = {
    m.match_id: scoreline_probabilities_to_1x2(lh, la, poisson_config.max_goals)
    for m, lh, la in poisson_replay
}


# =====================================================================
# 3. Assemble one master record per match, with every fold-independent
#    quantity precomputed once. Fold-dependent quantities (draw_margin,
#    blend weights, Model 2/3 regression fits) are computed later, per
#    fold, on that fold's training rows only.
# =====================================================================

@dataclass
class MasterRecord:
    match_id: str
    competition_code: str
    season: str
    match_date: str
    home_team: str
    away_team: str
    outcome: str
    elo_home_rating: float
    elo_away_rating: float
    poisson_probs: dict
    market_probs: dict | None  # None if ineligible (bookmaker_count < MIN)
    bookmaker_count: int | None
    fundamentals: dict | None  # None if either team lacks a full 10-match window or a stat is missing
    home_appearance_number: int | None
    away_appearance_number: int | None


records: list[MasterRecord] = []
n_missing_market = 0
n_missing_fundamentals = 0

for m in all_matches_sorted:
    ftr = m["full_time_result"]
    if ftr not in RESULT_TO_OUTCOME:
        continue
    mid = m["match_id"]
    outcome = RESULT_TO_OUTCOME[ftr]

    home_feat = rolling_by_match_team.get((mid, m["home_team_normalised"]))
    away_feat = rolling_by_match_team.get((mid, m["away_team_normalised"]))
    home_snap = home_feat.overall[ROLLING_WINDOW] if home_feat else None
    away_snap = away_feat.overall[ROLLING_WINDOW] if away_feat else None

    fundamentals = None
    if (
        home_snap is not None and away_snap is not None
        and home_snap.matches_in_window == ROLLING_WINDOW and away_snap.matches_in_window == ROLLING_WINDOW
    ):
        required = [
            home_snap.avg_goals_for, away_snap.avg_goals_for,
            home_snap.avg_shots_for, away_snap.avg_shots_for,
            home_snap.avg_shots_on_target_for, away_snap.avg_shots_on_target_for,
            home_snap.avg_corners_for, away_snap.avg_corners_for,
            home_snap.avg_cards_for, away_snap.avg_cards_for,
            home_snap.points_per_game, away_snap.points_per_game,
        ]
        if all(v is not None for v in required):
            elo_home, elo_away = elo_pre_match[mid]
            fundamentals = {
                "elo_rating_gap_incl_home_advantage": (elo_home + elo_config.home_advantage) - elo_away,
                "diff_avg_goals_for_last10": home_snap.avg_goals_for - away_snap.avg_goals_for,
                "diff_avg_shots_for_last10": home_snap.avg_shots_for - away_snap.avg_shots_for,
                "diff_avg_sot_for_last10": home_snap.avg_shots_on_target_for - away_snap.avg_shots_on_target_for,
                "diff_avg_corners_for_last10": home_snap.avg_corners_for - away_snap.avg_corners_for,
                "diff_avg_cards_for_last10": home_snap.avg_cards_for - away_snap.avg_cards_for,
                "diff_points_per_game_last10": home_snap.points_per_game - away_snap.points_per_game,
                "is_E1": 1.0 if m["competition_code"] == "E1" else 0.0,
                "is_SC0": 1.0 if m["competition_code"] == "SC0" else 0.0,
            }
    if fundamentals is None:
        n_missing_fundamentals += 1

    consensus_row = consensus_closing.get(mid)
    market_probs = None
    bookmaker_count = None
    if consensus_row is not None:
        bookmaker_count = _i(consensus_row["bookmaker_count"])
        if bookmaker_count is not None and bookmaker_count >= MIN_BOOKMAKERS_FOR_CONSENSUS:
            ph = _f(consensus_row["median_fair_home_probability"])
            pd = _f(consensus_row["median_fair_draw_probability"])
            pa = _f(consensus_row["median_fair_away_probability"])
            total = ph + pd + pa
            market_probs = {"home": ph / total, "draw": pd / total, "away": pa / total}
    if market_probs is None:
        n_missing_market += 1

    elo_home, elo_away = elo_pre_match[mid]
    records.append(MasterRecord(
        match_id=mid, competition_code=m["competition_code"], season=m["season"],
        match_date=m["match_date"], home_team=m["home_team_normalised"], away_team=m["away_team_normalised"],
        outcome=outcome, elo_home_rating=elo_home, elo_away_rating=elo_away,
        poisson_probs=poisson_pre_match[mid], market_probs=market_probs, bookmaker_count=bookmaker_count,
        fundamentals=fundamentals,
        home_appearance_number=home_feat.appearance_number if home_feat else None,
        away_appearance_number=away_feat.appearance_number if away_feat else None,
    ))

print(f"Assembled {len(records)} master records")
print(f"  missing/insufficient market consensus: {n_missing_market}")
print(f"  missing full 10-match fundamentals window or stat: {n_missing_fundamentals}")

# Primary Gate 1 eligibility: BOTH market and fundamentals available, so
# every model in the comparison is evaluated on the identical sample
# (protocol section 4).
eligible = [r for r in records if r.market_probs is not None and r.fundamentals is not None]
print(f"Primary Gate 1 eligible sample: {len(eligible)} of {len(records)} raw matches")

by_season: dict[str, list[MasterRecord]] = {}
for r in eligible:
    by_season.setdefault(r.season, []).append(r)
for season in SEASONS_IN_ORDER:
    print(f"  {season}: {len(by_season.get(season, []))} eligible")


# =====================================================================
# 4. Walk-forward folds and per-fold model fitting/evaluation.
# =====================================================================

folds = generate_expanding_walk_forward_folds(SEASONS_IN_ORDER)


def add_market_logit_features(base_features: dict, market_probs: dict) -> dict:
    out = dict(base_features)
    out["market_home_logit"] = float(np.log(market_probs["home"] / market_probs["away"]))
    out["market_draw_logit"] = float(np.log(market_probs["draw"] / market_probs["away"]))
    return out


def to_matrix(rows: list[MasterRecord], feature_names: list[str], with_market_logits: bool) -> np.ndarray:
    matrix = []
    for r in rows:
        feats = r.fundamentals
        if with_market_logits:
            feats = add_market_logit_features(feats, r.market_probs)
        matrix.append([feats[name] for name in feature_names])
    return np.array(matrix, dtype=float)


fold_results = []
per_match_predictions: list[dict] = []  # flattened, one row per (match, all model probs) for every eval row across all folds

for fold in folds:
    train_rows = [r for r in eligible if r.season in fold.train_seasons]
    eval_rows = by_season.get(fold.evaluate_season, [])
    if not train_rows or not eval_rows:
        raise ValueError(f"fold {fold.fold_id} has an empty train or eval set -- protocol violation")

    train_elo_inputs = [
        EloMatchInput(match_id=r.match_id, season=r.season,
                      match_date=datetime.strptime(r.match_date, "%Y-%m-%d").date(),
                      home_team=r.home_team, away_team=r.away_team,
                      full_time_result={"home": "H", "draw": "D", "away": "A"}[r.outcome])
        for r in [rec for rec in eligible if rec.season in fold.train_seasons]
    ]
    # calibrate_draw_margin re-simulates ratings on exactly this contiguous
    # training prefix -- identical to the master continuous replay's own
    # prefix for the same span (protocol section 5).
    draw_margin = calibrate_draw_margin(train_elo_inputs, elo_config, DRAW_MARGIN_CANDIDATES)

    def elo_probs_for(r: MasterRecord) -> dict:
        return three_way_probabilities(r.elo_home_rating, r.elo_away_rating, elo_config.home_advantage, draw_margin)

    train_actuals = [r.outcome for r in train_rows]
    train_elo_preds = [elo_probs_for(r) for r in train_rows]
    train_poisson_preds = [r.poisson_probs for r in train_rows]
    blend_weights_model1 = calibrate_blend_weights(
        {"elo": train_elo_preds, "poisson": train_poisson_preds}, train_actuals, step=BLEND_STEP
    )

    # Model 2: fundamentals-only.
    X_train_m2 = to_matrix(train_rows, MODEL2_FEATURE_NAMES, with_market_logits=False)
    model2 = fit_multinomial_logistic_regression(
        X_train_m2, train_actuals, MODEL2_FEATURE_NAMES, classes=OUTCOMES, seed=0
    )

    # Model 3: market + fundamentals.
    X_train_m3 = to_matrix(train_rows, MODEL3_FEATURE_NAMES, with_market_logits=True)
    model3 = fit_multinomial_logistic_regression(
        X_train_m3, train_actuals, MODEL3_FEATURE_NAMES, classes=OUTCOMES, seed=0
    )

    # Model 4: calibrated ensemble of Model 0 (market) + Model 2 (fundamentals), grid-searched on training predictions.
    train_market_preds = [r.market_probs for r in train_rows]
    train_model2_preds = model2.predict_proba_dict(X_train_m2)
    blend_weights_model4 = calibrate_blend_weights(
        {"market": train_market_preds, "fundamentals": train_model2_preds}, train_actuals, step=BLEND_STEP
    )

    fold_eval_predictions = []
    for r in eval_rows:
        elo_p = elo_probs_for(r)
        poisson_p = r.poisson_probs
        model1_p = blend_probabilities({"elo": elo_p, "poisson": poisson_p}, blend_weights_model1)
        model0_p = r.market_probs
        feats2 = r.fundamentals
        feats3 = add_market_logit_features(feats2, r.market_probs)
        model2_p = model2.predict_proba_dict(np.array([[feats2[n] for n in MODEL2_FEATURE_NAMES]]))[0]
        model3_p = model3.predict_proba_dict(np.array([[feats3[n] for n in MODEL3_FEATURE_NAMES]]))[0]
        model4_p = blend_probabilities({"market": model0_p, "fundamentals": model2_p}, blend_weights_model4)

        row_out = {
            "match_id": r.match_id, "competition_code": r.competition_code, "season": r.season,
            "outcome": r.outcome,
            "model_0_market": model0_p, "model_1_elo_poisson_blend": model1_p,
            "model_2_fundamentals": model2_p, "model_3_market_fundamentals": model3_p,
            "model_4_ensemble": model4_p,
        }
        fold_eval_predictions.append(row_out)
        per_match_predictions.append(row_out)

    fold_results.append({
        "fold_id": fold.fold_id,
        "train_seasons": list(fold.train_seasons),
        "evaluate_season": fold.evaluate_season,
        "n_train": len(train_rows),
        "n_eval": len(eval_rows),
        "draw_margin": draw_margin,
        "blend_weights_model1": blend_weights_model1.weights,
        "blend_weights_model4": blend_weights_model4.weights,
        "model2_n_iterations": model2.n_iterations,
        "model2_final_max_gradient_norm": model2.final_max_gradient_norm,
        "model3_n_iterations": model3.n_iterations,
        "model3_final_max_gradient_norm": model3.final_max_gradient_norm,
    })
    print(f"Fold {fold.fold_id}: n_train={len(train_rows)} n_eval={len(eval_rows)} "
          f"draw_margin={draw_margin} blend1={blend_weights_model1.weights} blend4={blend_weights_model4.weights}")

print(f"Total out-of-sample eligible predictions across all folds: {len(per_match_predictions)}")


# =====================================================================
# 5. Metrics: pooled + per-fold (temporal) + per-competition, per model.
# =====================================================================

MODEL_KEYS = {
    "market_consensus_baseline": "model_0_market",
    "existing_elo_poisson_blend": "model_1_elo_poisson_blend",
    "fundamentals_only": "model_2_fundamentals",
    "market_plus_fundamentals": "model_3_market_fundamentals",
    "calibrated_ensemble": "model_4_ensemble",
}

all_actuals = [row["outcome"] for row in per_match_predictions]


def per_match_log_loss(rows: list[dict], key: str) -> list[float]:
    return [log_loss_single(row[key], row["outcome"]) for row in rows]


def per_match_brier(rows: list[dict], key: str) -> list[float]:
    return [brier_score_single(row[key], row["outcome"]) for row in rows]


pooled_metrics = {}
per_match_losses = {}  # model_name -> list of per-match log losses, pooled, SAME row order as per_match_predictions
per_match_briers = {}

for name, key in MODEL_KEYS.items():
    preds = [row[key] for row in per_match_predictions]
    ll_series = per_match_log_loss(per_match_predictions, key)
    brier_series = per_match_brier(per_match_predictions, key)
    per_match_losses[name] = ll_series
    per_match_briers[name] = brier_series

    outcome_calibration = {}
    for outcome in OUTCOMES:
        predicted_p = [p[outcome] for p in preds]
        actual_ind = [1 if a == outcome else 0 for a in all_actuals]
        intercept, slope = fit_calibration_intercept_slope(predicted_p, actual_ind)
        auc = binary_auc(predicted_p, actual_ind)
        bins = binary_calibration_bins(predicted_p, actual_ind, n_bins=10)
        ece = binary_ece(bins)
        report = compute_outcome_calibration(preds, all_actuals, outcome, n_bins=10)
        outcome_calibration[outcome] = {
            "calibration_intercept": intercept,
            "calibration_slope": slope,
            "auc": auc,
            "ece": ece,
            "n": len(predicted_p),
            "bins": [
                {"bin_index": b.bin_index, "n": b.n, "mean_predicted_probability": b.mean_predicted_probability,
                 "observed_frequency": b.observed_frequency}
                for b in report.bins
            ],
        }

    per_competition = {}
    for comp in ["E0", "E1", "SC0"]:
        comp_rows = [row for row in per_match_predictions if row["competition_code"] == comp]
        if not comp_rows:
            continue
        per_competition[comp] = {
            "n": len(comp_rows),
            "log_loss": multiclass_log_loss([row[key] for row in comp_rows], [row["outcome"] for row in comp_rows]),
            "brier_score": multiclass_brier_score([row[key] for row in comp_rows], [row["outcome"] for row in comp_rows]),
        }

    per_fold_temporal = {}
    for fold in folds:
        season_rows = [row for row in per_match_predictions if row["season"] == fold.evaluate_season]
        if not season_rows:
            continue
        per_fold_temporal[fold.evaluate_season] = {
            "n": len(season_rows),
            "log_loss": multiclass_log_loss([row[key] for row in season_rows], [row["outcome"] for row in season_rows]),
            "brier_score": multiclass_brier_score([row[key] for row in season_rows], [row["outcome"] for row in season_rows]),
        }

    pooled_metrics[name] = {
        "n": len(per_match_predictions),
        "log_loss": multiclass_log_loss(preds, all_actuals),
        "brier_score": multiclass_brier_score(preds, all_actuals),
        "outcome_calibration": outcome_calibration,
        "per_competition": per_competition,
        "per_fold_temporal_stability": per_fold_temporal,
    }
    print(f"{name}: pooled log_loss={pooled_metrics[name]['log_loss']:.5f} "
          f"brier={pooled_metrics[name]['brier_score']:.5f}")


# =====================================================================
# 6. Pairwise bootstrap comparisons (paired, same matches, protocol section 8).
# =====================================================================

pairwise_comparisons = {}
comparison_pairs = [
    ("existing_elo_poisson_blend", "market_consensus_baseline"),
    ("fundamentals_only", "market_consensus_baseline"),
    ("market_plus_fundamentals", "market_consensus_baseline"),
    ("market_plus_fundamentals", "fundamentals_only"),
    ("calibrated_ensemble", "market_consensus_baseline"),
]
for model_a, model_b in comparison_pairs:
    ll_result = paired_bootstrap_mean_diff(
        per_match_losses[model_a], per_match_losses[model_b], seed=BOOTSTRAP_SEED, n_resamples=BOOTSTRAP_N_RESAMPLES
    )
    brier_result = paired_bootstrap_mean_diff(
        per_match_briers[model_a], per_match_briers[model_b], seed=BOOTSTRAP_SEED, n_resamples=BOOTSTRAP_N_RESAMPLES
    )
    pairwise_comparisons[f"{model_a}_minus_{model_b}"] = {
        "log_loss_diff": {
            "point_estimate": ll_result.point_estimate, "ci_lower": ll_result.ci_lower,
            "ci_upper": ll_result.ci_upper, "excludes_zero": ll_result.excludes_zero,
        },
        "brier_diff": {
            "point_estimate": brier_result.point_estimate, "ci_lower": brier_result.ci_lower,
            "ci_upper": brier_result.ci_upper, "excludes_zero": brier_result.excludes_zero,
        },
    }
    print(f"{model_a} vs {model_b}: log_loss diff={ll_result.point_estimate:+.5f} "
          f"CI=[{ll_result.ci_lower:+.5f},{ll_result.ci_upper:+.5f}] excludes_zero={ll_result.excludes_zero}")


# =====================================================================
# 7. Write results.
# =====================================================================

output = {
    "generated_at": datetime.now(timezone.utc).isoformat(),
    "protocol_commit": "f960e5e",
    "seasons_in_order": SEASONS_IN_ORDER,
    "min_bookmakers_for_consensus": MIN_BOOKMAKERS_FOR_CONSENSUS,
    "rolling_window": ROLLING_WINDOW,
    "raw_match_rows": len(all_matches),
    "skipped_bad_result": skipped_bad_result,
    "n_master_records": len(records),
    "n_missing_market_consensus": n_missing_market,
    "n_missing_fundamentals_window": n_missing_fundamentals,
    "n_eligible_primary_sample": len(eligible),
    "eligible_by_season": {s: len(by_season.get(s, [])) for s in SEASONS_IN_ORDER},
    "model2_feature_names": MODEL2_FEATURE_NAMES,
    "model3_feature_names": MODEL3_FEATURE_NAMES,
    "draw_margin_candidates": DRAW_MARGIN_CANDIDATES,
    "blend_step": BLEND_STEP,
    "bootstrap_seed": BOOTSTRAP_SEED,
    "bootstrap_n_resamples": BOOTSTRAP_N_RESAMPLES,
    "folds": fold_results,
    "pooled_metrics": pooled_metrics,
    "pairwise_comparisons": pairwise_comparisons,
}

out_path = PROC / "gate1_1x2_architecture_results.json"
with open(out_path, "w", encoding="utf-8") as fh:
    json.dump(output, fh, indent=2)
print(f"Wrote {out_path}")

# =====================================================================
# 8. Optional Phase 2 diagnostic extension (added 2026-09-22, additive,
#    off by default -- a normal Gate 1 rerun is byte-for-byte
#    unaffected unless PMLAB_DUMP_PER_MATCH_PREDICTIONS is set).
#
# Dumps the per-match, per-model out-of-sample predictions this script
# already computes in memory (per_match_predictions) to a CSV, so a
# separate, later analysis (research/probability_model_v2/, per the
# "PHASE 2 -- INDEPENDENT FOOTBALL PROBABILITY MODEL RESEARCH"
# instruction's Sections 13 and 15) can compute high-probability-region
# and disagreement-band diagnostics WITHOUT re-fitting or re-specifying
# any model here -- avoiding any risk of the diagnostic reproduction
# silently drifting from this frozen, already-published comparison.
# =====================================================================
import os as _os

_dump_path = _os.environ.get("PMLAB_DUMP_PER_MATCH_PREDICTIONS")
if _dump_path:
    import csv as _csv

    _fieldnames = ["match_id", "competition_code", "season", "outcome"] + [
        f"{_key}_{_outcome}" for _key in MODEL_KEYS.values() for _outcome in OUTCOMES
    ]
    with open(_dump_path, "w", newline="", encoding="utf-8") as _fh:
        _writer = _csv.DictWriter(_fh, fieldnames=_fieldnames)
        _writer.writeheader()
        for _row in per_match_predictions:
            _out_row = {
                "match_id": _row["match_id"],
                "competition_code": _row["competition_code"],
                "season": _row["season"],
                "outcome": _row["outcome"],
            }
            for _key in MODEL_KEYS.values():
                for _outcome in OUTCOMES:
                    _out_row[f"{_key}_{_outcome}"] = _row[_key][_outcome]
            _writer.writerow(_out_row)
    print(f"Wrote per-match predictions to {_dump_path}")

