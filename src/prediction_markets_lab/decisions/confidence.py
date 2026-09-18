"""Confidence scoring for opportunities.

V1 implementation (2026-09-18, Daily Engine V1 build). Replaces the Stage-1
placeholder that required a human to type "High"/"Medium"/"Low" for every
candidate by hand -- that would have blocked an automated Daily Bet Card,
which is the whole point of this build (see
docs/DAILY_ENGINE_V1_LOCK_AND_IMPLEMENTATION_ROADMAP.md).

This is a simple, deterministic heuristic derived only from signals the
consensus pipeline already computes: how many bookmakers contributed a
complete, margin-removed quote (probability.consensus.ConsensusResult.
bookmaker_count) and how much they disagree (std_dev). It is NOT a
calibrated confidence score and has not been validated against realised
outcomes -- do not treat "High" as meaning "will win more often." It
exists to flag, mechanically and transparently, when a probability
estimate rests on thin or disagreeing input, matching project
instructions' warning against arbitrary confidence claims by keeping the
rule simple, documented, and config-driven rather than invented per
candidate.

Once real Daily Card history accumulates, performance.calibration can
check whether "High"-labelled candidates really do settle more
predictably than "Low" ones, and these thresholds can be recalibrated
using that evidence rather than guessed again.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

ConfidenceLabel = Literal["High", "Medium", "Low"]


@dataclass(frozen=True)
class ConfidenceThresholds:
    """Configurable thresholds for each confidence label.

    Mirrors config/thresholds.yaml's `confidence` section.
    """

    high_min_bookmakers: int = 5
    high_max_std_dev: float = 0.02
    medium_min_bookmakers: int = 3
    medium_max_std_dev: float = 0.05

    def __post_init__(self) -> None:
        if self.high_min_bookmakers < 1 or self.medium_min_bookmakers < 1:
            raise ValueError("bookmaker-count thresholds must be at least 1")
        if self.high_min_bookmakers < self.medium_min_bookmakers:
            raise ValueError("high_min_bookmakers must be >= medium_min_bookmakers")
        if self.high_max_std_dev <= 0 or self.medium_max_std_dev <= 0:
            raise ValueError("std-dev thresholds must be positive")
        if self.high_max_std_dev > self.medium_max_std_dev:
            raise ValueError("high_max_std_dev must be <= medium_max_std_dev")


def assess_confidence(
    bookmaker_count: int,
    consensus_std_dev: float,
    thresholds: ConfidenceThresholds,
) -> ConfidenceLabel:
    """Label a consensus estimate's confidence from bookmaker count and dispersion.

    Args:
        bookmaker_count: Number of bookmakers whose margin-free probability
            fed the consensus for this outcome.
        consensus_std_dev: Cross-bookmaker standard deviation of the
            margin-free probability for this outcome.
        thresholds: The configured ConfidenceThresholds to apply.

    Returns:
        "High" if enough independent bookmakers agree closely, "Medium"
        if there is some support but less breadth/agreement, "Low"
        otherwise.

    Raises:
        ValueError: If bookmaker_count < 1 or consensus_std_dev < 0.
    """
    if bookmaker_count < 1:
        raise ValueError("bookmaker_count must be at least 1")
    if consensus_std_dev < 0:
        raise ValueError("consensus_std_dev must be non-negative")

    if (
        bookmaker_count >= thresholds.high_min_bookmakers
        and consensus_std_dev <= thresholds.high_max_std_dev
    ):
        return "High"
    if (
        bookmaker_count >= thresholds.medium_min_bookmakers
        and consensus_std_dev <= thresholds.medium_max_std_dev
    ):
        return "Medium"
    return "Low"
