"""Status transition and consistency validation for hypotheses and behaviours.

Enforces the lifecycle defined in docs/RESEARCH_ENGINE.md: a
hypothesis or behaviour may only move to certain next statuses from
its current one, preventing e.g. jumping straight from IDEA to
VALIDATED, or "un-rejecting" a rejected hypothesis in place (a genuine
revisit must be a new hypothesis, per
research/RESEARCH_SAFEGUARDS.md).
"""

from __future__ import annotations

from dataclasses import dataclass

from prediction_markets_lab.research.schemas import (
    BEHAVIOUR_STATUS_TRANSITIONS,
    HYPOTHESIS_STATUS_TRANSITIONS,
    Behaviour,
    Hypothesis,
)


@dataclass(frozen=True)
class TransitionResult:
    """Outcome of validating a status transition."""

    allowed: bool
    reason: str | None = None


def validate_hypothesis_status_transition(
    current_status: str, new_status: str
) -> TransitionResult:
    """Check whether a hypothesis may move from current_status to new_status.

    Args:
        current_status: The hypothesis's current status.
        new_status: The proposed next status.

    Returns:
        A TransitionResult. Same-status "transitions" (no-ops) are
        always allowed.
    """
    if current_status == new_status:
        return TransitionResult(True, None)
    if current_status not in HYPOTHESIS_STATUS_TRANSITIONS:
        return TransitionResult(False, f"unrecognised current status: {current_status!r}")
    if new_status not in HYPOTHESIS_STATUS_TRANSITIONS:
        return TransitionResult(False, f"unrecognised target status: {new_status!r}")

    allowed_next = HYPOTHESIS_STATUS_TRANSITIONS[current_status]
    if new_status not in allowed_next:
        return TransitionResult(
            False,
            f"cannot move a hypothesis from {current_status!r} to {new_status!r}; "
            f"allowed next statuses are {sorted(allowed_next) or 'none (terminal)'}",
        )
    return TransitionResult(True, None)


def validate_behaviour_status_transition(
    current_status: str, new_status: str
) -> TransitionResult:
    """Check whether a behaviour may move from current_status to new_status.

    Args:
        current_status: The behaviour's current status.
        new_status: The proposed next status.

    Returns:
        A TransitionResult. Same-status "transitions" (no-ops) are
        always allowed.
    """
    if current_status == new_status:
        return TransitionResult(True, None)
    if current_status not in BEHAVIOUR_STATUS_TRANSITIONS:
        return TransitionResult(False, f"unrecognised current status: {current_status!r}")
    if new_status not in BEHAVIOUR_STATUS_TRANSITIONS:
        return TransitionResult(False, f"unrecognised target status: {new_status!r}")

    allowed_next = BEHAVIOUR_STATUS_TRANSITIONS[current_status]
    if new_status not in allowed_next:
        return TransitionResult(
            False,
            f"cannot move a behaviour from {current_status!r} to {new_status!r}; "
            f"allowed next statuses are {sorted(allowed_next) or 'none (terminal)'}",
        )
    return TransitionResult(True, None)


def validate_hypothesis_definition_complete(hypothesis: Hypothesis) -> TransitionResult:
    """Check a hypothesis has everything required before leaving IDEA/DEFINED.

    Per docs/RESEARCH_ENGINE.md, in_sample_period, out_of_sample_period,
    target_metric and minimum_observations must be fixed before testing
    begins (i.e. before status reaches BACKTESTING).

    Args:
        hypothesis: The hypothesis to check.

    Returns:
        A TransitionResult; allowed=False lists which fields are missing.
    """
    missing = []
    if not hypothesis.target_metric.strip():
        missing.append("target_metric")
    if not hypothesis.in_sample_period.strip():
        missing.append("in_sample_period")
    if not hypothesis.out_of_sample_period.strip():
        missing.append("out_of_sample_period")
    if not hypothesis.test_method.strip():
        missing.append("test_method")

    if missing:
        return TransitionResult(
            False, f"hypothesis definition incomplete before testing: missing {missing}"
        )
    return TransitionResult(True, None)


def validate_no_rejected_reuse(existing_ids: set[str], new_id: str, notes: str) -> TransitionResult:
    """Check a new hypothesis doesn't silently reuse a rejected idea's identity.

    A genuine revisit of a rejected hypothesis must be registered as a
    brand-new hypothesis_id with notes explaining the new reason (per
    research/RESEARCH_SAFEGUARDS.md), not a reused ID.

    Args:
        existing_ids: All hypothesis_ids already present in the registry.
        new_id: The proposed new hypothesis_id.
        notes: The new hypothesis's notes field.

    Returns:
        A TransitionResult; allowed=False if new_id collides with an
        existing one.
    """
    if new_id in existing_ids:
        return TransitionResult(
            False,
            f"hypothesis_id {new_id!r} already exists — use a new, unique ID "
            "even when revisiting a rejected idea (see research/RESEARCH_SAFEGUARDS.md)",
        )
    return TransitionResult(True, None)
