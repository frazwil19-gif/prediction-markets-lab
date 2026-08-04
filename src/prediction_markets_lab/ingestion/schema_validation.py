"""Ingestion-time data validation.

Implements the ingestion-stage safety/failure checks from project
instructions section 21: missing odds, markets that don't form a valid
set of outcomes, and (via odds_conversion.overround) an implausible
overround that suggests corrupted data.
"""

from __future__ import annotations

from dataclasses import dataclass

from prediction_markets_lab.probability.odds_conversion import overround

# A market overround outside this range is treated as implausible and
# likely corrupted/misentered data, rather than a genuine bookmaker
# margin. These bounds are generous on purpose (real bookmaker margins
# are usually 2-8%) so genuine markets are never wrongly rejected.
MIN_PLAUSIBLE_OVERROUND = -0.01  # allow tiny float rounding below zero
MAX_PLAUSIBLE_OVERROUND = 0.35


@dataclass(frozen=True)
class ValidationResult:
    """Outcome of validating one market's odds for one bookmaker."""

    valid: bool
    reason: str | None = None


def validate_market_odds(decimal_odds: list[float], expected_outcome_count: int) -> ValidationResult:
    """Validate a single bookmaker's odds for a single market.

    Args:
        decimal_odds: The decimal odds quoted for every outcome in the
            market, in outcome order.
        expected_outcome_count: The number of outcomes this market type
            should have (e.g. 3 for football 1X2, 2 for tennis match
            winner).

    Returns:
        A ValidationResult. If valid is False, reason explains why the
        market must be rejected before it reaches the probability
        pipeline (section 21: "odds are missing", "outcomes do not sum
        to a valid market", "data appears corrupted").
    """
    if len(decimal_odds) != expected_outcome_count:
        return ValidationResult(
            False,
            f"expected {expected_outcome_count} outcomes, got {len(decimal_odds)} "
            "(odds may be missing)",
        )
    if any(o <= 1.0 for o in decimal_odds):
        return ValidationResult(False, "one or more odds are <= 1.0 (invalid/missing)")

    margin = overround(decimal_odds)
    if margin < MIN_PLAUSIBLE_OVERROUND:
        return ValidationResult(
            False, f"overround {margin:.2%} is negative beyond rounding tolerance"
        )
    if margin > MAX_PLAUSIBLE_OVERROUND:
        return ValidationResult(
            False,
            f"overround {margin:.2%} exceeds plausible bounds "
            f"(max {MAX_PLAUSIBLE_OVERROUND:.0%}) — data may be corrupted",
        )

    return ValidationResult(True, None)
