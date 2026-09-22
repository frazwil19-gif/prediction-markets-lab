"""Phase 2 diagnostic extension of Gate 1 -- EXECUTION.

Reuses Gate 1's exact, already-frozen model comparison
(scripts/run_gate1_1x2_probability_architecture_comparison.py) via its
additive, off-by-default per-match-predictions dump, then computes the
high-probability-region (instruction Section 13) and disagreement-band
(Section 15) diagnostics from research/probability_model_v2_diagnostics.py.

Does NOT fit any new model and does NOT change Gate 1's own frozen
feature set, hyperparameters, or fold structure -- see
research/probability_model_v2/EXPERIMENT_PLAN.md for why re-running the
comparison itself would be inappropriate repeated retesting.

Writes:
  research/probability_model_v2/per_match_predictions_gate1_reproduction.csv
  research/probability_model_v2/high_probability_analysis.csv
  research/probability_model_v2/disagreement_analysis.csv
"""

from __future__ import annotations

import csv
import os
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = REPO_ROOT / "research" / "probability_model_v2"
PREDICTIONS_CSV = OUT_DIR / "per_match_predictions_gate1_reproduction.csv"

# Published Gate 1 pooled log-loss figures (GATE1_CHECKPOINT.md point 12),
# checked against a fresh rerun below as a self-verification that this
# diagnostic extension has not silently drifted from the frozen comparison.
GATE1_PUBLISHED_POOLED_LOG_LOSS = {
    "market_consensus_baseline": 0.98726,
    "existing_elo_poisson_blend": 1.01085,
    "fundamentals_only": 1.01572,
    "market_plus_fundamentals": 0.99225,
    "calibrated_ensemble": 0.98981,
}

MODEL_PREFIXES = {
    "market": "model_0_market",
    "elo_poisson": "model_1_elo_poisson_blend",
    "fundamentals": "model_2_fundamentals",
    "market_fundamentals": "model_3_market_fundamentals",
    "ensemble": "model_4_ensemble",
}
OUTCOMES = ["home", "draw", "away"]
LOG_LOSS_KEY_MAP = {
    "market": "market_consensus_baseline",
    "elo_poisson": "existing_elo_poisson_blend",
    "fundamentals": "fundamentals_only",
    "market_fundamentals": "market_plus_fundamentals",
    "ensemble": "calibrated_ensemble",
}


def _multiclass_log_loss_from_rows(rows: list[dict], prefix: str) -> float:
    import math
    total = 0.0
    for row in rows:
        p = max(float(row[f"{prefix}_{row['outcome']}"]), 1e-15)
        total += -math.log(p)
    return total / len(rows)


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    env = dict(os.environ)
    env["PMLAB_DUMP_PER_MATCH_PREDICTIONS"] = str(PREDICTIONS_CSV)
    gate1_script = REPO_ROOT / "scripts" / "run_gate1_1x2_probability_architecture_comparison.py"
    print(f"Running {gate1_script} to (re)produce per-match predictions ...", file=sys.stderr)
    subprocess.run([sys.executable, str(gate1_script)], cwd=REPO_ROOT, env=env, check=True)

    with open(PREDICTIONS_CSV, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    print(f"Loaded {len(rows)} out-of-sample matches from {PREDICTIONS_CSV}", file=sys.stderr)

    # Self-verification: this rerun must reproduce Gate 1's published
    # pooled log loss for every model, or this diagnostic extension is
    # not trustworthy and must not be reported.
    for model_key, prefix in MODEL_PREFIXES.items():
        recomputed = _multiclass_log_loss_from_rows(rows, prefix)
        published = GATE1_PUBLISHED_POOLED_LOG_LOSS[LOG_LOSS_KEY_MAP[model_key]]
        delta = abs(recomputed - published)
        status = "OK" if delta < 1e-4 else "MISMATCH"
        print(f"  {model_key}: recomputed={recomputed:.5f} published={published:.5f} delta={delta:.2e} [{status}]",
              file=sys.stderr)
        if delta >= 1e-4:
            raise RuntimeError(
                f"Reproduction of Gate 1's pooled log loss for {model_key} does not match the "
                f"published figure (delta={delta:.2e}) -- refusing to report diagnostics computed "
                f"from a run that does not verifiably reproduce Gate 1's own frozen comparison."
            )

    from prediction_markets_lab.research.probability_model_v2_diagnostics import (
        high_probability_region_report,
        disagreement_band_report,
    )

    def flatten(model_key: str):
        prefix = MODEL_PREFIXES[model_key]
        mkt_prefix = MODEL_PREFIXES["market"]
        preds, mkts, actuals = [], [], []
        for row in rows:
            for outcome in OUTCOMES:
                preds.append(float(row[f"{prefix}_{outcome}"]))
                mkts.append(float(row[f"{mkt_prefix}_{outcome}"]))
                actuals.append(row["outcome"] == outcome)
        return preds, mkts, actuals

    high_prob_rows: list[dict] = []
    disagreement_rows: list[dict] = []
    for model_key in ["fundamentals", "market_fundamentals", "ensemble", "elo_poisson"]:
        preds, mkts, actuals = flatten(model_key)
        for r in high_probability_region_report(preds, mkts, actuals):
            high_prob_rows.append({"model": model_key, **r.__dict__})
        for r in disagreement_band_report(preds, mkts, actuals):
            disagreement_rows.append({"model": model_key, **r.__dict__})

    hp_path = OUT_DIR / "high_probability_analysis.csv"
    with open(hp_path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(high_prob_rows[0].keys()))
        w.writeheader()
        w.writerows(high_prob_rows)
    print(f"Wrote {hp_path}", file=sys.stderr)

    da_path = OUT_DIR / "disagreement_analysis.csv"
    with open(da_path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(disagreement_rows[0].keys()))
        w.writeheader()
        w.writerows(disagreement_rows)
    print(f"Wrote {da_path}", file=sys.stderr)


if __name__ == "__main__":
    main()
