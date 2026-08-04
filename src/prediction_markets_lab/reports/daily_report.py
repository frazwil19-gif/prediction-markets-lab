"""Daily report generator.

Renders the Markdown structure defined in
templates/daily_scan_template.md (project instructions section 15)
from a list of graded opportunities plus bankroll/exposure context.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date as date_type

from prediction_markets_lab.reports.markdown_renderer import render_field_list, render_heading
from prediction_markets_lab.storage.schemas import MarketRecord


@dataclass(frozen=True)
class DailyReportContext:
    """Everything needed to render a daily report, beyond the opportunities."""

    report_date: date_type
    markets_scanned: int
    football_markets: int
    tennis_markets: int
    current_bankroll_gbp: float
    current_exposure_gbp: float


def _grade_counts(opportunities: list[MarketRecord]) -> dict[str, int]:
    counts = {"A+": 0, "A": 0, "B": 0, "Reject": 0}
    for opp in opportunities:
        if opp.grade in ("A+", "A", "B"):
            counts[opp.grade] += 1
        else:
            counts["Reject"] += 1
    return counts


def _render_opportunity(index: int, opp: MarketRecord, recommended_stake_gbp: float) -> str:
    fields = {
        "Sport": opp.sport,
        "Competition": opp.competition,
        "Event": opp.event,
        "Market": opp.market_type,
        "Selection": opp.selection,
        "Exchange": opp.exchange,
        "Available odds": opp.exchange_odds,
        "Exchange implied probability": f"{opp.exchange_implied_probability:.1%}",
        "Consensus probability": f"{opp.consensus_probability:.1%}",
        "Model probability": (
            f"{opp.model_probability:.1%}" if opp.model_probability is not None else ""
        ),
        "Final probability": (
            f"{opp.final_probability:.1%}" if opp.final_probability is not None else ""
        ),
        "Probability edge": f"{opp.probability_edge:.1f}pp",
        "Net EV": f"{opp.net_ev:.1%}",
        "Confidence": opp.confidence_score,
        "Data quality": opp.data_quality_score,
        "Liquidity": opp.liquidity_score,
        "Grade": opp.grade,
        "Recommended stake": f"£{recommended_stake_gbp:.2f}",
        "Price valid until": "",
        "Primary reason": opp.decision,
        "Key risk": opp.rejection_reason,
        "Decision": opp.decision,
    }
    return f"{render_heading(f'Opportunity {index}', level=3)}\n\n{render_field_list(fields)}"


def generate_daily_report(
    context: DailyReportContext,
    opportunities: list[MarketRecord],
    recommended_stakes_gbp: dict[str, float],
    final_actions: list[str],
) -> str:
    """Generate the full daily report as a Markdown string.

    Args:
        context: Date, scan counts, and bankroll/exposure context.
        opportunities: All graded opportunities for the day, in the
            order they should be ranked/displayed. Only A+/A/B
            opportunities are typically shown under "Highest-ranked
            opportunities" and "Paper opportunities"; Reject-grade
            opportunities are summarised under "Rejected near-misses".
        recommended_stakes_gbp: Mapping of market_id to recommended
            stake, from risk.staking.recommended_stake_gbp.
        final_actions: The final action list lines, each one of "BET",
            "PAPER TRADE", "WATCH", or "NO BETS TODAY" (with context),
            per project instructions section 15.

    Returns:
        The complete report as a Markdown string, matching
        templates/daily_scan_template.md.
    """
    counts = _grade_counts(opportunities)

    summary_fields = {
        "Date": context.report_date.isoformat(),
        "Markets scanned": context.markets_scanned,
        "Football markets": context.football_markets,
        "Tennis markets": context.tennis_markets,
        "Grade A+": counts["A+"],
        "Grade A": counts["A"],
        "Grade B": counts["B"],
        "Rejected": counts["Reject"],
        "Current bankroll": f"£{context.current_bankroll_gbp:.2f}",
        "Current exposure": f"£{context.current_exposure_gbp:.2f}",
    }

    top_opportunities = [o for o in opportunities if o.grade in ("A+", "A")]
    paper_opportunities = [o for o in opportunities if o.grade == "B"]
    rejected = [o for o in opportunities if o.grade in ("C", "Reject")]

    sections = [
        f"{render_heading('Prediction Markets Daily Report', level=1)}",
        f"{render_heading('Summary')}\n\n{render_field_list(summary_fields)}",
        render_heading("Highest-ranked opportunities"),
    ]

    if top_opportunities:
        for i, opp in enumerate(top_opportunities, start=1):
            stake = recommended_stakes_gbp.get(opp.market_id, 0.0)
            sections.append(_render_opportunity(i, opp, stake))
    else:
        sections.append("_No Grade A or A+ opportunities today._")

    sections.append(render_heading("Paper opportunities"))
    if paper_opportunities:
        lines = [f"- {o.event} — {o.selection} (net EV {o.net_ev:.1%})" for o in paper_opportunities]
        sections.append("\n".join(lines))
    else:
        sections.append("_None._")

    sections.append(render_heading("Rejected near-misses"))
    if rejected:
        lines = [
            f"- {o.event} — {o.selection}: {o.rejection_reason or 'below threshold'}"
            for o in rejected
        ]
        sections.append("\n".join(lines))
    else:
        sections.append("_None._")

    sections.append(f"{render_heading('Missing information')}\n\n_None recorded._")
    sections.append(f"{render_heading('Risk checks')}\n\n_See risk.decision_gates output for this session._")

    sections.append(render_heading("Final action list"))
    if final_actions:
        sections.append("\n".join(f"- {action}" for action in final_actions))
    else:
        sections.append("- NO BETS TODAY")

    return "\n\n".join(sections) + "\n"
