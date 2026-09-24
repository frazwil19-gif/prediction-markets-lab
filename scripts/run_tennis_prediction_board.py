"""Paper tennis Prediction Board (Phase V2-2). Research only: no stakes, no Money Card.

Protocol: research/platform_v2/tennis_prospective/ATP_PROSPECTIVE_PROTOCOL.md
Cost: /sports listing is free; 1 credit per active covered tennis key (regions=uk, markets=h2h).
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

from prediction_markets_lab.ops.api_budget import check as budget_check, load_budget, month_spend
from prediction_markets_lab.tennis_prospective import board as B
from prediction_markets_lab.tennis_prospective.engine import parse_tennis_odds, predict, tour_of
from prediction_markets_lab.tennis_prospective.ledger import append_predictions

REPO = Path(__file__).resolve().parents[1]
OUT = REPO / "tennis_predictions"
BASE = "https://api.the-odds-api.com/v4/sports"
BUDGET_FILE = REPO / "config" / "api_budget.json"  # per-consumer cap + floors (optional consumer)


def _get(url: str) -> tuple[object, dict]:
    with urllib.request.urlopen(urllib.request.Request(url, headers={"Accept": "application/json"}), timeout=30) as r:
        hdr = {h: r.headers.get(h) for h in ("x-requests-used", "x-requests-remaining", "x-requests-last")}
        return json.loads(r.read()), hdr


def log_credits(call: str, hdr: dict) -> None:
    p = OUT / "credit_log.csv"
    new = not p.exists()
    with open(p, "a", newline="") as f:
        w = csv.writer(f)
        if new:
            w.writerow(["timestamp_utc", "call", "x_requests_used", "x_requests_remaining", "x_requests_last"])
        w.writerow([datetime.now(timezone.utc).isoformat(), call, hdr.get("x-requests-used"),
                    hdr.get("x-requests-remaining"), hdr.get("x-requests-last")])


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--tours", default="ATP,WTA")
    ap.add_argument("--max-keys", type=int, default=6, help="hard cap on paid calls per run")
    a = ap.parse_args()
    key = os.environ.get("THE_ODDS_API_KEY")
    if not key:
        print("THE_ODDS_API_KEY not set -- stopping cleanly (no data fabricated).")
        return 1
    OUT.mkdir(exist_ok=True)
    tours = set(a.tours.split(","))
    sports, hdr = _get(f"{BASE}/?{urllib.parse.urlencode({'apiKey': key})}")
    log_credits("sports_list", hdr)
    keys = sorted(s["key"] for s in sports if s.get("active") and tour_of(s["key"]) in tours
                  and not s.get("has_outrights"))
    now = datetime.now(timezone.utc)
    preds, fetched, events, skipped = [], [], 0, []
    remaining = int(hdr.get("x-requests-remaining") or 0)
    budget = load_budget(BUDGET_FILE)
    spent = month_spend(OUT / "credit_log.csv", now)
    for sk in keys[: a.max_keys]:
        if not budget_check(budget, "tennis_prediction_board", spent, remaining).allowed:
            skipped.append(sk)
            continue
        raw, h = _get(f"{BASE}/{sk}/odds/?{urllib.parse.urlencode({'apiKey': key, 'regions': 'uk', 'markets': 'h2h', 'oddsFormat': 'decimal'})}")
        log_credits(f"odds:{sk}", h)
        remaining = int(h.get("x-requests-remaining") or remaining)
        spent += int(h.get("x-requests-last") or 1)
        fetched.append(sk)
        qs = parse_tennis_odds(raw, sk)
        events += len(qs)
        preds += [p for p in (predict(q, now) for q in qs) if p is not None]
    added, existing = append_predictions(OUT / "ledger_predictions.csv", preds)
    day = now.date().isoformat()
    coverage = {"active_keys": fetched, "skipped_for_credit_guard": skipped, "keys_over_cap": keys[a.max_keys:],
                "events_returned": events, "scan_timestamp": now.isoformat(), "credits_remaining_after": remaining,
                "universe_note": "Odds-API-covered universe only (Slams, 1000s, 500s) -- not the full ATP/WTA calendar"}
    registry = json.loads((REPO / "config/tennis_engine_registry.json").read_text())
    board = B.build_board(day, preds, registry, coverage)
    (OUT / day).mkdir(exist_ok=True)
    stamp = now.strftime("%H%M")
    (OUT / day / f"board_{stamp}.json").write_text(json.dumps(board, indent=1))
    (OUT / day / f"board_{stamp}.md").write_text(B.render_markdown(board))
    # Scheduling audit (V2-4): GitHub cron can start hours late, so every run records what was
    # configured vs when it actually ran; minutes-to-start per prediction follows from the ledger's
    # prediction_timestamp and commence_time.
    rl = OUT / "run_log.csv"
    new_log = not rl.exists()
    with open(rl, "a", newline="") as f:
        w = csv.writer(f)
        if new_log:
            w.writerow(["scan_timestamp_utc", "trigger_event", "configured_schedule_utc", "run_id",
                        "active_keys", "events", "predictions_added", "median_minutes_to_start"])
        mins = sorted((datetime.fromisoformat(p.commence_time) - now).total_seconds() / 60 for p in preds)
        w.writerow([now.isoformat(), os.environ.get("TRIGGER_EVENT", "manual"), os.environ.get("TRIGGER_SCHEDULE", ""),
                    os.environ.get("RUN_ID", ""), "|".join(fetched), events, added,
                    round(mins[len(mins) // 2]) if mins else ""])
    print(json.dumps({"keys": fetched, "events": events, "predictions_this_scan": len(preds),
                      "ledger_added": added, "already_predicted": existing, "credits_remaining": remaining}, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
