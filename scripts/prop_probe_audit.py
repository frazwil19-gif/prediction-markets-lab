"""Audit a saved prop-price probe response (no network). Pre-registered metrics and Gate 0 rules:
research/platform_v2/props_c1/price_probe_2/GATE0_PREREGISTRATION.md.

Usage: python scripts/prop_probe_audit.py research_shadow/prop_price_probe/probe2  -> writes AUDIT.json + per_quote.csv there.
"""
from __future__ import annotations

import csv
import json
import statistics
import sys
from collections import defaultdict
from pathlib import Path

import yaml

REPO = Path(__file__).resolve().parents[1]
MARKETS = ("alternate_totals_corners", "alternate_totals_cards")
KNOWN_EXCHANGES = ("betfair_ex_uk", "betfair_ex_eu", "smarkets", "matchbook")
ROBUST_MIN_BOOKS = 3


def quotes(raw: dict) -> list[dict]:
    rows = []
    for b in raw.get("bookmakers", []):
        for m in b.get("markets", []):
            if m.get("key") not in MARKETS:
                continue
            by_line: dict[float, dict] = defaultdict(dict)
            for o in m.get("outcomes", []):
                if o.get("point") is not None and str(o.get("name", "")).lower() in ("over", "under"):
                    by_line[float(o["point"])][o["name"].lower()] = float(o["price"])
            for line, sides in sorted(by_line.items()):
                r = {"bookmaker": b["key"], "title": b.get("title", ""), "market": m["key"], "line": line,
                     "over": sides.get("over"), "under": sides.get("under"), "last_update": m.get("last_update") or b.get("last_update", ""),
                     "event_commence": raw.get("commence_time", ""), "two_sided": "over" in sides and "under" in sides}
                if r["two_sided"]:
                    io, iu = 1 / r["over"], 1 / r["under"]
                    r.update({"raw_p_over": round(io, 5), "raw_p_under": round(iu, 5), "overround": round(io + iu - 1, 5),
                              "fair_p_over": round(io / (io + iu), 5), "fair_p_under": round(iu / (io + iu), 5)})
                rows.append(r)
    return rows


def audit(raw: dict, commission: dict) -> dict:
    q = quotes(raw)
    exch_present = sorted({r["bookmaker"] for r in q if r["bookmaker"] in KNOWN_EXCHANGES or "_ex_" in r["bookmaker"]})
    out: dict = {"n_bookmakers_in_response": len(raw.get("bookmakers", [])), "exchanges_present": exch_present,
                 "exchange_commission": {e: commission.get(e) for e in exch_present}, "markets": {}}
    for mk in MARKETS:
        rows = [r for r in q if r["market"] == mk]
        lines = {}
        for line in sorted({r["line"] for r in rows}):
            lr = [r for r in rows if r["line"] == line]
            two = [r for r in lr if r["two_sided"]]
            ov = [r["over"] for r in lr if r["over"]]
            un = [r["under"] for r in lr if r["under"]]
            fp = [r["fair_p_over"] for r in two]
            lines[str(line)] = {
                "n_books": len(lr), "n_two_sided": len(two),
                "best_over": max(ov) if ov else None, "median_over": statistics.median(ov) if ov else None,
                "best_under": max(un) if un else None, "median_under": statistics.median(un) if un else None,
                "over_dispersion_best_worst": round(max(ov) / min(ov) - 1, 4) if len(ov) > 1 else None,
                "under_dispersion_best_worst": round(max(un) / min(un) - 1, 4) if len(un) > 1 else None,
                "median_fair_p_over": round(statistics.median(fp), 4) if fp else None,
                "fair_p_over_range": [min(fp), max(fp)] if fp else None,
                "median_overround": round(statistics.median(r["overround"] for r in two), 4) if two else None}
        def executable(r: dict) -> bool:
            is_ex = r["bookmaker"] in KNOWN_EXCHANGES or "_ex_" in r["bookmaker"]
            return not is_ex or commission.get(r["bookmaker"]) is not None
        exec_two = [r for r in rows if r["two_sided"] and executable(r)]
        best_line_n = max((v["n_two_sided"] for v in lines.values()), default=0)
        if not rows:
            gate = "C"
        elif not exec_two:
            gate = "B"
        else:
            gate = "A" if best_line_n >= ROBUST_MIN_BOOKS else "A (thin)"
        out["markets"][mk] = {"n_quotes": len(rows), "bookmakers": sorted({r["bookmaker"] for r in rows}), "lines": lines,
                              "max_two_sided_books_on_one_line": best_line_n, "gate0": gate}
    out["_per_quote"] = q
    return out


def main(d: str) -> int:
    path = Path(d)
    raw = json.loads((path / "raw_event_odds.json").read_text())
    comm = yaml.safe_load((REPO / "config/bet_selection_v2.yaml").read_text())["commission"]
    a = audit(raw, comm)
    per = a.pop("_per_quote")
    if per:
        keys = sorted({k for r in per for k in r}, key=lambda k: list(per[0]).index(k) if k in per[0] else 99)
        with (path / "per_quote.csv").open("w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=keys)
            w.writeheader()
            w.writerows(per)
    (path / "AUDIT.json").write_text(json.dumps(a, indent=1) + "\n")
    print(json.dumps(a, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1]))
