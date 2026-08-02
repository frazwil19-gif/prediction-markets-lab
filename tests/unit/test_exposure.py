import pytest

from prediction_markets_lab.risk.exposure import ExposureState


def test_exposure_starts_empty():
    state = ExposureState()
    assert state.total_exposure_gbp == 0.0
    assert state.open_bet_count == 0


def test_add_stake_updates_totals():
    state = ExposureState()
    state.add_stake(0.25)
    state.add_stake(0.50)
    assert state.total_exposure_gbp == pytest.approx(0.75)
    assert state.open_bet_count == 2


def test_add_stake_rejects_non_positive():
    state = ExposureState()
    with pytest.raises(ValueError):
        state.add_stake(0.0)
    with pytest.raises(ValueError):
        state.add_stake(-0.1)


def test_can_add_stake_within_limits():
    state = ExposureState()
    state.add_stake(0.25)
    assert state.can_add_stake(0.25, maximum_daily_exposure_gbp=0.75, maximum_open_bets=3)


def test_can_add_stake_blocked_by_exposure_limit():
    state = ExposureState()
    state.add_stake(0.50)
    state.add_stake(0.20)
    # Adding another 0.20 would take total to 0.90, over the 0.75 limit.
    assert not state.can_add_stake(
        0.20, maximum_daily_exposure_gbp=0.75, maximum_open_bets=3
    )


def test_can_add_stake_blocked_by_open_bet_count():
    state = ExposureState()
    state.add_stake(0.10)
    state.add_stake(0.10)
    state.add_stake(0.10)
    # Already at 3 open bets; a 4th should be blocked even with headroom.
    assert not state.can_add_stake(
        0.10, maximum_daily_exposure_gbp=1.00, maximum_open_bets=3
    )


def test_clear_resets_state():
    state = ExposureState()
    state.add_stake(0.25)
    state.clear()
    assert state.total_exposure_gbp == 0.0
    assert state.open_bet_count == 0
