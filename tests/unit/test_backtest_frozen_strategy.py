from prediction_markets_lab.backtesting.frozen_strategy import (
    STRATEGY_NAME,
    frozen_strategy_to_dict,
    load_and_freeze_current_strategy,
    rebuild_threshold_objects,
)


def test_frozen_strategy_has_expected_name():
    strategy = load_and_freeze_current_strategy()
    assert strategy.strategy_name == STRATEGY_NAME == "money-strategy-v1-frozen"


def test_frozen_config_hash_is_deterministic():
    a = load_and_freeze_current_strategy()
    b = load_and_freeze_current_strategy()
    assert a.config_hash == b.config_hash
    assert len(a.config_hash) == 64  # sha256 hex digest


def test_frozen_strategy_captures_every_threshold_family():
    strategy = load_and_freeze_current_strategy()
    assert set(strategy.thresholds.keys()) == {
        "grading",
        "confidence",
        "data_quality",
        "payout_policy",
        "money_qualification",
    }
    assert "starting_bankroll_gbp" in strategy.bankroll


def test_frozen_strategy_to_dict_is_json_safe():
    import json

    strategy = load_and_freeze_current_strategy()
    payload = frozen_strategy_to_dict(strategy)
    # Must not raise -- every value must already be JSON-serialisable
    # (no frozenset, no dataclass instances left un-flattened).
    json.dumps(payload)


def test_rebuild_threshold_objects_round_trips_values():
    strategy = load_and_freeze_current_strategy()
    rebuilt = rebuild_threshold_objects(strategy)
    assert rebuilt["grading"].a_plus_min_net_ev == strategy.thresholds["grading"]["a_plus_min_net_ev"]
    assert (
        rebuilt["money_qualification"].event_horizon_hours
        == strategy.thresholds["money_qualification"]["event_horizon_hours"]
    )
    assert rebuilt["staking"].starting_bankroll_gbp == strategy.bankroll["starting_bankroll_gbp"]
    # frozenset fields must survive the list -> frozenset round trip.
    assert isinstance(rebuilt["money_qualification"].eligible_confidence_labels, frozenset)


def test_hash_changes_if_a_threshold_value_changes():
    strategy = load_and_freeze_current_strategy()
    import dataclasses

    from prediction_markets_lab.backtesting import frozen_strategy as fs_module

    mutated_thresholds = dict(strategy.thresholds)
    mutated_grading = dict(mutated_thresholds["grading"])
    mutated_grading["a_plus_min_net_ev"] = 0.99
    mutated_thresholds["grading"] = mutated_grading

    mutated = dataclasses.replace(strategy, thresholds=mutated_thresholds)
    original_payload = {
        "strategy_name": strategy.strategy_name,
        "frozen_at_engine_version": strategy.frozen_at_engine_version,
        "thresholds": strategy.thresholds,
        "bankroll": strategy.bankroll,
    }
    mutated_payload = {
        "strategy_name": mutated.strategy_name,
        "frozen_at_engine_version": mutated.frozen_at_engine_version,
        "thresholds": mutated.thresholds,
        "bankroll": mutated.bankroll,
    }
    assert fs_module._canonical_json(original_payload) != fs_module._canonical_json(mutated_payload)
