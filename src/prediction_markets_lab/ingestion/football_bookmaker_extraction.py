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
#
# IMPORTANT -- this panel is season-dependent, not a permanent fact of
# the data source: it was verified against 2024/25 specifically and is
# kept as this frozen historical default because Cycle 1's committed
# processed files were built with it. A real drift was found on
# 2026-09-17 while running H-FB2-002's sealed 2025/26 OOS evaluation:
# the 2025/26 raw files DROP "BW", "BF", "WH" and "1XB" entirely and
# ADD "BFD", "BMGM", "BV", "CL", "LB" instead (confirmed by a direct
# header diff of the real 2024/25 vs 2025/26 E0 files -- "B365" and
# "PS" are the only two individual-bookmaker prefixes common to both
# seasons). Under the OLD default alone, only B365+PS (2 bookmakers)
# are extractable from 2025/26 data, below MIN_BOOKMAKERS_FOR_CONSENSUS
# (4), which silently produced zero consensus rows for every 2025/26
# match on the first run. This is a genuine ingestion/schema-drift
# defect, not a hypothesis-related finding -- it was caught and fixed
# during the DATA-ONLY canonicalisation step, before any win-rate, SOT,
# or subgroup figure was computed for H-FB2-002 (see
# H_FB2_002_SEALED_OOS_2025_26_CHECKPOINT.md for the full writeup).
#
# Rather than mutating the historical default above (which stays tied
# to Cycle 1's already-committed 2020/21-2024/25 processed files),
# callers extracting a season known to use the new panel should pass
# this constant explicitly via `bookmaker_prefixes=`.
KNOWN_BOOKMAKER_PREFIXES: tuple[str, ...] = ("B365", "BW", "BF", "PS", "WH", "1XB")

# Verified directly against the real 2025/26 E0 raw file's header
# (2026-09-17): the individual-bookmaker panel Football-Data.co.uk
# tracks for 1X2/O-U/AH changed between 2024/25 and 2025/26. This is
# the 2025/26 equivalent of KNOWN_BOOKMAKER_PREFIXES above, not a
# superset or a merge of the two -- a bookmaker dropped from the panel
# genuinely stops being quoted, so mixing both lists would not recover
# any additional real data and would just add dead lookups.
BOOKMAKER_PREFIXES_2025_26: tuple[str, ...] = ("B365", "BFD", "BMGM", "BV", "BW", "CL", "LB", "PS")

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
