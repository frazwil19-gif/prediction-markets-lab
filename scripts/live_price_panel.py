"""Track A / H3+H7: zero-credit live price panel at decision time (research only; no rule change).

For every row of paper_betting_v2/decision_shadow.csv (all evaluated candidates, PAPER_BET or not) whose price came
from a tennis scan, rebuild the full same-scan quote panel from tennis_predictions/price_snapshots.csv and the exchange
back/lay from exchange_probability_snapshots.csv, and record: n books, best / median price, best book, dispersion,
chosen-book rank and gap to best, exchange back/lay and spread, commission, best price NET of commission (unknown
commission -> excluded, never assumed zero), and the decision. Football panels come from the H1 per-book shadow
(research_shadow/h1_devig/) once it accumulates; this script reports how many rows it has.

Outputs research/platform_v2/track_a/H3_PANEL.csv + H3_PANEL_SUMMARY.json. Uses only files already in the repo.
"""
from __future__ import annotations

import csv
import json
import statistics
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

import yaml

REPO = Path(__file__).resolve().parents[1]
# Mirrors the candidate-exclusion set in bet_selection_v2/evaluate.py:evaluate_prediction (test guards drift). When every
# candidate carries one of these, bsv2 records a FALLBACK quote, which is NOT the best executable price.
UNUSABLE = frozenset({"PRICE_STALE", "PRICE_AT_OR_AFTER_START", "PROBABILITY_NOT_SAME_SNAPSHOT",
                      "EXCHANGE_SPREAD_TOO_WIDE", "EXCHANGE_SPREAD_UNKNOWN"})
BEST_USABLE, FALLBACK = "BEST_USABLE_NET_EV_LATEST_SNAPSHOT", "FALLBACK_NO_USABLE_CANDIDATE"
OUT = REPO / "research/platform_v2/track_a"


def read(p: Path) -> list[dict]:
    if not p.exists():
        return []
    with p.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def ts(s: str) -> datetime:
    d = datetime.fromisoformat(s.replace("Z", "+00:00"))
    return d if d.tzinfo else d.replace(tzinfo=timezone.utc)


def net_price(o: float, c: float) -> float:
    return 1 + (o - 1) * (1 - c)


def build(repo: Path = REPO) -> tuple[list[dict], dict]:
    cfg = yaml.safe_load((repo / "config/bet_selection_v2.yaml").read_text())
    comm, exch = cfg["commission"], set(cfg["exchange_keys"])
    max_age = float(cfg["decision_gates"]["paper_bet"]["max_price_age_minutes"])
    snaps = defaultdict(list)
    for r in read(repo / "tennis_predictions/price_snapshots.csv"):
        snaps[r["scan_timestamp_utc"]].append(r)
    exq = {(r["scan_timestamp_utc"], r["event_id"]): r for r in read(repo / "tennis_predictions/exchange_probability_snapshots.csv")}
    rows = []
    for d in read(repo / "paper_betting_v2/decision_shadow.csv"):
        if d["sport"] != "tennis":
            continue
        quotes = [q for q in snaps.get(d["price_observed_at"], []) if d["selection"] in (q["player_a"], q["player_b"])]
        if not quotes:
            continue
        side = "a" if quotes[0]["player_a"] == d["selection"] else "b"
        prices = {q["bookmaker"]: float(q[f"odds_{side}"]) for q in quotes if float(q[f"odds_{side}"] or 0) > 1}
        age = {q["bookmaker"]: round((ts(q["scan_timestamp_utc"]) - ts(q["last_update"])).total_seconds() / 60, 1)
               for q in quotes if q.get("last_update")}
        gross = sorted(prices.values(), reverse=True)
        nets = {b: net_price(o, float(comm[b]) if b in exch else 0.0) for b, o in prices.items()      # permitted venues:
                if (b not in exch or comm.get(b) is not None) and (age.get(b) is None or age[b] <= max_age)}  # known commission, fresh
        best_net_book = max(nets, key=nets.get) if nets else ""
        chosen = d["source"]
        x = exq.get((d["price_observed_at"], quotes[0]["event_id"]))
        back = lay = None
        if x and "ex_back=" in x["raw_prices"]:
            parts = dict(p.split("=") for p in x["raw_prices"].split(";"))
            i = 0 if side == "a" else 1
            back, lay = float(parts["ex_back"].split("/")[i]), float(parts["ex_lay"].split("/")[i])
        dec_price, dec_venue = float(d["decimal_odds"]), d["source"]
        reasons = d["bsv2_reasons"]
        books = {b: o for b, o in prices.items() if b not in exch}
        best_sb = max(books, key=books.get) if books else ""
        rows.append({
            "evaluated_at": d["evaluated_at"], "price_observed_at": d["price_observed_at"], "competition": d["competition"],
            "selection": d["selection"], "probability": d["probability"], "decision": d["bsv2_decision"],
            "decision_reasons": reasons, "grade": d["grade"],
            # DECISION_PRICE: exactly what the engine used, and why
            "decision_price": dec_price, "decision_venue": dec_venue, "decision_is_exchange": dec_venue in exch,
            "decision_net_price": (dec_price if dec_venue not in exch else
                                   round(net_price(dec_price, float(comm[dec_venue])), 4) if comm.get(dec_venue) is not None else ""),
            "decision_price_basis": FALLBACK if set(reasons.split("|")) & UNUSABLE else BEST_USABLE,
            "price_age_minutes": d["price_age_minutes"],
            # BEST_EXECUTABLE_PRICE_AT_DECISION_TIME (same scan; never rewritten into the decision ledger)
            "n_books": len(prices), "best_gross_price": gross[0], "best_gross_venue": max(prices, key=prices.get),
            "median_price": statistics.median(gross), "dispersion": round(gross[0] / gross[-1] - 1, 4),
            "best_sportsbook_price": books.get(best_sb, ""), "best_sportsbook_venue": best_sb,
            "best_executable_net_price": round(nets[best_net_book], 4) if nets else "", "best_executable_net_venue": best_net_book,
            "best_executable_quote_age_min": age.get(best_net_book, ""),
            "decision_rank_gross": 1 + sum(1 for v in gross if v > dec_price),
            "decision_gap_to_best_gross": round(dec_price / gross[0] - 1, 4),
            "exchange_back": back, "exchange_lay": lay,
            "exchange_back_net": round(net_price(back, float(comm["betfair_ex_uk"])), 4) if back else "",
            "exchange_spread_pct": round(lay / back - 1, 4) if back and lay else "",
            "commission_unknown_venues": ";".join(b for b in prices if b in exch and comm.get(b) is None),
            "all_quotes_json": json.dumps({b: {"price": o, "quote_age_min": age.get(b)} for b, o in sorted(prices.items())})})
    fb = sorted((repo / "research_shadow/h1_devig").glob("*.csv")) if (repo / "research_shadow/h1_devig").exists() else []
    n_fb = sum(len(read(p)) for p in fb)

    def med(k, rs):
        v = [float(r[k]) for r in rs if r[k] not in ("", None)]
        return round(statistics.median(v), 4) if v else None
    summary = {"tennis_rows": len(rows), "paper_bet_rows": sum(r["decision"] == "PAPER_BET" for r in rows),
               "median_n_books": med("n_books", rows), "median_dispersion": med("dispersion", rows),
               "median_decision_gap_to_best_gross": med("decision_gap_to_best_gross", rows),
               "share_decision_is_best_gross": round(sum(r["decision_rank_gross"] == 1 for r in rows) / len(rows), 3) if rows else None,
               "median_exchange_spread": med("exchange_spread_pct", rows),
               "share_best_executable_is_exchange": round(sum(r["best_executable_net_venue"] in exch for r in rows) / len(rows), 3) if rows else None,
               "decision_price_basis_counts": {b: sum(r["decision_price_basis"] == b for r in rows) for b in (BEST_USABLE, FALLBACK)},
               "n_decision_net_below_best_executable": sum("" not in (r["best_executable_net_price"], r["decision_net_price"]) and r["best_executable_net_price"] > r["decision_net_price"] for r in rows),
               "n_fallback_net_below_best_executable": sum(r["decision_price_basis"] == FALLBACK and "" not in (r["best_executable_net_price"], r["decision_net_price"])
                                                           and r["best_executable_net_price"] > r["decision_net_price"] for r in rows),
               "median_best_executable_quote_age_min": med("best_executable_quote_age_min", rows),
               "football_h1_panel_rows": n_fb,
               "note": "Descriptive only. Small N; no rule change; evaluated per H3/H7 evidence conditions, not calendar."}
    return rows, summary


def main() -> int:
    rows, summary = build()
    OUT.mkdir(parents=True, exist_ok=True)
    if rows:
        with (OUT / "H3_PANEL.csv").open("w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=list(rows[0]))
            w.writeheader()
            w.writerows(rows)
    (OUT / "H3_PANEL_SUMMARY.json").write_text(json.dumps(summary, indent=2) + "\n")
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
