"""Extract per-bookmaker H/D/A market triplets from a Football-Data CSV row.

Football-Data's wide-format rows encode each bookmaker's odds as three
separate columns (e.g. B365H, B365D, B365A for Bet365's home/draw/away
prices), both for opening and closing odds (closing columns have a "C"
suffix, e.g. B365CH). This module reconstructs, per bookmaker, the
matched triplet -- never mixing one bookmaker's home price with
another's draw or away price -- and separates opening from closing.

Average (Avg*/AvgC*) and maximum (Max*/MaxC*) odds columns are NOT
individual bookmakers and must never be counted as one when computing
bookmaker_count for consensus eligibility (project instructions
section 8, "Do not use average odds columns as if they were an
independent bookmaker").
"""

from __future__ import annotations

from dataclasses import dataclass

# Known per-bookmaker column prefixes in Football-Data's schema, as
# confirmed directly against live 2024/25 E0/E1/SC0 data (see
# reports/audits/football_data_column_inventory.csv). This list is
# deliberately explicit rather than inferred by pattern-matching column
# names, since aggregate columns (Max, Avg, BFE) use a similar H/D/A
# suffix convention and must be excluded.
KNOWN_BOOKMAKER_PREFIXES: tuple[str, ...] = ("B365", "BW", "BF", "PS", "WH", "1XB")

# Aggregate (non-bookmaker) prefixes that must never be counted as a
# bookmaker for consensus purposes.
AGGREGATE_PREFIXES: tuple[str, ...] = ("Max", "Avg", "BFE")


@dataclass(frozen=True)
class BookmakerTriplet:
    """One bookmaker's complete H/D/A market for one match, one price timing."""

    bookmaker: str
    price_timing: str  # "opening" | "closing"
    home_odds: float
    draw_odds: float
    away_odds: float


@dataclass(frozen=True)
class ExtractionResult:
    """All bookmaker triplets extracted from one CSV row, plus rejections."""

    complete_triplets: list[BookmakerTriplet]
    rejected_bookmakers: list[str]  # bookmaker names with an incomplete/invalid triplet


def _is_valid_odds(value: object) -> bool:
    """Check a single odds value is present, numeric, and plausible.

    Args:
        value: The raw cell value (already parsed to float or None by
            the caller, or a blank string).

    Returns:
        True if the value is a finite number > 1.0 (a valid decimal
        back-bet price). Zero, negative, non-numeric, and missing
        values are all invalid.
    """
    if value is None:
        return False
    try:
        f = float(value)
    except (TypeError, ValueError):
        return False
    return f > 1.0


def extract_bookmaker_triplets(
    row: dict[str, str],
    bookmaker_prefixes: tuple[str, ...] = KNOWN_BOOKMAKER_PREFIXES,
) -> ExtractionResult:
    """Extract every complete, valid bookmaker H/D/A triplet from one CSV row.

    Args:
        row: A dict of column name -> raw string value, as read from a
            Football-Data CSV row (e.g. via csv.DictReader). Blank
            cells should be empty strings or missing keys, not "0".
        bookmaker_prefixes: The bookmaker column prefixes to look for.
            Defaults to KNOWN_BOOKMAKER_PREFIXES.

    Returns:
        An ExtractionResult with one BookmakerTriplet per bookmaker per
        price timing (opening/closing) that has a complete, valid
        triplet, plus a list of bookmaker/timing labels that were
        rejected (missing or invalid) for audit purposes.
    """
    complete: list[BookmakerTriplet] = []
    rejected: list[str] = []

    for prefix in bookmaker_prefixes:
        for timing, suffix in (("opening", ""), ("closing", "C")):
            home_col = f"{prefix}{suffix}H"
            draw_col = f"{prefix}{suffix}D"
            away_col = f"{prefix}{suffix}A"

            home_raw = row.get(home_col)
            draw_raw = row.get(draw_col)
            away_raw = row.get(away_col)

            home_blank = home_raw is None or str(home_raw).strip() == ""
            draw_blank = draw_raw is None or str(draw_raw).strip() == ""
            away_blank = away_raw is None or str(away_raw).strip() == ""

            if home_blank and draw_blank and away_blank:
                # This bookmaker simply didn't quote this timing for this
                # match -- not an error, just absent. Skip silently.
                continue

            if not (_is_valid_odds(home_raw) and _is_valid_odds(draw_raw) and _is_valid_odds(away_raw)):
                rejected.append(f"{prefix} ({timing})")
                continue

            complete.append(
                BookmakerTriplet(
                    bookmaker=prefix,
                    price_timing=timing,
                    home_odds=float(home_raw),
                    draw_odds=float(draw_raw),
                    away_odds=float(away_raw),
                )
            )

    return ExtractionResult(complete_triplets=complete, rejected_bookmakers=rejected)


def bookmaker_count_by_timing(result: ExtractionResult) -> dict[str, int]:
    """Count complete bookmaker triplets per price timing.

    Args:
        result: The ExtractionResult to summarise.

    Returns:
        A dict like {"opening": 5, "closing": 5}.
    """
    counts = {"opening": 0, "closing": 0}
    for triplet in result.complete_triplets:
        counts[triplet.price_timing] += 1
    return counts
