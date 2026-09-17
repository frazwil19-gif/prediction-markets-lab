"""Mechanical PASS/PARTIAL/FAIL verdict for H-FB2-002's sealed 2025/26
out-of-sample test.

Implements the frozen, ordered, mutually exclusive rule fixed in
research/cycles/CYCLE_003_FOOTBALL/FOOTBALL_CYCLE_2_SEALED_OOS_PROTOCOL.md
section 17.2 (the pre-acquisition correction/refinement of the original
sections 11-13) BEFORE any 2025/26 data was downloaded, read, or
inspected in any way, mirroring the discipline already used for Tennis
Cycle 1's sealed-holdout verdict (research/holdout_verdict.py) and
Football Cycle 2's own development-phase verdict
(research/development_verdict.py).

This is a ONE-SHOT test: H-FB2-002 gets exactly one sealed evaluation
against 2025/26 data. There is no "inconclusive but promising" outcome
that leaves room for a second attempt -- a CI that merely touches zero
is FAIL, not PARTIAL.

The rule, in the fixed order it must be evaluated:

1. PARTIAL ("population deviation") if any of the three frozen
   competitions (E0, E1, SC0) is entirely absent from the acquired
   2025/26 raw corpus. Evaluated FIRST, regardless of how favourable the
   effect looks -- if the eligible population does not match the
   pre-registered E0+E1+SC0 specification, this cannot count as the
   genuine one-shot test.
2. Otherwise FAIL if the primary 95% CI does not lie entirely above zero
   (ci_lower <= 0.0) -- covers a CI that includes zero, touches zero
   exactly, or is entirely negative.
3. Otherwise PASS if the realised top-price-quintile sample size is
   >= min_n (100, item J / section 12).
4. Otherwise PARTIAL ("sample too small") -- the CI is favourable but
   the realised sample falls short of the pre-registered floor.

Competition-level effects, per-competition sample size (beyond the
population-completeness precondition in step 1), and the continuous
SOT-differential correlation diagnostic are explicitly NOT part of this
mechanical gate (protocol section 17.3/17.5) -- they are reported as
DIAGNOSTIC -- NOT PRIMARY EVIDENCE alongside the verdict, never used to
override it. Season-level stability does not apply: the sealed OOS test
spans exactly one season by definition (protocol section 17.4).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import FrozenSet, Literal

SealedOOSVerdict = Literal["PASS", "PARTIAL", "FAIL"]

FROZEN_COMPETITIONS: FrozenSet[str] = frozenset({"E0", "E1", "SC0"})


@dataclass(frozen=True)
class SealedOOSVerdictInput:
    """Evidence for H-FB2-002's single sealed 2025/26 evaluation.

    ci_lower/ci_upper: the primary diff_high_minus_low estimand's 95%
        bootstrap CI on the 2025/26 top price quintile.
    point_estimate: the primary estimand's point estimate. Not used
        directly by the verdict logic (the CI already determines
        direction for this one-sided pre-registered hypothesis); kept
        for reporting/auditability.
    n_top_quintile: realised sample size in the top price quintile on
        the 2025/26 data.
    competitions_present: the set of frozen competition codes (subset of
        FROZEN_COMPETITIONS) actually present in the acquired 2025/26
        raw corpus, before any eligibility filtering.
    min_n: the pre-registered minimum sample floor (item J / section
        12) -- default 100.
    """

    ci_lower: float
    ci_upper: float
    point_estimate: float
    n_top_quintile: int
    competitions_present: FrozenSet[str]
    min_n: int = 100

    def __post_init__(self) -> None:
        if self.ci_lower > self.ci_upper:
            raise ValueError("ci_lower must be <= ci_upper")
        if self.n_top_quintile < 0:
            raise ValueError("n_top_quintile cannot be negative")
        if self.min_n <= 0:
            raise ValueError("min_n must be positive")


@dataclass(frozen=True)
class SealedOOSVerdictResult:
    verdict: SealedOOSVerdict
    reason: str


def classify_sealed_oos_result(evidence: SealedOOSVerdictInput) -> SealedOOSVerdictResult:
    """Apply the frozen, mutually exclusive PASS/PARTIAL/FAIL rule."""
    missing_competitions = FROZEN_COMPETITIONS - evidence.competitions_present
    if missing_competitions:
        return SealedOOSVerdictResult(
            "PARTIAL",
            "population deviation: competition(s) "
            f"{sorted(missing_competitions)} entirely absent from the acquired 2025/26 "
            "corpus, so the eligible population does not match the frozen E0+E1+SC0 "
            "specification -- this evaluation cannot count as the genuine one-shot test",
        )

    ci_favourable = evidence.ci_lower > 0.0
    if not ci_favourable:
        return SealedOOSVerdictResult(
            "FAIL",
            "primary 95% CI does not lie entirely above zero (includes, touches, or is "
            "entirely below zero) -- there is no inconclusive category for this one-shot test",
        )

    if evidence.n_top_quintile >= evidence.min_n:
        return SealedOOSVerdictResult(
            "PASS",
            "primary CI lies entirely above zero and the realised top-quintile sample "
            f"({evidence.n_top_quintile}) meets the pre-registered floor of {evidence.min_n}",
        )

    return SealedOOSVerdictResult(
        "PARTIAL",
        "primary CI lies entirely above zero but the realised top-quintile sample "
        f"({evidence.n_top_quintile}) is below the pre-registered floor of {evidence.min_n}; "
        "a favourable CI on an undersized sample is weaker evidence than the same CI on "
        "the full season and is not treated as the genuine one-shot PASS",
    )
