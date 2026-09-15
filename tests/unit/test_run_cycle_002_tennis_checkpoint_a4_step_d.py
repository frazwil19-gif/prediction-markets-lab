import importlib.util
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
SCRIPT_PATH = REPO_ROOT / "scripts" / "run_cycle_002_tennis_checkpoint_a4_step_d.py"


def load_script_module():
    spec = importlib.util.spec_from_file_location("run_cycle_002_tennis_checkpoint_a4_step_d", SCRIPT_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_bonferroni_ci_percentiles_three_comparisons():
    module = load_script_module()
    lower, upper = module.bonferroni_ci_percentiles(3, familywise_alpha=0.05)
    assert lower == pytest.approx(100.0 * (0.05 / 6.0))
    assert upper == pytest.approx(100.0 * (1.0 - 0.05 / 6.0))


def test_bonferroni_ci_percentiles_single_comparison_is_plain_95_percent():
    module = load_script_module()
    lower, upper = module.bonferroni_ci_percentiles(1, familywise_alpha=0.05)
    assert lower == pytest.approx(2.5)
    assert upper == pytest.approx(97.5)


def test_bonferroni_ci_percentiles_rejects_invalid_inputs():
    module = load_script_module()
    with pytest.raises(ValueError):
        module.bonferroni_ci_percentiles(0)
    with pytest.raises(ValueError):
        module.bonferroni_ci_percentiles(3, familywise_alpha=0.0)
    with pytest.raises(ValueError):
        module.bonferroni_ci_percentiles(3, familywise_alpha=1.0)


def test_paired_bootstrap_corrected_is_exact_for_constant_per_match_losses():
    module = load_script_module()
    # Every row has identical per-match log loss for augmented vs baseline
    # (a confident-correct model vs. always-0.5), so resampling can never
    # change the mean -- the corrected CI must collapse to the point value,
    # and it must be more than plain 95% since n_comparisons=3 widens it
    # (verified indirectly: the bounds used are the Bonferroni ones, not 2.5/97.5).
    preds_augmented = [0.99] * 6
    preds_baseline = [0.5] * 6
    actuals = [1] * 6
    result = module.paired_bootstrap_log_loss_delta_corrected(preds_augmented, preds_baseline, actuals, n_comparisons=3, n_bootstrap=200, seed=1)

    import math
    expected_delta = -math.log(0.99) - (-math.log(0.5))
    assert result["point_delta_log_loss_augmented_minus_baseline"] == pytest.approx(expected_delta)
    assert result["ci_lower"] == pytest.approx(expected_delta)
    assert result["ci_upper"] == pytest.approx(expected_delta)
    assert result["promoted"] is True
    assert result["ci_percentile_bounds"] == pytest.approx(module.bonferroni_ci_percentiles(3))


def test_paired_bootstrap_corrected_not_promoted_when_models_are_identical():
    module = load_script_module()
    preds = [0.5] * 8
    actuals = [1, 0, 1, 0, 1, 0, 1, 0]
    result = module.paired_bootstrap_log_loss_delta_corrected(preds, preds, actuals, n_comparisons=3, n_bootstrap=200, seed=2)
    assert result["point_delta_log_loss_augmented_minus_baseline"] == pytest.approx(0.0)
    assert result["ci_upper"] == pytest.approx(0.0)
    assert result["promoted"] is False  # CI upper bound of exactly 0 is not < 0


def test_stability_table_skips_groups_under_30_rows():
    module = load_script_module()
    n_hard, n_clay = 40, 10
    rows = pd.DataFrame({
        "surface": ["Hard"] * n_hard + ["Clay"] * n_clay,
        "outcome_a_won": ([1, 0] * (n_hard // 2)) + ([1, 0] * (n_clay // 2)),
    })
    baseline_preds = [0.5] * (n_hard + n_clay)
    augmented_preds = [0.5] * (n_hard + n_clay)
    table = module._stability_table(rows, "surface", baseline_preds, augmented_preds)
    levels = {row["level"] for row in table}
    assert levels == {"Hard"}


def _synthetic_merged_df(n_per_season=300, candidate_signal_strength=6.0, seed=0):
    rng = np.random.default_rng(seed)
    rows = []
    seasons = [2021, 2022, 2023, 2024]
    for season in seasons:
        for i in range(n_per_season):
            elo_diff = rng.normal(0, 100)  # a weak, noisy Elo signal
            candidate = rng.normal(0, 1)
            # True outcome driven MOSTLY by the candidate feature, weakly by elo --
            # this is the "genuine incremental information" case.
            logit = 0.001 * elo_diff + candidate_signal_strength * candidate
            p = 1.0 / (1.0 + np.exp(-logit))
            outcome = int(rng.uniform() < p)
            rows.append({
                "_season": season,
                "tourney_date": pd.Timestamp(f"{season}-01-01") + pd.Timedelta(days=i % 300),
                "surface": "Hard" if i % 2 == 0 else "Clay",
                "best_of": 3,
                "outcome_a_won": outcome,
                "_elo_rating_diff": elo_diff,
                "rolling_win_pct_diff_a_minus_b": candidate,
            })
    return pd.DataFrame(rows)


def test_evaluate_family_promotes_a_strong_synthetic_incremental_feature():
    module = load_script_module()
    df = _synthetic_merged_df(candidate_signal_strength=6.0, seed=0)
    result = module.evaluate_family(df, ["rolling_win_pct_diff_a_minus_b"], [2021, 2022, 2023], 2024)
    assert result["bootstrap"]["promoted"] is True
    assert result["bootstrap"]["point_delta_log_loss_augmented_minus_baseline"] < 0


def test_evaluate_family_does_not_promote_pure_noise_feature():
    module = load_script_module()
    rng = np.random.default_rng(42)
    df = _synthetic_merged_df(candidate_signal_strength=6.0, seed=1)
    # Overwrite the candidate feature with pure noise unrelated to the outcome.
    df["rolling_win_pct_diff_a_minus_b"] = rng.normal(0, 1, len(df))
    # Also weaken elo's own signal irrelevance isn't the point here -- just
    # confirm a feature with NO real relationship to the (now noise-driven)
    # candidate column doesn't get promoted.
    result = module.evaluate_family(df, ["rolling_win_pct_diff_a_minus_b"], [2021, 2022, 2023], 2024)
    assert result["bootstrap"]["promoted"] is False
