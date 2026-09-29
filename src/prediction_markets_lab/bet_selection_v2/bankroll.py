"""Paper bankroll simulation (V2-6). Replays settled paper singles in event-start order under conservative policies.

No martingale, chasing or recovery staking exists here: a stake depends only on the current bankroll, the frozen
selection (P, odds, commission) and the caps/locks. Stakes below the practical minimum are rounded up only when that
still fits the per-bet cap; otherwise the bet is skipped and counted.
"""
from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass, field

from prediction_markets_lab.bet_selection_v2.prices import ts


@dataclass
class SimResult:
    bankroll_start: float
    policy: str
    final: float
    peak: float
    max_drawdown_gbp: float
    max_drawdown_pct: float
    bets: int = 0
    turnover: float = 0.0
    pnl: float = 0.0
    roi_on_turnover: float | None = None
    longest_losing_streak: int = 0
    skipped: dict = field(default_factory=dict)
    rounded_up_to_min: int = 0
    daily_loss_lock_days: int = 0
    drawdown_stop_fired: bool = False
    path: list = field(default_factory=list)


def kelly_fraction(p: float, odds: float, commission: float) -> float:
    b = (odds - 1.0) * (1.0 - commission)
    return max(0.0, (b * p - (1.0 - p)) / b) if b > 0 else 0.0


def policy_stake(policy: dict, bankroll: float, p: float, odds: float, commission: float, min_stake: float) -> float:
    kind = policy["kind"]
    if kind == "fraction":
        return bankroll * policy["fraction"]
    if kind == "kelly":
        return bankroll * min(policy["cap_fraction"], policy["multiplier"] * kelly_fraction(p, odds, commission))
    if kind == "min_stake":
        return min_stake
    raise ValueError(f"unknown staking kind {kind!r}")   # anything else (e.g. martingale) is refused


def simulate(settled: list[dict], start: float, name: str, policy: dict, sim_cfg: dict) -> SimResult:
    """settled: selection rows joined with 'status' (WON/LOST/VOID)."""
    bets = sorted(settled, key=lambda r: (r["event_start"], r["selection_id"]))
    bank = peak = start
    res = SimResult(start, name, start, start, 0.0, 0.0)
    skipped: Counter = Counter()
    day_open: dict[str, float] = {}
    day_exposure: defaultdict[str, float] = defaultdict(float)
    locked: set[str] = set()
    streak = 0
    for r in bets:
        day = ts(r["event_start"]).date().isoformat()
        if res.drawdown_stop_fired:
            skipped["DRAWDOWN_STOP"] += 1
            continue
        day_open.setdefault(day, bank)
        if day in locked:
            skipped["DAILY_LOSS_LOCK"] += 1
            continue
        p, odds = float(r["probability"]), float(r["decimal_odds"])
        comm = float(r["commission"] or 0.0)
        exch = str(r["is_exchange"]) == "True"
        min_stake = sim_cfg["practical_min_stake_gbp"]["exchange" if exch else "bookmaker"]
        stake = policy_stake(policy, bank, p, odds, comm, min_stake)
        cap = bank * sim_cfg["max_stake_fraction"]
        if stake <= 0:
            skipped["ZERO_STAKE"] += 1
            continue
        if stake < min_stake:
            if min_stake <= cap:
                stake = min_stake
                res.rounded_up_to_min += 1
            else:
                skipped["SKIP_MIN_STAKE"] += 1
                continue
        if stake > cap:
            if policy["kind"] == "min_stake":
                skipped["SKIP_MIN_STAKE"] += 1
                continue
            stake = cap
        if day_exposure[day] + stake > day_open[day] * sim_cfg["max_daily_exposure_fraction"] + 1e-9:
            skipped["DAILY_EXPOSURE_CAP"] += 1
            continue
        stake = round(stake, 2)
        day_exposure[day] += stake
        status = r["status"]
        pnl = stake * (odds - 1.0) * (1.0 - comm) if status == "WON" else (-stake if status == "LOST" else 0.0)
        bank += pnl
        res.bets += status != "VOID"
        res.turnover += stake if status != "VOID" else 0.0
        res.pnl += pnl
        streak = streak + 1 if status == "LOST" else (0 if status == "WON" else streak)
        res.longest_losing_streak = max(res.longest_losing_streak, streak)
        peak = max(peak, bank)
        dd = peak - bank
        if dd > res.max_drawdown_gbp:
            res.max_drawdown_gbp, res.max_drawdown_pct = dd, dd / peak
        res.path.append({"event_start": r["event_start"], "selection_id": r["selection_id"], "stake": stake,
                         "status": status, "bankroll": round(bank, 2)})
        if day_open[day] - bank >= day_open[day] * sim_cfg["daily_loss_lock_fraction"] - 1e-9:
            locked.add(day)
            res.daily_loss_lock_days += 1
        if dd >= peak * sim_cfg["drawdown_stop_fraction"] - 1e-9:
            res.drawdown_stop_fired = True
    res.final, res.peak = round(bank, 2), round(peak, 2)
    res.pnl, res.turnover = round(res.pnl, 2), round(res.turnover, 2)
    res.roi_on_turnover = round(res.pnl / res.turnover, 4) if res.turnover else None
    res.max_drawdown_gbp, res.max_drawdown_pct = round(res.max_drawdown_gbp, 2), round(res.max_drawdown_pct, 4)
    res.skipped = dict(skipped)
    return res


def simulate_all(settled: list[dict], sim_cfg: dict) -> list[SimResult]:
    return [simulate(settled, float(b), name, pol, sim_cfg)
            for b in sim_cfg["bankrolls_gbp"] for name, pol in sim_cfg["policies"].items()]
