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

  python scripts/betfair_catalogue_audit.py [--days 8] [--events-per-competition 10]

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
        cov, raw = audit(Client(app_key, token), now, a.days, a.events_per_competition, a.max_hours_to_kickoff)
    finally:
        logout(app_key, token)
    write_outputs(cov, raw, now)
    for code, e in cov["competitions"].items():
        print(code, {f: s.get("classification") for f, s in e["families"].items()})
    print(f"api calls: {cov['api_calls']}; coverage written to {OUT / 'COVERAGE.csv'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
