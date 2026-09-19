"""Load manually entered exchange prices (templates/exchange_price_entry.csv).

Provides the best executable exchange price per (market_id, selection),
choosing between Smarkets and Betfair by highest available decimal odds
for a back bet, as the project instructions direct the user to manually
compare both venues and use whichever offers the best net price.

2026-09-19 addition (operator's "MAJOR NEXT PHASE" instruction, Phase 2):
best_price_from_canonical_odds derives the same ExchangePrice shape
directly from a full multi-bookmaker odds panel (e.g. from
ingestion.the_odds_api_loader.build_canonical_odds_and_metadata), for
when the "best price" is simply the best of several bookmaker quotes
already fetched together, rather than a separately, manually-entered
single price. This keeps scripts/run_daily_scan.py's downstream code
(which only ever consumes an ExchangePrice) identical regardless of
source.
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


def best_price_from_canonical_odds(
    bookmaker_odds_by_market: dict[str, dict[str, dict[str, float]]],
    market_id: str,
    selection: str,
) -> ExchangePrice | None:
    """Find the best currently-obtainable price directly from a full
    multi-bookmaker odds panel, rather than a separately-entered price CSV.

    This is the live-data equivalent of best_price_for_selection: The
    Odds API (and any future live source producing the same canonical
    {market_id: {bookmaker: {selection: decimal_odds}}} shape) already
    returns every bookmaker's quote together, so "the best currently
    obtainable price" is just the maximum across bookmakers -- there is
    no separate best-price entry step for live data, unlike the manual
    CSV workflow where a human compares venues by hand.

    available_size_gbp is set to a nominal placeholder (1.0), following
    the same convention as the manual dry-run entries: V1's stakes
    (pence-to-low-pounds) are trivially small relative to any real fixed-
    odds bookmaker's liability limits, so liquidity is not the live
    binding constraint -- see decisions/liquidity.py's module docstring.
    This is NOT a claim about actual order-book depth (there is none --
    fixed-odds bookmakers do not publish one), just an honest "assume
    adequate" default consistent with how the manual workflow already
    treats fixed-odds prices.

    Args:
        bookmaker_odds_by_market: The canonical
            {market_id: {bookmaker: {selection: decimal_odds}}} structure,
            e.g. from ingestion.the_odds_api_loader.build_canonical_odds_and_metadata.
        market_id: The market to filter to.
        selection: The selection to filter to.

    Returns:
        The best matching ExchangePrice (exchange field holds the
        bookmaker's title), or None if no bookmaker quoted this
        selection for this market.
    """
    bookmaker_odds = bookmaker_odds_by_market.get(market_id, {})
    candidates = [
        (bookmaker, odds[selection]) for bookmaker, odds in bookmaker_odds.items() if selection in odds
    ]
    if not candidates:
        return None
    bookmaker, decimal_odds = max(candidates, key=lambda pair: pair[1])
    return ExchangePrice(
        market_id=market_id,
        exchange=bookmaker,
        selection=selection,
        decimal_odds=decimal_odds,
        available_size_gbp=1.0,
        commission=0.0,
        notes="best price selected automatically from a live multi-bookmaker odds panel",
    )
