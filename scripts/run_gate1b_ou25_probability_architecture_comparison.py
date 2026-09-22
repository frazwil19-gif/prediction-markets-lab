"""Gate 1b execution -- football Over/Under 2.5 probability-architecture
comparison (Phase 4, Multi-Market Expansion for Outcome Prediction, 2026-09-22).

Reads ONLY the existing, already-built cycle_002_discovery_features.csv
(Cycle 2's leakage-safe pre-match feature build, unchanged, unmodified).
Fetches nothing, purchases nothing, modifies no upstream file. Writes results
to research/ou25_discovery/.

Mirrors run_gate1_1x2_probability_architecture_comparison.py's own structure
and pooling convention, applied via the new
prediction_markets_lab.research.ou25_probability_architecture module (binary-
target reuse of existing logistic regression / walk-forward / binary metrics
/ bootstrap tooling -- see that module's docstring for the full reuse list).
"""

from __future__ import annotations

import csv
import json
from datetime import datetime, timezone
from pathlib import Path

from prediction_markets_lab.performance.binary_classification import (
    binary_auc,
    binary_brier_score,
    binary_calibration_bins,
    binary_log_loss,
    expected_calibration_error,
)
from prediction_markets_lab.performance.bootstrap import paired_bootstrap_mean_diff
from prediction_markets_lab.research.ou25_probability_architecture import (
    Candidate,
    MODEL_KEYS,
    Prediction,
    accuracy_at_threshold,
    build_candidate,
    fixed_band_calibration_report,
    partition_season,
    run_walk_forward_comparison,
    top_misses,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
FEATURES_PATH = REPO_ROOT / "data" / "processed" / "football" / "cycle_002_discovery_features.csv"
OUTPUT_DIR = REPO_ROOT / "research" / "ou25_discovery"


def load_candidates() -> list[Candidate]:
    with open(FEATURES_PATH, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    candidates = []
    for row in rows:
        c = build_candidate(row)
        if c is not None:
            candidates.append(c)
    return candidates


def _write_csv(path: Path, rows: list[dict]) -> None:
    if not rows:
        path.write_text("")
        return
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def _model_metrics(preds: list[Prediction]) -> dict:
    if not preds:
        return {"n": 0}
    probs = [p.predicted_probability for p in preds]
    actuals = [p.actual for p in preds]
    bins = binary_calibration_bins(probs, actuals, n_bins=min(10, max(2, len(preds) // 50 or 2)))
    return {
        "n": len(preds),
        "log_loss": binary_log_loss(probs, actuals),
        "brier_score": binary_brier_score(probs, actuals),
        "ece_quantile_bins": expected_calibration_error(bins),
        "auc": binary_auc(probs, actuals),
        "accuracy_at_0.5": accuracy_at_threshold(preds),
        "mean_predicted_probability": sum(probs) / len(probs),
        "actual_occurrence_rate": sum(actuals) / len(actuals),
    }


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    candidates = load_candidates()

    by_partition = {"discovery": 0, "validation": 0, "holdout": 0, "unknown": 0}
    for c in candidates:
        by_partition[partition_season(c.season)] += 1

    results = run_walk_forward_comparison(candidates)

    pooled_metrics = {k: _model_metrics(v) for k, v in results.pooled_predictions.items()}

    # Sealed-holdout-only metrics (2024_25 evaluate-season fold only), and
    # validation-only (2023_24), reported SEPARATELY from the pooled figure
    # -- never blended, per this project's chronological-honesty discipline.
    holdout_only = {
        k: _model_metrics([p for p in v if p.season == "2024_25"])
        for k, v in results.pooled_predictions.items()
    }
    validation_only = {
        k: _model_metrics([p for p in v if p.season == "2023_24"])
        for k, v in results.pooled_predictions.items()
    }

    # Bootstrap: market vs fundamentals, market vs market_fundamentals --
    # paired on the intersection of match_ids both models actually scored.
    def paired_log_loss_diff(key_a: str, key_b: str, seed: int) -> dict:
        preds_a = {p.match_id: p for p in results.pooled_predictions[key_a]}
        preds_b = {p.match_id: p for p in results.pooled_predictions[key_b]}
        common = sorted(set(preds_a) & set(preds_b))
        if len(common) < 10:
            return {"n_paired": len(common), "note": "too few paired matches for bootstrap"}
        from prediction_markets_lab.performance.binary_classification import (
            binary_log_loss_single,
        )

        losses_a = [binary_log_loss_single(preds_a[m].predicted_probability, preds_a[m].actual) for m in common]
        losses_b = [binary_log_loss_single(preds_b[m].predicted_probability, preds_b[m].actual) for m in common]
        res = paired_bootstrap_mean_diff(losses_a, losses_b, seed=seed)
        return {
            "n_paired": len(common),
            "point_estimate_a_minus_b": res.point_estimate,
            "ci_lower": res.ci_lower,
            "ci_upper": res.ci_upper,
            "excludes_zero": res.excludes_zero,
        }

    bootstrap = {
        "fundamentals_minus_market": paired_log_loss_diff("fundamentals", "market", seed=42),
        "market_fundamentals_minus_market": paired_log_loss_diff("market_fundamentals", "market", seed=43),
        "fundamentals_minus_naive": paired_log_loss_diff("fundamentals", "naive", seed=44),
    }

    calibration_rows = []
    for model_key in MODEL_KEYS:
        for band_row in fixed_band_calibration_report(results.pooled_predictions[model_key]):
            calibration_rows.append({"model": model_key, **band_row})

    misses = top_misses(results.pooled_predictions["market"], n=20)

    manifest = {
        "cycle": "gate1b_ou25_probability_architecture_comparison",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source_file": str(FEATURES_PATH.relative_to(REPO_ROOT)),
        "n_candidates_total": len(candidates),
        "n_by_partition": by_partition,
        "folds": [
            {
                "fold_id": f.fold_id,
                "train_seasons": list(f.train_seasons),
                "evaluate_season": f.evaluate_season,
            }
            for f in results.folds
        ],
        "pooled_metrics": pooled_metrics,
        "validation_only_metrics_2023_24": validation_only,
        "sealed_holdout_only_metrics_2024_25": holdout_only,
        "bootstrap_paired_log_loss_ci": bootstrap,
        "holdout_2025_26_availability": (
            "UNAVAILABLE -- cycle_002_discovery_features.csv does not cover 2025_26 "
            "(same data gap already documented in the Outcome Discovery cycle, "
            "research/outcome_discovery/HOLDOUT_REPORT.md). No genuine prospective "
            "holdout beyond 2024_25 currently exists for this target."
        ),
    }

    (OUTPUT_DIR / "GATE1B_OU25_RESULTS.json").write_text(json.dumps(manifest, indent=2))
    _write_csv(OUTPUT_DIR / "CALIBRATION_BANDS.csv", calibration_rows)
    _write_csv(OUTPUT_DIR / "TOP_MISSES_MARKET.csv", misses)

    for model_key in MODEL_KEYS:
        preds = results.pooled_predictions[model_key]
        _write_csv(
            OUTPUT_DIR / f"predictions_{model_key}.csv",
            [
                {
                    "match_id": p.match_id,
                    "season": p.season,
                    "predicted_probability": p.predicted_probability,
                    "actual": p.actual,
                }
                for p in preds
            ],
        )

    print(json.dumps({"n_candidates": len(candidates), "pooled_metrics": pooled_metrics}, indent=2))


if __name__ == "__main__":
    main()
