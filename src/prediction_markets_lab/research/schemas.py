"""Schemas for the Research Engine: Hypothesis, Behaviour, ResearchResult.

Field names here match the CSV headers in
research/hypotheses/hypothesis_registry.csv and
research/behaviours/behaviour_atlas.csv exactly, per project
instructions sections 4-7.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

HypothesisStatus = Literal[
    "IDEA",
    "DEFINED",
    "DATA_REQUIRED",
    "BACKTESTING",
    "OUT_OF_SAMPLE",
    "PAPER",
    "EXPERIMENTAL_LIVE",
    "VALIDATED",
    "REJECTED",
    "RETIRED",
]

BehaviourStatus = Literal[
    "UNTESTED",
    "TESTING",
    "NEAR_MISS",
    "VALIDATED",
    "REJECTED",
    "RETIRED",
    "MONITORING",
]

EvidenceGrade = Literal["A", "B", "C", "INSUFFICIENT"]

ResearchVerdict = Literal[
    "PROMOTE",
    "CONTINUE_TESTING",
    "PAPER_ONLY",
    "NEAR_MISS",
    "REJECT",
    "RETIRE",
]

# Statuses reachable from each status, per the lifecycle in
# docs/RESEARCH_ENGINE.md. Enforced by
# hypothesis_validation.validate_status_transition.
HYPOTHESIS_STATUS_TRANSITIONS: dict[str, set[str]] = {
    "IDEA": {"DEFINED", "REJECTED"},
    "DEFINED": {"DATA_REQUIRED", "BACKTESTING", "REJECTED"},
    "DATA_REQUIRED": {"BACKTESTING", "REJECTED"},
    "BACKTESTING": {"OUT_OF_SAMPLE", "REJECTED"},
    "OUT_OF_SAMPLE": {"PAPER", "REJECTED"},
    "PAPER": {"EXPERIMENTAL_LIVE", "REJECTED"},
    "EXPERIMENTAL_LIVE": {"VALIDATED", "REJECTED"},
    "VALIDATED": {"RETIRED"},
    "REJECTED": set(),  # terminal, unless re-registered as a new hypothesis
    "RETIRED": set(),  # terminal
}

BEHAVIOUR_STATUS_TRANSITIONS: dict[str, set[str]] = {
    "UNTESTED": {"TESTING", "REJECTED"},
    "TESTING": {"NEAR_MISS", "VALIDATED", "REJECTED"},
    "NEAR_MISS": {"TESTING", "VALIDATED", "REJECTED"},
    "VALIDATED": {"MONITORING", "RETIRED"},
    "MONITORING": {"RETIRED", "VALIDATED"},
    "REJECTED": set(),
    "RETIRED": set(),
}


class Hypothesis(BaseModel):
    """A single row in research/hypotheses/hypothesis_registry.csv."""

    model_config = ConfigDict(str_strip_whitespace=True)

    hypothesis_id: str
    created_at: str
    updated_at: str
    sport: str
    competition: str = ""
    market_type: str
    behaviour_name: str
    hypothesis_statement: str
    economic_or_market_rationale: str
    required_features: str = ""
    target_metric: str
    minimum_observations: int = Field(ge=1)
    test_method: str = ""
    in_sample_period: str = ""
    out_of_sample_period: str = ""
    multiple_testing_family: str = ""
    status: HypothesisStatus = "IDEA"
    priority: str = ""
    owner: str = ""
    linked_model_id: str = ""
    linked_behaviour_id: str = ""
    result_summary: str = ""
    promotion_reason: str = ""
    rejection_reason: str = ""
    next_review_date: str = ""
    notes: str = ""

    @model_validator(mode="after")
    def _require_falsifiable_statement(self) -> "Hypothesis":
        if not self.hypothesis_statement.strip():
            raise ValueError("hypothesis_statement must not be empty")
        return self


class Behaviour(BaseModel):
    """A single row in research/behaviours/behaviour_atlas.csv."""

    model_config = ConfigDict(str_strip_whitespace=True)

    behaviour_id: str
    behaviour_name: str
    sport: str
    competition_scope: str = ""
    market_type: str
    direction: str = ""
    definition: str
    rationale: str = ""
    first_tested_at: str = ""
    last_updated_at: str = ""
    sample_size: int = Field(default=0, ge=0)
    qualifying_signals: str = ""
    average_odds: float | None = None
    average_model_probability: float | None = None
    average_market_probability: float | None = None
    average_edge: float | None = None
    average_expected_value: float | None = None
    realised_roi: float | None = None
    average_clv: float | None = None
    clv_win_rate: float | None = None
    brier_score: float | None = None
    log_loss: float | None = None
    maximum_drawdown: float | None = None
    in_sample_result: str = ""
    out_of_sample_result: str = ""
    paper_result: str = ""
    live_result: str = ""
    stability_score: float | None = None
    calibration_score: float | None = None
    evidence_grade: EvidenceGrade = "INSUFFICIENT"
    status: BehaviourStatus = "UNTESTED"
    linked_hypotheses: str = ""
    known_limitations: str = ""
    next_action: str = ""


class ResearchResult(BaseModel):
    """A single completed test run, from src/.../research/... pipelines.

    Every field that represents an evidentiary result (p-value,
    confidence interval, calibration, etc.) may be None: the schema
    must support "no meaningful test completed yet" rather than force
    a fabricated placeholder value (project instructions section 7).
    """

    hypothesis_id: str
    model_version: str = ""
    data_version: str = ""
    run_timestamp: str
    sport: str
    competition: str = ""
    market_type: str
    sample_size: int = Field(ge=0)
    qualifying_signals: str = ""
    train_period: str = ""
    test_period: str = ""
    average_odds: float | None = None
    expected_roi: float | None = None
    realised_roi: float | None = None
    average_edge: float | None = None
    average_ev: float | None = None
    average_clv: float | None = None
    brier_score: float | None = None
    log_loss: float | None = None
    max_drawdown: float | None = None
    confidence_interval_lower: float | None = None
    confidence_interval_upper: float | None = None
    p_value: float | None = None
    multiple_testing_adjusted_p_value: float | None = None
    calibration_result: str = ""
    sensitivity_result: str = ""
    stability_result: str = ""
    verdict: ResearchVerdict = "CONTINUE_TESTING"
    limitations: str = ""
    artifact_paths: str = ""
