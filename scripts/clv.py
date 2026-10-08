"""CLV capture + EV-band study runner (config/clv.yaml; research/platform_v2/clv/CLV_ARCHITECTURE.md). Measurement only.

  python scripts/clv.py targets   # 0 credits: append new PAPER_BET + EV-study rows to research_shadow/clv/targets.csv
  python scripts/clv.py capture   # paid (surplus-only): near-close quotes for targets starting within the window
  python scripts/clv.py report    # 0 credits: research_shadow/clv/clv_report.{json,md}
  python scripts/clv.py all       # targets -> capture -> report
Triggered every 15 min by the Mac LaunchAgent (scripts/setup_clv_dispatcher_mac.sh) because GitHub cron is hours late.
"""
from __future__ import annotations

import json
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

import yaml

from prediction_markets_lab.clv import core as C
from prediction_markets_lab.ops import credit_ledger as CL
from prediction_markets_lab.ops import football_coverage as FC

REPO = Path(__file__).resolve().parents[1]
CONSUMER = "clv_capture"
BASE = "research_shadow/clv"   # own files only: never conflicts with production commits


def cfg(repo: Path) -> dict:
    return yaml.safe_load((repo / "config/clv.yaml").read_text())


def build_targets(repo: Path, now: datetime) -> int:
    c = cfg(repo)
    sels = C.read(repo / "paper_betting_v2/selections.csv")
    ledger = {r["prediction_id"]: r for r in C.read(repo / "predictions/unified_ledger.csv")}
    cur_rule = str(yaml.safe_load((repo / "config/bet_selection_v2.yaml").read_text())["rule_version"])
    shadow = C.read(repo / "paper_betting_v2/decision_shadow.csv")
    # decision_shadow carries no rule column; every row since 2026-10-01 20:28 is bsv2-4. If the rule is ever re-versioned,
    # rows after that change get the new label and drop out of the bsv2-4 study automatically.
    rule_by_time = {r["evaluated_at"]: cur_rule for r in shadow}
    tg = C.paper_bet_targets(sels, C.ts(c["active_from"]), c["study"]["bands"]) + C.study_cohort(shadow, ledger, c, rule_by_time)
    for t in tg:
        t["logged_at"] = now.isoformat()
    return C.append(repo / BASE / "targets.csv", C.COHORT_FIELDS, tg)


def _spent(ledger: Path, now: datetime, day: bool) -> int:
    pre = now.strftime("%Y-%m-%d" if day else "%Y-%m")
    return sum(int(r.get("credits_charged") or 0) for r in CL.read(ledger)
               if r["consumer"] == CONSUMER and r["timestamp_utc"].startswith(pre) and r["outcome"] == CL.PAID)


def floor(repo: Path, budget: dict, c: dict, now: datetime) -> float:
    import calendar
    days_left = calendar.monthrange(now.year, now.month)[1] - now.day + 1
    return FC.tier_floor(budget, int(budget["clv_capture"]["protect_as_tier"]), now) + days_left * float(c["extra_protected_daily_need"])


def capture(repo: Path, now: datetime, fetch_events=None, fetch_odds=None) -> dict:
    from prediction_markets_lab.ingestion import the_odds_api_loader as L
    fetch_events = fetch_events or L.fetch_events_raw
    fetch_odds = fetch_odds or L.fetch_odds_raw
    c, budget = cfg(repo), FC.load_budget(repo / "config/api_budget.json")
    b = budget["clv_capture"]
    base = repo / BASE
    ledger, out, missed = base / "credit_ledger.csv", base / "captures.csv", base / "missed.csv"
    targets = [t for t in C.read(base / "targets.csv") if C.capture_eligible(t, c)]
    done = {r["target_id"] for r in C.read(out)}
    terminal = {r["target_id"] for r in C.read(missed) if r["status"] == "NOT_CAPTURED_BEFORE_START"}
    for t in targets:   # missing data is logged, never imputed
        if t["target_id"] not in done and t["target_id"] not in terminal and C.ts(t["event_start"]) <= now:
            C.log_missed(missed, t, now, "NOT_CAPTURED_BEFORE_START", "no successful capture inside the window before start")
    todo = C.due(targets, done, now, float(c["capture_window_minutes"]))
    football = {name: key for key, name in FC.sport_keys(FC.load(repo / "config/football_coverage.yaml")).items()}
    groups: dict[str, list[dict]] = defaultdict(list)
    for t in todo:
        k = C.sport_key(t, football)
        (groups[k].append(t) if k else C.log_missed(missed, t, now, "ATTEMPT_FAILED", "UNSUPPORTED_SPORT_KEY"))
    summary = {"due": len(todo), "sport_keys": len(groups), "captured": 0, "skipped": []}
    rows = []
    for key, items in groups.items():
        markets = tuple(c["markets_by_sport"].get(items[0]["sport"], c["markets_by_sport"]["default"]))
        cost = len(markets)
        if _spent(ledger, now, False) + cost > int(b["monthly_cap"]) or _spent(ledger, now, True) + cost > int(b["daily_cap"]):
            summary["skipped"].append((key, "cap"))
            for t in items:
                C.log_missed(missed, t, now, "ATTEMPT_FAILED", "SKIPPED_CAP")
            CL.append(ledger, CONSUMER, f"odds:{key}", CL.SKIPPED_FLOOR, 0, cost, None, "monthly/daily cap", now=now)
            continue
        cfg_api = L.TheOddsApiConfig(markets=markets, markets_by_sport={})
        hdr: dict = {}
        try:
            fetch_events(key, cfg_api, hdr)          # free: credit headers only
        except Exception as exc:                     # optional consumer: fail closed
            for t in items:
                C.log_missed(missed, t, now, "ATTEMPT_FAILED", f"EVENTS_CHECK_FAILED: {type(exc).__name__}")
            continue
        rem, fl = hdr.get("x-requests-remaining"), floor(repo, budget, c, now)
        if rem in (None, "") or float(rem) < fl:
            for t in items:
                C.log_missed(missed, t, now, "ATTEMPT_FAILED", f"SKIPPED_CREDIT_FLOOR remaining={rem} floor={fl:.0f}")
            CL.append(ledger, CONSUMER, f"odds:{key}", CL.SKIPPED_FLOOR, 0, cost, hdr, f"remaining {rem} < floor {fl}", now=now)
            continue
        hdr = {}
        try:
            raw = fetch_odds(key, cfg_api, hdr)
        except Exception as exc:
            CL.append(ledger, CONSUMER, f"odds:{key}", CL.PAID, None, 0, hdr, f"error {type(exc).__name__}", now=now)
            for t in items:
                C.log_missed(missed, t, now, "ATTEMPT_FAILED", f"ODDS_CALL_FAILED: {type(exc).__name__}")
            continue
        CL.append(ledger, CONSUMER, f"odds:{key}", CL.PAID, int(hdr.get("x-requests-last") or cost), 0, hdr, "", now=now)
        for t in items:
            ev = C.find_event(raw if isinstance(raw, list) else [], t)
            r = C.measure(t, ev, now, float(c["near_close_minutes"]), key) if ev else None
            if r:
                rows.append(r)
            else:
                C.log_missed(missed, t, now, "ATTEMPT_FAILED", "EVENT_NOT_FOUND_OR_AMBIGUOUS" if not ev else "NO_REFERENCE_OR_STARTED")
    summary["captured"] = C.append(out, C.CAPTURE_FIELDS, rows)
    return summary


def report(repo: Path, now: datetime) -> dict:
    c = cfg(repo)
    base = repo / BASE
    targets = C.read(base / "targets.csv")
    caps = {r["target_id"]: r for r in C.read(base / "captures.csv")}
    settle = {r["prediction_id"]: r for r in C.read(repo / "predictions/unified_settlements.csv")}
    ledger_rows = [r for r in C.read(base / "credit_ledger.csv") if r["outcome"] == CL.PAID]
    month = now.strftime("%Y-%m")
    for t in targets:
        if t["target_id"] in caps:
            t.update(C.clv_row(caps[t["target_id"]]))
            t["capture_quality"] = caps[t["target_id"]]["capture_quality"]
    m = lambda rows, k: C.summarise([r.get(k) for r in rows if r["target_id"] in caps], c)
    paper = [t for t in targets if t["kind"] == "PAPER_BET"]
    pb = {"n_targets": len(paper), "n_captured": sum(t["target_id"] in caps for t in paper),
          "fair_clv": m(paper, "fair_clv"), "price_clv_same_book": m(paper, "price_clv_same_book"),
          "price_clv_best": m(paper, "price_clv_best"), "p_move": m(paper, "p_move")}
    dims = {"sport": lambda r: r["sport"], "engine": lambda r: r["engine_id"], "market": lambda r: f"{r['sport']}:{r['market']}",
            "bookmaker": lambda r: r["entry_book"], "ev_band": lambda r: r["ev_band"]}
    pb["by"] = {d: {k: {"n": len(v), "fair_clv": m(v, "fair_clv"), "price_clv_same_book": m(v, "price_clv_same_book")}
                    for k, v in C.group_by(paper, f).items()} for d, f in dims.items()}
    study = [t for t in targets if t["kind"] == "EV_STUDY"]
    proxy = C.tier_b_proxy(study, C.read(repo / "tennis_predictions/exchange_probability_snapshots.csv"),
                           C.read(repo / "tennis_predictions/price_snapshots.csv"))
    sealed = set(c["study"]["sealed_bands"])
    combined = [t for t in study if t["ev_band"] in sealed and t["target_id"] in caps]
    look_reached = [n for n in c["study"]["look_points"] if len(combined) >= n]
    unsealed = bool(look_reached)
    bands = {}
    for label in [b[2] for b in c["study"]["bands"]]:
        rows = [t for t in study if t["ev_band"] == label]
        evs = [float(t["entry_net_ev"]) for t in rows]
        books = C.group_by(rows, lambda r: r["entry_book"])
        top = max((len(v) for v in books.values()), default=0)
        entry = {"n": len(rows), "est_ev": C.summarise(evs, c) if evs else {"n": 0},
                 "tier_a_eligible": sum(C.capture_eligible(t, c) for t in rows),
                 "tier_a_captured": sum(t["target_id"] in caps for t in rows),
                 "top_book_share": round(top / len(rows), 3) if rows else None,
                 "price_age_median_min": C.summarise([float(t["entry_price_age_minutes"]) for t in rows
                                                      if t["entry_price_age_minutes"] not in ("", None)], c).get("median")}
        if label not in sealed or unsealed:
            entry.update({"fair_clv": m(rows, "fair_clv"), "price_clv_same_book": m(rows, "price_clv_same_book"),
                          "p_move": m(rows, "p_move"),
                          "tier_b_proxy_fair_clv": C.summarise([proxy[t["target_id"]]["proxy_fair_clv"] for t in rows
                                                                if t["target_id"] in proxy], c),
                          "outcomes": C.outcome_stats(rows, settle)})
        else:
            entry["sealed"] = f"CLV/P&L/calibration sealed until {c['study']['look_points'][0]} combined 0-2% Tier-A captures"
        bands[label] = entry
    r = {"version": c["version"], "generated_at": now.isoformat(),
         "credits": {"month": month, "spent_this_month": sum(int(x.get("credits_charged") or 0) for x in ledger_rows
                                                             if x["timestamp_utc"].startswith(month)),
                     "monthly_cap": json.loads((repo / "config/api_budget.json").read_text())["clv_capture"]["monthly_cap"],
                     "paid_calls_this_month": sum(x["timestamp_utc"].startswith(month) for x in ledger_rows)},
         "missed": len(C.read(base / "missed.csv")),
         "paper_bet_clv": pb,
         "ev_band_study": {"study_start": c["study"]["study_start"], "combined_0_2_tier_a": len(combined),
                           "look_points": c["study"]["look_points"], "looks_reached": look_reached, "bands": bands},
         "definitions": {"fair_clv": "(1+(odds-1)(1-commission)) x p_close - 1 (tennis p_close = Betfair back/lay mid; others UK median fair)",
                         "price_clv_same_book": "entry odds / same book closing odds - 1",
                         "price_clv_best": "entry odds / best UK closing odds - 1", "p_move": "p_close - p_entry"}}
    base.mkdir(parents=True, exist_ok=True)
    (base / "clv_report.json").write_text(json.dumps(r, indent=1))
    (base / "clv_report.md").write_text(render_md(r))
    return r


def _fmt(s: dict) -> str:
    if not s or not s.get("n"):
        return "n 0"
    ci = f" CI [{s['ci95'][0]:+.2%}, {s['ci95'][1]:+.2%}]" if s.get("ci95") else ""
    return f"n {s['n']} · mean {s['mean']:+.2%} · median {s['median']:+.2%} · positive {s['positive_rate']:.0%}{ci}"


def render_md(r: dict) -> str:
    pb, st, cr = r["paper_bet_clv"], r["ev_band_study"], r["credits"]
    L = [f"# CLV report ({r['version']}, {r['generated_at'][:16]}Z)", "",
         f"Credits {cr['month']}: {cr['spent_this_month']} of {cr['monthly_cap']} ({cr['paid_calls_this_month']} paid calls). "
         f"Missed captures logged: {r['missed']}.", "",
         "## PAPER_BET (live-rule) CLV", "",
         f"Targets {pb['n_targets']}, captured {pb['n_captured']}.", "",
         f"- fair-CLV: {_fmt(pb['fair_clv'])}", f"- price-CLV (same book): {_fmt(pb['price_clv_same_book'])}",
         f"- price-CLV (best UK): {_fmt(pb['price_clv_best'])}", ""]
    for d, groups in pb["by"].items():
        if groups:
            L += [f"**By {d}:** " + " · ".join(f"{k}: {_fmt(v['fair_clv'])}" for k, v in groups.items()), ""]
    L += ["## Tennis EV-band study (pre-registered; research only — live rule stays EV ≥ 2%)", "",
          f"Study start {st['study_start'][:16]}Z. Combined 0–2% Tier-A captures: **{st['combined_0_2_tier_a']}** "
          f"(looks at {st['look_points']}; reached: {st['looks_reached'] or 'none'}).", "",
          "| Band | N | est. EV mean | Tier A captured/eligible | top-book share | fair-CLV | Tier-B proxy | settled / ROI |",
          "|---|---|---|---|---|---|---|---|"]
    for k, b in st["bands"].items():
        ev = b["est_ev"].get("mean")
        o = b.get("outcomes", {})
        L.append(f"| {k} | {b['n']} | {'' if ev is None else f'{ev:+.2%}'} | {b['tier_a_captured']}/{b['tier_a_eligible']} | "
                 f"{b['top_book_share']} | {'sealed' if 'sealed' in b else _fmt(b.get('fair_clv'))} | "
                 f"{'sealed' if 'sealed' in b else _fmt(b.get('tier_b_proxy_fair_clv'))} | "
                 f"{'sealed' if 'sealed' in b else (str(o.get('settled')) + ' / ' + str(o.get('roi')))} |")
    L += ["", "Definitions: " + "; ".join(f"{k} = {v}" for k, v in r["definitions"].items())]
    return "\n".join(L) + "\n"


def main(argv: list[str]) -> int:
    cmd = argv[1] if len(argv) > 1 else "all"
    now = datetime.now(timezone.utc)
    if cmd in ("targets", "all"):
        print("targets added:", build_targets(REPO, now))
    if cmd in ("capture", "all"):
        print("capture:", capture(REPO, now))
    if cmd in ("report", "all"):
        r = report(REPO, now)
        print("report:", json.dumps({"paper": r["paper_bet_clv"]["n_captured"], "study_0_2": r["ev_band_study"]["combined_0_2_tier_a"]}))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
