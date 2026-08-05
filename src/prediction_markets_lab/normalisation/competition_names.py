"""Deterministic competition-name and code normalisation.

Maps Football-Data competition codes (e.g. "E0") to canonical
competition names and metadata used throughout the project.
"""

from __future__ import annotations

from dataclasses import dataclass

COMPETITION_REGISTRY: dict[str, "CompetitionInfo"] = {}


@dataclass(frozen=True)
class CompetitionInfo:
    """Canonical metadata for one competition."""

    code: str
    canonical_name: str
    country: str
    tier: int


def _register(info: CompetitionInfo) -> None:
    COMPETITION_REGISTRY[info.code] = info


_register(CompetitionInfo("E0", "Premier League", "England", 1))
_register(CompetitionInfo("E1", "Championship", "England", 2))
_register(CompetitionInfo("SC0", "Scottish Premiership", "Scotland", 1))


def normalise_competition_code(raw_code: str) -> CompetitionInfo | None:
    """Look up canonical competition info for a Football-Data code.

    Args:
        raw_code: The competition code as it appears in the source
            file's "Div" column, e.g. "E0".

    Returns:
        The CompetitionInfo, or None if raw_code is not registered
        (callers must treat this as unresolved, not guess).
    """
    return COMPETITION_REGISTRY.get(raw_code)
