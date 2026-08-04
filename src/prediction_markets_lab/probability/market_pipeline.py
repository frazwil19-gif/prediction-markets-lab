"""The correct bookmaker-market-to-consensus pipeline.

This module fixes a Stage 2 defect: scripts/generate_daily_shortlist.py
previously computed "consensus" from raw implied probabilities (each
bookmaker's own overround still baked in), grouped only by
(market_id, selection) — never actually removing any margin. That is
wrong and must not be used for real-money grading.

The correct process, per bookmaker, per market:

    1. Group all mutually exclusive outcomes quoted by that bookmaker.
    2. Convert decimal odds to raw implied probabilities.
    3. Calculate the bookmaker's overround.
    4. Remove the overround using the proportional method (V1 default).
    5. Retain the margin-free probability for each outcome.

Then, across bookmakers, per outcome:

    6. Aggregate the margin-free probabilities (median as V1 default,
       via probability.consensus).

Bookmakers that do not quote every expected outcome for a market are
rejected outright rather than silently treated as valid partial data
(an incomplete market cannot have its margin correctly removed).
"""

from __future__ import annotations

from dataclasses import dataclass

from prediction_markets_lab.probability.consensus import ConsensusResult, calculate_consensus
from prediction_markets_lab.probability.margin_removal import proportional_margin_removal
from prediction_markets_lab.probability.odds_conversion import (
    decimal_odds_list_to_implied_probabilities,
)


@dataclass(frozen=True)
class RejectedBookmaker:
    """A bookmaker's quotes for one market that could not be used."""

    market_id: str
    bookmaker: str
    reason: str


@dataclass(frozen=True)
class MarketConsensusResult:
    """Per-outcome consensus for a single market, plus rejection audit trail."""

    market_id: str
    consensus_by_outcome: dict[str, ConsensusResult]
    rejected_bookmakers: list[RejectedBookmaker]
    accepted_bookmaker_count: int


def _margin_free_probabilities_for_bookmaker(
    outcome_odds: dict[str, float], expected_outcomes: list[str]
) -> dict[str, float] | None:
    """Remove one bookmaker's margin, or return None if the market is incomplete.

    Args:
        outcome_odds: This bookmaker's quoted decimal odds, keyed by
            outcome name.
        expected_outcomes: The full set of outcomes this market type
            requires (e.g. ["home", "draw", "away"]).

    Returns:
        A dict of margin-free probability per outcome, in
        expected_outcomes order, or None if this bookmaker did not
        quote every expected outcome.
    """
    if set(outcome_odds.keys()) != set(expected_outcomes):
        return None

    ordered_odds = [outcome_odds[outcome] for outcome in expected_outcomes]
    raw_probs = decimal_odds_list_to_implied_probabilities(ordered_odds)
    fair_probs = proportional_margin_removal(raw_probs)
    return dict(zip(expected_outcomes, fair_probs))


def compute_market_consensus(
    market_id: str,
    bookmaker_odds: dict[str, dict[str, float]],
    expected_outcomes: list[str],
) -> MarketConsensusResult:
    """Compute margin-free, cross-bookmaker consensus for one market.

    Args:
        market_id: Identifier for the market, used only for the
            rejection audit trail.
        bookmaker_odds: Mapping of bookmaker name to that bookmaker's
            quoted decimal odds, keyed by outcome
            (see ingestion.manual_odds_loader.load_manual_odds_by_bookmaker).
        expected_outcomes: The full set of outcomes this market type
            requires, e.g. ["home", "draw", "away"] for football 1X2
            or ["player_a", "player_b"] for tennis match winner.

    Returns:
        A MarketConsensusResult with one ConsensusResult per outcome
        (median, mean, std dev, min, max, IQR, bookmaker count — see
        probability.consensus.ConsensusResult), plus the list of any
        bookmakers rejected for quoting an incomplete outcome set.

    Raises:
        ValueError: If expected_outcomes is empty, or if zero
            bookmakers remain after rejecting incomplete markets (there
            is nothing to build a consensus from).
    """
    if not expected_outcomes:
        raise ValueError("expected_outcomes must not be empty")

    fair_probs_by_outcome: dict[str, list[float]] = {outcome: [] for outcome in expected_outcomes}
    rejected: list[RejectedBookmaker] = []

    for bookmaker, outcome_odds in bookmaker_odds.items():
        fair_probs = _margin_free_probabilities_for_bookmaker(outcome_odds, expected_outcomes)
        if fair_probs is None:
            missing = set(expected_outcomes) - set(outcome_odds.keys())
            extra = set(outcome_odds.keys()) - set(expected_outcomes)
            reason_parts = []
            if missing:
                reason_parts.append(f"missing outcomes: {sorted(missing)}")
            if extra:
                reason_parts.append(f"unexpected outcomes: {sorted(extra)}")
            rejected.append(
                RejectedBookmaker(
                    market_id=market_id,
                    bookmaker=bookmaker,
                    reason="incomplete/mismatched outcome set — " + "; ".join(reason_parts),
                )
            )
            continue

        for outcome, prob in fair_probs.items():
            fair_probs_by_outcome[outcome].append(prob)

    accepted_count = len(bookmaker_odds) - len(rejected)
    if accepted_count == 0:
        raise ValueError(
            f"market {market_id!r} has no bookmaker with a complete outcome set "
            f"({len(rejected)} bookmaker(s) rejected) — cannot build a consensus"
        )

    consensus_by_outcome = {
        outcome: calculate_consensus(probs)
        for outcome, probs in fair_probs_by_outcome.items()
        if probs
    }

    return MarketConsensusResult(
        market_id=market_id,
        consensus_by_outcome=consensus_by_outcome,
        rejected_bookmakers=rejected,
        accepted_bookmaker_count=accepted_count,
    )
