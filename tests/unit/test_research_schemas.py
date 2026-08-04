import pytest
from pydantic import ValidationError

from prediction_markets_lab.research.schemas import Behaviour, Hypothesis, ResearchResult


def make_hypothesis(**overrides) -> Hypothesis:
    base = dict(
        hypothesis_id="H-0001",
        created_at="2026-08-03T00:00:00+00:00",
        updated_at="2026-08-03T00:00:00+00:00",
        sport="football",
        competition="Premier League",
        market_type="pre_match_1x2",
        behaviour_name="short-priced favourite overpricing",
        hypothesis_statement="Home favourites priced below 1.40 are systematically overpriced by bookmaker consensus.",
        economic_or_market_rationale="Popular teams attract disproportionate public money, pushing bookmaker margins toward favourites.",
        target_metric="net_ev",
        minimum_observations=100,
    )
    base.update(overrides)
    return Hypothesis(**base)


def test_hypothesis_valid_construction():
    h = make_hypothesis()
    assert h.status == "IDEA"


def test_hypothesis_rejects_empty_statement():
    with pytest.raises(ValidationError):
        make_hypothesis(hypothesis_statement="   ")


def test_hypothesis_rejects_invalid_status():
    with pytest.raises(ValidationError):
        make_hypothesis(status="MADE_UP_STATUS")


def test_hypothesis_rejects_non_positive_minimum_observations():
    with pytest.raises(ValidationError):
        make_hypothesis(minimum_observations=0)


def make_behaviour(**overrides) -> Behaviour:
    base = dict(
        behaviour_id="B-0001",
        behaviour_name="short-priced favourite overpricing",
        sport="football",
        market_type="pre_match_1x2",
        definition="Home favourites with bookmaker consensus implied probability > 70%",
    )
    base.update(overrides)
    return Behaviour(**base)


def test_behaviour_valid_construction():
    b = make_behaviour()
    assert b.status == "UNTESTED"
    assert b.evidence_grade == "INSUFFICIENT"


def test_behaviour_rejects_invalid_evidence_grade():
    with pytest.raises(ValidationError):
        make_behaviour(evidence_grade="A+")


def test_behaviour_allows_none_for_unset_metrics():
    b = make_behaviour()
    assert b.brier_score is None
    assert b.realised_roi is None


def make_research_result(**overrides) -> ResearchResult:
    base = dict(
        hypothesis_id="H-0001",
        run_timestamp="2026-08-03T00:00:00+00:00",
        sport="football",
        market_type="pre_match_1x2",
        sample_size=0,
    )
    base.update(overrides)
    return ResearchResult(**base)


def test_research_result_supports_missing_evidence():
    r = make_research_result()
    assert r.p_value is None
    assert r.confidence_interval_lower is None
    assert r.verdict == "CONTINUE_TESTING"


def test_research_result_rejects_invalid_verdict():
    with pytest.raises(ValidationError):
        make_research_result(verdict="MAYBE")


def test_research_result_rejects_negative_sample_size():
    with pytest.raises(ValidationError):
        make_research_result(sample_size=-1)
