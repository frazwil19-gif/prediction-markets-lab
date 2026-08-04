"""Load manually entered bookmaker odds (templates/manual_odds_entry.csv).

Provides two views of the same file:

- `load_manual_odds_by_market`: grouped by (market_id, selection) —
  convenient for quick inspection, but NOT sufficient for correct
  margin removal, since that requires all of one bookmaker's outcomes
  for a market together.
- `load_manual_odds_by_bookmaker`: grouped by (market_id, bookmaker) ->
  {selection: odds} — the correct grouping for margin removal. Use
  this one for anything that feeds into EV/grading.
"""

from __future__ import annotations

import csv
from collections import defaultdict
from pathlib import Path


def _read_rows(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        raise FileNotFoundError(f"manual odds file not found: {path}")

    required_columns = {"market_id", "selection", "bookmaker", "decimal_odds"}
    with open(path, newline="") as f:
        reader = csv.DictReader(f)
        if reader.fieldnames is None or not required_columns.issubset(reader.fieldnames):
            missing = required_columns - set(reader.fieldnames or [])
            raise ValueError(f"manual odds file is missing required columns: {missing}")
        return [row for row in reader if any(row.values())]


def load_manual_odds_by_market(path: Path) -> dict[str, dict[str, list[float]]]:
    """Load manual odds entries, grouped by market then by outcome.

    NOTE: this view loses the per-bookmaker grouping and must NOT be
    used for margin removal (see module docstring). It exists for
    quick inspection / previewing only (see scripts/import_manual_odds.py).

    Args:
        path: Path to a CSV file matching
            templates/manual_odds_entry.csv (must include at least
            market_id, selection, bookmaker, decimal_odds columns).

    Returns:
        A nested dict: {market_id: {selection: [decimal_odds, ...]}}.

    Raises:
        FileNotFoundError: If path does not exist.
        ValueError: If a row is missing a required column or has a
            non-numeric decimal_odds value.
    """
    result: dict[str, dict[str, list[float]]] = defaultdict(lambda: defaultdict(list))
    for row in _read_rows(path):
        market_id = row["market_id"]
        selection = row["selection"]
        try:
            odds = float(row["decimal_odds"])
        except (TypeError, ValueError) as exc:
            raise ValueError(
                f"non-numeric decimal_odds for market {market_id!r}, "
                f"selection {selection!r}: {row['decimal_odds']!r}"
            ) from exc
        result[market_id][selection].append(odds)

    return {market_id: dict(outcomes) for market_id, outcomes in result.items()}


def load_manual_odds_by_bookmaker(
    path: Path,
) -> dict[str, dict[str, dict[str, float]]]:
    """Load manual odds entries, grouped by market then by bookmaker.

    This is the correct grouping for margin removal: each bookmaker's
    full set of quoted outcomes for a market stays together, so
    probability.margin_removal can be applied per-bookmaker before any
    cross-bookmaker aggregation happens.

    Args:
        path: Path to a CSV file matching
            templates/manual_odds_entry.csv.

    Returns:
        A nested dict: {market_id: {bookmaker: {selection: decimal_odds}}}.

    Raises:
        FileNotFoundError: If path does not exist.
        ValueError: If a row is missing a required column, has a
            non-numeric decimal_odds value, or if the same bookmaker
            quotes the same outcome twice for the same market (which
            would silently overwrite data and hide a data-entry error).
    """
    result: dict[str, dict[str, dict[str, float]]] = defaultdict(lambda: defaultdict(dict))
    for row in _read_rows(path):
        market_id = row["market_id"]
        bookmaker = row["bookmaker"]
        selection = row["selection"]
        try:
            odds = float(row["decimal_odds"])
        except (TypeError, ValueError) as exc:
            raise ValueError(
                f"non-numeric decimal_odds for market {market_id!r}, "
                f"bookmaker {bookmaker!r}, selection {selection!r}: "
                f"{row['decimal_odds']!r}"
            ) from exc

        if selection in result[market_id][bookmaker]:
            raise ValueError(
                f"duplicate odds entry for market {market_id!r}, "
                f"bookmaker {bookmaker!r}, selection {selection!r} — "
                "each bookmaker should quote each outcome exactly once"
            )
        result[market_id][bookmaker][selection] = odds

    return {
        market_id: {bookmaker: dict(outcomes) for bookmaker, outcomes in bookmakers.items()}
        for market_id, bookmakers in result.items()
    }
