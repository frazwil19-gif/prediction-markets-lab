"""Read/write access to the Behaviour Atlas CSV.

Mirrors research.registry but for Behaviour records — see
docs/RESEARCH_ENGINE.md for how a Behaviour differs from a Hypothesis.
"""

from __future__ import annotations

from pathlib import Path

from prediction_markets_lab.research.hypothesis_validation import (
    validate_behaviour_status_transition,
)
from prediction_markets_lab.research.schemas import Behaviour
from prediction_markets_lab.storage.csv_store import (
    append_record,
    overwrite_records,
    read_records,
)


def load_atlas(path: Path) -> list[Behaviour]:
    """Load every behaviour from the atlas CSV.

    Args:
        path: Path to behaviour_atlas.csv.

    Returns:
        A list of validated Behaviour records. Empty list if the file
        does not exist yet.
    """
    return read_records(path, Behaviour)


def add_behaviour(path: Path, behaviour: Behaviour) -> None:
    """Add a new behaviour to the atlas, rejecting duplicate IDs.

    Args:
        path: Path to behaviour_atlas.csv.
        behaviour: The new behaviour to add.

    Raises:
        ValueError: If a behaviour with the same behaviour_id already
            exists in the atlas.
    """
    existing = load_atlas(path)
    existing_ids = {b.behaviour_id for b in existing}
    if behaviour.behaviour_id in existing_ids:
        raise ValueError(f"behaviour_id {behaviour.behaviour_id!r} already exists in the atlas")
    append_record(path, behaviour)


def update_behaviour_status(path: Path, behaviour_id: str, new_status: str) -> Behaviour:
    """Update a behaviour's status, enforcing the allowed transition graph.

    Args:
        path: Path to behaviour_atlas.csv.
        behaviour_id: The behaviour to update.
        new_status: The proposed new status.

    Returns:
        The updated Behaviour record.

    Raises:
        ValueError: If behaviour_id is not found, or the transition is
            not allowed from the behaviour's current status.
    """
    atlas = load_atlas(path)
    matches = [b for b in atlas if b.behaviour_id == behaviour_id]
    if not matches:
        raise ValueError(f"behaviour_id {behaviour_id!r} not found in atlas")
    if len(matches) > 1:
        raise ValueError(
            f"duplicate behaviour_id {behaviour_id!r} found in atlas — data is inconsistent"
        )

    current = matches[0]
    transition = validate_behaviour_status_transition(current.status, new_status)
    if not transition.allowed:
        raise ValueError(transition.reason)

    updated = current.model_copy(update={"status": new_status})
    new_atlas = [updated if b.behaviour_id == behaviour_id else b for b in atlas]
    overwrite_records(path, new_atlas)
    return updated
