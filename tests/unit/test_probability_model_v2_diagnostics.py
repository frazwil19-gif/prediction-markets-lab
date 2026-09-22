"""Tests for research.probability_model_v2_diagnostics -- pure post-hoc
diagnostic bucketing used by Phase 2's high-probability-region and
disagreement-band analyses (instruction Sections 13, 15)."""

from prediction_markets_lab.research.probability_model_v2_diagnostics import (
    HIGH_PROBABILITY_BANDS,
    DISAGREEMENT_BANDS,
    band_for_probability,
    band_for_disagreement,
    high_probability_region_report,
    disagreement_band_report,
)


def test_band_for_probability_below_50_is_none():
    assert band_for_probability(0.4999) is None
    assert band_for_probability(0.0) is None


def test_band_for_probability_boundaries():
    assert band_for_probability(0.50) == "50-54.9%"
    assert band_for_probability(0.549) == "50-54.9%"
    assert band_for_probability(0.55) == "55-59.9%"
    assert band_for_probability(0.799) == "70-79.9%"
    assert band_for_probability(0.80) == "80%+"
    assert band_for_probability(1.0) == "80%+"


def test_every_band_label_is_unique():
    labels = [label for label, _, _ in HIGH_PROBABILITY_BANDS]
    assert len(labels) == len(set(labels))
    labels2 = [label for label, _, _ in DISAGREEMENT_BANDS]
    assert len(labels2) == len(set(labels2))


def test_band_for_disagreement_agree_band():
    assert band_for_disagreement(0.0) == "model ~= market (-0.05, +0.05)"
    assert band_for_disagreement(0.049) == "model ~= market (-0.05, +0.05)"
    assert band_for_disagreement(-0.049) == "model ~= market (-0.05, +0.05)"


def test_band_for_disagreement_extremes():
    assert band_for_disagreement(-0.5) == "model << market (<= -0.20)"
    assert band_for_disagreement(0.5) == "model >> market (>= +0.20)"
    assert band_for_disagreement(1.0) == "model >> market (>= +0.20)"


def test_high_probability_region_report_empty_bands_are_reported_not_dropped():
    # All predictions in one band only -- every other band must still
    # appear in the output with n=0, never silently missing.
    preds = [0.55, 0.56, 0.58]
    mkts = [0.50, 0.50, 0.50]
    actuals = [True, False, True]
    report = high_probability_region_report(preds, mkts, actuals)
    assert len(report) == len(HIGH_PROBABILITY_BANDS)
    by_band = {r.band: r for r in report}
    assert by_band["50-54.9%"].n == 0
    assert by_band["50-54.9%"].actual_win_rate is None
    assert by_band["55-59.9%"].n == 3


def test_high_probability_region_report_below_50_excluded():
    preds = [0.3, 0.4, 0.6]
    mkts = [0.3, 0.4, 0.5]
    actuals = [True, True, True]
    report = high_probability_region_report(preds, mkts, actuals)
    total_n = sum(r.n for r in report)
    assert total_n == 1  # only the 0.6 prediction is >= 50%


def test_high_probability_region_report_calibration_math():
    # 60-64.9% band: predictions 0.60, 0.62, 0.64; 2 of 3 actually won.
    preds = [0.60, 0.62, 0.64]
    mkts = [0.55, 0.55, 0.55]
    actuals = [True, True, False]
    report = high_probability_region_report(preds, mkts, actuals)
    band = next(r for r in report if r.band == "60-64.9%")
    assert band.n == 3
    assert abs(band.mean_predicted_probability - 0.62) < 1e-9
    assert abs(band.actual_win_rate - (2 / 3)) < 1e-9
    assert abs(band.calibration_error - abs(0.62 - 2 / 3)) < 1e-9
    assert abs(band.mean_market_probability - 0.55) < 1e-9
    assert abs(band.mean_difference_from_market - (0.62 - 0.55)) < 1e-9


def test_high_probability_region_report_length_mismatch_raises():
    try:
        high_probability_region_report([0.5, 0.6], [0.5], [True, False])
        assert False, "expected ValueError"
    except ValueError:
        pass


def test_disagreement_band_report_all_bands_returned():
    model = [0.5]
    market = [0.5]
    actual = [True]
    report = disagreement_band_report(model, market, actual)
    assert len(report) == len(DISAGREEMENT_BANDS)
    by_band = {r.band: r for r in report}
    assert by_band["model ~= market (-0.05, +0.05)"].n == 1
    empty_bands = [r for r in report if r.band != "model ~= market (-0.05, +0.05)"]
    assert all(r.n == 0 for r in empty_bands)


def test_disagreement_band_report_directional_calibration():
    # Model consistently 15pp above market; realised win rate matches
    # the model, not the market -- model should show lower calibration
    # error than market in this synthetic band.
    model = [0.65, 0.65, 0.65, 0.65]
    market = [0.50, 0.50, 0.50, 0.50]
    actual = [True, True, True, False]  # win rate 0.75, closer to model's 0.65 than market's 0.50
    report = disagreement_band_report(model, market, actual)
    band = next(r for r in report if r.band == "model > market [+0.10, +0.20)")
    assert band.n == 4
    assert band.model_calibration_error < band.market_calibration_error


def test_disagreement_band_report_length_mismatch_raises():
    try:
        disagreement_band_report([0.5], [0.5, 0.6], [True, False])
        assert False, "expected ValueError"
    except ValueError:
        pass


def test_bands_are_deterministic_and_exhaustive_over_typical_range():
    import random
    rng = random.Random(20260922)
    for _ in range(500):
        p = rng.uniform(0.0, 1.0)
        # band_for_probability must not raise, and must agree with itself twice
        b1 = band_for_probability(p)
        b2 = band_for_probability(p)
        assert b1 == b2
        d = rng.uniform(-1.0, 1.0)
        assert band_for_disagreement(d) == band_for_disagreement(d)
