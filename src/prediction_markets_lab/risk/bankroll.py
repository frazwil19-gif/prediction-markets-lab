"""Bankroll state tracking.

Tracks current bankroll, peak bankroll and drawdown. This is a simple,
in-memory representation intended to be driven by values read from the
Google Sheets Bankroll tab or a local CSV; persistence is handled by
storage/ (future stage), not here.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class BankrollState:
    """Current bankroll state.

    Attributes:
        current_balance: Current bankroll balance in GBP.
        peak_balance: Highest balance ever recorded, used for drawdown.
    """

    current_balance: float
    peak_balance: float

    def __post_init__(self) -> None:
        if self.current_balance < 0:
            raise ValueError("current_balance cannot be negative")
        if self.peak_balance < 0:
            raise ValueError("peak_balance cannot be negative")
        if self.peak_balance < self.current_balance:
            # Peak can never be below the current balance.
            self.peak_balance = self.current_balance

    @property
    def drawdown(self) -> float:
        """Current drawdown from peak, as a positive GBP amount (0 if at peak)."""
        return max(0.0, self.peak_balance - self.current_balance)

    @property
    def drawdown_pct(self) -> float:
        """Current drawdown from peak, as a fraction of peak (0 if peak is 0)."""
        if self.peak_balance <= 0:
            return 0.0
        return self.drawdown / self.peak_balance

    def apply_change(self, net_change: float) -> "BankrollState":
        """Return a new BankrollState after applying a net profit/loss change.

        Args:
            net_change: Net GBP change to apply (positive for profit,
                negative for loss).

        Returns:
            A new BankrollState reflecting the updated balance and peak.

        Raises:
            ValueError: If applying the change would make the balance negative.
        """
        new_balance = self.current_balance + net_change
        if new_balance < 0:
            raise ValueError(
                f"applying change {net_change!r} would make balance negative "
                f"({new_balance!r})"
            )
        new_peak = max(self.peak_balance, new_balance)
        return BankrollState(current_balance=new_balance, peak_balance=new_peak)
