import importlib.util
from pathlib import Path

import numpy as np
import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
SCRIPT_PATH = REPO_ROOT / "scripts" / "run_cycle_002_tennis_calibration.py"


def load_script_module():
    spec = importlib.util.spec_from_file_location("run_cycle_002_tennis_calibration", SCRIPT_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_logit_sigmoid_are_inverses():
    module = load_script_module()
    for p in (0.01, 0.25, 0.5, 0.75, 0.99):
        assert module._sigmoid(module._logit(p)) == pytest.approx(p, abs=1e-9)


def test_paired_bootstrap_zero_delta_when_predictions_identical():
    module = load_script_module()
    preds = [0.6, 0.4, 0.7, 0.3, 0.55]
    actuals = [1, 0, 1, 0, 1]
    result = module.paired_bootstrap_log_loss_delta(preds, preds, actuals, n_bootstrap=200, seed=1)
    assert result["point_delta"] == pytest.approx(0.0)
    assert result["ci_lower"] == pytest.approx(0.0)
    assert result["ci_upper"] == pytest.approx(0.0)
    assert result["calibration_improves"] is False  # CI upper of exactly 0 is not < 0


def test_paired_bootstrap_detects_a_clearly_better_calibrated_variant():
    module = load_script_module()
    # "calibrated" is confidently correct on every row; "raw" is a coin flip.
    # Every row has an identical per-match log loss gap, so the CI collapses
    # to the exact point delta and must be negative (calibrated is better).
    n = 8
    calibrated = [0.95] * n
    raw = [0.5] * n
    actuals = [1] * n
    result = module.paired_bootstrap_log_loss_delta(calibrated, raw, actuals, n_bootstrap=200, seed=2)
    assert result["point_delta"] < 0
    assert result["calibration_improves"] is True


def test_metrics_block_reports_expected_keys_and_matches_manual_log_loss():
    module = load_script_module()
    rng = np.random.default_rng(3)
    n = 200
    preds = rng.uniform(0.05, 0.95, n).tolist()
    actuals = rng.integers(0, 2, n).tolist()
    m = module.metrics_block(preds, actuals)
    assert set(m.keys()) >= {"n", "log_loss", "brier_score", "auc", "calibration_intercept",
                              "calibration_slope", "expected_calibration_error", "calibration_bins"}
    assert m["n"] == n
    import math
    manual_log_loss = -sum(
        math.log(p) if a == 1 else math.log(1 - p) for p, a in zip(preds, actuals)
    ) / n
    assert m["log_loss"] == pytest.approx(manual_log_loss)


def test_a_perfectly_calibrated_raw_model_fits_near_identity_calibration():
    module = load_script_module()
    # Generate outcomes exactly consistent with the raw probabilities
    # themselves (a genuinely well-calibrated source) -- the fitted
    # intercept/slope should recover close to (0, 1), i.e. "don't touch it."
    rng = np.random.default_rng(4)
    n = 20000
    raw = rng.uniform(0.05, 0.95, n)
    outcomes = rng.binomial(1, raw)
    from prediction_markets_lab.performance.binary_classification import fit_calibration_intercept_slope
    intercept, slope = fit_calibration_intercept_slope(raw.tolist(), outcomes.tolist())
    assert intercept == pytest.approx(0.0, abs=0.05)
    assert slope == pytest.approx(1.0, abs=0.05)
