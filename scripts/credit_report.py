"""V2-14 Credit Plan A accounting: month-to-date Odds API spend by consumer, gate savings, and comparison with the
Plan A projection (research/platform_v2/v2_13_october/CREDIT_AUDIT.md). 0 API calls; reads append-only logs only.

Sources: status/credit_ledger.csv (V2-14: football + tennis paid/skipped calls), tennis_predictions/credit_log.csv
(tennis + the account-wide x-requests-used counter), predictions/nba_credit_log.csv (NBA).
Output: reports/credit_report.{json,md}
"""
from __future__ import annotations

import csv
import json
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

from prediction_markets_lab.ops import credit_ledger as CL

REPO = Path(__file__).resolve().parents[1]
# Plan A projections for a 30-day month (CREDIT_AUDIT.md s.3), kept here only for the comparison report.
PLAN_A_MONTHLY = {"football_daily_scan": (70, 100), "football_settlement": (0, 20), "tennis_prediction_board": (100, 150),
                  "nba_prediction_board": (20, 60)}
BASELINE_FOOTBALL_PER_DAY = 6   # unconditional 3 leagues x (h2h + totals) before Plan A (observed 23-30 Sep)


def _rows(p: Path) -> list[dict]:
    if not p.exists():
        return []
    with p.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def build(repo: Path, now: datetime) -> dict:
    month = now.strftime("%Y-%m")
    extra = sorted((repo / "research_shadow").glob("*/credit_ledger.csv"))   # research consumers keep their own ledgers
    led = [r for r in CL.read(repo / "status/credit_ledger.csv") + [x for p in extra for x in CL.read(p)]
           if r["timestamp_utc"].startswith(month)]   # (own files so research commits never conflict with production)
    by: dict[str, dict] = defaultdict(lambda: {"paid_calls": 0, "credits_charged": 0, "skipped_calls": 0,
                                               "credits_saved_estimate": 0})
    for r in led:
        b = by[r["consumer"]]
        if r["outcome"] == CL.PAID:
            b["paid_calls"] += 1
            b["credits_charged"] += int(r["credits_charged"] or 0)
        else:
            b["skipped_calls"] += 1
            b["credits_saved_estimate"] += int(r["credits_saved_estimate"] or 0)
    tennis_log = [r for r in _rows(repo / "tennis_predictions/credit_log.csv") if r["timestamp_utc"].startswith(month)]
    nba_log = [r for r in _rows(repo / "predictions/nba_credit_log.csv") if r["timestamp_utc"].startswith(month)]
    by["nba_prediction_board"]["credits_charged"] += sum(int(r["x_requests_last"] or 0) for r in nba_log)
    counters = [(r["timestamp_utc"], int(r["x_requests_used"])) for r in tennis_log + nba_log + led
                if str(r.get("x_requests_used", "")).isdigit()]
    latest_used = max(counters)[1] if counters else None
    day = now.day
    proj = {k: {"plan_a_month_range": v, "plan_a_to_date_range": [round(v[0] * day / 30, 1), round(v[1] * day / 30, 1)],
                "actual_to_date": by[k]["credits_charged"] if k in by else 0} for k, v in PLAN_A_MONTHLY.items()}
    fb_days = len({r["timestamp_utc"][:10] for r in led if r["consumer"] == "football_daily_scan"})
    import calendar
    dim = calendar.monthrange(now.year, now.month)[1]
    run_rate = None if latest_used is None else round(latest_used / day * dim)   # naive linear; early-month values are noisy
    return {"generated_at": now.isoformat(), "month": month, "account_used_month_to_date_latest_counter": latest_used,
            "projected_month_end_at_current_rate": run_rate,
            "by_consumer": {k: dict(v) for k, v in sorted(by.items())}, "plan_a_comparison": proj,
            "football_counterfactual": {"scan_days_logged": fb_days, "baseline_credits_if_ungated": fb_days * BASELINE_FOOTBALL_PER_DAY,
                                        "actual": by["football_daily_scan"]["credits_charged"] if "football_daily_scan" in by else 0},
            "note": "credits_saved_estimate = markets x regions of each skipped odds call; settlement scores and research calls "
                    "are not in the shared ledger yet (account counter covers them)."}


def render_md(r: dict) -> str:
    lines = [f"# Odds API credit report — {r['month']} (generated {r['generated_at'][:16]}Z)", "",
             f"Account credits used this month (latest logged counter): **{r['account_used_month_to_date_latest_counter']}** of 500",
             f"Naive month-end projection at the current rate: {r.get('projected_month_end_at_current_rate')} "
             "(shadow football tiers throttle themselves before the reserve; see config/api_budget.json football_shadow_tiers)", "",
             "| Consumer | Paid calls | Credits charged | Skipped (gate/floor) | Credits saved (est.) |", "|---|---|---|---|---|"]
    for k, v in r["by_consumer"].items():
        lines.append(f"| {k} | {v['paid_calls']} | {v['credits_charged']} | {v['skipped_calls']} | {v['credits_saved_estimate']} |")
    lines += ["", "| Consumer | Plan A to date | Actual to date |", "|---|---|---|"]
    for k, v in r["plan_a_comparison"].items():
        lines.append(f"| {k} | {v['plan_a_to_date_range'][0]}–{v['plan_a_to_date_range'][1]} | {v['actual_to_date']} |")
    fc = r["football_counterfactual"]
    lines += ["", f"Football: {fc['actual']} credits over {fc['scan_days_logged']} scan days vs {fc['baseline_credits_if_ungated']} "
              "if ungated (pre-Plan-A 6/day).", "", r["note"]]
    return "\n".join(lines) + "\n"


def main() -> int:
    r = build(REPO, datetime.now(timezone.utc))
    (REPO / "reports").mkdir(exist_ok=True)
    (REPO / "reports/credit_report.json").write_text(json.dumps(r, indent=1))
    (REPO / "reports/credit_report.md").write_text(render_md(r))
    print(json.dumps(r["by_consumer"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
