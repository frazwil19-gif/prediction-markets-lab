from prediction_markets_lab.reports.research_report import (
    WeeklyResearchReportContext,
    generate_weekly_research_report,
)
from prediction_markets_lab.research.schemas import Behaviour, Hypothesis


def make_hypothesis(hypothesis_id: str, status: str) -> Hypothesis:
    return Hypothesis(
        hypothesis_id=hypothesis_id,
        created_at="2026-08-03T00:00:00+00:00",
        updated_at="2026-08-03T00:00:00+00:00",
        sport="football",
        market_type="pre_match_1x2",
        behaviour_name="test behaviour",
        hypothesis_statement="Some falsifiable claim.",
        economic_or_market_rationale="Some rationale.",
        target_metric="net_ev",
        minimum_observations=100,
        status=status,
    )


def make_behaviour(behaviour_id: str, grade: str) -> Behaviour:
    return Behaviour(
        behaviour_id=behaviour_id,
        behaviour_name="test behaviour",
        sport="football",
        market_type="pre_match_1x2",
        definition="Some pattern.",
        evidence_grade=grade,
        sample_size=120,
    )


def test_weekly_report_keeps_realised_profit_and_ev_separate():
    context = WeeklyResearchReportContext(
        week_label="2026-W31",
        markets_analysed=20,
        signals_generated=4,
        live_bets=1,
        paper_trades=3,
        realised_profit_gbp=0.42,
        estimated_ev_gbp=0.15,
        performance_by_sport={"football": "3 markets"},
        performance_by_competition={"Premier League": "2 markets"},
        performance_by_market_type={"pre_match_1x2": "3 markets"},
        clv_summary="Average CLV +1.2%",
        calibration_summary="Brier 0.21",
        data_quality_issues=["one stale bookmaker price excluded"],
        model_drift_concerns=[],
    )
    report = generate_weekly_research_report(
        context,
        new_hypotheses=[make_hypothesis("H-0001", "IDEA")],
        testing_hypotheses=[make_hypothesis("H-0002", "BACKTESTING")],
        rejected_hypotheses=[],
        near_miss_hypotheses=[],
        strongest_behaviours=[make_behaviour("B-0001", "B")],
        weakest_behaviours=[make_behaviour("B-0002", "C")],
        recommended_next_research_task="Collect near-kickoff price data for H-FB-003.",
    )

    assert "Realised profit" in report
    assert "Estimated EV" in report
    assert "£0.42" in report
    assert "£0.15" in report
    assert "must never be conflated" in report
    assert "H-0001" in report
    assert "H-0002" in report
    assert "B-0001" in report
    assert "one stale bookmaker price excluded" in report
    assert "Collect near-kickoff price data" in report


def test_weekly_report_handles_empty_sections_gracefully():
    context = WeeklyResearchReportContext(
        week_label="2026-W31",
        markets_analysed=0,
        signals_generated=0,
        live_bets=0,
        paper_trades=0,
        realised_profit_gbp=0.0,
        estimated_ev_gbp=0.0,
        performance_by_sport={},
        performance_by_competition={},
        performance_by_market_type={},
        clv_summary="",
        calibration_summary="",
        data_quality_issues=[],
        model_drift_concerns=[],
    )
    report = generate_weekly_research_report(
        context,
        new_hypotheses=[],
        testing_hypotheses=[],
        rejected_hypotheses=[],
        near_miss_hypotheses=[],
        strongest_behaviours=[],
        weakest_behaviours=[],
        recommended_next_research_task="",
    )
    assert "_None._" in report
    assert "_None recorded._" in report
