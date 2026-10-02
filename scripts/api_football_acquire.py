"""API-Football EPL player-match acquisition for Player SOT Cycle 2 (pre-registered: player_sot/cycle2/PREREGISTRATION.md).

RUN ON FRASER'S MAC ONLY (standard library only; no installs). Data stays PRIVATE in data/private/api_football/
(gitignored) and is never committed or published. Decision record: research/platform_v2/player_sot/cycle2/DATA_DECISION.md.

  export API_FOOTBALL_KEY='<key>'          # never written anywhere
  python3 scripts/api_football_acquire.py

Requests: per season 1 x /fixtures?league=39&season=S&status=FT-AET-PEN, then 1 x /fixtures/players?fixture=<id> per
fixture (both teams' players in one response). The FREE plan does not allow /fixtures?ids= (confirmed 2026-10-02), so
this is ~380 requests per season, ~1,143 for 2022-2024: about 12 daily runs at the free 100/day. Throttled; stops
before the daily allowance runs out; resumable -- run the same command once a day until it prints "done".
"""
from __future__ import annotations

import csv
import gzip
import json
import os
import sys
import time
import urllib.request
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
OUT = REPO / "data/private/api_football"
BASE = "https://v3.football.api-sports.io"
LEAGUE = 39                      # English Premier League
SEASONS = (2022, 2023, 2024)     # 2024 required by the cycle-2 sample rule (2023-24 alone < 8,700 eligible rows)
PAUSE_SECONDS = 7.0              # <= ~8.5 requests/minute
MIN_REMAINING = 5                # stop before the daily allowance is exhausted
ROLE = {"G": "GK", "D": "DF", "M": "MD", "F": "FW"}
FIELDS = ["source", "competition", "season", "match_id", "date", "team_id", "opponent_id", "home", "player_id", "player_name",
          "role", "starter", "minute_in", "minute_out", "minutes", "shots", "sot", "goals"]


def get(path: str, key: str) -> tuple[dict, dict]:
    req = urllib.request.Request(BASE + path, headers={"x-apisports-key": key})
    with urllib.request.urlopen(req, timeout=60) as r:
        hdr = {k.lower(): v for k, v in r.headers.items()}
        body = json.loads(r.read())
    if body.get("errors"):
        raise RuntimeError(f"API error for {path.split('?')[0]}: {body['errors']}")   # message only; the key is never printed
    return body, hdr


def save(path: Path, obj: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with gzip.open(path, "wt", encoding="utf-8") as f:
        json.dump(obj, f)


def load(path: Path) -> dict:
    with gzip.open(path, "rt", encoding="utf-8") as f:
        return json.load(f)


def rows_from_fixture(fx: dict, season: int) -> list[dict]:
    """fx: a fixture object with 'fixture', 'teams' and 'players' (the /fixtures/players response)."""
    return _rows(fx, season)


def _rows(fx: dict, season: int) -> list[dict]:
    """Canonical player-match rows (same schema as research_shadow/player_sot.FIELDS). Players with no minutes are
    unused substitutes and are skipped. minute_in/out are approximations from minutes (no event parsing)."""
    f, teams = fx["fixture"], fx["teams"]
    home, away = teams["home"]["id"], teams["away"]["id"]
    out = []
    for team_block in fx.get("players") or []:
        tid = team_block["team"]["id"]
        for p in team_block.get("players") or []:
            st = (p.get("statistics") or [{}])[0]
            g = st.get("games") or {}
            mins = g.get("minutes")
            if not mins:
                continue
            starter = not g.get("substitute", True)
            shots = (st.get("shots") or {})
            out.append({"source": "api_football", "competition": "EPL", "season": f"{season}-{str(season + 1)[2:]}", "match_id": f["id"],
                        "date": f["date"][:10], "team_id": tid, "opponent_id": away if tid == home else home, "home": tid == home,
                        "player_id": p["player"]["id"], "player_name": p["player"].get("name", ""), "role": ROLE.get(g.get("position"), "UNK"),
                        "starter": starter, "minute_in": 0 if starter else max(90 - int(mins), 0), "minute_out": min(int(mins), 90) if starter else 90,
                        "minutes": int(mins), "shots": int(shots.get("total") or 0), "sot": int(shots.get("on") or 0),
                        "goals": int(((st.get("goals") or {}).get("total")) or 0)})
    return out


def main() -> int:
    key = os.environ.get("API_FOOTBALL_KEY")
    if not key:
        print("Set API_FOOTBALL_KEY in this terminal first (export API_FOOTBALL_KEY='...'). The key is never written anywhere.")
        return 2
    used = 0
    for season in SEASONS:
        list_path = OUT / "raw" / f"fixtures_{LEAGUE}_{season}.json.gz"
        if not list_path.exists():
            body, hdr = get(f"/fixtures?league={LEAGUE}&season={season}&status=FT-AET-PEN", key)
            used += 1
            save(list_path, body)
            print(f"season {season}: {body.get('results')} finished fixtures listed (remaining today: {hdr.get('x-ratelimit-requests-remaining')})")
            time.sleep(PAUSE_SECONDS)
        fixtures = sorted(load(list_path)["response"], key=lambda fx: fx["fixture"]["id"])
        for n, fx in enumerate(fixtures, 1):
            p = OUT / "raw" / f"players_{season}_{fx['fixture']['id']}.json.gz"
            if p.exists():
                continue
            body, hdr = get(f"/fixtures/players?fixture={fx['fixture']['id']}", key)
            used += 1
            save(p, {"fixture": fx["fixture"], "teams": fx["teams"], "players": body.get("response", [])})
            rem = int(hdr.get("x-ratelimit-requests-remaining") or 0)
            if n % 20 == 0 or rem < MIN_REMAINING:
                print(f"season {season}: {n}/{len(fixtures)} fixtures saved (remaining today: {rem})")
            if rem < MIN_REMAINING:
                done = sum(1 for _ in (OUT / "raw").glob("players_*.json.gz"))
                print(f"Daily allowance nearly used -- stopping after {used} requests ({done} fixtures saved in total). "
                      "Run the same command again tomorrow; saved fixtures are skipped.")
                return 0
            time.sleep(PAUSE_SECONDS)
    rows = []
    for season in SEASONS:
        for p in sorted((OUT / "raw").glob(f"players_{season}_*.json.gz")):
            rows.extend(rows_from_fixture(load(p), season))
    with gzip.open(OUT / "player_match.csv.gz", "wt", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        w.writeheader()
        w.writerows(rows)
    starters = sum(1 for r in rows if r["starter"])
    print(f"done: {used} requests this run; {len(rows)} player-match rows ({starters} starters) -> {OUT / 'player_match.csv.gz'} (private, gitignored)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
