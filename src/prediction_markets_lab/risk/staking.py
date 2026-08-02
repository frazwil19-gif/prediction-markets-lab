"""Stake recommendation logic.

V1 uses fixed stakes per grade (not Kelly or proportional staking), as
specified in project instructions section 10. Stakes are always capped
by the configured maximum_stake_gbp regardless of grade.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class StakingConfig:
    """Bankroll and staking configuration for a single user/session.

    Mirrors config/bankroll.yaml. See that file for the authoritative
    default values.
    """

    starting_bankroll_gbp: float
    normal_stake_gbp: float
    maximum_stake_gbp: float
    maximum_daily_exposure_gbp: float
    maximum_open_bets: int
    daily_loss_stop_gbp: float
    weekly_loss_stop_gbp: float

    def __post_init__(self) -> None:
        if self.starting_bankroll_gbp <= 0:
            raise ValueError("starting_bankroll_gbp must be positive")
        if self.normal_stake_gbp <= 0:
            raise ValueError("normal_stake_gbp must be positive")
        if self.maximum_stake_gbp < self.normal_stake_gbp:
            raise ValueError("maximum_stake_gbp cannot be less than normal_stake_gbp")
        if self.maximum_daily_exposure_gbp < self.maximum_stake_gbp:
            raise ValueError(
                "maximum_daily_exposure_gbp cannot be less than maximum_stake_gbp"
            )
        if self.maximum_open_bets < 1:
            raise ValueError("maximum_open_bets must be at least 1")
        if self.daily_loss_stop_gbp <= 0:
            raise ValueError("daily_loss_stop_gbp must be positive")
        if self.weekly_loss_stop_gbp <= 0:
            raise ValueError("weekly_loss_stop_gbp must be positive")


# Grade-specific stake amounts, in GBP, before capping by maximum_stake_gbp.
# These mirror project instructions section 10.
GRADE_STAKES_GBP: dict[str, float] = {
    "A+": 0.50,
    "A": 0.25,
}


def recommended_stake_gbp(grade: str, config: StakingConfig) -> float:
    """Return the recommended stake for a given grade, capped by config.

    Args:
        grade: One of "A+", "A", "B", "C", "Reject".
        config: The active StakingConfig.

    Returns:
        The recommended stake in GBP. Grades "B", "C" and "Reject" always
        return 0.0, since they are paper-trade-only, watchlist-only, or
        no-trade decisions respectively.

    Raises:
        ValueError: If grade is not a recognised value.
    """
    if grade not in {"A+", "A", "B", "C", "Reject"}:
        raise ValueError(f"unrecognised grade: {grade!r}")

    if grade not in GRADE_STAKES_GBP:
        # B, C, Reject: no live stake.
        return 0.0

    stake = GRADE_STAKES_GBP[grade]
    return min(stake, config.maximum_stake_gbp)
