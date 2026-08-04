import pytest

from prediction_markets_lab.research.research_prioritisation import (
    PrioritisationInputs,
    prioritise,
)


def test_strong_candidate_reaches_p1():
    inputs = PrioritisationInputs(
        evidence_strength=0.8,
        expected_information_gain=0.7,
        data_availability=0.9,
        implementation_cost=0.1,
        expected_signal_frequency=0.7,
        liquidity=0.7,
        independence_from_validated_behaviours=0.8,
        overfitting_risk=0.1,
        relevance_to_current_goals=0.8,
    )
    result = prioritise(inputs)
    assert result.priority_tier == "P1"
    assert result.priority_score > 0.70


def test_weak_candidate_reaches_defer():
    inputs = PrioritisationInputs(
        evidence_strength=0.1,
        expected_information_gain=0.1,
        data_availability=0.1,
        implementation_cost=0.9,
        expected_signal_frequency=0.1,
        liquidity=0.1,
        independence_from_validated_behaviours=0.1,
        overfitting_risk=0.9,
        relevance_to_current_goals=0.1,
    )
    result = prioritise(inputs)
    assert result.priority_tier == "DEFER"


def test_do_not_retest_short_circuits():
    inputs = PrioritisationInputs(evidence_strength=0.9, do_not_retest=True)
    result = prioritise(inputs)
    assert result.priority_tier == "DO_NOT_RETEST"
    assert result.priority_score == 0.0


def test_high_implementation_cost_reduces_score():
    low_cost = prioritise(PrioritisationInputs(evidence_strength=0.5, implementation_cost=0.1))
    high_cost = prioritise(PrioritisationInputs(evidence_strength=0.5, implementation_cost=0.9))
    assert low_cost.priority_score > high_cost.priority_score


def test_high_overfitting_risk_reduces_score():
    low_risk = prioritise(PrioritisationInputs(evidence_strength=0.5, overfitting_risk=0.1))
    high_risk = prioritise(PrioritisationInputs(evidence_strength=0.5, overfitting_risk=0.9))
    assert low_risk.priority_score > high_risk.priority_score


def test_not_ranked_by_historical_roi_alone():
    # A candidate with strong "evidence_strength" (which might stem from
    # historical ROI) but weak everything else must not automatically
    # score as highly as a well-rounded candidate with more modest
    # evidence_strength but strong data availability/independence/etc.
    only_roi_like = prioritise(
        PrioritisationInputs(
            evidence_strength=0.95,
            expected_information_gain=0.0,
            data_availability=0.0,
            implementation_cost=1.0,
            expected_signal_frequency=0.0,
            liquidity=0.0,
            independence_from_validated_behaviours=0.0,
            overfitting_risk=1.0,
            relevance_to_current_goals=0.0,
        )
    )
    well_rounded = prioritise(
        PrioritisationInputs(
            evidence_strength=0.5,
            expected_information_gain=0.6,
            data_availability=0.8,
            implementation_cost=0.2,
            expected_signal_frequency=0.6,
            liquidity=0.6,
            independence_from_validated_behaviours=0.7,
            overfitting_risk=0.2,
            relevance_to_current_goals=0.6,
        )
    )
    assert well_rounded.priority_score > only_roi_like.priority_score


def test_rejects_weights_not_summing_to_one():
    with pytest.raises(ValueError):
        prioritise(PrioritisationInputs(evidence_strength=0.5), weights={"evidence_strength": 0.5})


def test_explanation_names_strongest_and_weakest_factor():
    result = prioritise(
        PrioritisationInputs(evidence_strength=0.9, data_availability=0.1)
    )
    assert "Strongest factor" in result.explanation
    assert "Weakest factor" in result.explanation
