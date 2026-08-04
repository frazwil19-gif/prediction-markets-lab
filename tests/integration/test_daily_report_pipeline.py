"""Replaces the Stage 1 placeholder import test now that
reports.daily_report has real logic.
"""

from datetime import date

from prediction_markets_lab.reports.daily_report import (
    DailyReportContext,
    generate_daily_report,
)
from prediction_markets_lab.storage.schemas import MarketRecord


def make_opportunity(grade: str, net_ev: float) -> MarketRecord:
    return MarketRecord(
        market_id=f"M-{grade}",
        scan_timestamp="2026-08-03T09:00:00+00:00",
        event_date="2026-08-03",
        sport="football",
        competition="Premier League",
        event="Arsenal vs Chelsea",
        market_type="pre_match_1x2",
        selection="home",
        bookmaker_count=5,
        consensus_probability=0.47,
        exchange="Smarkets",
        exchange_odds=2.20,
        exchange_implied_probability=0.4545,
        commission=0.02,
        probability_edge=2.5,
        gross_ev=net_ev + 0.01,
        net_ev=net_ev,
        grade=grade,
        decision="test decision",
        rejection_reason="below threshold" if grade in ("C", "Reject") else "",
    )


def test_generate_daily_report_includes_all_sections():
    context = DailyReportContext(
        report_date=date(2026, 8, 3),
        markets_scanned=4,
        football_markets=3,
        tennis_markets=1,
        current_bankroll_gbp=10.0,
        current_exposure_gbp=0.25,
    )
    opportunities = [
        make_opportunity("A+", 0.10),
        make_opportunity("B", 0.03),
        make_opportunity("Reject", -0.02),
    ]
    report = generate_daily_report(
        context,
        opportunities,
        recommended_stakes_gbp={"M-A+": 0.50},
        final_actions=["BET: M-A+ home @ 2.20 Smarkets, £0.50"],
    )

    assert "# Prediction Markets Daily Report" in report
    assert "## Summary" in report
    assert "## Highest-ranked opportunities" in report
    assert "### Opportunity 1" in report
    assert "## Paper opportunities" in report
    assert "## Rejected near-misses" in report
    assert "## Final action list" in report
    assert "BET: M-A+" in report
    assert "£0.50" in report


def test_generate_daily_report_handles_no_qualifying_opportunities():
    context = DailyReportContext(
        report_date=date(2026, 8, 3),
        markets_scanned=2,
        football_markets=2,
        tennis_markets=0,
        current_bankroll_gbp=10.0,
        current_exposure_gbp=0.0,
    )
    opportunities = [make_opportunity("Reject", -0.05)]
    report = generate_daily_report(
        context, opportunities, recommended_stakes_gbp={}, final_actions=[]
    )
    assert "No Grade A or A+ opportunities today" in report
    assert "NO BETS TODAY" in report
