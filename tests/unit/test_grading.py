import pytest

from prediction_markets_lab.decisions.grading import (
    GradingInput,
    GradingThresholds,
    grade_opportunity,
)


def make_evidence(**overrides) -> GradingInput:
    base = dict(
        net_ev=0.10,
        probability_edge_pp=5.0,
        bookmaker_count=6,
        data_quality_ok=True,
        no_material_info_risk=True,
        exchange_price_current=True,
        market_rules_match=True,
        liquidity_adequate=True,
    )
    base.update(overrides)
    return GradingInput(**base)


def default_thresholds() -> GradingThresholds:
    return GradingThresholds()


def test_grade_a_plus_when_all_thresholds_met():
    evidence = make_evidence(net_ev=0.10, probability_edge_pp=5.0, bookmaker_count=6)
    result = grade_opportunity(evidence, default_thresholds())
    assert result.grade == "A+"


def test_grade_a_when_a_plus_thresholds_not_met_but_a_thresholds_are():
    evidence = make_evidence(net_ev=0.06, probability_edge_pp=3.5, bookmaker_count=4)
    result = grade_opportunity(evidence, default_thresholds())
    assert result.grade == "A"


def test_grade_b_when_below_a_but_above_b_floor():
    evidence = make_evidence(net_ev=0.03, probability_edge_pp=1.0, bookmaker_count=2)
    result = grade_opportunity(evidence, default_thresholds())
    assert result.grade == "B"


def test_grade_b_when_material_info_risk_blocks_a_despite_strong_numbers():
    evidence = make_evidence(
        net_ev=0.10,
        probability_edge_pp=5.0,
        bookmaker_count=6,
        no_material_info_risk=False,
    )
    result = grade_opportunity(evidence, default_thresholds())
    assert result.grade == "B"


def test_grade_c_when_below_b_floor_but_non_negative():
    evidence = make_evidence(net_ev=0.01)
    result = grade_opportunity(evidence, default_thresholds())
    assert result.grade == "C"


def test_reject_when_net_ev_negative():
    evidence = make_evidence(net_ev=-0.01)
    result = grade_opportunity(evidence, default_thresholds())
    assert result.grade == "Reject"


@pytest.mark.parametrize(
    "flag",
    [
        "exchange_price_current",
        "market_rules_match",
        "liquidity_adequate",
        "data_quality_ok",
    ],
)
def test_reject_when_any_safety_gate_fails_regardless_of_strong_numbers(flag):
    evidence = make_evidence(net_ev=0.20, probability_edge_pp=10.0, bookmaker_count=10)
    evidence = make_evidence(**{flag: False}, net_ev=0.20, probability_edge_pp=10.0, bookmaker_count=10)
    result = grade_opportunity(evidence, default_thresholds())
    assert result.grade == "Reject"


def test_grading_thresholds_rejects_inconsistent_config():
    with pytest.raises(ValueError):
        GradingThresholds(a_plus_min_net_ev=0.03, a_min_net_ev=0.05)
    with pytest.raises(ValueError):
        GradingThresholds(a_plus_min_edge_pp=1.0, a_min_edge_pp=3.0)
    with pytest.raises(ValueError):
        GradingThresholds(a_plus_min_bookmakers=2, a_min_bookmakers=4)
    with pytest.raises(ValueError):
        GradingThresholds(b_min_net_ev=0.0, c_min_net_ev=0.05)
