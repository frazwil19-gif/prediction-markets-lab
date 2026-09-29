"""Paper multi RESEARCH schema (V2-6). Multis are DISABLED: this module assesses dependency and never selects or records.

Combined odds are never fabricated: without an observed quoted multi price, `combined_price_source` is NOT_QUOTED and
the product of leg prices is shown only as `theoretical_product_odds`.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from math import prod

from prediction_markets_lab.bet_selection_v2.evaluate import MULTI, PAPER_BET, Candidate
from prediction_markets_lab.bet_selection_v2.prices import ts

BLOCKING = {"SAME_EVENT", "SAME_PARTICIPANT"}
ELIGIBLE_LEG_DECISIONS = (PAPER_BET, MULTI)


@dataclass
class MultiResearchRecord:
    legs: list[str]
    enabled: bool
    blocked: bool
    dependency_flags: list[str]
    joint_probability_independent: float
    joint_probability_status: str       # INDEPENDENCE_ASSUMED_RESEARCH_ONLY / UNVALIDATED / BLOCKED
    theoretical_product_odds: float | None
    combined_price_source: str = "NOT_QUOTED"
    quoted_multi_odds: float | None = None
    notes: list[str] = field(default_factory=list)


def _participants(c: Candidate) -> set[str]:
    return {x.strip().lower() for x in c.event_name.replace(" @ ", " v ").split(" v ") if x.strip()}


def _competition(c: Candidate) -> str:
    return c.event_key.split("|")[1] if "|" in c.event_key else ""


def dependency_flags(a: Candidate, b: Candidate) -> list[str]:
    flags = []
    if a.event_key == b.event_key:
        flags.append("SAME_EVENT")
    if _participants(a) & _participants(b):
        flags.append("SAME_PARTICIPANT")
    same_comp = _competition(a) == _competition(b) and a.sport == b.sport
    if same_comp and a.sport == "tennis":
        flags.append("SAME_TOURNAMENT_DRAW")
    if same_comp and a.sport == "football" and abs((ts(a.event_start) - ts(b.event_start)).total_seconds()) <= 72 * 3600:
        flags.append("SAME_COMPETITION_ROUND")
    if a.sport == b.sport and ts(a.event_start).date() == ts(b.event_start).date():
        flags.append("SAME_DAY_SAME_SPORT")
    return flags or ["NONE_DETECTED"]


def assess_pair(a: Candidate, b: Candidate, cfg: dict, quoted_multi_odds: float | None = None) -> MultiResearchRecord:
    notes = []
    for leg in (a, b):
        if leg.decision not in ELIGIBLE_LEG_DECISIONS:
            notes.append(f"leg {leg.prediction_id} not independently eligible ({leg.decision})")
    flags = dependency_flags(a, b)
    blocked = bool(BLOCKING & set(flags)) or bool(notes)
    if BLOCKING & set(flags):
        status = "BLOCKED"
    elif flags == ["NONE_DETECTED"]:
        status = "INDEPENDENCE_ASSUMED_RESEARCH_ONLY"
    else:
        status = "UNVALIDATED"
    odds = [x.decimal_odds for x in (a, b)]
    theo = round(prod(odds), 4) if all(o for o in odds) else None
    return MultiResearchRecord(legs=[a.prediction_id, b.prediction_id], enabled=bool(cfg["multi"]["enabled"]),
                               blocked=blocked, dependency_flags=flags,
                               joint_probability_independent=round(a.probability * b.probability, 6),
                               joint_probability_status=status, theoretical_product_odds=theo,
                               combined_price_source="QUOTED" if quoted_multi_odds else "NOT_QUOTED",
                               quoted_multi_odds=quoted_multi_odds, notes=notes)
