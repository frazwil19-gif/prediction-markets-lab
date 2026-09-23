"""Established bookmaker margin-removal (de-vigging) methods, for R&D comparison only
(Platform V2, Phase V2-1 Workstream A, 2026-09-23).

NOT wired into production. Production uses
`probability.margin_removal.proportional_margin_removal`; `multiplicative` below is
numerically identical to it (asserted in tests) so comparisons are like-for-like.

Every method maps one bookmaker's decimal odds for a complete market (2-way or 3-way)
to probabilities that are each in [0, 1] and sum to 1. None has a parameter fitted to
outcomes -- each solves only for the constant that removes that book's own overround.

Methods (q_i = 1/odds_i, B = sum q_i):
  multiplicative  p_i = q_i / B
  additive        p_i = q_i - (B - 1)/n   (negative values clipped to 0, renormalised; flagged)
  power           p_i = q_i ** k, k solved so sum p_i = 1
  odds_ratio      odds(p_i) = odds(q_i) / c, c solved so sum p_i = 1   (Cheung 2015)
  shin            Shin (1992/1993) insider-trading model, z solved iteratively (Jullien & Salanie form)
"""
from __future__ import annotations

import math
from typing import Callable, Sequence

METHODS: tuple[str, ...] = ("multiplicative", "additive", "power", "odds_ratio", "shin")
SOLVER_TOLERANCE = 1e-12
SOLVER_MAX_ITERATIONS = 200


def _implied(odds: Sequence[float]) -> list[float]:
    if len(odds) < 2:
        raise ValueError("a market needs at least 2 outcomes")
    if any((o is None) or (not math.isfinite(o)) or o <= 1.0 for o in odds):
        raise ValueError(f"decimal odds must be finite and > 1.0, got {list(odds)}")
    return [1.0 / o for o in odds]


def _bisect(f: Callable[[float], float], lo: float, hi: float) -> float:
    flo = f(lo)
    for _ in range(SOLVER_MAX_ITERATIONS):
        mid = 0.5 * (lo + hi)
        fm = f(mid)
        if abs(fm) < SOLVER_TOLERANCE:
            return mid
        if (fm > 0) == (flo > 0):
            lo, flo = mid, fm
        else:
            hi = mid
    return 0.5 * (lo + hi)


def multiplicative(odds: Sequence[float]) -> list[float]:
    q = _implied(odds)
    b = sum(q)
    return [x / b for x in q]


def additive(odds: Sequence[float]) -> list[float]:
    q = _implied(odds)
    n, b = len(q), sum(q)
    p = [x - (b - 1.0) / n for x in q]
    if min(p) < 0:
        p = [max(x, 0.0) for x in p]
    s = sum(p)
    return [x / s for x in p]


def power(odds: Sequence[float]) -> list[float]:
    q = _implied(odds)
    if abs(sum(q) - 1.0) < SOLVER_TOLERANCE:
        return list(q)
    # sum q**k is strictly decreasing in k (all q in (0,1)); root is k>1 if B>1, k<1 if B<1
    k = _bisect(lambda k: sum(x ** k for x in q) - 1.0, 1e-6, 50.0)
    p = [x ** k for x in q]
    s = sum(p)
    return [x / s for x in p]


def odds_ratio(odds: Sequence[float]) -> list[float]:
    q = _implied(odds)
    if abs(sum(q) - 1.0) < SOLVER_TOLERANCE:
        return list(q)

    def probs(c: float) -> list[float]:
        return [x / (c + x - c * x) for x in q]

    # sum probs(c) is strictly decreasing in c; c=1 gives B
    c = _bisect(lambda c: sum(probs(c)) - 1.0, 1e-6, 1e6)
    p = probs(c)
    s = sum(p)
    return [x / s for x in p]


def shin(odds: Sequence[float]) -> list[float]:
    q = _implied(odds)
    b = sum(q)
    if b <= 1.0:
        # Shin's model is defined for a positive overround only; with no margin the
        # insider share is zero and Shin reduces to normalisation.
        return [x / b for x in q]

    def probs(z: float) -> list[float]:
        return [(math.sqrt(z * z + 4.0 * (1.0 - z) * x * x / b) - z) / (2.0 * (1.0 - z)) for x in q]

    z = _bisect(lambda z: sum(probs(z)) - 1.0, 0.0, 0.999)
    p = probs(z)
    s = sum(p)
    return [x / s for x in p]


_FUNCS: dict[str, Callable[[Sequence[float]], list[float]]] = {
    "multiplicative": multiplicative,
    "additive": additive,
    "power": power,
    "odds_ratio": odds_ratio,
    "shin": shin,
}


def devig(odds: Sequence[float], method: str) -> list[float]:
    try:
        return _FUNCS[method](odds)
    except KeyError:
        raise ValueError(f"unknown method {method!r}; expected one of {METHODS}") from None


def consensus(book_odds: Sequence[Sequence[float]], method: str) -> list[float]:
    """Mean across bookmakers of each book's de-vigged probabilities (the production
    aggregation rule), renormalised. Every book must quote the same outcomes in order."""
    if not book_odds:
        raise ValueError("no bookmakers")
    n = len(book_odds[0])
    if any(len(b) != n for b in book_odds):
        raise ValueError("bookmakers quote different numbers of outcomes")
    per = [devig(b, method) for b in book_odds]
    mean = [sum(p[i] for p in per) / len(per) for i in range(n)]
    s = sum(mean)
    return [x / s for x in mean]
