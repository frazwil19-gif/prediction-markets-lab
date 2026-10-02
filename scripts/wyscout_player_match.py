"""Build the canonical player-match table from the Wyscout public soccer dataset (Pappalardo et al. 2019, CC BY 4.0).

Openly licensed (CC BY 4.0), free, no account: 2017/18 first divisions of England, Spain, Italy, Germany, France.
Run in GitHub Actions (figshare is not reachable from the research container). Downloads via the figshare API,
derives per player-match: starter flag, minutes (lineup/bench/substitutions; red cards not modelled), shots
(eventName 'Shot', or subEventName 'Free kick shot' / 'Penalty'), shots on target (tag 1801 'accurate' or 101 'goal';
blocked 2101 is not on target), goals (tag 101). Writes data/open/wyscout/player_match.csv.gz + ATTRIBUTION.md and
the audit to research/platform_v2/player_sot/WYSCOUT_AUDIT.json. No model is fitted.
"""
from __future__ import annotations

import gzip
import io
import json
import sys
import urllib.request
import zipfile
from pathlib import Path

import pandas as pd

from prediction_markets_lab.research_shadow import player_sot as PS

REPO = Path(__file__).resolve().parents[1]
OUT = REPO / "data/open/wyscout"
AUDIT = REPO / "research/platform_v2/player_sot/WYSCOUT_AUDIT.json"
COLLECTION = "https://api.figshare.com/v2/collections/4415000/articles?page_size=100"
LEAGUES = {"England": "EPL", "Spain": "LaLiga", "Italy": "SerieA", "Germany": "Bundesliga", "France": "Ligue1"}
SHOT_SUBEVENTS = {"Free kick shot", "Penalty"}
GOAL, ACCURATE, BLOCKED = 101, 1801, 2101
ROLE_MAP = {"GK": "GK", "DF": "DF", "MD": "MD", "FW": "FW"}
UA = {"User-Agent": "prediction-markets-lab research (CC BY 4.0 dataset download)"}


def get(url: str) -> bytes:
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=600) as r:
        return r.read()


def figshare_files() -> dict[str, str]:
    files = {}
    for art in json.loads(get(COLLECTION)):
        meta = json.loads(get(f"https://api.figshare.com/v2/articles/{art['id']}"))
        for f in meta.get("files", []):
            files[f["name"]] = f["download_url"]
    return files


def load_json_member(blob: bytes, member_suffix: str) -> list:
    with zipfile.ZipFile(io.BytesIO(blob)) as z:
        name = next(n for n in z.namelist() if n.endswith(member_suffix))
        return json.loads(z.read(name))


def build_league(matches: list, events: list, players: dict, comp: str) -> pd.DataFrame:
    ev = pd.DataFrame([{"matchId": e["matchId"], "playerId": e["playerId"], "teamId": e["teamId"], "eventName": e.get("eventName"),
                        "subEventName": e.get("subEventName"), "tags": {t["id"] for t in e.get("tags", [])}} for e in events
                       if e.get("eventName") == "Shot" or e.get("subEventName") in SHOT_SUBEVENTS])
    ev["sot"] = ev.tags.map(lambda t: int((ACCURATE in t or GOAL in t) and BLOCKED not in t))
    ev["goal"] = ev.tags.map(lambda t: int(GOAL in t))
    agg = ev.groupby(["matchId", "playerId"]).agg(shots=("sot", "size"), sot=("sot", "sum"), goals=("goal", "sum")).reset_index()
    rows = []
    for m in matches:
        sides = {int(tid): td for tid, td in m["teamsData"].items()}
        ids = list(sides)
        for tid, td in sides.items():
            opp = next(i for i in ids if i != tid)
            form = td.get("formation", {})
            subs = form.get("substitutions") or []
            if subs == "null":
                subs = []
            out_min = {s["playerOut"]: int(s["minute"]) for s in subs}
            in_min = {s["playerIn"]: int(s["minute"]) for s in subs}
            for pl, starter in [(p, True) for p in form.get("lineup", [])] + [(p, False) for p in form.get("bench", [])]:
                pid = pl["playerId"]
                if not starter and pid not in in_min:
                    continue                                   # unused substitute: not a player-match
                mi = 0 if starter else in_min[pid]
                mo = min(out_min.get(pid, PS.FULL_MATCH), PS.FULL_MATCH)
                info = players.get(pid, {})
                rows.append({"source": "wyscout_public_2019", "competition": comp, "season": "2017-18", "match_id": m["wyId"],
                             "date": m["dateutc"][:10], "team_id": tid, "opponent_id": opp, "home": td.get("side") == "home", "player_id": pid,
                             "player_name": info.get("shortName", ""), "role": ROLE_MAP.get((info.get("role") or {}).get("code2"), "UNK"),
                             "starter": starter, "minute_in": mi, "minute_out": mo, "minutes": max(mo - mi, 0)})
    df = pd.DataFrame(rows).merge(agg.rename(columns={"matchId": "match_id", "playerId": "player_id"}), on=["match_id", "player_id"], how="left")
    for c in ("shots", "sot", "goals"):
        df[c] = df[c].fillna(0).astype(int)
    return df[PS.FIELDS]


def main() -> int:
    files = figshare_files()
    print("figshare files:", sorted(files))
    players = {p["wyId"]: p for p in json.loads(get(files["players.json"]))}
    matches_zip, events_zip = get(files["matches.zip"]), get(files["events.zip"])
    frames = []
    for country, comp in LEAGUES.items():
        frames.append(build_league(load_json_member(matches_zip, f"matches_{country}.json"), load_json_member(events_zip, f"events_{country}.json"), players, comp))
        print(comp, len(frames[-1]))
    df = pd.concat(frames, ignore_index=True)
    OUT.mkdir(parents=True, exist_ok=True)
    with gzip.open(OUT / "player_match.csv.gz", "wt", encoding="utf-8") as f:
        df.to_csv(f, index=False)
    (OUT / "ATTRIBUTION.md").write_text(
        "# Wyscout public soccer dataset — attribution (CC BY 4.0)\n\n"
        "Derived from: Pappalardo, L., Cintia, P., Rossi, A. et al. A public data set of spatio-temporal match events in soccer "
        "competitions. Scientific Data 6, 236 (2019). https://doi.org/10.1038/s41597-019-0247-7 — data on figshare "
        "(collection 4415000), licensed CC BY 4.0 (https://creativecommons.org/licenses/by/4.0/).\n\n"
        "Changes: events aggregated to player-match shots / shots on target / goals; minutes derived from lineups, bench and "
        "substitutions (red cards not modelled) by scripts/wyscout_player_match.py.\n")
    AUDIT.parent.mkdir(parents=True, exist_ok=True)
    AUDIT.write_text(json.dumps({"source": "Wyscout public dataset (CC BY 4.0), 2017-18", **PS.audit(df)}, indent=1) + "\n")
    print(AUDIT.read_text()[:3000])
    return 0


if __name__ == "__main__":
    sys.exit(main())
