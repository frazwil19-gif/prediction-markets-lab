"""Commission handling.

In V1, commission is a single configured rate per exchange (see
config/commissions.yaml) applied directly inside
expected_value.net_expected_value. This module re-exports the relevant
validation helper so callers can import commission-specific logic from
a stable, dedicated location as the project grows (e.g. tiered
commission bands in a future stage).
"""

from __future__ import annotations

from prediction_markets_lab.ev.expected_value import _validate_commission


def validate_commission_rate(commission: float) -> None:
    """Validate a commission rate is in the acceptable range [0, 1).

    Args:
        commission: Exchange commission rate, e.g. 0.02 for 2%.

    Raises:
        ValueError: If commission is not in [0, 1).
    """
    _validate_commission(commission)
