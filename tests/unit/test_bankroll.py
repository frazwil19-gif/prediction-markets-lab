import pytest

from prediction_markets_lab.risk.bankroll import BankrollState


def test_bankroll_state_initial_peak_defaults_to_balance_if_lower():
    state = BankrollState(current_balance=10.0, peak_balance=5.0)
    assert state.peak_balance == 10.0  # peak cannot be below current


def test_bankroll_state_rejects_negative_balance():
    with pytest.raises(ValueError):
        BankrollState(current_balance=-1.0, peak_balance=10.0)


def test_drawdown_zero_at_peak():
    state = BankrollState(current_balance=10.0, peak_balance=10.0)
    assert state.drawdown == 0.0
    assert state.drawdown_pct == 0.0


def test_drawdown_after_loss():
    state = BankrollState(current_balance=8.0, peak_balance=10.0)
    assert state.drawdown == pytest.approx(2.0)
    assert state.drawdown_pct == pytest.approx(0.2)


def test_apply_change_profit_updates_peak():
    state = BankrollState(current_balance=10.0, peak_balance=10.0)
    new_state = state.apply_change(2.0)
    assert new_state.current_balance == pytest.approx(12.0)
    assert new_state.peak_balance == pytest.approx(12.0)


def test_apply_change_loss_does_not_reduce_peak():
    state = BankrollState(current_balance=10.0, peak_balance=10.0)
    new_state = state.apply_change(-3.0)
    assert new_state.current_balance == pytest.approx(7.0)
    assert new_state.peak_balance == pytest.approx(10.0)
    assert new_state.drawdown == pytest.approx(3.0)


def test_apply_change_rejects_change_that_makes_balance_negative():
    state = BankrollState(current_balance=1.0, peak_balance=10.0)
    with pytest.raises(ValueError):
        state.apply_change(-2.0)
