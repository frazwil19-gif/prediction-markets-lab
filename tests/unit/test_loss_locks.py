import pytest

from prediction_markets_lab.risk.loss_locks import check_loss_locks


def test_no_stop_triggered_when_losses_below_thresholds():
    status = check_loss_locks(
        daily_loss_gbp=0.25,
        weekly_loss_gbp=0.50,
        daily_loss_stop_gbp=0.75,
        weekly_loss_stop_gbp=2.00,
    )
    assert not status.trading_halted
    assert status.halt_reason is None


def test_daily_stop_triggered():
    status = check_loss_locks(
        daily_loss_gbp=0.75,
        weekly_loss_gbp=0.75,
        daily_loss_stop_gbp=0.75,
        weekly_loss_stop_gbp=2.00,
    )
    assert status.daily_stop_triggered
    assert status.trading_halted
    assert status.halt_reason == "daily loss stop reached"


def test_weekly_stop_triggered():
    status = check_loss_locks(
        daily_loss_gbp=0.10,
        weekly_loss_gbp=2.00,
        daily_loss_stop_gbp=0.75,
        weekly_loss_stop_gbp=2.00,
    )
    assert status.weekly_stop_triggered
    assert status.trading_halted
    assert status.halt_reason == "weekly loss stop reached"


def test_both_stops_triggered():
    status = check_loss_locks(
        daily_loss_gbp=0.75,
        weekly_loss_gbp=2.00,
        daily_loss_stop_gbp=0.75,
        weekly_loss_stop_gbp=2.00,
    )
    assert status.halt_reason == "daily and weekly loss stop both reached"


def test_rejects_negative_losses():
    with pytest.raises(ValueError):
        check_loss_locks(
            daily_loss_gbp=-0.1,
            weekly_loss_gbp=0.0,
            daily_loss_stop_gbp=0.75,
            weekly_loss_stop_gbp=2.00,
        )
