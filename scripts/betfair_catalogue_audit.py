"""Betfair Exchange READ-ONLY catalogue audit (football). No betting: only read methods are callable.

Purpose (directive "TURN THE RESEARCH PLATFORM INTO PROFIT ENGINES" §2A): enumerate the real marketTypeCodes Betfair
lists for the 10 project leagues, and measure for each market family (match odds, corners, bookings/cards, player
SOT, to score, player card, GK saves, other) the event coverage, number of markets, runner structure, two-sided
availability (back AND lay), spread, matched volume where returned, and time to kickoff.

RUN IT ON A UK MACHINE (Fraser's Mac). Betfair blocks API access from US IP addresses, which includes GitHub-hosted
runners. Credentials are read at run time and never written anywhere:
  BETFAIR_APP_KEY   (environment; the free DELAYED application key)
  BETFAIR_USERNAME  (environment)
  password          (typed at the prompt via getpass; or BETFAIR_PASSWORD if set in the environment)

  python scripts/betfair_catalogue_audit.py [--days 8] [--events-per-competition 10]   # 10-league coverage
  python scripts/betfair_catalogue_audit.py --discover                                 # schema discovery, any competition, <=36h
  python scripts/betfair_catalogue_audit.py --capture --max-hours-to-kickoff 6         # 10-league per-runner liquidity snapshot

Outputs:
  research/platform_v2/price_execution/betfair_audit/COVERAGE.json + COVERAGE.csv (aggregates only, committable)
  research/platform_v2/price_execution/betfair_audit/raw/<utc>.json (raw responses; gitignored, never committed)
"""
from __future__ import annotations

import argparse
import csv
import getpass
import json
import os
import statistics
import sys
import urllib.parse
import urllib.request
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Callable

REPO = Path(__file__).resolve().parents[1]
OUT = REPO / "research/platform_v2/price_execution/betfair_audit"
LOGIN_URL = "https://identitysso.betfair.com/api/login"
LOGOUT_URL = "https://identitysso.betfair.com/api/logout"
RPC_URL = "https://api.betfair.com/exchange/betting/json-rpc/v1"
FOOTBALL = "1"
READ_ONLY_METHODS = frozenset({"listCompetitions", "listMarketTypes", "listEvents", "listMarketCatalogue", "listMarketBook"})
CATALOGUE_MAX = 200          # listMarketCatalogue maxResults (no heavy projections)
BOOK_BATCH = 40              # listMarketBook ids per call with EX_BEST_OFFERS (weight 5 -> 200 point limit)
BOOK_SAMPLE_PER_FAMILY = 20  # markets priced per competition x family
TIMEOUT = 20

# project code -> name keywords (Betfair competition names are matched, never assumed; unmatched -> UNRESOLVED)
COMPETITIONS = {
    "E0": [["english", "premier league"]], "E1": [["english", "championship"]], "SC0": [["scottish", "premiership"]],
    "SP1": [["spanish", "la liga"], ["spanish", "laliga"]], "D1": [["german", "bundesliga"]], "I1": [["italian", "serie a"]],
    "F1": [["french", "ligue 1"]], "N1": [["dutch", "eredivisie"]], "P1": [["portuguese", "primeira"]],
    "B1": [["belgian", "first division"], ["belgian", "pro league"], ["belgian", "jupiler"]],
}
# codes/names that contain a family keyword but are NOT that family (found in the first live run, 2026-10-02)
NOT_FAMILY = ["BOTH_TEAMS_TO_SCORE", "TOP_GOALSCORER", "MATCH_ODDS_AND_", "WIN_TO_NIL"]
FAMILIES = [  # first match wins; tested on codes AND names (match_odds: exact code only)
    ("match_odds", []),
    ("player_sot", ["SHOTS_ON_TARGET", "SHOT_ON_TARGET", "PLAYER_SOT", "SOT"]),
    ("player_to_score", ["TO_SCORE", "GOALSCORER", "GOAL_SCORER", "SCORER"]),
    ("player_card", ["SHOWN_A_CARD", "PLAYER_CARD", "PLAYER_BOOKED", "TO_BE_CARDED"]),
    ("gk_saves", ["SAVES", "SAVE"]),
    ("corners", ["CORNER"]),
    ("bookings_cards", ["BOOKING", "CARDS", "CARD"]),
]
FAMILY_NAMES = [f for f, _ in FAMILIES] + ["other"]
EXCLUDE_COMPETITION_WORDS = ("women", "u21", "u23", "u19", "reserve", "beloften", "national division", "youth")
DEFAULT_MAX_HOURS = 36.0     # prop/corner markets are typically listed close to kickoff: sample only near events


def family_of(code: str, name: str = "") -> str:
    hay = f"{code} {name}".upper().replace(" ", "_")
    if code.upper() == "MATCH_ODDS" or name.strip().lower() == "match odds":
        return "match_odds"
    if any(x in hay for x in NOT_FAMILY):
        return "other"
    for fam, keys in FAMILIES:
        if any(k in hay for k in keys):
            return fam
    return "other"


def match_competitions(comps: list[dict]) -> dict[str, dict | None]:
    out = {}
    for code, alts in COMPETITIONS.items():
        hits = [c for c in comps if any(all(k in c["competition"]["name"].lower() for k in kw) for kw in alts)]
        hits = [h for h in hits if not any(x in h["competition"]["name"].lower() for x in EXCLUDE_COMPETITION_WORDS)]
        out[code] = max(hits, key=lambda c: c.get("marketCount", 0)) if hits else None
    return out


class Client:
    """Read-only JSON-RPC client. Any method outside READ_ONLY_METHODS raises before a request is built."""

    def __init__(self, app_key: str, token: str, transport: Callable[[str, bytes, dict], dict] | None = None):
        self._h = {"X-Application": app_key, "X-Authentication": token, "Content-Type": "application/json", "Accept": "application/json"}
        self._t = transport or _http
        self.calls = 0

    def call(self, method: str, params: dict) -> list | dict:
        if method not in READ_ONLY_METHODS:
            raise PermissionError(f"{method} is not a read-only method; refused")
        body = json.dumps({"jsonrpc": "2.0", "method": f"SportsAPING/v1.0/{method}", "params": params, "id": 1}).encode()
        self.calls += 1
        r = self._t(RPC_URL, body, self._h)
        if "error" in r:
            raise RuntimeError(f"{method}: {json.dumps(r['error'])[:300]}")
        return r["result"]


def _http(url: str, body: bytes, headers: dict) -> dict:
    req = urllib.request.Request(url, data=body, headers=headers, method="POST")
    with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
        return json.loads(r.read())


def login(app_key: str, username: str, password: str) -> str:
    data = urllib.parse.urlencode({"username": username, "password": password}).encode()
    req = urllib.request.Request(LOGIN_URL, data=data, method="POST",
                                 headers={"X-Application": app_key, "Accept": "application/json", "Content-Type": "application/x-www-form-urlencoded"})
    with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
        res = json.loads(r.read())
    if res.get("status") != "SUCCESS":
        raise RuntimeError(f"login failed: {res.get('error')}")   # error code only; never the credentials
    return res["token"]


def logout(app_key: str, token: str) -> None:
    req = urllib.request.Request(LOGOUT_URL, method="POST", headers={"X-Application": app_key, "X-Authentication": token, "Accept": "application/json"})
    try:
        urllib.request.urlopen(req, timeout=TIMEOUT).read()
    except Exception:
        pass


def book_stats(book: dict) -> dict:
    runners = book.get("runners", [])
    two = [r for r in runners if r.get("ex", {}).get("availableToBack") and r.get("ex", {}).get("availableToLay")]
    spreads = []
    for r in two:
        b, l = r["ex"]["availableToBack"][0]["price"], r["ex"]["availableToLay"][0]["price"]
        spreads.append(l / b - 1)
    return {"n_runners": len(runners), "n_two_sided": len(two), "all_two_sided": bool(runners) and len(two) == len(runners),
            "runner_two_sided_share": (len(two) / len(runners)) if runners else None,   # per-runner (player markets: 1 runner per player)
            "median_spread": statistics.median(spreads) if spreads else None, "total_matched": book.get("totalMatched"),
            "status": book.get("status"), "inplay": book.get("inplay")}


def classify(n_events: int, n_with: int, two_sided_share: float | None) -> str:
    if n_events == 0:
        return "UNRESOLVED"
    if n_with == 0:
        return "ABSENT"
    cov = n_with / n_events
    if cov >= 0.8 and (two_sided_share or 0) >= 0.5:
        return "GOOD COVERAGE"
    if cov >= 0.2:
        return "PARTIAL COVERAGE"
    return "RARE"


def audit(client: Client, now: datetime, days: int, per_comp: int, max_hours: float = DEFAULT_MAX_HOURS) -> tuple[dict, dict]:
    raw: dict = {"generated_at": now.isoformat()}
    comps = client.call("listCompetitions", {"filter": {"eventTypeIds": [FOOTBALL]}})
    raw["competitions"] = comps
    matched = match_competitions(comps)
    window = {"from": now.isoformat(), "to": (now + timedelta(days=days)).isoformat()}
    cov: dict = {"generated_at": now.isoformat(), "window_days": days, "events_sampled_per_competition": per_comp, "competitions": {}}
    for code, comp in matched.items():
        entry: dict = {"betfair_competition": comp["competition"] if comp else None, "families": {}}
        cov["competitions"][code] = entry
        if not comp:
            entry["families"] = {f: {"classification": "UNRESOLVED"} for f in FAMILY_NAMES}
            continue
        cid = comp["competition"]["id"]
        mtypes = client.call("listMarketTypes", {"filter": {"competitionIds": [cid]}})
        events = client.call("listEvents", {"filter": {"competitionIds": [cid], "marketStartTime": window}})
        n_listed = len(events)
        near = [e for e in events if e["event"].get("openDate") and
                (datetime.fromisoformat(e["event"]["openDate"].replace("Z", "+00:00")) - now).total_seconds() / 3600 <= max_hours]
        events = sorted(near, key=lambda e: e["event"].get("openDate", ""))[:per_comp]
        entry.update({"market_types": [{"code": m["marketType"], "family": family_of(m["marketType"]), "marketCount": m.get("marketCount")} for m in mtypes],
                      "n_events_sampled": len(events), "n_events_listed_in_window": n_listed, "max_hours_to_kickoff": max_hours})
        raw.setdefault("by_competition", {})[code] = {"market_types": mtypes, "events": events}
        if not events:
            entry["families"] = {f: {"classification": "UNRESOLVED", "note": f"no event within {max_hours:g}h of kickoff ({n_listed} listed in window)"}
                                 for f in FAMILY_NAMES}
            continue
        cats = []
        for e in events:
            cats += client.call("listMarketCatalogue", {"filter": {"eventIds": [e["event"]["id"]]}, "maxResults": CATALOGUE_MAX,
                                                        "marketProjection": ["MARKET_START_TIME", "MARKET_DESCRIPTION", "RUNNER_DESCRIPTION", "EVENT"]})
        raw["by_competition"][code]["catalogue"] = cats
        by_fam: dict = defaultdict(list)
        for m in cats:
            by_fam[family_of(m.get("description", {}).get("marketType", "") if isinstance(m.get("description"), dict) else "", m.get("marketName", ""))].append(m)
        books: dict = {}
        for fam, ms in by_fam.items():
            ids = [m["marketId"] for m in ms[:BOOK_SAMPLE_PER_FAMILY]]
            for i in range(0, len(ids), BOOK_BATCH):
                for b in client.call("listMarketBook", {"marketIds": ids[i:i + BOOK_BATCH], "priceProjection": {"priceData": ["EX_BEST_OFFERS"]}}):
                    books[b["marketId"]] = b
        raw["by_competition"][code]["books"] = list(books.values())
        for fam in FAMILY_NAMES:
            ms = by_fam.get(fam, [])
            ev_with = {m["event"]["id"] for m in ms if m.get("event")}
            st = [book_stats(books[m["marketId"]]) for m in ms if m["marketId"] in books]
            two = [s["all_two_sided"] for s in st]
            sp = [s["median_spread"] for s in st if s["median_spread"] is not None]
            tm = [s["total_matched"] for s in st if s["total_matched"] is not None]
            ttk = [(datetime.fromisoformat(m["marketStartTime"].replace("Z", "+00:00")) - now).total_seconds() / 3600 for m in ms if m.get("marketStartTime")]
            share = (sum(two) / len(two)) if two else None
            entry["families"][fam] = {
                "n_markets": len(ms), "n_events_with_market": len(ev_with), "n_events_sampled": len(events),
                "market_names": sorted({m.get("marketName", "") for m in ms})[:25],
                "runner_counts": sorted({len(m.get("runners", [])) for m in ms}),
                "n_books_sampled": len(st), "two_sided_share": round(share, 3) if share is not None else None,
                "median_spread": round(statistics.median(sp), 4) if sp else None,
                "median_total_matched": round(statistics.median(tm), 2) if tm else None,
                "hours_to_kickoff_range": [round(min(ttk), 1), round(max(ttk), 1)] if ttk else None,
                "classification": classify(len(events), len(ev_with), share)}
    cov["api_calls"] = client.calls
    cov["delayed_key_note"] = "Delayed application key: prices are delayed and volume fields may be absent; sufficient for coverage/structure research, not for execution."
    return cov, raw


DISCOVER_EVENTS = 25         # busiest near-kickoff football events sampled in --discover mode
INTEREST = ("corners", "bookings_cards", "player_sot", "player_to_score", "player_card", "gk_saves")


def discover(client: Client, now: datetime, max_hours: float, n_events: int = DISCOVER_EVENTS) -> tuple[dict, dict]:
    """SCHEMA DISCOVERY (any competition): which marketTypeCodes / runner structures exist on football events
    kicking off within `max_hours`. Not evidence of coverage for the project's leagues."""
    window = {"from": now.isoformat(), "to": (now + timedelta(hours=max_hours)).isoformat()}
    events = client.call("listEvents", {"filter": {"eventTypeIds": [FOOTBALL], "marketStartTime": window}})
    events = sorted(events, key=lambda e: -int(e.get("marketCount") or 0))[:n_events]
    raw: dict = {"generated_at": now.isoformat(), "events": events, "catalogue": []}
    codes: dict = {}
    for e in events:
        cat = client.call("listMarketCatalogue", {"filter": {"eventIds": [e["event"]["id"]]}, "maxResults": CATALOGUE_MAX,
                                                  "marketProjection": ["MARKET_START_TIME", "MARKET_DESCRIPTION", "RUNNER_DESCRIPTION", "EVENT", "COMPETITION"]})
        raw["catalogue"] += cat
        for m in cat:
            code = (m.get("description") or {}).get("marketType", "")
            c = codes.setdefault(code, {"family": family_of(code, m.get("marketName", "")), "events": set(), "competitions": set(),
                                        "market_names": set(), "runner_counts": set(), "example_runners": [], "hours": [], "market_ids": []})
            c["events"].add(e["event"]["id"])
            c["competitions"].add((m.get("competition") or {}).get("name", "?"))
            c["market_names"].add(m.get("marketName", ""))
            c["runner_counts"].add(len(m.get("runners", [])))
            if not c["example_runners"]:
                c["example_runners"] = [r.get("runnerName", "") for r in m.get("runners", [])][:8]
            if m.get("marketStartTime"):
                c["hours"].append((datetime.fromisoformat(m["marketStartTime"].replace("Z", "+00:00")) - now).total_seconds() / 3600)
            c["market_ids"].append(m["marketId"])
    ids = [mid for c in codes.values() if c["family"] in INTEREST for mid in c["market_ids"][:5]]
    books = {}
    for i in range(0, len(ids), BOOK_BATCH):
        for b in client.call("listMarketBook", {"marketIds": ids[i:i + BOOK_BATCH], "priceProjection": {"priceData": ["EX_BEST_OFFERS"]}}):
            books[b["marketId"]] = b
    raw["books"] = list(books.values())
    out = {"generated_at": now.isoformat(), "mode": "SCHEMA_DISCOVERY (any competition; NOT coverage evidence for project leagues)",
           "max_hours_to_kickoff": max_hours, "n_events_sampled": len(events),
           "events": [{"name": e["event"].get("name"), "openDate": e["event"].get("openDate"), "marketCount": e.get("marketCount")} for e in events],
           "market_types": {}}
    for code, c in sorted(codes.items(), key=lambda kv: (kv[1]["family"] == "other", kv[0])):
        st = [book_stats(books[mid]) for mid in c["market_ids"] if mid in books]
        two = [s["all_two_sided"] for s in st]
        out["market_types"][code] = {"family": c["family"], "n_events": len(c["events"]), "n_markets": len(c["market_ids"]),
                                     "competitions": sorted(c["competitions"])[:10], "market_names": sorted(c["market_names"])[:15],
                                     "runner_counts": sorted(c["runner_counts"]), "example_runners": c["example_runners"],
                                     "hours_to_kickoff_range": [round(min(c["hours"]), 1), round(max(c["hours"]), 1)] if c["hours"] else None,
                                     "n_books_sampled": len(st), "two_sided_share": round(sum(two) / len(two), 3) if two else None,
                                     "runner_two_sided_share": round(statistics.mean(s["runner_two_sided_share"] for s in st if s["runner_two_sided_share"] is not None), 3)
                                     if any(s["runner_two_sided_share"] is not None for s in st) else None,
                                     "median_total_matched": statistics.median([s["total_matched"] for s in st if s["total_matched"] is not None])
                                     if any(s["total_matched"] is not None for s in st) else None,
                                     "median_spread": round(statistics.median([s["median_spread"] for s in st if s["median_spread"] is not None]), 4)
                                     if any(s["median_spread"] is not None for s in st) else None}
    out["families_found"] = sorted({v["family"] for v in out["market_types"].values()} - {"other"})
    out["api_calls"] = client.calls
    return out, raw


CAPTURE_FAMILIES = ("corners", "player_sot", "bookings_cards")
CAPTURE_FIELDS = ["capture_ts", "competition", "event", "kickoff", "mins_to_kickoff", "market_id", "market_type", "family", "market_name",
                  "status", "inplay", "number_of_winners", "betting_type", "market_total_matched", "runner", "back", "back_size", "lay", "lay_size", "spread", "side_status",
                  "last_traded"]
CORNERS_SPREAD_GATE = 0.10   # pre-registered corners A/B/C rule (research/platform_v2/corners_abc/PREREGISTRATION.md §4) -- reported, never changed


def _q(xs: list[float], q: float) -> float | None:
    return round(float(statistics.quantiles(xs, n=100)[int(q * 100) - 1]), 4) if len(xs) >= 2 else (round(xs[0], 4) if xs else None)


def capture(client: Client, now: datetime, max_hours: float) -> tuple[dict, list[dict]]:
    """Per-runner liquidity capture for the project's leagues (corners, player SOT, cards) for events within
    max_hours. Returns (aggregate summary -- committable, per-runner rows -- private/raw)."""
    comps = match_competitions(client.call("listCompetitions", {"filter": {"eventTypeIds": [FOOTBALL]}}))
    window = {"from": (now - timedelta(minutes=5)).isoformat(), "to": (now + timedelta(hours=max_hours)).isoformat()}
    rows: list[dict] = []
    for code, comp in comps.items():
        if not comp:
            continue
        events = client.call("listEvents", {"filter": {"competitionIds": [comp["competition"]["id"]], "marketStartTime": window}})
        for e in events:
            cat = client.call("listMarketCatalogue", {"filter": {"eventIds": [e["event"]["id"]]}, "maxResults": CATALOGUE_MAX,
                                                      "marketProjection": ["MARKET_START_TIME", "MARKET_DESCRIPTION", "RUNNER_DESCRIPTION", "EVENT"]})
            want = {m["marketId"]: m for m in cat if family_of((m.get("description") or {}).get("marketType", ""), m.get("marketName", "")) in CAPTURE_FAMILIES}
            ids = list(want)
            for i in range(0, len(ids), BOOK_BATCH):
                for b in client.call("listMarketBook", {"marketIds": ids[i:i + BOOK_BATCH], "priceProjection": {"priceData": ["EX_BEST_OFFERS"]}}):
                    m = want[b["marketId"]]
                    names = {r["selectionId"]: r.get("runnerName", "") for r in m.get("runners", [])}
                    ko = datetime.fromisoformat(m["marketStartTime"].replace("Z", "+00:00"))
                    code_ = (m.get("description") or {}).get("marketType", "")
                    for r in b.get("runners", []):
                        atb, atl = r.get("ex", {}).get("availableToBack") or [], r.get("ex", {}).get("availableToLay") or []
                        back, lay = (atb[0] if atb else {}), (atl[0] if atl else {})
                        both = bool(atb and atl)
                        rows.append({"capture_ts": now.isoformat(), "competition": code, "event": m.get("event", {}).get("name", e["event"].get("name")),
                                     "kickoff": m["marketStartTime"], "mins_to_kickoff": round((ko - now).total_seconds() / 60, 1), "market_id": b["marketId"],
                                     "market_type": code_, "family": family_of(code_, m.get("marketName", "")), "market_name": m.get("marketName", ""),
                                     "status": b.get("status"), "inplay": b.get("inplay"), "number_of_winners": b.get("numberOfWinners"),
                                     "betting_type": (m.get("description") or {}).get("bettingType"), "market_total_matched": b.get("totalMatched"),
                                     "runner": names.get(r.get("selectionId"), str(r.get("selectionId"))), "back": back.get("price"), "back_size": back.get("size"),
                                     "lay": lay.get("price"), "lay_size": lay.get("size"),
                                     "spread": round(lay["price"] / back["price"] - 1, 5) if both else None,
                                     "side_status": "BOTH" if both else ("BACK_ONLY" if atb else ("LAY_ONLY" if atl else "NONE")),
                                     "last_traded": r.get("lastPriceTraded")})
    return summarise_capture(rows, now, max_hours), rows


def summarise_capture(rows: list[dict], now: datetime, max_hours: float) -> dict:
    out: dict = {"capture_ts": now.isoformat(), "max_hours_to_kickoff": max_hours, "n_runner_rows": len(rows),
                 "note": "Aggregates only; per-runner prices stay private (raw/). Liquidity description, not an execution rule.", "groups": {}}
    groups: dict = defaultdict(list)
    for r in rows:
        groups[(r["competition"], r["market_type"])].append(r)
    for (comp, mt), rs in sorted(groups.items()):
        both = [r for r in rs if r["side_status"] == "BOTH"]
        sp = [r["spread"] for r in both]
        mkt = {r["market_id"]: r["market_total_matched"] for r in rs}
        matched = [v for v in mkt.values() if v is not None]
        g = {"family": rs[0]["family"], "events": len({r["event"] for r in rs}), "markets": len(mkt), "runners": len(rs),
             "both": len(both), "back_only": sum(r["side_status"] == "BACK_ONLY" for r in rs), "lay_only": sum(r["side_status"] == "LAY_ONLY" for r in rs),
             "none": sum(r["side_status"] == "NONE" for r in rs),
             "spread_p25_p50_p75": [_q(sp, .25), _q(sp, .5), _q(sp, .75)] if sp else None,
             "back_size_p25_p50_p75": [_q(bs, .25), _q(bs, .5), _q(bs, .75)] if (bs := [r["back_size"] for r in rs if r["back_size"] is not None]) else None,
             "lay_size_p25_p50_p75": [_q(ls, .25), _q(ls, .5), _q(ls, .75)] if (ls := [r["lay_size"] for r in rs if r["lay_size"] is not None]) else None,
             "two_sided_share": round(len(both) / len(rs), 4) if rs else None,
             "number_of_winners": sorted({r["number_of_winners"] for r in rs if r["number_of_winners"] is not None}),
             "market_matched_median_max": [round(statistics.median(matched), 2), round(max(matched), 2)] if matched else None,
             "market_matched_p25_p50_p75": [_q(matched, .25), _q(matched, .5), _q(matched, .75)] if matched else None,
             "mins_to_kickoff_range": [min(r["mins_to_kickoff"] for r in rs), max(r["mins_to_kickoff"] for r in rs)]}
        if g["family"] == "corners":
            per_market = defaultdict(list)
            for r in rs:
                per_market[r["market_id"]].append(r)
            ok = [all(x["side_status"] == "BOTH" and x["spread"] <= CORNERS_SPREAD_GATE for x in v) for v in per_market.values()]
            g["markets_passing_preregistered_10pct_gate"] = f"{sum(ok)}/{len(ok)}"
        out["groups"][f"{comp}|{mt}"] = g
    return out


def write_outputs(cov: dict, raw: dict, now: datetime) -> None:
    (OUT / "raw").mkdir(parents=True, exist_ok=True)
    (OUT / "raw" / f"{now.strftime('%Y%m%dT%H%M%SZ')}.json").write_text(json.dumps(raw, default=str))
    (OUT / "COVERAGE.json").write_text(json.dumps(cov, indent=1, default=str) + "\n")
    with (OUT / "COVERAGE.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["competition", "family", "classification", "n_events_sampled", "n_events_with_market", "n_markets", "two_sided_share",
                    "median_spread", "median_total_matched", "market_names"])
        for code, e in cov["competitions"].items():
            for fam, s in e["families"].items():
                w.writerow([code, fam, s.get("classification"), s.get("n_events_sampled", ""), s.get("n_events_with_market", ""), s.get("n_markets", ""),
                            s.get("two_sided_share", ""), s.get("median_spread", ""), s.get("median_total_matched", ""), "; ".join(s.get("market_names", []))])


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--days", type=int, default=8)
    ap.add_argument("--events-per-competition", type=int, default=10)
    ap.add_argument("--max-hours-to-kickoff", type=float, default=DEFAULT_MAX_HOURS)
    ap.add_argument("--capture", action="store_true", help="per-runner liquidity capture (corners, player SOT, cards) for the 10 leagues' events within --max-hours-to-kickoff")
    ap.add_argument("--discover", action="store_true", help="schema discovery on the busiest football events within --max-hours-to-kickoff (any competition)")
    a = ap.parse_args()
    app_key, user = os.environ.get("BETFAIR_APP_KEY"), os.environ.get("BETFAIR_USERNAME")
    if not app_key or not user:
        print("Set BETFAIR_APP_KEY and BETFAIR_USERNAME in this terminal first (values are never written).")
        return 2
    pw = os.environ.get("BETFAIR_PASSWORD") or getpass.getpass("Betfair password (not stored): ")
    token = login(app_key, user, pw)
    del pw
    now = datetime.now(timezone.utc)
    try:
        if a.capture:
            summ, cap_rows = capture(Client(app_key, token), now, a.max_hours_to_kickoff)
        elif a.discover:
            sch, raw = discover(Client(app_key, token), now, a.max_hours_to_kickoff)
        else:
            cov, raw = audit(Client(app_key, token), now, a.days, a.events_per_competition, a.max_hours_to_kickoff)
    finally:
        logout(app_key, token)
    if a.capture:
        stamp = now.strftime('%Y%m%dT%H%M%SZ')
        (OUT / "raw").mkdir(parents=True, exist_ok=True)
        with (OUT / "raw" / f"capture_{stamp}.csv").open("w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=CAPTURE_FIELDS)
            w.writeheader()
            w.writerows(cap_rows)
        (OUT / f"CAPTURE_SUMMARY_{stamp}.json").write_text(json.dumps(summ, indent=1, default=str) + "\n")
        for k, g in summ["groups"].items():
            if g["family"] in ("corners", "player_sot"):
                print(f"  {k:40s} events={g['events']} runners={g['runners']} both={g['both']} back-only={g['back_only']} "
                      f"spread(p50)={(g['spread_p25_p50_p75'] or [None, None])[1]} matched(med,max)={g['market_matched_median_max']}"
                      + (f" gate10%={g['markets_passing_preregistered_10pct_gate']}" if 'markets_passing_preregistered_10pct_gate' in g else ""))
        print(f"runner rows: {summ['n_runner_rows']}; summary written: CAPTURE_SUMMARY_{stamp}.json (per-runner prices stay in raw/)")
        return 0
    if a.discover:
        (OUT / "raw").mkdir(parents=True, exist_ok=True)
        (OUT / "raw" / f"discover_{now.strftime('%Y%m%dT%H%M%SZ')}.json").write_text(json.dumps(raw, default=str))
        (OUT / "SCHEMA_DISCOVERY.json").write_text(json.dumps(sch, indent=1, default=str) + "\n")
        print("families found:", sch["families_found"] or "none")
        for code, v in sch["market_types"].items():
            if v["family"] != "other":
                print(f"  {code:28s} {v['family']:16s} events={v['n_events']} names={v['market_names'][:3]} "
                      f"markets-fully-two-sided={v['two_sided_share']} runners-two-sided={v['runner_two_sided_share']} median-matched={v['median_total_matched']}")
        print(f"api calls: {sch['api_calls']}; written to {OUT / 'SCHEMA_DISCOVERY.json'}")
        return 0
    write_outputs(cov, raw, now)
    for code, e in cov["competitions"].items():
        print(code, {f: s.get("classification") for f, s in e["families"].items()})
    print(f"api calls: {cov['api_calls']}; coverage written to {OUT / 'COVERAGE.csv'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
