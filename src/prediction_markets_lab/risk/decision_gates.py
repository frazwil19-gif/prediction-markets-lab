"""Combined risk gate: the final go/no-go check before a live stake.

Brings together exposure limits (risk.exposure) and loss stops
(risk.loss_locks) into a single check. A grade of A+ or A from
decisions.grading is necessary but not sufficient for a live trade —
this gate must also pass.
"""

from __future__ import annotations

from dataclasses import dataclass

from prediction_markets_lab.risk.exposure import ExposureState
from prediction_markets_lab.risk.loss_locks import LossLockStatus
from prediction_markets_lab.risk.staking import StakingConfig


@dataclass(frozen=True)
class RiskGateResult:
    """Outcome of the combined pre-trade risk gate check."""

    passed: bool
    reason: str | None


def check_risk_gates(
    proposed_stake_gbp: float,
    exposure: ExposureState,
    loss_lock_status: LossLockStatus,
    config: StakingConfig,
) -> RiskGateResult:
    """Check whether a proposed live stake is permitted right now.

    Args:
        proposed_stake_gbp: The stake amount being considered, in GBP.
        exposure: Current open-position exposure state for the day.
        loss_lock_status: Current daily/weekly loss-stop status.
        config: The active StakingConfig (limits).

    Returns:
        A RiskGateResult. If passed is False, reason explains why the
        trade must be blocked.
    """
    if loss_lock_status.trading_halted:
        return RiskGateResult(False, loss_lock_status.halt_reason)

    if proposed_stake_gbp > config.maximum_stake_gbp:
        return RiskGateResult(
            False,
            f"proposed stake £{proposed_stake_gbp:.2f} exceeds maximum "
            f"stake £{config.maximum_stake_gbp:.2f}",
        )

    if not exposure.can_add_stake(
        proposed_stake_gbp,
        config.maximum_daily_exposure_gbp,
        config.maximum_open_bets,
    ):
        return RiskGateResult(
            False,
            "adding this stake would breach maximum daily exposure or "
            "maximum open bets",
        )

    return RiskGateResult(True, None)
