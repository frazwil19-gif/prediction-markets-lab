"""Football Cycle 2 -- formal hypothesis development-test support (H-FB2-001, H-FB2-002).

Pre-registration: research/cycles/CYCLE_003_FOOTBALL/
HYPOTHESIS_PREREGISTRATION_H-FB2-001_H-FB2-002.md (frozen and committed
before any development test using these functions was run -- see that
document's commit for the exact freeze point).

This module holds the pure, independently-testable logic the two
formal development-test scripts share:

  - Asian Handicap settlement, identical logic to the discovery-phase
    script's private `_settle_asian_handicap_home`
    (scripts/run_cycle_002_discovery_scan.py), promoted to a tested
    `src/` function now that a formally pre-registered hypothesis
    depends on it directly.
  - A FAVOURITE-perspective view of an Asian Handicap outcome, so a
    SIGNED pricing-error statistic can be computed. The discovery-phase
    scan only ever reported an unsigned ECE gap, which the operator's
    review correctly flagged as unable to say whether extreme
    favourites are OVER- or UNDER-priced on the handicap, or on which
    side. This module adds the signed statistic; it does not replace
    or re-run the original ECE-based discovery finding.
  - A one-sample percentile bootstrap CI (the discovery scripts only
    had a two-sample DIFFERENCE version; H-FB2-001's primary estimand
    is the mean of a single signed quantity).
"""

from __future__ import annotations

import random
from dataclasses import dataclass


def settle_half_line_home(margin: int, line: float) -> float:
    """Settle a whole/half Asian Handicap line for the home side.

    Returns 1.0 (home covers), 0.0 (away covers), or 0.5 (push --
    possible only on whole-number lines).
    """
    adjusted = margin + line
    if adjusted > 0:
        return 1.0
    if adjusted < 0:
        return 0.0
    return 0.5


def settle_asian_handicap_home(margin: int, line: float) -> float:
    """Settle any Asian Handicap line (whole/half/quarter) for the home side.

    Quarter lines (e.g. -0.25, -0.75) split the stake 50/50 between the
    two neighbouring half-lines. Returns a fraction in
    {0.0, 0.25, 0.5, 0.75, 1.0}: 0.5 is a genuine push (whole-line
    only); 0.25/0.75 is a quarter-line half-win/half-loss, a real
    settlement outcome distinct from a push.
    """
    doubled = line * 4
    is_quarter_line = abs(doubled - round(doubled)) < 1e-9 and round(doubled) % 2 != 0
    if is_quarter_line:
        lo, hi = line - 0.25, line + 0.25
        return (settle_half_line_home(margin, lo) + settle_half_line_home(margin, hi)) / 2
    return settle_half_line_home(margin, line)


@dataclass(frozen=True)
class FavouritePerspective:
    """An Asian Handicap outcome re-expressed from the pre-match FAVOURITE's
    side, so a pricing residual has a consistent sign regardless of
    whether the favourite happens to be the home or away team.
    """

    favourite_cover_probability: float
    favourite_result_fraction: float
    is_clean: bool
    favourite_covers: bool | None


def favourite_perspective(
    favourite_side: str,
    ah_home_probability: float,
    ah_away_probability: float,
    home_result_fraction: float,
) -> FavouritePerspective:
    """Re-express an Asian Handicap outcome from the pre-match favourite's side.

    Args:
        favourite_side: "home" or "away" -- which side the pre-match
            1X2 market favours. Must be determined only from pre-match
            1X2 prices, never from the outcome.
        ah_home_probability: the market's fair (margin-removed) AH
            home-cover probability.
        ah_away_probability: the market's fair (margin-removed) AH
            away-cover probability.
        home_result_fraction: the AH settlement fraction from the HOME
            side, as produced by settle_asian_handicap_home.

    Returns:
        A FavouritePerspective with the probability and the result
        both reframed onto the favourite's own side.
    """
    if favourite_side not in ("home", "away"):
        raise ValueError(f"favourite_side must be 'home' or 'away', got {favourite_side!r}")
    if favourite_side == "home":
        cover_probability = ah_home_probability
        result_fraction = home_result_fraction
    else:
        cover_probability = ah_away_probability
        result_fraction = 1.0 - home_result_fraction
    is_clean = result_fraction in (0.0, 1.0)
    covers = (result_fraction == 1.0) if is_clean else None
    return FavouritePerspective(
        favourite_cover_probability=cover_probability,
        favourite_result_fraction=result_fraction,
        is_clean=is_clean,
        favourite_covers=covers,
    )


def bootstrap_ci_mean(values: list[float], seed: int = 42, n_resamples: int = 2000) -> dict:
    """Percentile bootstrap 95% CI for the mean of a single sample.

    Same method/seed/resample-count convention as the discovery-phase
    scripts' bootstrap_ci_mean_diff (percentile method, i.i.d.
    resampling with replacement), extended here to a one-sample
    statistic.
    """
    if not values:
        raise ValueError("values must not be empty")
    rng = random.Random(seed)
    point = sum(values) / len(values)
    means = []
    for _ in range(n_resamples):
        resample = [rng.choice(values) for _ in values]
        means.append(sum(resample) / len(resample))
    means.sort()
    lo = means[int(0.025 * len(means))]
    hi = means[int(0.975 * len(means))]
    return {"point_estimate": point, "ci_lower": lo, "ci_upper": hi, "n": len(values)}


def signed_ah_pricing_residual(rows: list[FavouritePerspective]) -> dict:
    """Mean signed pricing residual for the favourite side of the AH line.

    residual_i = actual_favourite_covers_i (0/1) - favourite_cover_probability_i

    Positive mean => favourites cover MORE often than the market's own
    fair probability implies (the market UNDERPRICES the favourite
    covering). Negative mean => favourites cover LESS often than
    implied (the market OVERPRICES the favourite covering). Only rows
    with is_clean=True are used (pushes and quarter-line half-results
    excluded), exactly as the discovery-phase ECE read excluded pushes.
    """
    clean = [r for r in rows if r.is_clean]
    if not clean:
        return {"n": 0, "status": "insufficient_n"}
    residuals = [
        (1.0 if r.favourite_covers else 0.0) - r.favourite_cover_probability for r in clean
    ]
    ci = bootstrap_ci_mean(residuals)
    return {
        "n": len(clean),
        "mean_signed_residual": ci["point_estimate"],
        "ci_95": [ci["ci_lower"], ci["ci_upper"]],
        "interpretation": (
            "positive = favourites cover MORE than the market's fair AH probability implies "
            "(market underprices the favourite covering); negative = favourites cover LESS "
            "(market overprices the favourite covering)"
        ),
    }
