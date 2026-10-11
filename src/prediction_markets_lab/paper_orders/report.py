"""Weekly / monthly paper performance report from the paper-order ledger (no manual input)."""
from __future__ import annotations

import math
import statistics
from collections import Counter, defaultdict
from datetime import datetime, timedelta
from pathlib import Path

from prediction_markets_lab.daily_card import capacity as Q
from prediction_markets_lab.paper_orders.ledger import _rows, _ts


def _num(x):
    try:
        return float(x)
    except (TypeError, ValueError):
        return None


def _stat(xs):
    xs = [x for x in xs if x is not None]
    if not xs:
        return {"n": 0}
    return {"n": len(xs), "mean": round(statistics.fmean(xs), 4), "median": round(statistics.median(xs), 4),
            "positive_rate": round(sum(x > 0 for x in xs) / len(xs), 3)}


def metrics(orders: list[dict], stakes: list[float]) -> dict:
    settled = [o for o in orders if o["status"] in ("WON", "LOST")]
    p = [float(o["probability"]) for o in settled]
    w = [o["status"] == "WON" for o in settled]
    pnl = [float(o["paper_pnl_gbp"]) for o in settled if o["paper_pnl_gbp"] != ""]
    eps = 1e-12
    cum, peak, dd = 0.0, 0.0, 0.0
    for o in sorted(settled, key=lambda r: r["event_start"]):
        cum += float(o["paper_pnl_gbp"] or 0)
        peak = max(peak, cum)
        dd = max(dd, peak - cum)
    cal = defaultdict(list)
    for pi, wi in zip(p, w):
        cal[f"{int(pi * 10) * 10}-{int(pi * 10) * 10 + 9}%"].append((pi, wi))
    exp_profit = sum(float(o["estimated_ev"]) * float(o["simulated_stake_gbp"]) for o in settled)
    turnover = sum(float(o["simulated_stake_gbp"]) for o in settled)
    return {"orders": len(orders), "settled": len(settled), "open": sum(o["status"] == "OPEN" for o in orders),
            "expected_wins": round(sum(p), 2), "actual_wins": sum(w),
            "expected_profit_gbp": round(exp_profit, 2), "realised_paper_profit_gbp": round(sum(pnl), 2),
            "roi": round(sum(pnl) / turnover, 4) if turnover else None, "max_drawdown_gbp": round(dd, 2),
            "brier": round(statistics.fmean((a - b) ** 2 for a, b in zip(p, w)), 4) if p else None,
            "log_loss": round(statistics.fmean(-(b * math.log(max(a, eps)) + (1 - b) * math.log(max(1 - a, eps)))
                                               for a, b in zip(p, w)), 4) if p else None,
            "calibration": {k: {"n": len(v), "mean_p": round(statistics.fmean(a for a, _ in v), 3),
                                "win_rate": round(sum(b for _, b in v) / len(v), 3)} for k, v in sorted(cal.items())},
            "avg_odds": _stat([float(o["available_odds"]) for o in orders]), "ev": _stat([float(o["estimated_ev"]) for o in orders]),
            "clv_fair": _stat([_num(o["clv_fair"]) for o in orders]), "clv_price": _stat([_num(o["clv_price"]) for o in orders]),
            "close_coverage": round(sum(o["clv_fair"] != "" for o in orders) / len(orders), 3) if orders else None,
            "unique_events": len({o["event_id"] for o in orders}),
            "hypothetical": {f"£{s:g}": {"turnover": round(turnover * s, 2), "expected_profit": round(exp_profit * s, 2),
                                         "realised": round(sum(pnl) * s, 2)} for s in stakes}}


def concentration(orders: list[dict]) -> dict:
    out = {}
    for k in ("sport", "engine_id", "source", "execution_class", "market"):
        c = Counter(o[k] for o in orders)
        out[k] = {"top": c.most_common(1)[0] if c else None, "top_share": round(c.most_common(1)[0][1] / len(orders), 3) if c else None,
                  "counts": dict(c.most_common())}
    return out


def build(repo: Path, orders: list[dict], cfg: dict, now: datetime) -> dict:
    shadow = _rows(repo / "paper_betting_v2/decision_shadow.csv")
    r = {"generated_at": now.isoformat(), "mode": "PAPER — unattended prospective validation; stakes SIMULATED", "windows": {}}
    for name, days in [*cfg["report_windows_days"].items(), ("all", None)]:
        start = now - timedelta(days=days) if days else None
        o = [x for x in orders if start is None or _ts(x["decision_at"]) >= start]
        sh = [x for x in shadow if start is None or _ts(x["evaluated_at"]) >= start]
        evaluated = len({x["prediction_id"] for x in sh})
        qualified = len({x["prediction_id"] for x in sh if x["bsv2_decision"] == "PAPER_BET"})
        r["windows"][name] = {"metrics": metrics(o, cfg["hypothetical_stakes_gbp"]),
                              "candidates_evaluated": evaluated, "qualified_in_shadow": qualified,
                              "qualification_rate": round(qualified / evaluated, 4) if evaluated else None,
                              "rejections": Q.rejection_categories(sh)["rejections_by_reason"],
                              "by": {k: {g: metrics([x for x in o if x[k] == g], [1]) for g in sorted({x[k] for x in o})}
                                     for k in ("sport", "market", "engine_id", "execution_class")},
                              "concentration": concentration(o),
                              "data_failures": dict(Counter(f for x in o for f in x["dq_flags"].split("|") if f))}
    return r


def render_md(r: dict) -> str:
    L = [f"# Paper performance report ({r['generated_at'][:16]}Z)", "", f"**{r['mode']}**", ""]
    for name, w in r["windows"].items():
        m = w["metrics"]
        L += [f"## {name.title()}", "",
              f"Candidates evaluated {w['candidates_evaluated']} · qualified {w['qualified_in_shadow']} "
              f"(rate {w['qualification_rate']}) · paper orders {m['orders']} (settled {m['settled']}, open {m['open']}) · "
              f"unique events {m['unique_events']}", "",
              f"Expected wins {m['expected_wins']} vs actual {m['actual_wins']} · expected profit £{m['expected_profit_gbp']} vs "
              f"realised £{m['realised_paper_profit_gbp']} (£1 simulated) · ROI {m['roi']} · max drawdown £{m['max_drawdown_gbp']} · "
              f"Brier {m['brier']} · log loss {m['log_loss']}", "",
              f"CLV fair {m['clv_fair']} · CLV price {m['clv_price']} · close coverage {m['close_coverage']}", "",
              f"Avg odds {m['avg_odds']} · EV {m['ev']}", "",
              "Hypothetical (labelled, not live): " + " · ".join(f"{k}: turnover £{v['turnover']}, exp £{v['expected_profit']}, realised £{v['realised']}"
                                                               for k, v in m["hypothetical"].items()), ""]
        for k, groups in w["by"].items():
            if groups:
                L.append(f"**By {k}:** " + " · ".join(f"{g}: n {v['orders']}, settled {v['settled']}, P/L £{v['realised_paper_profit_gbp']}, "
                                                    f"CLV {v['clv_fair'].get('mean')}" for g, v in groups.items()))
        L += ["", "Rejections: " + " · ".join(f"{k} {v}" for k, v in list(w["rejections"].items())[:8]),
              "Data/settlement flags: " + (", ".join(f"{k} {v}" for k, v in w["data_failures"].items()) or "none"), ""]
    L += ["Small samples: differences inside noise are not evidence (first-weekend rule)."]
    return "\n".join(L) + "\n"
