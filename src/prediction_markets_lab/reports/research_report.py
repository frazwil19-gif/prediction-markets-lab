"""Weekly/monthly research report generation.

Renders the templates in templates/weekly_research_report.md,
templates/monthly_research_report.md, templates/hypothesis_review.md
and templates/behaviour_atlas_report.md from the Hypothesis Registry,
Behaviour Atlas and accumulated ResearchResult history.

Critically, this module keeps four things visually and structurally
separate on every report it renders, per project instructions section
10: realised profit, estimated EV, model quality, and evidence
strength. A profitable week must never, by itself, cause a promotion
recommendation — this module only reports; promotion is a human
decision (see docs/RESEARCH_ENGINE.md).
"""

from __future__ import annotations

from dataclasses import dataclass

from prediction_markets_lab.reports.markdown_renderer import render_field_list, render_heading
from prediction_markets_lab.research.schemas import Behaviour, Hypothesis


@dataclass(frozen=True)
class WeeklyResearchReportContext:
    """Trading-layer summary stats for the week, kept separate from research evidence."""

    week_label: str
    markets_analysed: int
    signals_generated: int
    live_bets: int
    paper_trades: int
    realised_profit_gbp: float
    estimated_ev_gbp: float
    performance_by_sport: dict[str, str]
    performance_by_competition: dict[str, str]
    performance_by_market_type: dict[str, str]
    clv_summary: str
    calibration_summary: str
    data_quality_issues: list[str]
    model_drift_concerns: list[str]


def generate_weekly_research_report(
    context: WeeklyResearchReportContext,
    new_hypotheses: list[Hypothesis],
    testing_hypotheses: list[Hypothesis],
    rejected_hypotheses: list[Hypothesis],
    near_miss_hypotheses: list[Hypothesis],
    strongest_behaviours: list[Behaviour],
    weakest_behaviours: list[Behaviour],
    recommended_next_research_task: str,
) -> str:
    """Render the weekly research report as a Markdown string.

    Args:
        context: Trading-layer summary numbers for the week (realised
            profit and estimated EV are reported side by side, never
            merged).
        new_hypotheses: Hypotheses registered this week.
        testing_hypotheses: Hypotheses currently in BACKTESTING,
            OUT_OF_SAMPLE, PAPER, or EXPERIMENTAL_LIVE.
        rejected_hypotheses: Hypotheses rejected this week.
        near_miss_hypotheses: Hypotheses/behaviours at NEAR_MISS status.
        strongest_behaviours: Behaviours with the best evidence_grade,
            for visibility only — inclusion here is not a promotion.
        weakest_behaviours: Behaviours with weak/declining evidence.
        recommended_next_research_task: A single free-text
            recommendation, chosen via research_prioritisation, for
            the highest-value next research task.

    Returns:
        The complete report as a Markdown string.
    """
    summary_fields = {
        "Week": context.week_label,
        "Markets analysed": context.markets_analysed,
        "Signals generated": context.signals_generated,
        "Live bets": context.live_bets,
        "Paper trades": context.paper_trades,
    }

    performance_fields = {
        "Realised profit (GBP, actual outcome)": f"£{context.realised_profit_gbp:.2f}",
        "Estimated EV (GBP, at time of decision — NOT the same as realised profit)": (
            f"£{context.estimated_ev_gbp:.2f}"
        ),
    }

    sections = [
        render_heading("Weekly Research Report", level=1),
        f"{render_heading('Summary')}\n\n{render_field_list(summary_fields)}",
        (
            f"{render_heading('Performance summary')}\n\n"
            f"{render_field_list(performance_fields)}\n\n"
            "_Realised profit and estimated EV are reported separately and must "
            "never be conflated — a profitable week does not, by itself, "
            "validate or promote any hypothesis or behaviour (see "
            "docs/RESEARCH_ENGINE.md)._"
        ),
        f"{render_heading('Performance by sport')}\n\n{render_field_list(context.performance_by_sport)}",
        f"{render_heading('Performance by competition')}\n\n{render_field_list(context.performance_by_competition)}",
        f"{render_heading('Performance by market type')}\n\n{render_field_list(context.performance_by_market_type)}",
        f"{render_heading('CLV summary')}\n\n{context.clv_summary or '_None recorded._'}",
        f"{render_heading('Calibration summary')}\n\n{context.calibration_summary or '_None recorded._'}",
    ]

    sections.append(render_heading("New hypotheses"))
    sections.append(_render_hypothesis_list(new_hypotheses))

    sections.append(render_heading("Hypotheses currently testing"))
    sections.append(_render_hypothesis_list(testing_hypotheses))

    sections.append(render_heading("Rejected hypotheses"))
    sections.append(_render_hypothesis_list(rejected_hypotheses))

    sections.append(render_heading("Near-misses"))
    sections.append(_render_hypothesis_list(near_miss_hypotheses))

    sections.append(render_heading("Strongest behaviours (evidence, not promotion)"))
    sections.append(_render_behaviour_list(strongest_behaviours))

    sections.append(render_heading("Weakest behaviours"))
    sections.append(_render_behaviour_list(weakest_behaviours))

    sections.append(render_heading("Data-quality issues"))
    sections.append(
        "\n".join(f"- {issue}" for issue in context.data_quality_issues)
        if context.data_quality_issues
        else "_None recorded._"
    )

    sections.append(render_heading("Model-drift concerns"))
    sections.append(
        "\n".join(f"- {c}" for c in context.model_drift_concerns)
        if context.model_drift_concerns
        else "_None recorded._"
    )

    sections.append(render_heading("Recommended next research task"))
    sections.append(recommended_next_research_task or "_None — insufficient data to prioritise this week._")

    return "\n\n".join(sections) + "\n"


def _render_hypothesis_list(hypotheses: list[Hypothesis]) -> str:
    if not hypotheses:
        return "_None._"
    lines = [
        f"- `{h.hypothesis_id}` ({h.status}): {h.hypothesis_statement}"
        for h in hypotheses
    ]
    return "\n".join(lines)


def _render_behaviour_list(behaviours: list[Behaviour]) -> str:
    if not behaviours:
        return "_None._"
    lines = [
        f"- `{b.behaviour_id}` — {b.behaviour_name} "
        f"(evidence grade {b.evidence_grade}, status {b.status}, n={b.sample_size})"
        for b in behaviours
    ]
    return "\n".join(lines)
