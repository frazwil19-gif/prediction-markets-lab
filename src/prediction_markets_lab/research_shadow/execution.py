"""Reusable PRICE / EXECUTION layer (research; design in research/platform_v2/price_execution/EXECUTION_LAYER_DESIGN.md).

prediction -> fair odds -> market quotes -> commissions -> stale/quality checks -> best executable net odds
-> central EV -> uncertainty-adjusted EV -> (decision is made elsewhere).

Not wired into production: Stage A / bet selection keep their own frozen logic. Every quote is preserved, and the
MARKET_CONSENSUS probability, the BEST_EXECUTABLE price and the DECISION price are distinct fields that are never
substituted for one another. Unknown commission -> the venue is not executable (never assumed zero).
"""
from __future__ import annotations

import statistics
from dataclasses import dataclass, field
from datetime import datetime

OUTCOME_SIDES = ("over", "under")


@dataclass(frozen=True)
class Quote:
    venue: str
    side: str                       # outcome label, e.g. "over" / "home"
    back: float | None              # decimal odds to back
    lay: float | None = None        # exchange lay price, if any
    observed_at: datetime | None = None
    is_exchange: bool = False


@dataclass(frozen=True)
class Policy:
    commission: dict[str, float | None]     # venue -> rate; None = unknown
    max_quote_age_minutes: float
    max_exchange_spread: float              # lay/back - 1 above this: exchange quote not used for consensus
    min_odds: float = 1.01


@dataclass
class Assessment:
    side: str
    probability: float
    fair_odds: float
    consensus_probability: float | None
    consensus_venues: list[str]
    best_venue: str | None
    best_gross_odds: float | None
    best_net_odds: float | None
    central_ev: float | None
    ev_at_lower_p: float | None
    quotes_used: list[dict] = field(default_factory=list)
    excluded: list[dict] = field(default_factory=list)
    decision_price: float | None = None     # set only by a separate decision step


def net_odds(o: float, commission: float) -> float:
    """Exchange winnings are reduced by commission: net = 1 + (o - 1)(1 - c)."""
    return 1 + (o - 1) * (1 - commission)


def ev(p: float, o_net: float) -> float:
    return p * o_net - 1


def _age_ok(q: Quote, now: datetime, max_age: float) -> bool:
    return q.observed_at is not None and 0 <= (now - q.observed_at).total_seconds() / 60 <= max_age


def consensus(quotes: list[Quote], sides: tuple[str, ...], policy: Policy, now: datetime) -> tuple[dict[str, float], list[str]]:
    """Median across venues of proportionally de-vigged fair probabilities from venues quoting EVERY side.
    Exchanges contribute the back/lay mid when the spread is within policy; otherwise they are skipped."""
    by_venue: dict[str, dict[str, float]] = {}
    for q in quotes:
        if not _age_ok(q, now, policy.max_quote_age_minutes) or q.back is None or q.back < policy.min_odds:
            continue
        if q.is_exchange:
            if q.lay is None or q.lay / q.back - 1 > policy.max_exchange_spread:
                continue
            price = 2.0 / (1 / q.back + 1 / q.lay)
        else:
            price = q.back
        by_venue.setdefault(q.venue, {})[q.side] = price
    fair = []
    venues = []
    for v, px in sorted(by_venue.items()):
        if set(px) != set(sides):
            continue                                    # never manufacture a missing side
        inv = {s: 1 / px[s] for s in sides}
        tot = sum(inv.values())
        fair.append({s: inv[s] / tot for s in sides})
        venues.append(v)
    if not fair:
        return {}, []
    return {s: statistics.median(f[s] for f in fair) for s in sides}, venues


def assess(side: str, p: float, p_lower: float | None, quotes: list[Quote], sides: tuple[str, ...], policy: Policy, now: datetime) -> Assessment:
    cons, cvenues = consensus(quotes, sides, policy, now)
    used, excluded = [], []
    best: tuple[float, float, str] | None = None
    for q in quotes:
        if q.side != side:
            continue
        reason = None
        if q.back is None or q.back < policy.min_odds:
            reason = "NO_BACK_PRICE"
        elif not _age_ok(q, now, policy.max_quote_age_minutes):
            reason = "STALE_OR_UNTIMED"
        elif q.is_exchange and policy.commission.get(q.venue) is None:
            reason = "COMMISSION_UNKNOWN"
        if reason:
            excluded.append({"venue": q.venue, "back": q.back, "reason": reason})
            continue
        n = net_odds(q.back, policy.commission[q.venue]) if q.is_exchange else q.back
        used.append({"venue": q.venue, "back": q.back, "net": round(n, 4), "is_exchange": q.is_exchange})
        if best is None or n > best[1]:
            best = (q.back, n, q.venue)
    return Assessment(side=side, probability=p, fair_odds=1 / p, consensus_probability=cons.get(side), consensus_venues=cvenues,
                      best_venue=best[2] if best else None, best_gross_odds=best[0] if best else None,
                      best_net_odds=round(best[1], 4) if best else None, central_ev=round(ev(p, best[1]), 5) if best else None,
                      ev_at_lower_p=round(ev(p_lower, best[1]), 5) if (best and p_lower is not None) else None,
                      quotes_used=used, excluded=excluded)
