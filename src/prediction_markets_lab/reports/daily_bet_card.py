"""Daily Bet Card renderer -- V1 (2026-09-18, Daily Engine V1 build).

Renders the phone-readable Daily Bet Card format specified by the
operator's "GO -- begin implementation of the Daily Probability Engine
V1" instruction: a header block (timestamp, bankroll, scan counts,
grade counts, total exposure), ranked selections with the requested
per-selection fields, an OPTIONAL MULTI section (V1 always reports "not
built" here -- see decisions.recommendation's module docstring and
docs/DAILY_ENGINE_V1_LOCK_AND_IMPLEMENTATION_ROADMAP.md's FUTURE bucket;
singles are the default and multis are explicitly deprioritised), and a
REJECT/WATCH summary with system warnings.

This is deliberately a plain-text/Markdown renderer (no new dependency),
consistent with reports.daily_report's existing Markdown approach, and
is a distinct, additional artifact -- it does not replace
reports.daily_report.generate_daily_report, which remains the more
detailed per-opportunity Stage 2 report format.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from prediction_markets_lab.decisions.recommendation import RecommendationResult

_GRADE_ORDER = {"A+": 0, "A": 1, "B": 2, "C": 3, "Reject": 4}


@dataclass(frozen=True)
class DailyBetCardContext:
    """Header-level context for a Daily Bet Card."""

    generated_at: datetime
    bankroll_gbp: float
    fixtures_scanned: int
    markets_scanned: int


def _rank_key(rec: RecommendationResult) -> tuple[int, float]:
    grade = rec.market_record.grade
    return (_GRADE_ORDER.get(grade, 99), -rec.market_record.net_ev)


def _fair_odds(probability: float) -> float:
    return float("inf") if probability <= 0 else 1.0 / probability


def _potential_profit_gbp(stake_gbp: float, decimal_odds: float) -> float:
    return stake_gbp * (decimal_odds - 1.0)


def render_daily_bet_card(
    context: DailyBetCardContext,
    recommendations: list[RecommendationResult],
    system_warnings: list[str] | None = None,
) -> str:
    """Render the full Daily Bet Card as plain text/Markdown.

    Args:
        context: Header-level scan/bankroll context.
        recommendations: Every graded candidate from today's scan (all
            grades, not just A+/A/B) -- the reject/watch summary is
            derived from this same list, so nothing is silently dropped.
        system_warnings: Any operational warnings to surface (e.g.
            "N bookmakers rejected for an incomplete outcome set",
            "using illustrative/synthetic odds -- see run notes").

    Returns:
        The complete Daily Bet Card as a string.
    """
    ranked = sorted(recommendations, key=_rank_key)
    actionable = [r for r in ranked if r.market_record.grade in ("A+", "A", "B")]
    rejected_or_watch = [r for r in ranked if r.market_record.grade in ("C", "Reject")]
    total_exposure = sum(r.stake_gbp for r in ranked)
    grade_counts = {g: 0 for g in ("A+", "A", "B", "C", "Reject")}
    for r in ranked:
        grade_counts[r.market_record.grade] = grade_counts.get(r.market_record.grade, 0) + 1

    lines: list[str] = []
    lines.append("DAILY BET CARD")
    lines.append(f"Timestamp: {context.generated_at.isoformat(timespec='minutes')}")
    lines.append(f"Bankroll: £{context.bankroll_gbp:.2f}")
    lines.append(f"Fixtures scanned: {context.fixtures_scanned}")
    lines.append(f"Markets scanned: {context.markets_scanned}")
    lines.append(f"Candidates analysed: {len(ranked)}")
    lines.append(
        f"A+/A/B selections: {grade_counts['A+'] + grade_counts['A'] + grade_counts['B']}"
    )
    lines.append(f"Total recommended exposure: £{total_exposure:.2f}")
    lines.append("")

    lines.append("RANKED SELECTIONS")
    if not actionable:
        lines.append("(none -- no candidate cleared Grade B or better today. This is a valid,")
        lines.append(" expected outcome; thresholds are never loosened to manufacture a bet.)")
    for i, rec in enumerate(actionable, start=1):
        m = rec.market_record
        fair_odds = _fair_odds(m.final_probability if m.final_probability is not None else m.consensus_probability)
        potential_profit = _potential_profit_gbp(rec.stake_gbp, m.exchange_odds)
        lines.append(f"{i}. [{m.grade}] {m.selection} -- {m.event} ({m.market_type})")
        lines.append(f"   Odds: {m.exchange_odds:.2f} ({m.exchange})")
        lines.append(
            f"   Estimated P: {m.consensus_probability:.1%}   Fair odds: {fair_odds:.2f}"
        )
        lines.append(f"   Confidence: {m.confidence_score}   Net EV: {m.net_ev:+.1%}")
        lines.append(f"   Stake: £{rec.stake_gbp:.2f}   Potential profit: £{potential_profit:.2f}")
        lines.append(f"   Rationale: {m.decision}")
    lines.append("")

    lines.append("OPTIONAL MULTI")
    lines.append(
        "Not built in V1 -- singles only. A multi engine (independent-leg qualification, "
        "correlation/dependency check, joint-probability estimation) is explicitly "
        "deprioritised behind a working singles pipeline; see "
        "docs/DAILY_ENGINE_V1_LOCK_AND_IMPLEMENTATION_ROADMAP.md."
    )
    lines.append("")

    lines.append("REJECT / WATCH SUMMARY")
    lines.append(
        f"Watch (Grade C): {grade_counts['C']}   Reject: {grade_counts['Reject']}"
    )
    for rec in rejected_or_watch:
        m = rec.market_record
        lines.append(f"- [{m.grade}] {m.selection} ({m.event}, {m.market_type}): {m.decision}")
    if system_warnings:
        lines.append("")
        lines.append("System warnings:")
        for warning in system_warnings:
            lines.append(f"- {warning}")

    return "\n".join(lines) + "\n"
