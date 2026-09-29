"""V2-6E controlled historical tennis pilot (The Odds API historical endpoint). PREPARED, NOT EXECUTED.

Pre-registration: research/platform_v2/historical_v2_6e/PILOT_PREREGISTRATION.md
Modes:
  plan      print the frozen request plan and the maximum cost (no network)
  execute   paid calls -- refuses unless PILOT_AUTHORISED equals AUTH_TOKEN and THE_ODDS_API_KEY is set;
            HARD CAP 700 credits (checked before every call from actual x-requests-used deltas); stops at the
            validation gate after the first snapshot if exchange back+lay / UK books / timestamps are missing
  analyse   offline: saved snapshots -> frozen live tennis engine (as-of snapshot) -> bsv2-1 decisions ->
            settlement vs hash-verified tennis-data 2024 results. Never writes paper_betting_v2/.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.parse
import urllib.request
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
OUT = REPO / "research/platform_v2/historical_v2_6e"
RAW = OUT / "pilot_raw"
BASE = "https://api.the-odds-api.com/v4/historical/sports"
AUTH_TOKEN = "V2-6E-PILOT-APPROVED-BY-FRASER"
HARD_CAP = 700
COST_PER_CALL = 10            # verified: 10 x markets(1) x regions(1); empty responses free
SNAPSHOT_HOUR_UTC = 20        # D-1 20:00 UTC (mirrors production's evening board, <= 24 h before day-D matches)
REGION, MARKET = "uk", "h2h"

# Match days (UTC dates) from the hash-verified tennis-data 2024 files: schedule only, no outcome information.
TOURNAMENTS = {
    "tennis_atp_wimbledon": ("2024-07-01", "2024-07-14"),
    "tennis_wta_wimbledon": ("2024-07-01", "2024-07-13"),
    "tennis_atp_us_open": ("2024-08-26", "2024-09-08"),
    "tennis_wta_us_open": ("2024-08-26", "2024-09-07"),
}


@dataclass(frozen=True)
class Call:
    sport_key: str
    match_day: str
    snapshot: str   # ISO UTC requested `date`

    @property
    def fname(self) -> str:
        return f"{self.sport_key}__{self.match_day}.json"


def match_days_from_tennis_data(td_dir: Path | None) -> dict[str, list[str]]:
    """Exact distinct match dates per key from tennis-data 2024 (falls back to the full date range)."""
    out: dict[str, list[str]] = {}
    for key, (a, b) in TOURNAMENTS.items():
        days = None
        if td_dir is not None:
            import pandas as pd
            tour = "atp" if "_atp_" in key else "wta"
            name = "Wimbledon" if "wimbledon" in key else "US Open"
            d = pd.read_excel(td_dir / f"tennis_data_{tour}_2024.xlsx")
            days = sorted({x.date().isoformat() for x in d[d.Tournament.str.contains(name)].Date})
        if not days:
            s, e = date.fromisoformat(a), date.fromisoformat(b)
            days = [(s + timedelta(days=i)).isoformat() for i in range((e - s).days + 1)]
        out[key] = days
    return out


def build_plan(days: dict[str, list[str]]) -> list[Call]:
    calls = []
    for key in TOURNAMENTS:                       # frozen order; the first call is the validation snapshot
        for d in days[key]:
            snap = datetime.fromisoformat(d).replace(hour=SNAPSHOT_HOUR_UTC, tzinfo=timezone.utc) - timedelta(days=1)
            calls.append(Call(key, d, snap.strftime("%Y-%m-%dT%H:%M:%SZ")))
    return calls


# ---------------------------------------------------------------- validation gate (applied to the first snapshot)
def validation_gate(payload: dict) -> tuple[bool, list[str]]:
    reasons = []
    if not payload.get("timestamp"):
        reasons.append("NO_SNAPSHOT_TIMESTAMP")
    events = payload.get("data") or []
    if not events:
        reasons.append("NO_EVENTS")
    with_ex, with_books = 0, 0
    for ev in events:
        keys = {(b.get("key"), m.get("key")) for b in ev.get("bookmakers", []) for m in b.get("markets", [])}
        if ("betfair_ex_uk", "h2h") in keys and ("betfair_ex_uk", "h2h_lay") in keys:
            with_ex += 1
        books = {b.get("key") for b in ev.get("bookmakers", []) if not str(b.get("key", "")).startswith(("betfair_ex", "matchbook", "smarkets"))
                 and any(m.get("key") == "h2h" for m in b.get("markets", []))}
        if len(books) >= 2:
            with_books += 1
        if any(not m.get("last_update") for b in ev.get("bookmakers", []) for m in b.get("markets", [])):
            reasons.append("MISSING_QUOTE_LAST_UPDATE")
            break
    if events and with_ex == 0:
        reasons.append("NO_BETFAIR_BACK_AND_LAY")
    if events and with_books < max(1, len(events) // 2):
        reasons.append("FEWER_THAN_HALF_EVENTS_WITH_2_UK_BOOKS")
    return (not reasons), sorted(set(reasons))


# ---------------------------------------------------------------- execution (paid; guarded)
def _get(url: str) -> tuple[dict, dict]:
    with urllib.request.urlopen(urllib.request.Request(url, headers={"Accept": "application/json"}), timeout=60) as r:
        hdr = {h: r.headers.get(h) for h in ("x-requests-used", "x-requests-remaining", "x-requests-last")}
        return json.loads(r.read()), hdr


def execute(plan: list[Call], key: str, getter=_get, cap: int = HARD_CAP) -> dict:
    RAW.mkdir(parents=True, exist_ok=True)
    log = {"started_at": datetime.now(timezone.utc).isoformat(), "cap": cap, "calls": [], "stopped": None, "spent": 0}
    used0 = None
    for i, c in enumerate(plan):
        if (RAW / c.fname).exists():
            log["calls"].append({"call": c.fname, "skipped": "already saved (idempotent)"})
            continue
        if log["spent"] + COST_PER_CALL > cap:
            log["stopped"] = f"HARD_CAP: next call would exceed {cap}"
            break
        q = urllib.parse.urlencode({"apiKey": key, "regions": REGION, "markets": MARKET, "oddsFormat": "decimal", "date": c.snapshot})
        payload, hdr = getter(f"{BASE}/{c.sport_key}/odds?{q}")
        used = int(hdr.get("x-requests-used") or 0)
        last = int(hdr.get("x-requests-last") or 0)
        used0 = used - last if used0 is None else used0
        log["spent"] = used - used0
        (RAW / c.fname).write_text(json.dumps({"request": c.__dict__, "headers": hdr, "payload": payload}))
        log["calls"].append({"call": c.fname, "snapshot_returned": payload.get("timestamp"), "events": len(payload.get("data") or []),
                             "cost": last, "spent_total": log["spent"]})
        if last > COST_PER_CALL:
            log["stopped"] = f"UNEXPECTED_COST {last} > {COST_PER_CALL}"
            break
        if i == 0:
            ok, why = validation_gate(payload)
            log["validation_gate"] = {"passed": ok, "reasons": why}
            if not ok:
                log["stopped"] = "VALIDATION_GATE_FAILED"
                break
    log["finished_at"] = datetime.now(timezone.utc).isoformat()
    (OUT / "pilot_execution_log.json").write_text(json.dumps(log, indent=1))
    return log


# ---------------------------------------------------------------- offline analysis
def analyse(td_dir: Path, raw: Path = RAW) -> dict:
    import numpy as np
    import pandas as pd

    from prediction_markets_lab.bet_selection_v2 import prices as PR
    from prediction_markets_lab.bet_selection_v2.evaluate import PAPER_BET, evaluate_prediction, load_config
    from prediction_markets_lab.normalisation.player_names import full_name_matches_abbreviated, parse_abbreviated_name
    from prediction_markets_lab.prediction_platform.registry import Registry
    from prediction_markets_lab.tennis_prospective.engine import parse_tennis_odds, predict

    cfg, reg = load_config(), Registry.load()
    td = {}
    for tour in ("atp", "wta"):
        d = pd.read_excel(td_dir / f"tennis_data_{tour}_2024.xlsx")
        td[tour] = d[d.Tournament.str.contains("Wimbledon|US Open")]
    decided, first_seen = [], set()
    stats = {"snapshots": 0, "events": 0, "predictions": 0, "validated": 0, "research_only": 0}
    for f in sorted(raw.glob("*.json")):
        blob = json.loads(f.read_text())
        payload, sk = blob["payload"], blob["request"]["sport_key"]
        ts = PR.ts(payload["timestamp"])
        stats["snapshots"] += 1
        quotes = parse_tennis_odds(payload.get("data") or [], sk)
        stats["events"] += len(quotes)
        snap_rows = PR.tennis_snapshot_rows(quotes, ts)
        for q in quotes:
            p = predict(q, ts)                 # frozen live hierarchy, as-of the snapshot
            if p is None or p.prediction_id in first_seen:
                continue
            stats["predictions"] += 1
            if not p.source_validated:
                stats["research_only"] += 1
                continue                       # research-only rows are never bet (production rule)
            first_seen.add(p.prediction_id)    # first validated snapshot is canonical
            stats["validated"] += 1
            pred = {"prediction_id": p.prediction_id, "engine_id": p.engine_id, "engine_status": reg.get(p.engine_id)["status"],
                    "sport": "tennis", "event_id": p.event_id, "event_key": f"tennis|{sk}|{p.event_id}",
                    "event_name": f"{p.player_a} v {p.player_b}", "event_start": p.commence_time, "market": "match_winner",
                    "selection": p.predicted_winner, "estimated_probability": str(p.predicted_probability),
                    "prediction_valid": "True", "live_price": "", "live_price_source": "", "prediction_timestamp": ts.isoformat()}
            best, _ = evaluate_prediction(pred, PR.tennis_from_snapshots(pred, snap_rows), cfg, ts)
            # settlement: unique tennis-data match (+-1 day, both players structurally matched)
            tour = "atp" if "_atp_" in sk else "wta"
            day = PR.ts(p.commence_time).date()
            c = td[tour][(td[tour].Date.dt.date - day).abs() <= timedelta(days=1)]
            hits = []
            for r in c.itertuples(index=False):
                try:
                    w, l = parse_abbreviated_name(str(r.Winner)), parse_abbreviated_name(str(r.Loser))
                except ValueError:
                    continue
                if {full_name_matches_abbreviated(p.player_a, w) and full_name_matches_abbreviated(p.player_b, l),
                        full_name_matches_abbreviated(p.player_b, w) and full_name_matches_abbreviated(p.player_a, l)} & {True}:
                    sel_won = full_name_matches_abbreviated(p.predicted_winner, w)
                    hits.append((sel_won, str(r.Comment)))
            row = best.row()
            if len(hits) == 1 and hits[0][1].lower().startswith("completed"):
                row["won"] = int(hits[0][0])
            else:
                row["won"] = None
                row["settle_status"] = "UNMATCHED" if not hits else ("AMBIGUOUS" if len(hits) > 1 else "RETIRED_OR_WO_EXCLUDED")
            decided.append(row)
    df = pd.DataFrame(decided)
    res = {"label": "HISTORICAL SIMULATION (paid snapshots, as-of) -- not paper bets, not prospective evidence",
           "rule_version": cfg["rule_version"], "stats": stats}
    if len(df):
        res["decisions"] = df.decision.value_counts().to_dict()
        q = df[(df.decision == PAPER_BET) & df.won.notna()]
        pnl = np.where(q.won == 1, (q.decimal_odds.astype(float) - 1) * (1 - q.commission.astype(float)), -1.0) if len(q) else np.array([])
        rng = np.random.default_rng(20260929)
        ci = ([float(np.percentile(pnl[rng.integers(0, len(pnl), (2000, len(pnl)))].mean(1), p)) for p in (2.5, 97.5)]
              if len(pnl) > 1 else [None, None])
        pos = df[df.net_ev.notna()]
        res["value_distribution"] = {"validated_priced": int(len(pos)), "net_ev_positive": int((pos.net_ev > 0).sum()),
                                     "net_ev_median": float(pos.net_ev.median()) if len(pos) else None}
        res["paper_bet_equivalent"] = {"n": int((df.decision == PAPER_BET).sum()), "settled": int(len(q)),
                                       "per_100_validated": round(100 * (df.decision == PAPER_BET).sum() / max(1, len(df)), 2),
                                       "mean_est_net_ev": float(q.net_ev.mean()) if len(q) else None,
                                       "roi": float(pnl.mean()) if len(pnl) else None, "roi_ci95": ci}
        df.to_csv(OUT / "pilot_decisions.csv", index=False)
    (OUT / "PILOT_RESULTS.json").write_text(json.dumps(res, indent=1, default=str))
    return res


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("mode", choices=["plan", "execute", "analyse"])
    ap.add_argument("--td-dir", type=Path)
    a = ap.parse_args()
    plan = build_plan(match_days_from_tennis_data(a.td_dir))
    if a.mode == "plan":
        print(json.dumps({"calls": len(plan), "max_credits": len(plan) * COST_PER_CALL, "hard_cap": HARD_CAP,
                          "first_call_validation": plan[0].__dict__, "plan": [c.__dict__ for c in plan]}, indent=1))
        return 0
    if a.mode == "execute":
        if os.environ.get("PILOT_AUTHORISED") != AUTH_TOKEN:
            print("REFUSED: pilot execution requires Fraser's explicit authorisation (PILOT_AUTHORISED).")
            return 2
        key = os.environ.get("THE_ODDS_API_KEY")
        if not key:
            print("REFUSED: THE_ODDS_API_KEY not set.")
            return 2
        print(json.dumps(execute(plan, key), indent=1))
        return 0
    if a.td_dir is None:
        print("analyse needs --td-dir")
        return 2
    print(json.dumps(analyse(a.td_dir), indent=1, default=str))
    return 0


if __name__ == "__main__":
    sys.exit(main())
