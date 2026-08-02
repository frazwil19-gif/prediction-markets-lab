import pytest

from prediction_markets_lab.ev.commission import validate_commission_rate


def test_validate_commission_rate_accepts_valid_values():
    validate_commission_rate(0.0)
    validate_commission_rate(0.02)
    validate_commission_rate(0.999)


def test_validate_commission_rate_rejects_out_of_range():
    with pytest.raises(ValueError):
        validate_commission_rate(1.0)
    with pytest.raises(ValueError):
        validate_commission_rate(-0.01)
