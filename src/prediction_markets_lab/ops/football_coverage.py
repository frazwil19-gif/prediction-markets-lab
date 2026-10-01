"""Football league coverage (final football coverage task, 2026-10-01).

Single reader for config/football_coverage.yaml (which leagues are observed, at which credit tier, with which paid
markets, and which are paper-eligible) and for the tier throttle in config/api_budget.json.

Observation, paper eligibility and real-money eligibility are separate. This module never touches real money
(config/competitions.yaml football.money_card_competitions stays the only real-money allow-list).

Tier throttle (no fixed caps on shadow data): a Tier-T league pays for odds only while the account's remaining credits
stay above   base + days_left_in_month x (sum of the protected daily needs of every higher-priority consumer)
where base = max(global reserve, the largest min_remaining of an optional core consumer). Tier 1 is only stopped by the
existing hard floor. Tier 3 therefore stops first, then Tier 2; Tier 1 is never sacrificed for shadow data.
"""
from __future__ import annotations

import calendar
import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

import yaml

REPO = Path(__file__).resolve().parents[3]
COVERAGE_PATH = REPO / "config" / "football_coverage.yaml"
BUDGET_PATH = REPO / "config" / "api_budget.json"
TIER_PAPER_CORE, TIER_SHADOW, TIER_CONDITIONAL = 1, 2, 3
SHADOW_LEAGUE_STATUS = "PROSPECTIVE_SHADOW_LEAGUE"   # not in any bsv2 engine_statuses list -> never a PAPER_BET


@dataclass(frozen=True)
class League:
    code: str
    name: str
    sport_key: str | None
    tier: int
    markets: tuple[str, ...]
    observe: bool
    paper_eligible: bool
    grade_1x2: str
    evidence: str


def load(path: Path = COVERAGE_PATH) -> list[League]:
    out = []
    for r in yaml.safe_load(path.read_text())["leagues"]:
        lg = League(r["code"], r["name"], r.get("sport_key"), int(r["tier"]), tuple(r.get("markets") or ()),
                    bool(r["observe"]), bool(r["paper_eligible"]), str(r["grade_1x2"]), str(r["evidence"]))
        if lg.tier not in (TIER_PAPER_CORE, TIER_SHADOW, TIER_CONDITIONAL):
            raise ValueError(f"{lg.code}: unknown tier {lg.tier}")
        if lg.observe and (not lg.sport_key or "h2h" not in lg.markets):
            raise ValueError(f"{lg.code}: an observed league needs a sport key and the h2h market")
        if lg.paper_eligible and (lg.tier != TIER_PAPER_CORE or not lg.observe):
            raise ValueError(f"{lg.code}: paper-eligible leagues must be observed Tier 1 (never throttled)")
        out.append(lg)
    if len({lg.code for lg in out}) != len(out) or len({lg.name for lg in out}) != len(out):
        raise ValueError("duplicate league code or name")
    return out


def observed(leagues: list[League]) -> list[League]:
    return [lg for lg in leagues if lg.observe]


def sport_keys(leagues: list[League]) -> dict[str, str]:
    return {lg.sport_key: lg.name for lg in observed(leagues)}


def markets_by_sport(leagues: list[League]) -> dict[str, tuple[str, ...]]:
    return {lg.sport_key: lg.markets for lg in observed(leagues)}


def paper_competitions(leagues: list[League]) -> frozenset[str]:
    return frozenset(lg.name for lg in leagues if lg.paper_eligible)


def by_name(leagues: list[League]) -> dict[str, League]:
    return {lg.name: lg for lg in leagues}


def tier_floors(budget: dict, leagues: list[League], now: datetime) -> dict[str, float]:
    """sport_key -> minimum remaining credits required to pay for odds this run (Tier 1: the hard floor)."""
    t = budget["football_shadow_tiers"]
    need = t["protected_daily_need"]
    cons = budget["consumers"]
    base = max([float(budget["global_reserve_remaining"])]
               + [float(c["min_remaining"]) for c in cons.values() if "min_remaining" in c])
    days_left = calendar.monthrange(now.year, now.month)[1] - now.day + 1
    protect = {TIER_SHADOW: sum(float(need[k]) for k in t["protects"]["2"]),
               TIER_CONDITIONAL: sum(float(need[k]) for k in t["protects"]["3"])}
    hard = float(cons["football_daily_scan"]["hard_floor_remaining"])
    return {lg.sport_key: hard if lg.tier == TIER_PAPER_CORE else round(base + days_left * protect[lg.tier], 1)
            for lg in observed(leagues)}


def load_budget(path: Path = BUDGET_PATH) -> dict:
    return json.loads(path.read_text())
