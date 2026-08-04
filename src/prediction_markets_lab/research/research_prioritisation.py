"""Research prioritisation: which hypothesis to work on next.

Implements project instructions section 9: ranks candidates on
multiple factors (evidence strength, expected information gain, data
availability, implementation cost, expected signal frequency,
liquidity, independence from validated behaviours, overfitting risk,
relevance to current goals) rather than by historical ROI alone, which
would systematically favour overfit or lucky candidates.
"""

from __future__ import annotations

from dataclasses import dataclass, field

PriorityTier = str  # "P1" | "P2" | "P3" | "DEFER" | "DO_NOT_RETEST"


@dataclass(frozen=True)
class PrioritisationInputs:
    """Scored inputs for one hypothesis/behaviour, each on a 0.0-1.0 scale.

    A 0.0-1.0 scale (rather than raw units) keeps every factor
    comparable and keeps the weights in `component_weights` meaningful;
    callers are responsible for mapping their own raw data (e.g. "how
    many free data sources exist") onto this scale and documenting how
    they did so.
    """

    evidence_strength: float = 0.0
    expected_information_gain: float = 0.0
    data_availability: float = 0.0
    implementation_cost: float = 0.0  # higher = MORE costly (this factor is inverted when scoring)
    expected_signal_frequency: float = 0.0
    liquidity: float = 0.0
    independence_from_validated_behaviours: float = 0.0
    overfitting_risk: float = 0.0  # higher = MORE risky (this factor is inverted when scoring)
    relevance_to_current_goals: float = 0.0
    do_not_retest: bool = False  # short-circuits to DO_NOT_RETEST tier


DEFAULT_COMPONENT_WEIGHTS: dict[str, float] = {
    "evidence_strength": 0.20,
    "expected_information_gain": 0.15,
    "data_availability": 0.10,
    "implementation_cost": 0.10,  # inverted: (1 - implementation_cost) is scored
    "expected_signal_frequency": 0.10,
    "liquidity": 0.10,
    "independence_from_validated_behaviours": 0.10,
    "overfitting_risk": 0.10,  # inverted: (1 - overfitting_risk) is scored
    "relevance_to_current_goals": 0.05,
}


@dataclass(frozen=True)
class PrioritisationResult:
    """The outcome of prioritising a single hypothesis/behaviour."""

    priority_score: float
    component_scores: dict[str, float]
    priority_tier: PriorityTier
    explanation: str


def _clamp(value: float) -> float:
    return max(0.0, min(1.0, value))


def prioritise(
    inputs: PrioritisationInputs,
    weights: dict[str, float] | None = None,
) -> PrioritisationResult:
    """Compute a priority score, tier, and explanation for one candidate.

    Args:
        inputs: The 0.0-1.0 scored factors for this hypothesis/behaviour.
        weights: Optional override for component weights. Must sum to
            (approximately) 1.0; defaults to DEFAULT_COMPONENT_WEIGHTS.

    Returns:
        A PrioritisationResult with the overall priority_score (0.0-1.0),
        the individual component_scores actually used in the weighted
        sum (after any inversion), a priority_tier, and a
        human-readable explanation.

    Raises:
        ValueError: If weights is provided but does not sum to
            approximately 1.0 (within 1e-6).
    """
    active_weights = weights if weights is not None else DEFAULT_COMPONENT_WEIGHTS
    weight_sum = sum(active_weights.values())
    if abs(weight_sum - 1.0) > 1e-6:
        raise ValueError(f"weights must sum to 1.0, got {weight_sum!r}")

    if inputs.do_not_retest:
        return PrioritisationResult(
            priority_score=0.0,
            component_scores={},
            priority_tier="DO_NOT_RETEST",
            explanation="marked do_not_retest — excluded from prioritisation entirely",
        )

    component_scores = {
        "evidence_strength": _clamp(inputs.evidence_strength),
        "expected_information_gain": _clamp(inputs.expected_information_gain),
        "data_availability": _clamp(inputs.data_availability),
        "implementation_cost": _clamp(1.0 - inputs.implementation_cost),
        "expected_signal_frequency": _clamp(inputs.expected_signal_frequency),
        "liquidity": _clamp(inputs.liquidity),
        "independence_from_validated_behaviours": _clamp(
            inputs.independence_from_validated_behaviours
        ),
        "overfitting_risk": _clamp(1.0 - inputs.overfitting_risk),
        "relevance_to_current_goals": _clamp(inputs.relevance_to_current_goals),
    }

    priority_score = sum(
        component_scores[name] * active_weights[name] for name in active_weights
    )

    if priority_score >= 0.70:
        tier = "P1"
    elif priority_score >= 0.50:
        tier = "P2"
    elif priority_score >= 0.30:
        tier = "P3"
    else:
        tier = "DEFER"

    strongest = max(component_scores, key=lambda k: component_scores[k])
    weakest = min(component_scores, key=lambda k: component_scores[k])
    explanation = (
        f"priority_score={priority_score:.2f} -> {tier}. "
        f"Strongest factor: {strongest} ({component_scores[strongest]:.2f}). "
        f"Weakest factor: {weakest} ({component_scores[weakest]:.2f}). "
        "Score is a weighted average of normalised factors, not historical ROI."
    )

    return PrioritisationResult(
        priority_score=priority_score,
        component_scores=component_scores,
        priority_tier=tier,
        explanation=explanation,
    )
