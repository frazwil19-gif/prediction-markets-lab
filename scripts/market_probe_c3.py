"""Market availability probe C3: NBA spreads/totals and tennis game handicap/total games at UK books.

Answers, before any engine is built: which UK books offer the market, how often, and how far their lines/prices
disagree. Research only; config/market_probe_c3.yaml holds dates, caps and the pre-registered kill criteria.
Output: research_shadow/market_probe_c3/quotes.csv (one row per book x market x outcome) and summary.json.
"""
from __future__ import annotations

import csv
import json
import sys
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path

import yaml

from prediction_markets_lab.ops import credit_ledger as CL
from prediction_markets_lab.ops import football_coverage as FC

REPO = Path(__file__).resolve().parents[1]
CONSUMER = "market_probe_c3"
BASE = "research_shadow/market_probe_c3"
FIELDS = ["probe", "captured_at", "sport_key", "event_id", "commence_time", "home", "away", "bookmaker", "market",
          "outcome", "point", "price", "last_update"]


def _ts(s: str) -> datetime:
    d = datetime.fromisoformat(str(s).replace("Z", "+00:00"))
    return d if d.tzinfo else d.replace(tzinfo=timezone.utc)


def _read(p: Path) -> list[dict]:
    if not p.exists():
        return []
    with p.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def rows_from(raw: list, probe: str, key: str, now: datetime) -> list[dict]:
    out = []
    for e in raw if isinstance(raw, list) else []:
        for b in e.get("bookmakers", []):
            for m in b.get("markets", []):
                for o in m.get("outcomes", []):
                    out.append({"probe": probe, "captured_at": now.isoformat(), "sport_key": key, "event_id": e.get("id"),
                                "commence_time": e.get("commence_time"), "home": e.get("home_team"), "away": e.get("away_team"),
                                "bookmaker": b.get("key"), "market": m.get("key"), "outcome": o.get("name"),
                                "point": o.get("point"), "price": o.get("price"), "last_update": m.get("last_update")})
    return out


def summarise(rows: list[dict], kill: dict) -> dict:
    """Per probe x market: events, UK books per event, share of events with >= min books, main-line dispersion."""
    out: dict = {}
    by = defaultdict(lambda: defaultdict(lambda: defaultdict(set)))
    lines = defaultdict(lambda: defaultdict(list))
    for r in rows:
        if r["bookmaker"].startswith(("betfair_ex", "matchbook", "smarkets")):
            continue
        by[(r["probe"], r["market"])][r["event_id"]][r["bookmaker"]].add(r["outcome"])
        if r["point"] not in (None, ""):
            lines[(r["probe"], r["market"])][(r["event_id"], r["bookmaker"])].append(float(r["point"]))
    for (probe, market), evs in by.items():
        n_books = [len(b) for b in evs.values()]
        ok = sum(n >= kill["min_uk_books_per_event"] for n in n_books)
        per_event: dict = defaultdict(list)
        for (eid, _book), pts in lines[(probe, market)].items():
            per_event[eid].append(max(abs(p) for p in pts))     # the book's main line (absolute)
        disp = [max(v) - min(v) for v in per_event.values() if len(v) >= 2]
        out[f"{probe}:{market}"] = {"events": len(evs), "median_uk_books": sorted(n_books)[len(n_books) // 2] if n_books else 0,
                                    "share_events_with_min_books": round(ok / len(evs), 3) if evs else 0.0,
                                    "events_with_line_disagreement": sum(d > 0 for d in disp), "max_line_spread": max(disp, default=0.0),
                                    "availability_kill": (ok / len(evs) if evs else 0) < kill["min_event_share"]}
    return out


def run(repo: Path, now: datetime, fetch_events=None, fetch_odds=None, list_sports=None) -> dict:
    from prediction_markets_lab.ingestion import the_odds_api_loader as L
    fetch_events = fetch_events or L.fetch_events_raw
    fetch_odds = fetch_odds or L.fetch_odds_raw
    cfg = yaml.safe_load((repo / "config/market_probe_c3.yaml").read_text())
    budget = FC.load_budget(repo / "config/api_budget.json")
    base = repo / BASE
    ledger, quotes = base / "credit_ledger.csv", base / "quotes.csv"
    led = CL.read(ledger)
    spent = sum(int(r.get("credits_charged") or 0) for r in led if r["consumer"] == CONSUMER and r["outcome"] == CL.PAID)
    today = now.strftime("%Y-%m-%d")
    done_today = {r["call"] for r in led if r["timestamp_utc"].startswith(today) and r["outcome"] == CL.PAID}
    summary: dict = {"spent_total": spent, "calls": []}
    for name, p in cfg["probes"].items():
        if not (_ts(p["active_from"]) <= now < _ts(p["active_to"])) or any(c.startswith(f"{name}:") for c in done_today):
            continue
        keys = list(p.get("sport_keys", []))
        if not keys and list_sports:
            keys = [k for k in list_sports() if k.startswith(p["sport_key_prefix"])]
        cost = len(p["markets"])
        best, best_n, hdr_ev = None, 0, {}
        api = L.TheOddsApiConfig(markets=tuple(p["markets"]), markets_by_sport={})
        for k in keys:
            hdr: dict = {}
            try:
                evs = fetch_events(k, api, hdr)
            except Exception:
                continue
            n = sum(now < _ts(e["commence_time"]) <= now + timedelta(hours=cfg["horizon_hours"]) for e in evs or [])
            if n > best_n:
                best, best_n, hdr_ev = k, n, hdr
        if not best:
            continue
        rem = hdr_ev.get("x-requests-remaining")
        import calendar
        days_left = calendar.monthrange(now.year, now.month)[1] - now.day + 1
        fl = FC.tier_floor(budget, 2, now) + days_left * 2.5
        if spent + cost > cfg["total_credit_cap"] or rem in (None, "") or float(rem) < fl:
            CL.append(ledger, CONSUMER, f"{name}:{best}", CL.SKIPPED_FLOOR, 0, cost, hdr_ev, f"cap/floor (remaining {rem}, floor {fl})", now=now)
            continue
        hdr = {}
        raw = fetch_odds(best, api, hdr)
        CL.append(ledger, CONSUMER, f"{name}:{best}", CL.PAID, int(hdr.get("x-requests-last") or cost), 0, hdr, "", now=now)
        spent += int(hdr.get("x-requests-last") or cost)
        new = rows_from(raw, name, best, now)
        base.mkdir(parents=True, exist_ok=True)
        header = not quotes.exists()
        with quotes.open("a", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=FIELDS)
            if header:
                w.writeheader()
            w.writerows(new)
        summary["calls"].append((name, best, len(new)))
    s = summarise(_read(quotes), cfg["kill_criteria"])
    if s or summary["calls"]:
        base.mkdir(parents=True, exist_ok=True)
        (base / "summary.json").write_text(json.dumps({"generated_at": now.isoformat(), "credits_spent_total": spent,
                                                       "by_market": s, "kill_criteria": cfg["kill_criteria"]}, indent=1))
    return summary


def _list_sports() -> list[str]:
    import urllib.parse
    from prediction_markets_lab.ingestion import the_odds_api_loader as L
    c = L.TheOddsApiConfig()
    url = f"{c.base_url}/v4/sports/?{urllib.parse.urlencode({'apiKey': c.resolve_api_key()})}"   # free endpoint
    return [s["key"] for s in L._get_json(url, "sports", c) if s.get("active")]


def main() -> int:
    print(run(REPO, datetime.now(timezone.utc), list_sports=_list_sports))
    return 0


if __name__ == "__main__":
    sys.exit(main())
