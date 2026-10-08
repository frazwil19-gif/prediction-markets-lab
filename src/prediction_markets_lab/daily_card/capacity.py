"""Qualified Turnover Capacity (QTC) + expected-vs-realised report (directive 2026-10-08 items 8, 10, 11).

Reads append-only paper/live records only; 0 API calls. Monitoring only — never changes any decision.

* Qualifying bets = bsv2 PAPER_BET rows (paper_betting_v2/selections.csv): every bet the system would have staked.
* Expected profit = sum(stake x net_ev) where net_ev = P x odds_net - 1 (bsv2's own commission-adjusted EV);
  expected wins = sum(P). Compared with settled reality.
* Capacity: qualifying bets per day -> monthly turnover at flat stakes; bankroll scenarios apply an ILLUSTRATIVE
  stake fraction and daily cap (config/qualified_capacity.yaml) day by day to the observed qualifying stream, and split
  the shortfall into theoretical / opportunity / daily-cap / bankroll / execution-price limits.
* Execution-price limit is UNMEASURED until manual Bet Log fills exist (odds taken vs card price).
"""
from __future__ import annotations

import csv
import statistics
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path


def _rows(p: Path) -> list[dict]:
    if not p.exists():
        return []
    with p.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def _f(x) -> float | None:
    try:
        return float(x)
    except (TypeError, ValueError):
        return None


def _stats(xs: list[float]) -> dict:
    return {"n": len(xs), "mean": round(statistics.fmean(xs), 4) if xs else None,
            "median": round(statistics.median(xs), 4) if xs else None}


def expected_vs_realised(sel: list[dict], settle: dict[str, dict], stake: float = 1.0) -> dict:
    settled = [s for s in sel if settle.get(s["selection_id"], {}).get("status") in ("WON", "LOST")]
    exp_profit = sum(stake * float(s["net_ev"]) for s in settled)
    exp_wins = sum(float(s["probability"]) for s in settled)
    real_pnl = sum(stake * float(settle[s["selection_id"]]["pnl_units"]) for s in settled)
    wins = sum(settle[s["selection_id"]]["status"] == "WON" for s in settled)
    n = len(settled)
    sd_wins = sum(float(s["probability"]) * (1 - float(s["probability"])) for s in settled) ** 0.5
    return {"settled_bets": n, "stake_per_bet_gbp": stake, "expected_profit_gbp": round(exp_profit, 2),
            "realised_profit_gbp": round(real_pnl, 2), "expected_wins": round(exp_wins, 2), "actual_wins": wins,
            "wins_z": round((wins - exp_wins) / sd_wins, 2) if sd_wins > 0 else None,
            "open_bets": len(sel) - n,
            "note": "Small samples: |wins_z| < 2 is ordinary noise; do not react to it (first-weekend rule)."}


def capacity(sel: list[dict], cfg: dict, observed_from: str | None = None, observed_to: str | None = None) -> dict:
    """observed_from/to (YYYY-MM-DD): the window in which bsv2 was evaluating (evaluation_runs.csv), so days with
    zero qualifying bets count — rates are per OBSERVED day, not per day that happened to have a bet."""
    if not sel:
        return {"qualifying_bets": 0, "observed_window": [observed_from, observed_to],
                "note": "no qualifying bets under the current rule in the observed window"}
    days = sorted({s["decision_at"][:10] for s in sel})
    first, last = min(days[0], observed_from or days[0]), max(days[-1], observed_to or days[-1])
    span = (datetime.fromisoformat(last) - datetime.fromisoformat(first)).days + 1
    per_day = len(sel) / span
    dpm = cfg["days_per_month"]
    evs = [float(s["net_ev"]) for s in sel]
    mean_ev = statistics.fmean(evs)
    by_group = defaultdict(list)
    for s in sel:
        for key in (("sport", s["sport"]), ("market", f"{s['sport']}:{s['market']}"), ("engine", s["engine_id"])):
            by_group[key].append(s)
    groups = {f"{k}={v}": {"bets": len(rs), "per_month": round(len(rs) / span * dpm, 1),
                           "odds": _stats([float(r["decimal_odds"]) for r in rs]),
                           "net_ev": _stats([float(r["net_ev"]) for r in rs])}
              for (k, v), rs in sorted(by_group.items())}
    flat = {f"£{s:g}": {"monthly_turnover_gbp": round(per_day * dpm * s, 2),
                        "monthly_expected_profit_gbp": round(per_day * dpm * s * mean_ev, 2)} for s in cfg["flat_stakes_gbp"]}
    per_day_counts = Counter(s["decision_at"][:10] for s in sel)
    daily_ev = defaultdict(list)
    for s in sel:
        daily_ev[s["decision_at"][:10]].append(float(s["net_ev"]))
    scen = {}
    for b in cfg["bankroll_scenarios_gbp"]:
        stake = max(cfg["scenario_min_stake_gbp"], b * cfg["scenario_stake_fraction_of_bankroll"])
        cap = b * cfg["scenario_daily_cap_fraction_of_bankroll"]
        per_day_max = int(cap // stake)
        theo = sum(len(v) for v in daily_ev.values()) * stake * mean_ev     # all qualifying bets at this stake
        capped = sum(sum(sorted(v, reverse=True)[:per_day_max]) for v in daily_ev.values()) * stake
        scale = dpm / span
        scen[f"£{b}"] = {"stake_gbp": round(stake, 2), "daily_cap_gbp": round(cap, 2), "max_bets_per_day": per_day_max,
                         "expected_profit_per_month_theoretical_gbp": round(theo * scale, 2),
                         "expected_profit_per_month_after_daily_cap_gbp": round(capped * scale, 2),
                         "expected_turnover_per_month_gbp": round(sum(min(n, per_day_max) for n in per_day_counts.values()) * stake * scale, 2)}
    return {"qualifying_bets": len(sel), "days_observed": span, "observed_window": [first, last],
            "days_with_a_qualifying_bet": len(days), "qualifying_per_day": round(per_day, 2),
            "qualifying_per_month": round(per_day * dpm, 1),
            "sample_flag": "LOW_SAMPLE" if len(sel) < cfg["min_sample_for_rate_note"] else "OK",
            "odds": _stats([float(s["decimal_odds"]) for s in sel]), "net_ev": _stats(evs),
            "by_group": groups, "flat_turnover": flat, "bankroll_scenarios": scen,
            "limits": {"theoretical": "all qualifying bets staked (no caps) — bankroll_scenarios.*.theoretical",
                       "opportunity": f"{round(per_day * dpm, 1)} qualifying bets/month observed — the binding limit while this is small",
                       "daily_cap": "bets beyond the daily cap dropped (lowest EV first) — bankroll_scenarios.*.after_daily_cap",
                       "bankroll": "stake = fraction of bankroll (illustrative 2%; live policy is £1 flat)",
                       "execution_price": "UNMEASURED — needs Bet Log fills (odds taken vs card price, min-odds misses)"},
            "caveat": "Expected profit uses the model's own EV estimates; real edge is unproven until settled results and CLV accrue."}


def rejection_categories(shadow: list[dict]) -> dict:
    latest: dict[str, dict] = {}
    for r in shadow:                          # one row per prediction: its latest evaluation
        if r["prediction_id"] not in latest or r["evaluated_at"] > latest[r["prediction_id"]]["evaluated_at"]:
            latest[r["prediction_id"]] = r
    c: Counter = Counter()
    for r in latest.values():
        if r["bsv2_decision"] != "PAPER_BET":
            for reason in (r["bsv2_reasons"] or r["bsv2_decision"]).split("|"):
                c[reason] += 1
    return {"predictions_evaluated": len(latest), "rejections_by_reason": dict(c.most_common())}


def current_rule_version(repo: Path) -> str:
    import yaml
    return str(yaml.safe_load((repo / "config/bet_selection_v2.yaml").read_text())["rule_version"])


def build(repo: Path, cfg: dict, now: datetime) -> dict:
    """Capacity uses ONLY bets and runs under the current bsv2 rule version: earlier versions (e.g. bsv2-1, before the
    exchange-spread gate) qualified bets the live rule would reject, so mixing them overstates capacity (qtc-1 showed
    ~30/month; under bsv2-4 the measured rate is far lower). Expected-vs-realised still covers every paper bet."""
    rule = current_rule_version(repo)
    sel_all = _rows(repo / "paper_betting_v2/selections.csv")
    sel = [s for s in sel_all if s["rule_version"] == rule]
    settle = {r["selection_id"]: r for r in _rows(repo / "paper_betting_v2/settlements.csv")}
    runs = sorted((r for r in _rows(repo / "paper_betting_v2/evaluation_runs.csv") if r["rule_version"] == rule),
                  key=lambda r: r["run_at"])
    by_rule = Counter(s["rule_version"] for s in sel_all)
    return {"report_version": cfg["report_version"], "generated_at": now.isoformat(),
            "capacity_rule_version": rule, "paper_bets_by_rule_version": dict(sorted(by_rule.items())),
            "runs_under_current_rule": len(runs),
            "expected_vs_realised": expected_vs_realised(sel_all, settle),
            "capacity": capacity(sel, cfg, runs[0]["run_at"][:10] if runs else None, now.date().isoformat()),
            "rejections": rejection_categories(_rows(repo / "paper_betting_v2/decision_shadow.csv")),
            "scenario_policy_note": "Bankroll scenarios are illustrative (2% flat, 10% daily cap); live policy stays £1 flat, £5/day."}


def render_md(r: dict) -> str:
    e, c = r["expected_vs_realised"], r["capacity"]
    L = [f"# Qualified Turnover Capacity & expected vs realised ({r['report_version']}, {r['generated_at'][:16]}Z)", "",
         "## Expected vs realised (paper qualifying bets, £1 each)", "",
         f"Settled {e['settled_bets']} (open {e['open_bets']}). Expected profit **£{e['expected_profit_gbp']}** vs realised "
         f"**£{e['realised_profit_gbp']}**. Expected wins {e['expected_wins']} vs actual {e['actual_wins']} (z {e['wins_z']}).",
         "", e["note"], ""]
    L += [f"Capacity below uses only rule **{r['capacity_rule_version']}** ({r['runs_under_current_rule']} evaluation runs). "
          f"Paper bets by rule version: {r['paper_bets_by_rule_version']}.", ""]
    if not c.get("qualifying_bets"):
        L += ["## Capacity", "", f"0 qualifying bets under {r['capacity_rule_version']} in {c.get('observed_window')}.", ""]
    if c.get("qualifying_bets"):
        L += ["## Capacity", "", f"{c['qualifying_bets']} qualifying bets over {c['days_observed']} days → "
              f"{c['qualifying_per_month']}/month ({c['sample_flag']}; bets on {c['days_with_a_qualifying_bet']} of those days). Odds mean {c['odds']['mean']} / median {c['odds']['median']}; "
              f"net EV mean {c['net_ev']['mean']} / median {c['net_ev']['median']}.", "",
              "| Group | Bets | /month | Odds mean | EV mean |", "|---|---|---|---|---|"]
        L += [f"| {k} | {v['bets']} | {v['per_month']} | {v['odds']['mean']} | {v['net_ev']['mean']} |" for k, v in c["by_group"].items()]
        L += ["", "| Flat stake | Turnover/month | Expected profit/month |", "|---|---|---|"]
        L += [f"| {k} | £{v['monthly_turnover_gbp']} | £{v['monthly_expected_profit_gbp']} |" for k, v in c["flat_turnover"].items()]
        L += ["", "| Bankroll | Stake | Daily cap | Max bets/day | Exp. profit/month (no cap) | after daily cap | Turnover/month |",
              "|---|---|---|---|---|---|---|"]
        L += [f"| {k} | £{v['stake_gbp']} | £{v['daily_cap_gbp']} | {v['max_bets_per_day']} | £{v['expected_profit_per_month_theoretical_gbp']} "
              f"| £{v['expected_profit_per_month_after_daily_cap_gbp']} | £{v['expected_turnover_per_month_gbp']} |"
              for k, v in c["bankroll_scenarios"].items()]
        L += ["", "Limits:"] + [f"- **{k}**: {v}" for k, v in c["limits"].items()] + ["", c["caveat"], ""]
    rj = r["rejections"]
    L += ["## Rejection categories (latest evaluation per prediction)", "", f"{rj['predictions_evaluated']} predictions evaluated.", ""]
    L += [f"- {k}: {v}" for k, v in rj["rejections_by_reason"].items()]
    L += ["", r["scenario_policy_note"]]
    return "\n".join(L) + "\n"
