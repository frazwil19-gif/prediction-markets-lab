"""End-to-end integration test spanning the trading and research layers.

Demonstrates: market observations -> corrected per-bookmaker consensus
-> EV calculation -> grading decision -> result record -> a
hypothesis-linked ResearchResult -> a Behaviour Atlas update -> a
weekly research report that reflects it all, per project instructions
section 15.
"""

from pathlib import Path

from prediction_markets_lab.decisions.grading import (
    GradingInput,
    GradingThresholds,
    grade_opportunity,
)
from prediction_markets_lab.ev.expected_value import evaluate
from prediction_markets_lab.probability.market_pipeline import compute_market_consensus
from prediction_markets_lab.reports.research_report import (
    WeeklyResearchReportContext,
    generate_weekly_research_report,
)
from prediction_markets_lab.research.behaviour_atlas import add_behaviour, load_atlas
from prediction_markets_lab.research.evidence_grading import (
    EvidenceGradingThresholds,
    EvidenceInputs,
    grade_evidence,
)
from prediction_markets_lab.research.registry import add_hypothesis, load_registry
from prediction_markets_lab.research.schemas import Behaviour, Hypothesis, ResearchResult
from prediction_markets_lab.storage.csv_store import append_record, read_records
from prediction_markets_lab.storage.schemas import ResultRecord


def test_full_pipeline_from_market_observations_to_research_report(tmp_path: Path):
    # 1. Market observations: two bookmakers quote a full football 1X2 market.
    bookmaker_odds = {
        "Bookmaker A": {"home": 2.10, "draw": 3.40, "away": 3.60},
        "Bookmaker B": {"home": 2.05, "draw": 3.50, "away": 3.75},
    }

    # 2. Corrected per-bookmaker margin removal + cross-bookmaker consensus.
    market_result = compute_market_consensus(
        "M-FB-100", bookmaker_odds, expected_outcomes=["home", "draw", "away"]
    )
    assert market_result.accepted_bookmaker_count == 2
    home_consensus = market_result.consensus_by_outcome["home"]

    # 3. EV calculation against an exchange price.
    exchange_odds = 2.20
    commission = 0.02
    ev_result = evaluate(
        probability=home_consensus.consensus_probability,
        decimal_odds=exchange_odds,
        commission=commission,
    )

    # 4. Grading decision.
    evidence = GradingInput(
        net_ev=ev_result.net_ev,
        probability_edge_pp=ev_result.probability_edge_pp,
        bookmaker_count=home_consensus.bookmaker_count,
        data_quality_ok=True,
        no_material_info_risk=True,
        exchange_price_current=True,
        market_rules_match=True,
        liquidity_adequate=True,
    )
    grading_result = grade_opportunity(evidence, GradingThresholds())
    assert grading_result.grade in {"A+", "A", "B", "C", "Reject"}

    # 5. Result record (the match was settled: home won).
    results_path = tmp_path / "results.csv"
    append_record(
        results_path,
        ResultRecord(
            market_id="M-FB-100",
            event="Arsenal vs Chelsea",
            settlement_date="2026-08-04",
            winning_outcome="home",
            result_source="manual",
        ),
    )
    settled_results = read_records(results_path, ResultRecord)
    assert len(settled_results) == 1
    assert settled_results[0].winning_outcome == "home"

    # 6. A hypothesis this market's observation feeds evidence toward.
    hypotheses_path = tmp_path / "hypothesis_registry.csv"
    hypothesis = Hypothesis(
        hypothesis_id="H-TEST-100",
        created_at="2026-08-03T00:00:00+00:00",
        updated_at="2026-08-03T00:00:00+00:00",
        sport="football",
        competition="Premier League",
        market_type="pre_match_1x2",
        behaviour_name="test integration behaviour",
        hypothesis_statement="Home favourites in this test are systematically mispriced.",
        economic_or_market_rationale="Test rationale.",
        target_metric="net_ev",
        minimum_observations=1,
        test_method="single-observation smoke test",
        in_sample_period="test period",
        out_of_sample_period="test period",
        status="OUT_OF_SAMPLE",
    )
    add_hypothesis(hypotheses_path, hypothesis)
    loaded_hypotheses = load_registry(hypotheses_path)
    assert loaded_hypotheses[0].hypothesis_id == "H-TEST-100"

    # 7. A ResearchResult recording this test (schema-only in this
    # integration test — no CSV store exists yet for ResearchResult in
    # Stage 3, since research result *aggregation* across many markets
    # is a Stage 3+ concern; the schema itself is exercised here).
    research_result = ResearchResult(
        hypothesis_id="H-TEST-100",
        run_timestamp="2026-08-04T00:00:00+00:00",
        sport="football",
        competition="Premier League",
        market_type="pre_match_1x2",
        sample_size=1,
        average_edge=ev_result.probability_edge_pp,
        average_ev=ev_result.net_ev,
        realised_roi=1.0 if grading_result.grade != "Reject" else None,
        verdict="CONTINUE_TESTING",
        limitations="single-observation smoke test — not a real evidentiary claim",
    )
    assert research_result.sample_size == 1

    # 8. Evidence grading based on accumulated (here: minimal) evidence.
    evidence_inputs = EvidenceInputs(
        out_of_sample_observations=1,
        paper_observations=0,
        out_of_sample_result_positive=research_result.average_ev is not None
        and research_result.average_ev > 0,
    )
    evidence_grade_result = grade_evidence(evidence_inputs, EvidenceGradingThresholds())
    assert evidence_grade_result.grade in {"A", "B", "C", "INSUFFICIENT"}

    # 9. Behaviour Atlas update reflecting this evidence.
    behaviour_path = tmp_path / "behaviour_atlas.csv"
    behaviour = Behaviour(
        behaviour_id="BEH-TEST-100",
        behaviour_name="test integration behaviour",
        sport="football",
        market_type="pre_match_1x2",
        definition="Home favourites in test fixtures.",
        sample_size=1,
        average_edge=ev_result.probability_edge_pp,
        average_expected_value=ev_result.net_ev,
        evidence_grade=evidence_grade_result.grade,
        status="TESTING",
        linked_hypotheses="H-TEST-100",
    )
    add_behaviour(behaviour_path, behaviour)
    loaded_atlas = load_atlas(behaviour_path)
    assert loaded_atlas[0].evidence_grade == evidence_grade_result.grade

    # 10. Weekly research report reflecting everything above.
    context = WeeklyResearchReportContext(
        week_label="2026-W31",
        markets_analysed=1,
        signals_generated=1 if grading_result.grade != "Reject" else 0,
        live_bets=0,
        paper_trades=1 if grading_result.grade == "B" else 0,
        realised_profit_gbp=0.0,  # not settled financially in this smoke test
        estimated_ev_gbp=ev_result.net_ev,
        performance_by_sport={"football": "1 market"},
        performance_by_competition={"Premier League": "1 market"},
        performance_by_market_type={"pre_match_1x2": "1 market"},
        clv_summary="",
        calibration_summary="",
        data_quality_issues=[],
        model_drift_concerns=[],
    )
    report = generate_weekly_research_report(
        context,
        new_hypotheses=[hypothesis],
        testing_hypotheses=[hypothesis] if hypothesis.status not in ("VALIDATED", "REJECTED") else [],
        rejected_hypotheses=[],
        near_miss_hypotheses=[],
        strongest_behaviours=[behaviour],
        weakest_behaviours=[],
        recommended_next_research_task="Continue collecting out-of-sample observations for H-TEST-100.",
    )

    assert "H-TEST-100" in report
    assert "BEH-TEST-100" in report
    assert "must never be conflated" in report
    assert f"£{ev_result.net_ev:.2f}" in report
