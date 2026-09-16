"""Extract match statistics, Over/Under 2.5, and Asian Handicap prices
from a Football-Data CSV row, for Football Cycle 2's discovery dataset.

This module is additive to (never a replacement for)
`football_bookmaker_extraction.py`, which remains the sole source of
truth for the 1X2 market already used by Cycle 1. Match statistics and
the two new markets extracted here were present in the raw
Football-Data files acquired for Cycle 1 but never extracted by Cycle
1's canonicalisation step (see
`research/cycles/CYCLE_003_FOOTBALL/FOOTBALL_CYCLE_2_DIRECTION_CHANGE_REPORT.md`
section 1.2).

Column-naming convention, confirmed directly against
https://www.football-data.co.uk/notes.txt and against every raw file in
this repository: for any bookmaker prefix and any market, the closing
price column is the opening price column with a single "C" inserted
immediately after the bookmaker prefix (e.g. B365H -> B365CH,
B365>2.5 -> B365C>2.5, B365AHH -> B365CAHH, AHh -> AHCh). This holds
uniformly across the 1X2, Over/Under, and Asian Handicap column
families and is exploited directly below rather than re-derived per
market.

IMPORTANT price-semantics correction (found while building this
cycle's extraction/orchestration script, verified by (a) header
inspection of every raw file in this repo across E0/E1/SC0 x
2020/21-2024/25 and (b) https://www.football-data.co.uk/notes.txt):
the SIX-bookmaker individual panel used for the 1X2 market in Cycle 1
(`football_bookmaker_extraction.KNOWN_BOOKMAKER_PREFIXES` = B365, BW,
BF, PS, WH, 1XB) does NOT extend to Over/Under 2.5 or Asian Handicap.
For those two markets, in THIS data source, only two individual
bookmakers publish both opening and closing odds across the full
2020/21-2024/25 corpus: Bet365 (B365) and Pinnacle (P). A third
individual bookmaker, Betfair Exchange (BFE), appears only from
2024/25 onward (one season, all three competitions) -- confirmed by a
full competition x season header sweep, not assumed. Football-Data
additionally publishes two of its OWN cross-bookmaker summary
statistics for these markets, Max (best price available per side,
independently, across its monitored panel) and Avg (mean price per
side, independently, across that same panel) -- see notes.txt:
"MaxH = Market maximum home win odds", "AvgH = Market average home win
odds". These are summary statistics computed by the source across a
wider, unnamed bookmaker panel, NOT a single bookmaker's simultaneous
two-sided quote. In particular Max_side_a and Max_side_b need not come
from the same bookmaker, so a "Max" pair is not a coherent tradeable
book and must never be margin-removed or treated as an executable
price; Avg is closer to a market-consensus proxy (and is treated as
one below, after margin removal) but is still the source's own
computation, not something built here from our own set of individual
quotes, and must be labelled as such rather than presented as if it
were one bookmaker's price or as if we computed it from a panel of
our own choosing.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class MatchStatistics:
    """Raw, unadjusted match statistics for one match (both teams).

    All fields are Optional[int] (or Optional[str] for referee) and are
    None -- never imputed -- when the source column is absent or blank
    for that match. These are outcome-of-the-match statistics: never
    safe to use as a PRE-match feature for that same match. See
    `docs/DATA_LEAKAGE_RULES.md` and this cycle's leakage-safe feature
    module, which lags these by at least one match before use.
    """

    home_shots: int | None
    away_shots: int | None
    home_shots_on_target: int | None
    away_shots_on_target: int | None
    home_corners: int | None
    away_corners: int | None
    home_fouls: int | None
    away_fouls: int | None
    home_yellow_cards: int | None
    away_yellow_cards: int | None
    home_red_cards: int | None
    away_red_cards: int | None
    referee: str | None


def _parse_int(value: object) -> int | None:
    """Parse a raw CSV cell as a non-negative integer, or None if blank/invalid."""
    if value is None:
        return None
    text = str(value).strip()
    if text == "":
        return None
    try:
        parsed = int(float(text))
    except ValueError:
        return None
    if parsed < 0:
        return None
    return parsed


def extract_match_statistics(row: dict[str, str]) -> MatchStatistics:
    """Extract raw match statistics from one Football-Data CSV row.

    Args:
        row: A dict of column name -> raw string value, as read from a
            Football-Data CSV row.

    Returns:
        A MatchStatistics record. Any field whose source column is
        absent or blank is None, never imputed or defaulted to zero.
    """
    return MatchStatistics(
        home_shots=_parse_int(row.get("HS")),
        away_shots=_parse_int(row.get("AS")),
        home_shots_on_target=_parse_int(row.get("HST")),
        away_shots_on_target=_parse_int(row.get("AST")),
        home_corners=_parse_int(row.get("HC")),
        away_corners=_parse_int(row.get("AC")),
        home_fouls=_parse_int(row.get("HF")),
        away_fouls=_parse_int(row.get("AF")),
        home_yellow_cards=_parse_int(row.get("HY")),
        away_yellow_cards=_parse_int(row.get("AY")),
        home_red_cards=_parse_int(row.get("HR")),
        away_red_cards=_parse_int(row.get("AR")),
        referee=(row.get("Referee") or "").strip() or None,
    )


# The 1X2 individual-bookmaker panel (unchanged from Cycle 1). Retained
# here only so callers can reuse it explicitly if they ever need to;
# it is NOT the right default for Over/Under or Asian Handicap (see
# module docstring and TWO_WAY_INDIVIDUAL_BOOKMAKER_PREFIXES below).
KNOWN_BOOKMAKER_PREFIXES: tuple[str, ...] = ("B365", "BW", "BF", "PS", "WH", "1XB")

# Individual bookmakers confirmed (by header sweep across every raw
# file in this repo, all of E0/E1/SC0 x 2020/21-2024/25) to publish
# BOTH opening and closing odds for Over/Under 2.5 and Asian Handicap
# across the FULL corpus. This is the correct default for
# extract_two_way_market when called for those two markets.
TWO_WAY_INDIVIDUAL_BOOKMAKER_PREFIXES: tuple[str, ...] = ("B365", "P")

# Betfair Exchange individual quotes for Over/Under and Asian Handicap
# exist ONLY from the 2024/25 season onward (confirmed by the same
# header sweep -- absent in 2020/21 through 2023/24 for all three
# competitions). Extracted separately, never merged into the main
# panel above, and any downstream use must treat its coverage as
# single-season, not corpus-wide.
BFE_ONLY_PREFIX: tuple[str, ...] = ("BFE",)

# Football-Data's own cross-bookmaker SUMMARY statistics (not single
# bookmaker quotes -- see module docstring). "Max" is diagnostic-only
# (never margin-removed: the two sides need not share a bookmaker).
# "Avg" is used as a market-consensus proxy after margin removal.
MARKET_SUMMARY_PREFIXES: tuple[str, ...] = ("Max", "Avg")


@dataclass(frozen=True)
class TwoWayPrice:
    """One bookmaker's two-outcome market price for one match, one price timing."""

    bookmaker: str
    price_timing: str  # "opening" | "closing"
    side_a_odds: float
    side_b_odds: float


@dataclass(frozen=True)
class TwoWayExtractionResult:
    complete_prices: list[TwoWayPrice]
    rejected_bookmakers: list[str]


def _is_valid_odds(value: object) -> bool:
    if value is None:
        return False
    try:
        f = float(value)
    except (TypeError, ValueError):
        return False
    return f > 1.0


def extract_two_way_market(
    row: dict[str, str],
    side_a_suffix: str,
    side_b_suffix: str,
    bookmaker_prefixes: tuple[str, ...] = TWO_WAY_INDIVIDUAL_BOOKMAKER_PREFIXES,
) -> TwoWayExtractionResult:
    """Extract every complete, valid two-way INDIVIDUAL bookmaker price
    pair from one row (never Max/Avg -- use
    extract_market_summary_two_way for those).

    Generalises `football_bookmaker_extraction.extract_bookmaker_triplets`
    to two-outcome markets (Over/Under 2.5 goals, Asian Handicap),
    reusing the same closing-column convention (a "C" inserted directly
    after the bookmaker prefix).

    Args:
        row: A dict of column name -> raw string value.
        side_a_suffix: The column suffix for side A's opening odds
            (e.g. ">2.5" for Over/Under, "AHH" for Asian Handicap home).
        side_b_suffix: The column suffix for side B's opening odds
            (e.g. "<2.5", "AHA").
        bookmaker_prefixes: Individual-bookmaker prefixes to check.
            Defaults to TWO_WAY_INDIVIDUAL_BOOKMAKER_PREFIXES (B365,
            P), the two confirmed to cover the full 2020/21-2024/25
            corpus for these markets. Pass BFE_ONLY_PREFIX separately
            to extract Betfair Exchange's 2024/25-only quotes without
            conflating its coverage with the full-corpus panel.

    Returns:
        A TwoWayExtractionResult with one TwoWayPrice per bookmaker per
        price timing that has a complete, valid pair, plus a list of
        rejected (incomplete/invalid) bookmaker/timing labels.
    """
    complete: list[TwoWayPrice] = []
    rejected: list[str] = []

    for prefix in bookmaker_prefixes:
        for timing, c_insert in (("opening", ""), ("closing", "C")):
            col_a = f"{prefix}{c_insert}{side_a_suffix}"
            col_b = f"{prefix}{c_insert}{side_b_suffix}"

            raw_a = row.get(col_a)
            raw_b = row.get(col_b)

            blank_a = raw_a is None or str(raw_a).strip() == ""
            blank_b = raw_b is None or str(raw_b).strip() == ""

            if blank_a and blank_b:
                continue

            if not (_is_valid_odds(raw_a) and _is_valid_odds(raw_b)):
                rejected.append(f"{prefix} ({timing})")
                continue

            complete.append(
                TwoWayPrice(
                    bookmaker=prefix,
                    price_timing=timing,
                    side_a_odds=float(raw_a),
                    side_b_odds=float(raw_b),
                )
            )

    return TwoWayExtractionResult(complete_prices=complete, rejected_bookmakers=rejected)


@dataclass(frozen=True)
class MarketSummaryTwoWayPrice:
    """A Football-Data cross-bookmaker SUMMARY statistic for one match,
    one price timing -- NOT a single bookmaker's tradeable quote.

    summary_type "max": side_a_odds/side_b_odds are each independently
    the best price found across Football-Data's monitored panel for
    that side; the two need not come from the same bookmaker, so this
    pair is not a coherent two-sided book. Never margin-remove it or
    compute an "implied probability sum" from it as if it were a real
    overround.

    summary_type "avg": side_a_odds/side_b_odds are each independently
    the mean price across that same panel. Used here as a
    market-consensus PROXY after margin removal, but it is
    Football-Data's own computation across a panel of unstated size,
    not a consensus we built from a chosen set of individual quotes --
    label it as such in any downstream analysis (e.g.
    "source_avg_fair_probability", never "our consensus").
    """

    summary_type: str  # "max" | "avg"
    price_timing: str  # "opening" | "closing"
    side_a_odds: float | None
    side_b_odds: float | None


def extract_market_summary_two_way(
    row: dict[str, str],
    side_a_suffix: str,
    side_b_suffix: str,
) -> list[MarketSummaryTwoWayPrice]:
    """Extract Football-Data's own Max/Avg summary prices for a two-way market.

    Each side is validated and reported independently (unlike
    extract_two_way_market, a summary row is kept even if only one
    side is present/valid -- Max/Avg are not a matched bookmaker pair,
    so there is no "incomplete pair" concept here; a missing/invalid
    side is simply None).

    Args:
        row: A dict of column name -> raw string value.
        side_a_suffix: e.g. ">2.5" or "AHH".
        side_b_suffix: e.g. "<2.5" or "AHA".

    Returns:
        A list of MarketSummaryTwoWayPrice, at most one per
        (summary_type, price_timing) combination (so up to 4: max
        opening, max closing, avg opening, avg closing), omitting any
        combination where both sides are absent.
    """
    results: list[MarketSummaryTwoWayPrice] = []

    for prefix, summary_type in ((p, p.lower()) for p in MARKET_SUMMARY_PREFIXES):
        for timing, c_insert in (("opening", ""), ("closing", "C")):
            col_a = f"{prefix}{c_insert}{side_a_suffix}"
            col_b = f"{prefix}{c_insert}{side_b_suffix}"

            raw_a = row.get(col_a)
            raw_b = row.get(col_b)

            a = float(raw_a) if _is_valid_odds(raw_a) else None
            b = float(raw_b) if _is_valid_odds(raw_b) else None

            if a is None and b is None:
                continue

            results.append(
                MarketSummaryTwoWayPrice(
                    summary_type=summary_type,
                    price_timing=timing,
                    side_a_odds=a,
                    side_b_odds=b,
                )
            )

    return results


def extract_asian_handicap_line(row: dict[str, str]) -> dict[str, float | None]:
    """Extract the (single) Asian Handicap line at opening and closing.

    Per https://www.football-data.co.uk/notes.txt, AHh is described as
    "Market size of handicap (home team) (since 2019/2020)" -- i.e. a
    market-level reference line, NOT documented as tied to any one
    bookmaker. It may be negative, zero, or a quarter value (e.g.
    -0.25) and is validated only as "is a number", not as odds
    (`> 1.0`).

    Returns:
        {"opening_line": float | None, "closing_line": float | None}
    """
    def _parse_line(value: object) -> float | None:
        if value is None:
            return None
        text = str(value).strip()
        if text == "":
            return None
        try:
            return float(text)
        except ValueError:
            return None

    return {
        "opening_line": _parse_line(row.get("AHh")),
        "closing_line": _parse_line(row.get("AHCh")),
    }
