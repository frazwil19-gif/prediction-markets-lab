"""Deterministic team-name normalisation for football data.

Football-Data uses its own team-name conventions (e.g. "Nott'm Forest",
"Man United", "Sheffield United") which may differ from other sources.
This module maps raw source names to a single canonical name, using an
explicit alias table -- no fuzzy matching is applied silently, per
project instructions section 9.
"""

from __future__ import annotations

from pathlib import Path

import yaml

DEFAULT_ALIASES_PATH = (
    Path(__file__).resolve().parent.parent.parent.parent / "config" / "football_team_aliases.yaml"
)


def load_alias_table(path: Path = DEFAULT_ALIASES_PATH) -> dict[str, str]:
    """Load the raw-name -> canonical-name alias table.

    Args:
        path: Path to config/football_team_aliases.yaml.

    Returns:
        A dict mapping every known raw source name to its canonical
        name (flattened from the YAML's {canonical: [aliases]} form).

    Raises:
        ValueError: If the same raw name is mapped to two different
            canonical names (a configuration error).
    """
    with open(path) as f:
        data = yaml.safe_load(f) or {}

    flattened: dict[str, str] = {}
    for canonical, aliases in data.items():
        all_names = [canonical] + list(aliases or [])
        for raw_name in all_names:
            if raw_name in flattened and flattened[raw_name] != canonical:
                raise ValueError(
                    f"raw name {raw_name!r} is mapped to two different canonical "
                    f"names: {flattened[raw_name]!r} and {canonical!r}"
                )
            flattened[raw_name] = canonical
    return flattened


def normalise_team_name(raw_name: str, alias_table: dict[str, str]) -> str | None:
    """Normalise a single raw team name using the alias table.

    Args:
        raw_name: The team name as it appears in the source file.
        alias_table: The flattened alias table from load_alias_table.

    Returns:
        The canonical name, or None if raw_name is not recognised
        (callers must treat this as "unresolved" and flag it -- see
        reports/audits/unresolved_team_names.csv -- rather than
        guessing).
    """
    return alias_table.get(raw_name)
