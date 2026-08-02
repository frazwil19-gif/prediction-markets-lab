"""Open-position and daily exposure tracking."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class ExposureState:
    """Tracks currently open stakes and count of open bets for one day.

    Attributes:
        open_stakes_gbp: List of stake amounts (GBP) currently at risk.
    """

    open_stakes_gbp: list[float] = field(default_factory=list)

    @property
    def total_exposure_gbp(self) -> float:
        """Sum of all currently open stakes, in GBP."""
        return sum(self.open_stakes_gbp)

    @property
    def open_bet_count(self) -> int:
        """Number of currently open bets."""
        return len(self.open_stakes_gbp)

    def can_add_stake(
        self,
        new_stake_gbp: float,
        maximum_daily_exposure_gbp: float,
        maximum_open_bets: int,
    ) -> bool:
        """Check whether a new stake can be added without breaching limits.

        Args:
            new_stake_gbp: The proposed new stake, in GBP.
            maximum_daily_exposure_gbp: Configured maximum total exposure
                for the day.
            maximum_open_bets: Configured maximum number of simultaneously
                open bets.

        Returns:
            True if adding new_stake_gbp would keep both total exposure and
            open bet count within their configured limits, False otherwise.
        """
        if self.open_bet_count + 1 > maximum_open_bets:
            return False
        if self.total_exposure_gbp + new_stake_gbp > maximum_daily_exposure_gbp:
            return False
        return True

    def add_stake(self, stake_gbp: float) -> None:
        """Record a new open stake.

        Args:
            stake_gbp: Stake amount to add, in GBP. Must be positive.

        Raises:
            ValueError: If stake_gbp is not positive.
        """
        if stake_gbp <= 0:
            raise ValueError("stake_gbp must be positive")
        self.open_stakes_gbp.append(stake_gbp)

    def clear(self) -> None:
        """Clear all open stakes, e.g. at the start of a new trading day."""
        self.open_stakes_gbp.clear()
