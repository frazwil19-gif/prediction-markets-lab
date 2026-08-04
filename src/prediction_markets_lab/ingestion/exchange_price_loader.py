"""Load manually entered exchange prices (templates/exchange_price_entry.csv).

Provides the best executable exchange price per (market_id, selection),
choosing between Smarkets and Betfair by highest available decimal odds
for a back bet, as the project instructions direct the user to manually
compare both venues and use whichever offers the best net price.
"""

from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class ExchangePrice:
    """A single exchange price quote for one selection."""

    market_id: str
    exchange: str
    selection: str
    decimal_odds: float
    available_size_gbp: float
    commission: float
    notes: str = ""


def load_exchange_prices(path: Path) -> list[ExchangePrice]:
    """Load all exchange price rows from a CSV file.

    Args:
        path: Path to a CSV file matching
            templates/exchange_price_entry.csv.

    Returns:
        A list of ExchangePrice records in file order.

    Raises:
        FileNotFoundError: If path does not exist.
        ValueError: If a row has non-numeric odds, size, or commission.
    """
    if not path.exists():
        raise FileNotFoundError(f"exchange price file not found: {path}")

    prices: list[ExchangePrice] = []
    with open(path, newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if not any(row.values()):
                continue
            try:
                prices.append(
                    ExchangePrice(
                        market_id=row["market_id"],
                        exchange=row["exchange"],
                        selection=row["selection"],
                        decimal_odds=float(row["decimal_odds"]),
                        available_size_gbp=float(row["available_size_gbp"]),
                        commission=float(row["commission"]),
                        notes=row.get("notes", "") or "",
                    )
                )
            except (TypeError, ValueError) as exc:
                raise ValueError(f"invalid numeric value in exchange price row: {row}") from exc

    return prices


def best_price_for_selection(
    prices: list[ExchangePrice], market_id: str, selection: str
) -> ExchangePrice | None:
    """Find the best executable back-bet price for a given market/selection.

    "Best" means the highest decimal odds among quotes with non-zero
    available size — i.e. the price a back bettor would actually
    prefer, matching the manual "check both venues, use the better
    net price" workflow.

    Args:
        prices: All loaded exchange prices.
        market_id: The market to filter to.
        selection: The selection to filter to.

    Returns:
        The best matching ExchangePrice, or None if no matching quote
        with available size exists.
    """
    candidates = [
        p
        for p in prices
        if p.market_id == market_id
        and p.selection == selection
        and p.available_size_gbp > 0
    ]
    if not candidates:
        return None
    return max(candidates, key=lambda p: p.decimal_odds)
