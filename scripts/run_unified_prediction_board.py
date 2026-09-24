"""V2-5 Unified cross-sport PAPER Prediction Board.

Protocol: research/platform_v2/unified_board/PROSPECTIVE_PROTOCOL.md.
Subcommands (each ends by rebuilding the board, performance and health):
  ingest-football  daily card -> 1X2 / O-U / Double Chance rows      (0 credits; reads the card daily_scan wrote)
  ingest-tennis    mirror the frozen tennis ledger                    (0 credits)
  collect-nba      basketball_nba h2h, only when the engine is active and games start within 36h
                   (/sports and /events are free; <=1 odds call per UTC day under the budget guard)
  settle           football-data.co.uk (free) + tennis mirror + NBA scores (budgeted, every 3rd day)
  build            board/performance/health only
Never stakes, grades or qualifies bets (Money Card is separate).
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import sys
import urllib.parse
import urllib.request
from datetime import date, datetime, timezone
from pathlib import Path

import yaml

from prediction_markets_lab.ops.api_budget import check as budget_check, load_budget, month_spend
from prediction_markets_lab.prediction_platform import adapters as A
from prediction_markets_lab.prediction_platform import board as B
from prediction_markets_lab.prediction_platform import health as H
from prediction_markets_lab.prediction_platform import performance as P
from prediction_markets_lab.prediction_platform import settle as S
from prediction_markets_lab.prediction_platform.ledger import append_unique, read_rows
from prediction_markets_lab.prediction_platform.registry import Registry
from prediction_markets_lab.prediction_platform.schema import PREDICTION_FIELDS, SETTLEMENT_FIELDS, to_row

REPO = Path(__file__).resolve().parents[1]
PRED_DIR = REPO / "predictions"
LEDGER = PRED_DIR / "unified_ledger.csv"
SETTLEMENTS = PRED_DIR / "unified_settlements.csv"
STATE = PRED_DIR / "platform_state.json"
NBA_CREDIT_LOG = PRED_DIR / "nba_credit_log.csv"
REPORTS = REPO / "reports"
ODDS = "https://api.the-odds-api.com/v4/sports"
NBA_SCORES_EVERY_DAYS = 3


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def load_state() -> dict:
    return json.loads(STATE.read_text()) if STATE.exists() else {}


def save_state(st: dict) -> None:
    PRED_DIR.mkdir(exist_ok=True)
    STATE.write_text(json.dumps(st, indent=1, sort_keys=True))


def payout_floor() -> float:
    return float(yaml.safe_load((REPO / "config/thresholds.yaml").read_text())["payout_policy"]["normal_min_decimal_odds"])


def run_context(now: datetime) -> A.RunContext:
    ev, cron = os.environ.get("TRIGGER_EVENT", ""), os.environ.get("TRIGGER_SCHEDULE", "")
    configured = None
    if ev == "schedule" and cron:
        parts = cron.split()
        if len(parts) == 5 and parts[0].isdigit() and parts[1].isdigit():
            configured = f"{now.date().isoformat()}T{int(parts[1]):02d}:{int(parts[0]):02d}:00+00:00"
        else:
            configured = f"cron:{cron}"
    elif ev:
        configured = f"MANUAL:{ev}"
    return A.RunContext(configured_scan_time=configured, actual_workflow_start=os.environ.get("WORKFLOW_START") or None,
                        single_min_odds=payout_floor())


def record(preds: list, skips: list, st: dict, label: str) -> None:
    added, dup = append_unique(LEDGER, [to_row(p) for p in preds], PREDICTION_FIELDS)
    reasons: dict[str, int] = {}
    for s in skips:
        k = f"{s.engine_id}: {s.reason.split(':')[0]}"
        reasons[k] = reasons.get(k, 0) + 1
    st.setdefault("skips", {})[label] = reasons
    st.setdefault("last_runs", {})[label] = {"at": now_utc().isoformat(), "candidates": len(preds), "added": added,
                                             "already_recorded": dup}
    print(f"{label}: {len(preds)} valid, {added} added, {dup} already recorded; skipped {sum(reasons.values())} {reasons}")


def ingest_football(card_path: Path | None, reg: Registry, st: dict) -> None:
    if card_path is None:
        days = sorted(d for d in (REPO / "daily_cards").iterdir() if d.is_dir() and (d / "card.json").exists())
        card_path = days[-1] / "card.json" if days else None
    if card_path is None:
        print("no daily card found -- nothing ingested")
        return
    card = json.loads(card_path.read_text())
    preds, skips = A.football_from_card(card, reg, run_context(now_utc()), now_utc(), origin=str(card_path.relative_to(REPO)))
    record(preds, skips, st, "football")


def ingest_tennis(reg: Registry, st: dict) -> None:
    rows = read_rows(REPO / "tennis_predictions/ledger_predictions.csv")
    run_log = read_rows(REPO / "tennis_predictions/run_log.csv")
    preds, skips = A.tennis_from_ledger(rows, run_log, reg, payout_floor(), origin="tennis_predictions/ledger_predictions.csv")
    record(preds, skips, st, "tennis")
    st["last_tennis_ingest"] = now_utc().isoformat()


def _get(url: str) -> tuple[object, dict]:
    with urllib.request.urlopen(urllib.request.Request(url, headers={"Accept": "application/json"}), timeout=30) as r:
        hdr = {h: r.headers.get(h) for h in ("x-requests-used", "x-requests-remaining", "x-requests-last")}
        return json.loads(r.read()), hdr


def _log_credit(call: str, hdr: dict) -> None:
    new = not NBA_CREDIT_LOG.exists()
    PRED_DIR.mkdir(exist_ok=True)
    with NBA_CREDIT_LOG.open("a", newline="") as f:
        w = csv.writer(f)
        if new:
            w.writerow(["timestamp_utc", "call", "x_requests_used", "x_requests_remaining", "x_requests_last"])
        w.writerow([now_utc().isoformat(), call, hdr.get("x-requests-used"), hdr.get("x-requests-remaining"), hdr.get("x-requests-last")])


def _nba_budget_ok(remaining: int, cost: int) -> bool:
    d = budget_check(load_budget(REPO / "config/api_budget.json"), "nba_prediction_board", month_spend(NBA_CREDIT_LOG, now_utc()),
                     remaining, cost)
    if not d.allowed:
        print(f"NBA budget guard: {d.reason}")
    return d.allowed


def collect_nba(reg: Registry, st: dict) -> None:
    now = now_utc()
    if not reg.collectable(A.NBA, now):
        print(f"NBA not active until {reg.get(A.NBA)['activation_date_utc']} -- no API calls made")
        return
    if st.get("nba_last_odds_date") == now.date().isoformat():
        print("NBA odds already fetched today -- no API calls made")
        return
    key = os.environ.get("THE_ODDS_API_KEY")
    if not key:
        print("THE_ODDS_API_KEY not set -- stopping cleanly")
        return
    sports, hdr = _get(f"{ODDS}/?{urllib.parse.urlencode({'apiKey': key})}")               # free
    if not any(s["key"] == "basketball_nba" and s.get("active") for s in sports):
        print("basketball_nba not active -- no paid call")
        return
    events, _ = _get(f"{ODDS}/basketball_nba/events?{urllib.parse.urlencode({'apiKey': key})}")   # free
    soon = [e for e in events if 0 < (datetime.fromisoformat(e["commence_time"].replace("Z", "+00:00")) - now).total_seconds() <= A.NBA_WINDOW_MIN * 60]
    if not soon:
        print("no NBA games within 36h -- no paid call")
        return
    if not _nba_budget_ok(int(hdr.get("x-requests-remaining") or 0), 1):
        return
    raw, h = _get(f"{ODDS}/basketball_nba/odds/?{urllib.parse.urlencode({'apiKey': key, 'regions': 'uk', 'markets': 'h2h', 'oddsFormat': 'decimal'})}")
    _log_credit("odds:basketball_nba", h)
    st["nba_last_odds_date"] = now.date().isoformat()
    preds, skips = A.nba_from_odds(raw, reg, run_context(now), now, origin="odds_api:basketball_nba")
    record(preds, skips, st, "nba")


def settle(st: dict) -> None:
    now = now_utc()
    preds = read_rows(LEDGER)
    done = {r["prediction_id"] for r in read_rows(SETTLEMENTS)}
    new: list[dict] = []
    # tennis mirror
    tset = {r["prediction_id"]: r for r in read_rows(REPO / "tennis_predictions/ledger_settlements.csv")}
    new += S.mirror_tennis(tset, {p["prediction_id"] for p in preds}, done)
    # football-data (free; reachable from GitHub runners)
    fb_due = [p for p in preds if p["sport"] == "football" and p["prediction_id"] not in done]
    review: list[dict] = []
    if fb_due:
        from prediction_markets_lab.settlement import football_data_results as fd
        results, aliases = [], fd.load_settlement_aliases()
        for code in sorted(set(S.COMP_TO_FD.values())):
            url = fd.fd_url(code, now.date())
            try:
                with urllib.request.urlopen(url, timeout=60) as r:
                    results += fd.parse_fd_csv(r.read().decode("utf-8-sig", errors="replace"), code, aliases)
            except Exception as exc:  # network failure -> nothing settled for this league (fail closed)
                print(f"football-data {code} unavailable: {exc}")
        fb_new, review = S.settle_football(fb_due, done, results, aliases, now)
        new += fb_new
    # NBA scores (budgeted, every 3rd day, only when an NBA prediction has started and is unsettled)
    nba_due = [p for p in preds if p["sport"] == "basketball" and p["prediction_id"] not in done
               and datetime.fromisoformat(p["event_start"]) < now]
    last = st.get("nba_last_scores_date")
    if nba_due and (last is None or (now.date() - date.fromisoformat(last)).days >= NBA_SCORES_EVERY_DAYS):
        key = os.environ.get("THE_ODDS_API_KEY")
        if key:
            _, hdr = _get(f"{ODDS}/?{urllib.parse.urlencode({'apiKey': key})}")
            if _nba_budget_ok(int(hdr.get("x-requests-remaining") or 0), 2):
                scores, h = _get(f"{ODDS}/basketball_nba/scores/?{urllib.parse.urlencode({'apiKey': key, 'daysFrom': 3})}")
                _log_credit("scores:basketball_nba", h)
                st["nba_last_scores_date"] = now.date().isoformat()
                new += S.settle_from_odds_api_scores(nba_due, done, scores, now)
    added, _ = append_unique(SETTLEMENTS, new, SETTLEMENT_FIELDS)
    st["pending_review"] = review
    st.setdefault("last_runs", {})["settle"] = {"at": now.isoformat(), "added": added, "pending_review": len(review)}
    print(f"settle: {added} new settlements; {len(review)} pending review")


def build(reg: Registry, st: dict) -> None:
    now = now_utc()
    preds = read_rows(LEDGER)
    settlements = {r["prediction_id"]: r for r in read_rows(SETTLEMENTS)}
    perf = P.report(preds, settlements)
    health = H.evaluate(REPO, now, st)
    active = [e for e in reg.engines if reg.collectable(e, now)]
    board = B.build(preds, settlements, reg.engines, active, health, perf, st.get("skips", {}), now)
    B.write(board, REPORTS)
    (REPORTS / "latest_prediction_performance.json").write_text(json.dumps(
        {"generated_at": now.isoformat(), "protocol": "research/platform_v2/unified_board/PROSPECTIVE_PROTOCOL.md",
         "pending_review": st.get("pending_review", []), **perf}, indent=1, default=str))
    print(f"board: {board['summary']}")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("command", choices=["ingest-football", "ingest-tennis", "collect-nba", "settle", "build"])
    ap.add_argument("--card", type=Path)
    ap.add_argument("--ci-passed", action="store_true", help="record that this workflow's test step passed")
    a = ap.parse_args()
    reg = Registry.load()
    errs = reg.validate()
    if errs:
        print("REGISTRY INVALID -- no predictions produced:", errs)
        return 1
    st = load_state()
    if a.ci_passed:
        st["last_ci_pass"] = now_utc().isoformat()
    if a.command == "ingest-football":
        ingest_football(a.card, reg, st)
    elif a.command == "ingest-tennis":
        ingest_tennis(reg, st)
    elif a.command == "collect-nba":
        collect_nba(reg, st)
    elif a.command == "settle":
        settle(st)
    save_state(st)
    build(reg, st)
    save_state(st)
    return 0


if __name__ == "__main__":
    sys.exit(main())
