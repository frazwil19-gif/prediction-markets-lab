import math

import pytest

from prediction_markets_lab.models.football_blended import (
    BlendWeights,
    blend_probabilities,
    calibrate_blend_weights,
    generate_predeclared_weight_grid,
)


def _pred(h, d, a):
    return {"home": h, "draw": d, "away": a}


def test_blend_weights_rejects_negative_weight():
    with pytest.raises(ValueError):
        BlendWeights({"market": 1.2, "elo": -0.2})


def test_blend_weights_rejects_bad_sum():
    with pytest.raises(ValueError):
        BlendWeights({"market": 0.5, "elo": 0.6})


def test_blend_weights_accepts_valid():
    BlendWeights({"market": 0.7, "elo": 0.3})


def test_blend_probabilities_sums_to_one():
    components = {"market": _pred(0.5, 0.3, 0.2), "elo": _pred(0.4, 0.3, 0.3)}
    weights = BlendWeights({"market": 0.6, "elo": 0.4})
    blended = blend_probabilities(components, weights)
    assert math.isclose(sum(blended.values()), 1.0, abs_tol=1e-9)


def test_blend_probabilities_full_weight_on_one_component_reproduces_it():
    components = {"market": _pred(0.5, 0.3, 0.2), "elo": _pred(0.4, 0.35, 0.25)}
    weights = BlendWeights({"market": 1.0, "elo": 0.0})
    blended = blend_probabilities(components, weights)
    assert blended["home"] == pytest.approx(0.5)
    assert blended["draw"] == pytest.approx(0.3)
    assert blended["away"] == pytest.approx(0.2)


def test_blend_probabilities_equal_weight_is_the_midpoint():
    components = {"market": _pred(0.6, 0.2, 0.2), "elo": _pred(0.4, 0.4, 0.2)}
    weights = BlendWeights({"market": 0.5, "elo": 0.5})
    blended = blend_probabilities(components, weights)
    assert blended["home"] == pytest.approx(0.5)
    assert blended["draw"] == pytest.approx(0.3)
    assert blended["away"] == pytest.approx(0.2)


def test_blend_probabilities_rejects_mismatched_component_names():
    components = {"market": _pred(0.5, 0.3, 0.2)}
    weights = BlendWeights({"market": 0.5, "elo": 0.5})
    with pytest.raises(ValueError):
        blend_probabilities(components, weights)


def test_generate_predeclared_weight_grid_two_components_step_0_1():
    grid = generate_predeclared_weight_grid(("market", "elo"), step=0.1)
    assert len(grid) == 11
    for bw in grid:
        assert math.isclose(sum(bw.weights.values()), 1.0, abs_tol=1e-9)
    weight_sets = {round(bw.weights["market"], 2) for bw in grid}
    assert weight_sets == {round(i * 0.1, 2) for i in range(11)}


def test_generate_predeclared_weight_grid_three_components_step_0_1_count():
    grid = generate_predeclared_weight_grid(("market", "elo", "poisson"), step=0.1)
    assert len(grid) == 66  # C(12, 2)


def test_generate_predeclared_weight_grid_rejects_single_component():
    with pytest.raises(ValueError):
        generate_predeclared_weight_grid(("market",), step=0.1)


def test_generate_predeclared_weight_grid_rejects_bad_step():
    with pytest.raises(ValueError):
        generate_predeclared_weight_grid(("market", "elo"), step=0.3)


def test_calibrate_blend_weights_prefers_the_better_component():
    # "good" is always right and confident; "bad" is uninformative uniform.
    n = 30
    actuals = (["home", "draw", "away"] * 10)[:n]
    good_preds = [_pred(0.97, 0.02, 0.01) if a == "home" else _pred(0.01, 0.97, 0.02) if a == "draw" else _pred(0.01, 0.02, 0.97) for a in actuals]
    bad_preds = [_pred(1 / 3, 1 / 3, 1 / 3)] * n
    weights = calibrate_blend_weights({"good": good_preds, "bad": bad_preds}, actuals, step=0.1)
    assert weights.weights["good"] >= 0.8


def test_calibrate_blend_weights_rejects_single_component():
    with pytest.raises(ValueError):
        calibrate_blend_weights({"only_one": [_pred(0.5, 0.3, 0.2)]}, ["home"])


def test_calibrate_blend_weights_rejects_length_mismatch():
    with pytest.raises(ValueError):
        calibrate_blend_weights(
            {"a": [_pred(0.5, 0.3, 0.2)], "b": [_pred(0.4, 0.3, 0.3), _pred(0.4, 0.3, 0.3)]},
            ["home"],
        )
