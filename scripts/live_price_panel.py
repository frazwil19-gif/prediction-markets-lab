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
        nets = {b: net_price(o, float(comm[b]) if b in exch else 0.0) for b, o in prices.items()
                if b not in exch or comm.get(b) is not None}
        best_net_book = max(nets, key=nets.get)
        chosen = d["source"]
        x = exq.get((d["price_observed_at"], quotes[0]["event_id"]))
        back = lay = None
        if x and "ex_back=" in x["raw_prices"]:
            parts = dict(p.split("=") for p in x["raw_prices"].split(";"))
            i = 0 if side == "a" else 1
            back, lay = float(parts["ex_back"].split("/")[i]), float(parts["ex_lay"].split("/")[i])
        rows.append({
            "evaluated_at": d["evaluated_at"], "competition": d["competition"], "selection": d["selection"],
            "probability": d["probability"], "decision": d["bsv2_decision"], "grade": d["grade"],
            "chosen_book": chosen, "chosen_odds": d["decimal_odds"], "price_age_minutes": d["price_age_minutes"],
            "n_books": len(prices), "best_odds": gross[0], "best_book": max(prices, key=prices.get),
            "median_odds": statistics.median(gross), "dispersion": round(gross[0] / gross[-1] - 1, 4),
            "chosen_rank": 1 + sum(1 for v in gross if v > float(d["decimal_odds"])),
            "chosen_gap_to_best": round(float(d["decimal_odds"]) / gross[0] - 1, 4),
            "best_net_book": best_net_book, "best_net_odds": round(nets[best_net_book], 4),
            "best_net_quote_age_min": age.get(best_net_book, ""),
            "chosen_net_odds": round(nets.get(chosen, float("nan")), 4) if chosen in nets else "",
            "exchange_back": back, "exchange_lay": lay,
            "exchange_spread_ticks_pct": round(lay / back - 1, 4) if back and lay else "",
            "chosen_is_exchange": chosen in exch, "commission_unknown_books": ";".join(b for b in prices if b in exch and comm.get(b) is None)})
    fb = sorted((repo / "research_shadow/h1_devig").glob("*.csv")) if (repo / "research_shadow/h1_devig").exists() else []
    n_fb = sum(len(read(p)) for p in fb)

    def med(k, rs):
        v = [float(r[k]) for r in rs if r[k] not in ("", None)]
        return round(statistics.median(v), 4) if v else None
    summary = {"tennis_rows": len(rows), "paper_bet_rows": sum(r["decision"] == "PAPER_BET" for r in rows),
               "median_n_books": med("n_books", rows), "median_dispersion": med("dispersion", rows),
               "median_chosen_gap_to_best": med("chosen_gap_to_best", rows),
               "share_chosen_is_best": round(sum(r["chosen_rank"] == 1 for r in rows) / len(rows), 3) if rows else None,
               "median_exchange_spread": med("exchange_spread_ticks_pct", rows),
               "share_best_net_is_exchange": round(sum(r["best_net_book"] in exch for r in rows) / len(rows), 3) if rows else None,
               "n_chosen_exchange_but_sportsbook_better_net": sum(
                   r["chosen_is_exchange"] and r["best_net_book"] not in exch and r["chosen_net_odds"] != "" and r["best_net_odds"] > r["chosen_net_odds"] for r in rows),
               "median_best_net_quote_age_min": med("best_net_quote_age_min", rows),
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
