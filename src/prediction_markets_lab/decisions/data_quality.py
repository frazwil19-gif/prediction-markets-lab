"""Data quality assessment for opportunities.

V1 implementation (2026-09-18, Daily Engine V1 build). Replaces the
Stage-1 placeholder that required a human to set `data_quality_ok`
manually for every candidate -- automating that mechanical part is
required for an automated Daily Bet Card.

This checks only what the pipeline can verify mechanically: whether
enough bookmakers contributed a complete, valid outcome set to the
consensus, and whether the price snapshot is recent enough to trust. It
deliberately does NOT check things that still require a human for V1
(e.g. whether a fixture has been postponed, or whether team news has
emerged since the price was quoted) -- see
decisions.grading.GradingInput.no_material_info_risk, which stays a
separate, explicitly human-owned gate, not something this module claims
to automate.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class DataQualityThresholds:
    """Configurable thresholds for the mechanical data-quality check.

    Mirrors config/thresholds.yaml's `data_quality` section.
    """

    min_bookmakers: int = 3
    max_quote_age_minutes: float = 240.0

    def __post_init__(self) -> None:
        if self.min_bookmakers < 1:
            raise ValueError("min_bookmakers must be at least 1")
        if self.max_quote_age_minutes <= 0:
            raise ValueError("max_quote_age_minutes must be positive")


@dataclass(frozen=True)
class DataQualityAssessment:
    """The outcome of the mechanical data-quality check, with reasons."""

    ok: bool
    reasons: list[str]


def assess_data_quality(
    bookmaker_count: int,
    quote_age_minutes: float,
    thresholds: DataQualityThresholds,
) -> DataQualityAssessment:
    """Check whether a consensus estimate rests on adequate, fresh data.

    Args:
        bookmaker_count: Number of bookmakers accepted into the consensus
            for this market (probability.market_pipeline.
            MarketConsensusResult.accepted_bookmaker_count).
        quote_age_minutes: Minutes since the odds were entered/quoted.
        thresholds: The configured DataQualityThresholds to apply.

    Returns:
        A DataQualityAssessment with `ok=True` only if every check
        passes, and human-readable reasons for any failure (empty list
        if ok).

    Raises:
        ValueError: If quote_age_minutes is negative.
    """
    if quote_age_minutes < 0:
        raise ValueError("quote_age_minutes must be non-negative")

    reasons: list[str] = []
    if bookmaker_count < thresholds.min_bookmakers:
        reasons.append(
            f"only {bookmaker_count} bookmaker(s) contributed to consensus "
            f"(minimum {thresholds.min_bookmakers})"
        )
    if quote_age_minutes > thresholds.max_quote_age_minutes:
        reasons.append(
            f"price quote is {quote_age_minutes:.0f} minutes old "
            f"(maximum {thresholds.max_quote_age_minutes:.0f})"
        )

    return DataQualityAssessment(ok=not reasons, reasons=reasons)
