"""Read/write access to the Hypothesis Registry CSV.

Thin wrapper over storage.csv_store, adding hypothesis-specific
invariants: no duplicate hypothesis_id, and status-transition
validation on update.
"""

from __future__ import annotations

from pathlib import Path

from prediction_markets_lab.research.hypothesis_validation import (
    validate_hypothesis_status_transition,
)
from prediction_markets_lab.research.schemas import Hypothesis
from prediction_markets_lab.storage.csv_store import (
    append_record,
    overwrite_records,
    read_records,
)


def load_registry(path: Path) -> list[Hypothesis]:
    """Load every hypothesis from the registry CSV.

    Args:
        path: Path to hypothesis_registry.csv.

    Returns:
        A list of validated Hypothesis records. Empty list if the file
        does not exist yet.
    """
    return read_records(path, Hypothesis)


def add_hypothesis(path: Path, hypothesis: Hypothesis) -> None:
    """Add a new hypothesis to the registry, rejecting duplicate IDs.

    Args:
        path: Path to hypothesis_registry.csv.
        hypothesis: The new hypothesis to add.

    Raises:
        ValueError: If a hypothesis with the same hypothesis_id already
            exists in the registry.
    """
    existing = load_registry(path)
    existing_ids = {h.hypothesis_id for h in existing}
    if hypothesis.hypothesis_id in existing_ids:
        raise ValueError(
            f"hypothesis_id {hypothesis.hypothesis_id!r} already exists in the registry "
            "— use a new, unique ID (see research/RESEARCH_SAFEGUARDS.md for revisiting "
            "rejected ideas)"
        )
    append_record(path, hypothesis)


def update_hypothesis_status(path: Path, hypothesis_id: str, new_status: str) -> Hypothesis:
    """Update a hypothesis's status, enforcing the allowed transition graph.

    Args:
        path: Path to hypothesis_registry.csv.
        hypothesis_id: The hypothesis to update.
        new_status: The proposed new status.

    Returns:
        The updated Hypothesis record.

    Raises:
        ValueError: If hypothesis_id is not found, or the transition is
            not allowed from the hypothesis's current status.
    """
    registry = load_registry(path)
    matches = [h for h in registry if h.hypothesis_id == hypothesis_id]
    if not matches:
        raise ValueError(f"hypothesis_id {hypothesis_id!r} not found in registry")
    if len(matches) > 1:
        raise ValueError(
            f"duplicate hypothesis_id {hypothesis_id!r} found in registry — data is inconsistent"
        )

    current = matches[0]
    transition = validate_hypothesis_status_transition(current.status, new_status)
    if not transition.allowed:
        raise ValueError(transition.reason)

    updated = current.model_copy(update={"status": new_status})
    new_registry = [updated if h.hypothesis_id == hypothesis_id else h for h in registry]
    overwrite_records(path, new_registry)
    return updated
