"""Daily and weekly loss-stop checks.

These are hard stops per project instructions section 21: once the
configured daily or weekly loss limit is reached, no further live bets
are permitted for the remainder of that period, regardless of grade.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class LossLockStatus:
    """Result of checking realised losses against configured stop limits."""

    daily_loss_gbp: float
    weekly_loss_gbp: float
    daily_loss_stop_gbp: float
    weekly_loss_stop_gbp: float

    @property
    def daily_stop_triggered(self) -> bool:
        """True if today's realised loss has reached or exceeded the daily stop."""
        return self.daily_loss_gbp >= self.daily_loss_stop_gbp

    @property
    def weekly_stop_triggered(self) -> bool:
        """True if this week's realised loss has reached or exceeded the weekly stop."""
        return self.weekly_loss_gbp >= self.weekly_loss_stop_gbp

    @property
    def trading_halted(self) -> bool:
        """True if either the daily or weekly loss stop has been triggered."""
        return self.daily_stop_triggered or self.weekly_stop_triggered

    @property
    def halt_reason(self) -> str | None:
        """Human-readable reason for the halt, or None if not halted."""
        if self.daily_stop_triggered and self.weekly_stop_triggered:
            return "daily and weekly loss stop both reached"
        if self.daily_stop_triggered:
            return "daily loss stop reached"
        if self.weekly_stop_triggered:
            return "weekly loss stop reached"
        return None


def check_loss_locks(
    daily_loss_gbp: float,
    weekly_loss_gbp: float,
    daily_loss_stop_gbp: float,
    weekly_loss_stop_gbp: float,
) -> LossLockStatus:
    """Check realised losses against configured daily and weekly stop limits.

    Args:
        daily_loss_gbp: Realised loss so far today, in GBP (non-negative;
            0 means no net loss today).
        weekly_loss_gbp: Realised loss so far this week, in GBP.
        daily_loss_stop_gbp: Configured daily loss stop threshold.
        weekly_loss_stop_gbp: Configured weekly loss stop threshold.

    Returns:
        A LossLockStatus describing whether trading should halt.

    Raises:
        ValueError: If any loss value is negative.
    """
    if daily_loss_gbp < 0 or weekly_loss_gbp < 0:
        raise ValueError("loss values must be non-negative")
    return LossLockStatus(
        daily_loss_gbp=daily_loss_gbp,
        weekly_loss_gbp=weekly_loss_gbp,
        daily_loss_stop_gbp=daily_loss_stop_gbp,
        weekly_loss_stop_gbp=weekly_loss_stop_gbp,
    )
