"""V2-6 Bet-Selection V2 runner (PAPER research layer; 0 API credits).

Subcommands:
  evaluate   upcoming unified predictions x real price snapshots -> decisions; append price snapshots and PAPER_BET
             selections (immutable); log the run; rebuild the report
  settle     settle paper selections from the platform's verified settlements (fail closed); rebuild the report
  report     rebuild reports/bet_selection_v2.{json,md} only
  diagnose   retrospective diagnostic of already-settled valid predictions at their original ledger price and time.
             Writes reports/bet_selection_v2_retrospective.json. NEVER writes selections (no backfilling).
Spec: research/platform_v2/bet_selection_v2/BET_SELECTION_V2_SPEC.md
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

from prediction_markets_lab.bet_selection_v2 import paper_ledger as L
from prediction_markets_lab.bet_selection_v2 import prices as PR
from prediction_markets_lab.bet_selection_v2 import report as R
from prediction_markets_lab.bet_selection_v2.evaluate import DECISIONS, PAPER_BET, evaluate_prediction, load_config

REPO = Path(__file__).resolve().parents[1]
OUT = REPO / "paper_betting_v2"
SELECTIONS, SNAPSHOTS, SETTLEMENTS, RUNS = (OUT / "selections.csv", OUT / "price_snapshots.csv", OUT / "settlements.csv",
                                            OUT / "evaluation_runs.csv")
REPORTS = REPO / "reports"
RUN_FIELDS = ["run_at", "trigger", "rule_version", "events_scanned", "valid_predictions", "high_p_candidates",
              "priced_candidates", *DECISIONS, "paper_bets_added", "snapshots_added", "money_card_qualified",
              "football_fixtures_on_card"]


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def latest_card() -> tuple[dict | None, dict | None]:
    days = sorted(d for d in (REPO / "daily_cards").iterdir() if d.is_dir() and (d / "card.json").exists()) \
        if (REPO / "daily_cards").exists() else []
    if not days:
        return None, None
    card = json.loads((days[-1] / "card.json").read_text())
    mc = days[-1] / "money_card.json"
    return card, (json.loads(mc.read_text()) if mc.exists() else None)


def gather_snapshots(pred: dict, tennis_rows: list[dict], card: dict | None,
                     prob_rows: list[dict] | None = None) -> list[PR.PriceSnapshot]:
    snaps = []
    own = PR.from_ledger_row(pred)
    if own:
        snaps.append(own)
    snaps += PR.tennis_from_snapshots(pred, tennis_rows, prob_rows)
    if card:
        snaps += PR.football_from_card(pred, card)
    seen, out = set(), []
    for s in snaps:
        k = (s.source, s.decimal_odds, s.observed_at)
        if k not in seen:
            seen.add(k)
            out.append(s)
    return out


def valid_legacy_prediction_ids(cfg: dict) -> set[str]:
    notes = {r["selection_id"]: r["annotation"] for r in L.read_rows(OUT / "selection_annotations.csv")}
    return {r["prediction_id"] for r in L.read_rows(SELECTIONS)
            if r["rule_version"] != cfg["rule_version"] and notes.get(r["selection_id"]) == "VALID_SAME_SNAPSHOT"}


def evaluate(cfg: dict, now: datetime) -> dict:
    preds = L.read_rows(REPO / "predictions/unified_ledger.csv")
    upcoming = [p for p in preds if PR.ts(p["event_start"]) > now]
    tennis_rows = L.read_rows(REPO / "tennis_predictions/price_snapshots.csv")
    prob_rows = L.read_rows(REPO / "tennis_predictions/probability_snapshots.csv")
    card, money = latest_card()
    decided, all_cands = [], []
    for p in upcoming:
        best, cands = evaluate_prediction(p, gather_snapshots(p, tennis_rows, card, prob_rows), cfg, now)
        decided.append(best)
        all_cands += cands
    snaps_added = L.record_snapshots(SNAPSHOTS, all_cands, {c.prediction_id: c.decision for c in decided})
    added = L.record_selections(SELECTIONS, decided, cfg["rule_version"], cfg["paper_stake_units"], now,
                                exclude_prediction_ids=valid_legacy_prediction_ids(cfg))
    hp = cfg["high_probability_threshold"]
    run = {"run_at": now.isoformat(), "trigger": os.environ.get("TRIGGER_EVENT", "manual"), "rule_version": cfg["rule_version"],
           "events_scanned": len({p["event_key"] for p in upcoming}),
           "valid_predictions": sum(c.prediction_valid for c in decided),
           "high_p_candidates": sum(c.prediction_valid and c.probability >= hp for c in decided),
           "priced_candidates": sum(c.prediction_valid and c.net_ev is not None for c in decided),
           **{d: sum(c.decision == d for c in decided) for d in DECISIONS},
           "paper_bets_added": added, "snapshots_added": snaps_added,
           "money_card_qualified": (money or {}).get("money_qualified_count", ""),
           "football_fixtures_on_card": (card or {}).get("fixtures_scanned", "")}
    new = not RUNS.exists()
    OUT.mkdir(exist_ok=True)
    with RUNS.open("a", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=RUN_FIELDS)
        if new:
            w.writeheader()
        w.writerow(run)
    REPORTS.mkdir(exist_ok=True)
    rows = [c.row() for c in decided]
    with (REPORTS / "bet_selection_v2_candidates.csv").open("w", newline="", encoding="utf-8") as f:
        if rows:
            w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
            w.writeheader()
            w.writerows(rows)
    print(json.dumps(run, indent=1))
    return {"run": run, "decided": rows}


def settle(now: datetime) -> int:
    sels = L.read_rows(SELECTIONS)
    plat = {r["prediction_id"]: r for r in L.read_rows(REPO / "predictions/unified_settlements.csv")}
    done = {r["selection_id"] for r in L.read_rows(SETTLEMENTS)}
    n = L.append_settlements(SETTLEMENTS, L.settle(sels, plat, done, now))
    print(f"paper settlements added: {n}")
    return n


def build_report(cfg: dict, now: datetime, latest: dict | None = None) -> dict:
    runs = L.read_rows(RUNS)
    all_sels = L.read_rows(SELECTIONS)
    # current rule version + earlier-version rows annotated VALID_SAME_SNAPSHOT (they satisfy the current semantics)
    notes_ = {r["selection_id"]: r["annotation"] for r in L.read_rows(OUT / "selection_annotations.csv")}
    sels = [r for r in all_sels if r["rule_version"] == cfg["rule_version"] or notes_.get(r["selection_id"]) == "VALID_SAME_SNAPSHOT"]
    notes = {r["selection_id"]: r for r in L.read_rows(OUT / "selection_annotations.csv")}
    legacy = [{"selection_id": r["selection_id"], "rule_version": r["rule_version"], "event": r["event_name"],
               "selection": r["selection"], "annotation": notes.get(r["selection_id"], {}).get("annotation", "NOT_ANNOTATED")}
              for r in all_sels if r["rule_version"] != cfg["rule_version"]]
    sett = {r["selection_id"]: r for r in L.read_rows(SETTLEMENTS)}
    if latest is None:
        p = REPORTS / "bet_selection_v2_candidates.csv"
        latest = {"decided": L.read_rows(p) if p.exists() else []}
    rep = {"generated_at": now.isoformat(), "product": "BET-SELECTION V2 (PAPER research; not a betting card)",
           "rule_version": cfg["rule_version"], "real_money_enabled": False, "multis_enabled": cfg["multi"]["enabled"],
           "funnel": R.funnel_from_runs(runs), "latest_run": runs[-1] if runs else None,
           "latest_decisions": R.decision_breakdown(latest["decided"]) if latest["decided"] else {},
           "paper_results": R.results(sels, sett, cfg["bankroll_simulation"]),
           "superseded_rule_version_selections": legacy}
    REPORTS.mkdir(exist_ok=True)
    (REPORTS / "bet_selection_v2.json").write_text(json.dumps(rep, indent=1, default=str))
    (REPORTS / "bet_selection_v2.md").write_text(render_md(rep, latest["decided"]))
    return rep


def _f(x, pct=False):
    if x in (None, ""):
        return "—"
    return f"{100 * float(x):.1f}%" if pct else f"{float(x):.2f}"


def render_md(rep: dict, decided: list[dict]) -> str:
    fun, res = rep["funnel"], rep["paper_results"]["overall"]
    lr = rep["latest_run"] or {}
    L_ = [f"# BET-SELECTION V2 — PAPER RESEARCH ({rep['generated_at'][:10]})", "",
          "_Paper only. Real money disabled. Not a betting card; the Money Card is separate and unchanged._", "",
          "## Latest run funnel", ""]
    if lr:
        L_ += [f"Run {lr['run_at'][:16]}Z · events scanned {lr['events_scanned']} · valid predictions {lr['valid_predictions']} · "
               f"high-P (≥70%) {lr['high_p_candidates']} · priced {lr['priced_candidates']} · PAPER_BET {lr['PAPER_BET']} · "
               f"MULTI-research {lr['MULTI_RESEARCH_ELIGIBLE']} · WATCH {lr['WATCH']} · REJECT {lr['REJECT']} · "
               f"new paper bets {lr['paper_bets_added']} · Money Card qualified {lr['money_card_qualified'] or '—'}", ""]
    else:
        L_ += ["No evaluation run yet.", ""]
    dd = rep.get("latest_decisions") or {}
    if dd.get("reason_counts"):
        L_ += ["Reason codes (latest run): " + " · ".join(f"{k} {v}" for k, v in dd["reason_counts"].items()), ""]
    L_ += ["## Candidates (latest run, best price per prediction)", "",
           "| Event | Start | Sel | P | Fair | Odds (source) | Break-even | Net EV | Decision |", "|---|---|---|---|---|---|---|---|---|"]
    for c in sorted(decided, key=lambda c: (c["decision"] != PAPER_BET, -float(c["probability"])))[:40]:
        odds = f"{_f(c['decimal_odds'])} ({c['source']})" if c.get("decimal_odds") not in (None, "") else "—"
        L_.append(f"| {c['event_name']} | {str(c['event_start'])[:16]} | {c['selection']} | {_f(c['probability'], True)} | "
                  f"{_f(c['fair_odds'])} | {odds} | {_f(c['break_even_probability'], True)} | {_f(c['net_ev'], True)} | {c['decision']} |")
    if not decided:
        L_.append("| — | no upcoming prediction | | | | | | | |")
    L_ += ["", "## Paper results (all time)", "",
           f"Selections {res['selections']} · settled {res['settled']} · pending {res['pending']} · win rate {_f(res['win_rate'], True)} · "
           f"avg P {_f(res['avg_probability'], True)} · avg odds {_f(res['avg_odds'])} · expected net {res['expected_net_pnl_units']:+.2f}u · "
           f"realised net {res['realised_net_pnl_units']:+.2f}u · yield {_f(res['roi_yield'], True)} · max DD {res['max_drawdown_units']:.2f}u · "
           f"longest losing streak {res['longest_losing_streak']}",
           "", f"Days evaluated {fun['days_evaluated']} · no-bet days {len(fun['no_bet_days'])}"
           + (f" ({', '.join(fun['no_bet_days'])})" if fun["no_bet_days"] else ""), "",
           "## Bankroll simulations (descriptive; small samples prove nothing)", "",
           "| Start £ | Policy | Bets | Final £ | P&L £ | Max DD | Skipped | Locks |", "|---|---|---|---|---|---|---|---|"]
    for s in rep["paper_results"]["bankroll_simulations"]:
        L_.append(f"| {s['bankroll_start']:.0f} | {s['policy']} | {s['bets']} | {s['final']:.2f} | {s['pnl']:+.2f} | "
                  f"{100 * s['max_drawdown_pct']:.1f}% | {s['skipped'] or '—'} | "
                  f"{'stop' if s['drawdown_stop_fired'] else ''}{' daily×' + str(s['daily_loss_lock_days']) if s['daily_loss_lock_days'] else ''} |")
    L_ += ["", "Positive estimated EV is not realised profit. The live-money gate is pre-registered in "
           "`research/platform_v2/bet_selection_v2/LIVE_GATE_PREREGISTRATION.md`; real-money betting stays disabled."]
    return "\n".join(L_) + "\n"


def diagnose(cfg: dict) -> dict:
    """Re-evaluate settled VALID predictions at their own prediction time and recorded price. Diagnostic only."""
    preds = {p["prediction_id"]: p for p in L.read_rows(REPO / "predictions/unified_ledger.csv")}
    sett = L.read_rows(REPO / "predictions/unified_settlements.csv")
    rows = []
    for s in sett:
        p = preds.get(s["prediction_id"])
        if not p or str(p["prediction_valid"]) != "True" or s["settlement_status"] != "SETTLED":
            continue
        at = PR.ts(p["prediction_timestamp"])
        best, _ = evaluate_prediction(p, [x for x in [PR.from_ledger_row(p)] if x], cfg, at)
        comm = best.commission or 0.0
        won = str(s["correct"]) == "1"
        pnl = ((best.decimal_odds - 1) * (1 - comm) if won else -1.0) if best.decimal_odds else None
        rows.append({"prediction_id": p["prediction_id"], "event": p["event_name"], "P": best.probability,
                     "odds": best.decimal_odds, "source": best.source, "net_ev": best.net_ev,
                     "decision_at_prediction_time": best.decision, "reasons": best.reasons, "correct": int(won),
                     "hypothetical_unit_pnl": pnl})
    n = len(rows)
    summary = {"n": n, "decisions": dict(Counter(r["decision_at_prediction_time"] for r in rows)),
               "mean_net_ev": round(sum(r["net_ev"] for r in rows if r["net_ev"] is not None) / n, 4) if n else None,
               "hypothetical_level_stakes_pnl_units": round(sum(r["hypothetical_unit_pnl"] or 0 for r in rows), 4),
               "label": "RETROSPECTIVE DIAGNOSTIC -- not paper selections, not backfilled, not evidence of an edge"}
    out = {"generated_at": now_utc().isoformat(), "summary": summary, "rows": rows}
    REPORTS.mkdir(exist_ok=True)
    (REPORTS / "bet_selection_v2_retrospective.json").write_text(json.dumps(out, indent=1, default=str))
    print(json.dumps(summary, indent=1))
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("command", choices=["evaluate", "settle", "report", "diagnose"])
    a = ap.parse_args()
    cfg = load_config()
    now = now_utc()
    latest = None
    if a.command == "evaluate":
        latest = evaluate(cfg, now)
    elif a.command == "settle":
        settle(now)
    elif a.command == "diagnose":
        diagnose(cfg)
        return 0
    build_report(cfg, now, latest)
    return 0


if __name__ == "__main__":
    sys.exit(main())
