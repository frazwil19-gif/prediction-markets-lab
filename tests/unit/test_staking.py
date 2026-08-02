import pytest

from prediction_markets_lab.risk.staking import StakingConfig, recommended_stake_gbp


def default_config(**overrides) -> StakingConfig:
    base = dict(
        starting_bankroll_gbp=10.00,
        normal_stake_gbp=0.25,
        maximum_stake_gbp=0.50,
        maximum_daily_exposure_gbp=0.75,
        maximum_open_bets=3,
        daily_loss_stop_gbp=0.75,
        weekly_loss_stop_gbp=2.00,
    )
    base.update(overrides)
    return StakingConfig(**base)


def test_recommended_stake_a_plus():
    config = default_config()
    assert recommended_stake_gbp("A+", config) == pytest.approx(0.50)


def test_recommended_stake_a():
    config = default_config()
    assert recommended_stake_gbp("A", config) == pytest.approx(0.25)


def test_recommended_stake_b_c_reject_are_zero():
    config = default_config()
    assert recommended_stake_gbp("B", config) == 0.0
    assert recommended_stake_gbp("C", config) == 0.0
    assert recommended_stake_gbp("Reject", config) == 0.0


def test_recommended_stake_capped_by_maximum():
    # Even if a grade's nominal stake exceeds the configured max, it is capped.
    config = default_config(maximum_stake_gbp=0.30)
    assert recommended_stake_gbp("A+", config) == pytest.approx(0.30)


def test_recommended_stake_rejects_unknown_grade():
    config = default_config()
    with pytest.raises(ValueError):
        recommended_stake_gbp("D", config)


def test_staking_config_rejects_invalid_bankroll():
    with pytest.raises(ValueError):
        default_config(starting_bankroll_gbp=0.0)


def test_staking_config_rejects_max_stake_below_normal_stake():
    with pytest.raises(ValueError):
        default_config(normal_stake_gbp=0.30, maximum_stake_gbp=0.25)


def test_staking_config_rejects_daily_exposure_below_max_stake():
    with pytest.raises(ValueError):
        default_config(maximum_stake_gbp=0.50, maximum_daily_exposure_gbp=0.40)
