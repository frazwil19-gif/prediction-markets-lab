from prediction_markets_lab.research.hypothesis_validation import (
    validate_behaviour_status_transition,
    validate_hypothesis_definition_complete,
    validate_hypothesis_status_transition,
    validate_no_rejected_reuse,
)
from prediction_markets_lab.research.schemas import Hypothesis


def test_hypothesis_valid_forward_transition():
    result = validate_hypothesis_status_transition("IDEA", "DEFINED")
    assert result.allowed


def test_hypothesis_same_status_is_noop_allowed():
    result = validate_hypothesis_status_transition("BACKTESTING", "BACKTESTING")
    assert result.allowed


def test_hypothesis_rejects_skipping_stages():
    result = validate_hypothesis_status_transition("IDEA", "VALIDATED")
    assert not result.allowed
    assert "cannot move" in result.reason


def test_hypothesis_rejects_unrejecting_a_rejected_hypothesis():
    result = validate_hypothesis_status_transition("REJECTED", "DEFINED")
    assert not result.allowed


def test_hypothesis_can_always_move_to_rejected_from_active_states():
    for state in ["IDEA", "DEFINED", "BACKTESTING", "OUT_OF_SAMPLE", "PAPER", "EXPERIMENTAL_LIVE"]:
        result = validate_hypothesis_status_transition(state, "REJECTED")
        assert result.allowed, f"expected REJECTED to be reachable from {state}"


def test_hypothesis_rejects_unrecognised_status():
    result = validate_hypothesis_status_transition("IDEA", "NOT_A_REAL_STATUS")
    assert not result.allowed


def test_behaviour_valid_forward_transition():
    result = validate_behaviour_status_transition("UNTESTED", "TESTING")
    assert result.allowed


def test_behaviour_near_miss_can_return_to_testing():
    result = validate_behaviour_status_transition("NEAR_MISS", "TESTING")
    assert result.allowed


def test_behaviour_rejects_terminal_state_transition():
    result = validate_behaviour_status_transition("RETIRED", "VALIDATED")
    assert not result.allowed


def test_definition_complete_flags_missing_fields():
    h = Hypothesis(
        hypothesis_id="H-TEST",
        created_at="2026-08-03T00:00:00+00:00",
        updated_at="2026-08-03T00:00:00+00:00",
        sport="football",
        market_type="pre_match_1x2",
        behaviour_name="test",
        hypothesis_statement="Some falsifiable claim.",
        economic_or_market_rationale="Some rationale.",
        target_metric="",  # missing
        minimum_observations=50,
    )
    result = validate_hypothesis_definition_complete(h)
    assert not result.allowed
    assert "target_metric" in result.reason


def test_definition_complete_passes_when_all_present():
    h = Hypothesis(
        hypothesis_id="H-TEST",
        created_at="2026-08-03T00:00:00+00:00",
        updated_at="2026-08-03T00:00:00+00:00",
        sport="football",
        market_type="pre_match_1x2",
        behaviour_name="test",
        hypothesis_statement="Some falsifiable claim.",
        economic_or_market_rationale="Some rationale.",
        target_metric="net_ev",
        minimum_observations=50,
        test_method="backtest then out-of-sample",
        in_sample_period="2020-2023",
        out_of_sample_period="2024-2025",
    )
    result = validate_hypothesis_definition_complete(h)
    assert result.allowed


def test_no_rejected_reuse_blocks_duplicate_id():
    result = validate_no_rejected_reuse({"H-0001"}, "H-0001", "revisiting old idea")
    assert not result.allowed


def test_no_rejected_reuse_allows_new_id():
    result = validate_no_rejected_reuse({"H-0001"}, "H-0002", "new angle on old idea")
    assert result.allowed
