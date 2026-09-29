"""Funnel, results and breakdown reporting (V2-6). Descriptive only: no projections, no profit promises."""
from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import asdict

from prediction_markets_lab.bet_selection_v2.bankroll import simulate_all

P_BANDS = [(0.0, 0.5, "<50%"), (0.5, 0.6, "50-59.9%"), (0.6, 0.7, "60-69.9%"), (0.7, 0.8, "70-79.9%"),
           (0.8, 0.9, "80-89.9%"), (0.9, 1.01, "90%+")]
ODDS_BANDS = [(1.0, 1.33, "<1.33"), (1.33, 1.5, "1.33-1.49"), (1.5, 2.0, "1.50-1.99"), (2.0, 3.0, "2.00-2.99"),
              (3.0, 1e9, "3.00+")]


def band(x: float, bands) -> str:
    for lo, hi, lab in bands:
        if lo <= x < hi:
            return lab
    return "?"


def funnel_from_runs(runs: list[dict]) -> dict:
    keys = ["events_scanned", "valid_predictions", "high_p_candidates", "priced_candidates", "PAPER_BET",
            "MULTI_RESEARCH_ELIGIBLE", "WATCH", "REJECT", "paper_bets_added", "money_card_qualified"]
    tot = {k: sum(int(float(r.get(k) or 0)) for r in runs) for k in keys}
    by_day: dict[str, int] = defaultdict(int)
    for r in runs:
        by_day[r["run_at"][:10]] += int(float(r.get("paper_bets_added") or 0))
    return {"runs": len(runs), "totals_over_runs": tot,
            "note": "per-run counts summed; a prediction re-evaluated in several runs is counted in each run",
            "days_evaluated": len(by_day), "no_bet_days": sorted(d for d, n in by_day.items() if n == 0),
            "bet_days": {d: n for d, n in sorted(by_day.items()) if n}}


def _stats(rows: list[dict]) -> dict:
    settled = [r for r in rows if r.get("status") in ("WON", "LOST")]
    n = len(settled)
    won = sum(r["status"] == "WON" for r in settled)
    exp = sum(float(r["net_ev"]) * float(r["stake_units"]) for r in settled)
    real = sum(float(r["pnl_units"]) for r in settled)
    stake = sum(float(r["stake_units"]) for r in settled)
    cum = peak = dd = 0.0
    streak = longest = 0
    for r in sorted(settled, key=lambda r: (r["event_start"], r["selection_id"])):
        cum += float(r["pnl_units"])
        peak = max(peak, cum)
        dd = max(dd, peak - cum)
        streak = streak + 1 if r["status"] == "LOST" else 0
        longest = max(longest, streak)
    return {"selections": len(rows), "settled": n, "pending": sum(r.get("status", "PENDING") == "PENDING" for r in rows),
            "void": sum(r.get("status") == "VOID" for r in rows), "won": won,
            "win_rate": round(won / n, 4) if n else None,
            "avg_probability": round(sum(float(r["probability"]) for r in settled) / n, 4) if n else None,
            "avg_odds": round(sum(float(r["decimal_odds"]) for r in settled) / n, 4) if n else None,
            "expected_net_pnl_units": round(exp, 4), "realised_net_pnl_units": round(real, 4),
            "roi_yield": round(real / stake, 4) if stake else None, "max_drawdown_units": round(dd, 4),
            "longest_losing_streak": longest}


def results(selections: list[dict], settlements: dict[str, dict], sim_cfg: dict) -> dict:
    joined = []
    for s in selections:
        st = settlements.get(s["selection_id"])
        joined.append({**s, "status": st["status"] if st else "PENDING", "pnl_units": st["pnl_units"] if st else 0.0})
    out = {"overall": _stats(joined), "breakdowns": {}}
    for name, keyf in {"sport": lambda r: r["sport"], "engine": lambda r: r["engine_id"],
                       "p_band": lambda r: band(float(r["probability"]), P_BANDS),
                       "odds_band": lambda r: band(float(r["decimal_odds"]), ODDS_BANDS),
                       "decision": lambda r: r["decision"], "source_type": lambda r: "exchange" if str(r["is_exchange"]) == "True" else "bookmaker"}.items():
        groups: dict[str, list] = defaultdict(list)
        for r in joined:
            groups[keyf(r)].append(r)
        out["breakdowns"][name] = {k: _stats(v) for k, v in sorted(groups.items())}
    settled = [r for r in joined if r["status"] in ("WON", "LOST", "VOID")]
    sims = simulate_all(settled, sim_cfg)
    out["bankroll_simulations"] = [{k: v for k, v in asdict(s).items() if k != "path"} for s in sims]
    return out


def decision_breakdown(decided: list[dict]) -> dict:
    reasons: Counter = Counter()
    for c in decided:
        for r in str(c["reasons"]).split("|"):
            if r:
                reasons[r] += 1
    by = lambda key: {k: dict(Counter(c["decision"] for c in decided if c[key] == k)) for k in sorted({c[key] for c in decided})}
    return {"decisions": dict(Counter(c["decision"] for c in decided)), "reason_counts": dict(reasons.most_common()),
            "by_sport": by("sport"), "by_engine": by("engine_id")}
