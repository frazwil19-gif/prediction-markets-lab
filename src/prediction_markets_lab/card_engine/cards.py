"""Card legs, deterministic enumeration, joint probability, uncertainty and equal-capital comparison (pure functions)."""
from __future__ import annotations

import hashlib
import itertools
import math
from dataclasses import dataclass, field

EXCHANGES = ("betfair_ex", "matchbook", "smarkets")
HIGH_P, POS_EV = "HIGH_P", "POS_EV"
INDEPENDENT = "INDEPENDENT_DISTINCT_EVENTS"   # supported by V2-7 A1/A2 within the stated precision
UNVERIFIED = "UNVERIFIED_DEPENDENCE"


@dataclass(frozen=True)
class Leg:
    scan: str
    book: str
    sport_key: str
    event_id: str
    event_name: str
    start: str
    selection: str
    opponent: str
    p: float                 # same-scan engine P (Betfair midpoint), selection side
    odds: float              # this book's price for the selection, same scan
    quote_last_update: str
    exchange_width: float    # Betfair book width behind p (probability points)
    engine: str              # engine_id@version
    quality: tuple[str, ...] = field(default_factory=tuple)   # failed quality checks; empty = clean

    @property
    def ev(self) -> float:
        return self.p * self.odds - 1.0          # bookmaker leg: no commission

    @property
    def clean(self) -> bool:
        return not self.quality


def leg_sigma(p: float, width: float, cal_se: float) -> float:
    """Per-leg probability uncertainty: calibration SE of its band (historical holdout) combined with half the exchange
    book width (midpoint error bound treated as a 1-sigma term)."""
    return math.sqrt(cal_se ** 2 + (width / 2.0) ** 2)


def dependence(legs: tuple[Leg, ...]) -> tuple[str, list[str]]:
    flags = []
    if len({l.event_id for l in legs}) < len(legs):
        return UNVERIFIED, ["SAME_EVENT"]
    names = [n.lower() for l in legs for n in (l.selection, l.opponent)]
    if len(set(names)) < len(names):
        return UNVERIFIED, ["SAME_PARTICIPANT"]
    if len({l.sport_key for l in legs}) < len(legs):
        flags.append("SAME_TOURNAMENT")          # flagged; A1 found no deviation for tennis same-tournament doubles
    return INDEPENDENT, flags


@dataclass
class Card:
    card_id: str
    rule_version: str
    scan: str
    book: str
    group: str
    k: int
    legs: tuple[Leg, ...]
    dependence: str
    dependence_flags: list[str]
    p_joint: float | None
    sigma_joint: float | None
    odds_indicative: float
    fair_odds: float | None
    break_even: float
    ev: float | None
    ev_low: float | None      # EV at P_joint - 1 sigma
    ev_high: float | None
    all_legs_pos_ev: bool
    all_legs_clean: bool
    status: str
    reasons: list[str]


def card_id(rule: str, scan: str, book: str, group: str, legs: tuple[Leg, ...]) -> str:
    key = "|".join([rule, scan, book, group] + sorted(f"{l.event_id}:{l.selection}" for l in legs))
    return hashlib.sha256(key.encode()).hexdigest()[:16]


def build_card(rule: str, group: str, legs: tuple[Leg, ...], cal_se) -> Card:
    legs = tuple(sorted(legs, key=lambda l: (l.start, l.event_id)))
    dep, flags = dependence(legs)
    o = math.prod(l.odds for l in legs)
    reasons = ["ODDS_INDICATIVE_NOT_EXECUTION_VERIFIED"]
    pj = sj = ev = lo = hi = fair = None
    if dep == INDEPENDENT:
        pj = math.prod(l.p for l in legs)
        # delta method on log P_joint
        sj = pj * math.sqrt(sum((leg_sigma(l.p, l.exchange_width, cal_se(l.p)) / l.p) ** 2 for l in legs))
        fair, ev = 1 / pj, pj * o - 1
        lo, hi = max(pj - sj, 0.0) * o - 1, min(pj + sj, 1.0) * o - 1
    else:
        reasons.append("JOINT_P_NOT_ESTIMABLE")
    pos = all(l.ev > 0 for l in legs)
    clean = all(l.clean for l in legs)
    if not clean:
        reasons += sorted({q for l in legs for q in l.quality})
    if dep != INDEPENDENT:
        status = "RESEARCH_ONLY_UNVERIFIED"
    elif not clean:
        status = "REJECT_LEG_QUALITY"
    elif group == POS_EV and pos and lo is not None and lo > 0:
        status = "SHADOW_CANDIDATE"                # would be PAPER_CANDIDATE if multis were ever enabled (they are not)
        reasons.append("ALL_LEGS_POS_EV_AND_EV_LOW_GT_0")
    elif group == POS_EV and pos:
        status = "SHADOW_WATCH"
        reasons.append("EV_LOW_LE_0")
    else:
        status = "RESEARCH_HIGH_P"
        if not pos:
            reasons.append("NOT_ALL_LEGS_POS_EV")
    return Card(card_id(rule, legs[0].scan, legs[0].book, group, legs), rule, legs[0].scan, legs[0].book, group, len(legs),
                legs, dep, flags, pj, sj, o, fair, 1 / o, ev, lo, hi, pos, clean, status, reasons)


def enumerate_cards(rule: str, legs: list[Leg], cal_se, max_legs_per_pool: int = 12, max_k: int = 3) -> tuple[list[Card], dict]:
    """Deterministic, bounded enumeration per (book, group). Pools: HIGH_P = P>=0.70 favourites (research, any EV);
    POS_EV = clean legs with EV>0. Each pool is capped at `max_legs_per_pool` by a pre-declared order (HIGH_P: P desc;
    POS_EV: EV desc; ties by event id) -- truncation is recorded, never hidden."""
    cards, space = [], {}
    by_book: dict[str, list[Leg]] = {}
    for l in legs:
        by_book.setdefault(l.book, []).append(l)
    for book in sorted(by_book):
        # quality-failed legs never enter a pool (their P is unreliable); they are counted, not combined
        pools = {HIGH_P: sorted([l for l in by_book[book] if l.clean and l.p >= 0.70], key=lambda l: (-l.p, l.event_id)),
                 POS_EV: sorted([l for l in by_book[book] if l.clean and l.ev > 0], key=lambda l: (-l.ev, l.event_id))}
        for group, pool in pools.items():
            kept = pool[:max_legs_per_pool]
            n_cards = 0
            for k in range(1, max_k + 1):
                for combo in itertools.combinations(kept, k):
                    if len({l.event_id for l in combo}) < k:
                        continue
                    cards.append(build_card(rule, group, combo, cal_se))
                    n_cards += 1
            space[f"{book}|{group}"] = {"pool": len(pool), "kept": len(kept), "truncated": len(pool) - len(kept),
                                        "cards": n_cards,
                                        "quality_rejected_legs": sum(1 for l in by_book[book] if not l.clean)}
    return cards, space


# ---------------------------------------------------------------- equal-capital comparison (same legs as singles)
def equal_capital(legs: tuple[Leg, ...], stake_fraction: float) -> dict:
    """Card with total stake s vs the same legs as singles with s/k each. Independent legs assumed (card is INDEPENDENT).
    Returns EV (fraction of bankroll), expected log-growth, P(lose entire stake)."""
    k, s = len(legs), stake_fraction
    ps, os_ = [l.p for l in legs], [l.odds for l in legs]
    pj, oj = math.prod(ps), math.prod(os_)
    card_ev = s * (pj * oj - 1)
    card_g = pj * math.log1p(s * (oj - 1)) + (1 - pj) * math.log1p(-s) if s < 1 else float("-inf")
    sing_ev = sum(s / k * (p * o - 1) for p, o in zip(ps, os_))
    sing_g = 0.0
    for wins in itertools.product((1, 0), repeat=k):
        pr = math.prod(p if w else 1 - p for p, w in zip(ps, wins))
        ret = sum((s / k) * ((o - 1) if w else -1) for o, w in zip(os_, wins))
        sing_g += pr * math.log1p(ret)
    return {"stake_fraction": s, "card_ev": card_ev, "singles_ev": sing_ev, "card_log_growth": card_g,
            "singles_log_growth": sing_g, "card_p_total_loss": 1 - pj, "singles_p_total_loss": math.prod(1 - p for p in ps),
            "better_growth": "CARD" if card_g > sing_g else "SINGLES"}
