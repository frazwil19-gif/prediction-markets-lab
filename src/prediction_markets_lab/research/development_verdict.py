"""Mechanical DEVELOPMENT-PROMOTE / DEVELOPMENT-PARTIAL / DEVELOPMENT-REJECT
verdict for a Football Cycle 2 formal hypothesis's development-period test.

Implements the ordered, mutually exclusive rule fixed in
research/cycles/CYCLE_003_FOOTBALL/
HYPOTHESIS_PREREGISTRATION_H-FB2-001_H-FB2-002.md (items N/O/P for each
hypothesis) BEFORE either hypothesis's development test was run, mirroring
the discipline already used for Tennis Cycle 1's sealed-holdout verdict
(research/holdout_verdict.py).

IMPORTANT: "DEVELOPMENT-PROMOTE" here means only "this hypothesis is
strong enough, on the existing (non-blind) development corpus, to
justify spending the future 2025/26 sealed out-of-sample test on it." It
is NOT equivalent to VALIDATED, PASS, or any claim of an established
trading edge -- see the pre-registration document section 2 (commission/
execution caveat) and FOOTBALL_CYCLE_2_SEALED_OOS_PROTOCOL.md.

The rule, in the fixed order it must be evaluated:

1. REJECT if the primary CI does not exclude zero in the pre-registered
   direction (two-sided: excludes zero at all; one-sided: lies entirely
   above zero), OR if the sign fails the minimum stability bar (item N:
   same sign in at least `min_seasons_same_sign` of the seasons tested).
2. Otherwise PROMOTE, only if ALL of: the CI condition above holds; the
   minimum stability bar (1) is cleared; the sample size floor is met in
   EVERY reported season with a usable sample; and no single competition,
   removed on its own, flips the sign of the pooled effect on the
   remaining competitions.
3. Otherwise PARTIAL -- the CI/sign bar is met, but either the sample-
   size floor or the single-competition-independence check fails.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

DevelopmentVerdict = Literal["DEVELOPMENT-PROMOTE", "DEVELOPMENT-PARTIAL", "DEVELOPMENT-REJECT"]


@dataclass(frozen=True)
class DevelopmentVerdictInput:
    """Evidence for a single pre-registered hypothesis's development test.

    ci_lower/ci_upper: the primary estimand's 95% bootstrap CI.
    point_estimate: the primary estimand's point estimate (used only to
        confirm direction when one_sided_positive_required is True).
    one_sided_positive_required: True for a hypothesis pre-registered
        with a single expected direction (e.g. H-FB2-002); False for a
        two-sided hypothesis (e.g. H-FB2-001).
    n_seasons_same_sign: how many of the individual seasons tested show
        the same sign as the pooled point estimate.
    n_seasons_tested: how many individual seasons had a usable sample at
        all (a season with zero eligible rows is not counted either way).
    min_seasons_same_sign: the pre-registered minimum (item N) -- default
        3, matching "at least 3 of 5" in both H-FB2-001 and H-FB2-002.
    n_floor_met_in_every_reported_season: True only if every season with
        a usable sample also clears the pre-registered minimum-N floor
        (item J) on its own.
    single_competition_independent: True only if excluding any one
        competition (E0, E1, SC0) on its own does not flip the sign of
        the pooled effect on the remaining two competitions.
    """

    ci_lower: float
    ci_upper: float
    point_estimate: float
    one_sided_positive_required: bool
    n_seasons_same_sign: int
    n_seasons_tested: int
    n_floor_met_in_every_reported_season: bool
    single_competition_independent: bool
    min_seasons_same_sign: int = 3

    def __post_init__(self) -> None:
        if self.ci_lower > self.ci_upper:
            raise ValueError("ci_lower must be <= ci_upper")
        if self.n_seasons_same_sign > self.n_seasons_tested:
            raise ValueError("n_seasons_same_sign cannot exceed n_seasons_tested")


@dataclass(frozen=True)
class DevelopmentVerdictResult:
    verdict: DevelopmentVerdict
    reason: str


def classify_development_result(evidence: DevelopmentVerdictInput) -> DevelopmentVerdictResult:
    """Apply the frozen, mutually exclusive DEVELOPMENT-* rule."""
    if evidence.one_sided_positive_required:
        ci_favourable = evidence.ci_lower > 0.0
    else:
        ci_favourable = evidence.ci_lower > 0.0 or evidence.ci_upper < 0.0

    sign_stable = evidence.n_seasons_same_sign >= evidence.min_seasons_same_sign

    if not ci_favourable:
        return DevelopmentVerdictResult(
            "DEVELOPMENT-REJECT",
            "primary CI does not exclude zero in the pre-registered direction",
        )
    if not sign_stable:
        return DevelopmentVerdictResult(
            "DEVELOPMENT-REJECT",
            f"sign matches the pooled estimate in only {evidence.n_seasons_same_sign} of "
            f"{evidence.n_seasons_tested} seasons tested, below the pre-registered minimum of "
            f"{evidence.min_seasons_same_sign} (item N)",
        )

    if evidence.n_floor_met_in_every_reported_season and evidence.single_competition_independent:
        return DevelopmentVerdictResult(
            "DEVELOPMENT-PROMOTE",
            "primary CI excludes zero in the pre-registered direction, sign is stable across "
            "seasons, the sample-size floor is met in every reported season, and no single "
            "competition drives the pooled effect",
        )

    missing = []
    if not evidence.n_floor_met_in_every_reported_season:
        missing.append("the sample-size floor is not met in every reported season")
    if not evidence.single_competition_independent:
        missing.append("the pooled effect's sign flips when a single competition is excluded")
    return DevelopmentVerdictResult(
        "DEVELOPMENT-PARTIAL",
        "primary CI/sign bar is met, but " + " and ".join(missing),
    )
