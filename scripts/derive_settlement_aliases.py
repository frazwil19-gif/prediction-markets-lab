"""Collect fixture-identity evidence for settlement team aliases (0 Odds API credits; proposals only).

For each paper-tier football league (config/football_coverage.yaml, paper_state != SHADOW):
  * Odds API names: FREE /v4/sports/{sport}/events (0 credits; the run stops calling if a response reports a charge)
    plus already-archived /scores payloads in settlement_archive/ (no new call);
  * football-data names: fixtures.csv (upcoming) + current-season results CSV (played), times Europe/London;
then runs settlement.alias_derivation.derive per league and writes
  research/platform_v2/settlement_hardening/alias_evidence/<utc>.json  (full evidence)
  research/platform_v2/settlement_hardening/PROPOSED_ALIASES.csv       (latest proposals)
Nothing is applied automatically: config/settlement_team_aliases.yaml changes only in a reviewed commit with tests.
Runs in GitHub Actions (football-data.co.uk is not reachable from the research container).
"""
from __future__ import annotations

import csv
import io
import json
import os
import sys
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

from prediction_markets_lab.ops import football_coverage as FC
from prediction_markets_lab.settlement import alias_derivation as AD
from prediction_markets_lab.settlement import football_data_results as fd

REPO = Path(__file__).resolve().parents[1]
OUT = REPO / "research/platform_v2/settlement_hardening"
ODDS = "https://api.the-odds-api.com/v4/sports"
FIXTURES_URL = "https://www.football-data.co.uk/fixtures.csv"
UK = ZoneInfo("Europe/London")
UA = {"User-Agent": "prediction-markets-lab settlement alias evidence (non-commercial)"}


def get(url: str) -> tuple[bytes, dict]:
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=60) as r:
        return r.read(), {k.lower(): v for k, v in r.headers.items()}


def fd_rows(text: str, code: str) -> list[AD.Fixture]:
    out = []
    for row in csv.DictReader(io.StringIO(text.lstrip("﻿"))):
        if (row.get("Div") or code) != code or not row.get("HomeTeam") or not row.get("Date") or not row.get("Time"):
            continue
        try:
            d = fd._parse_date(row["Date"])
            hh, mm = (int(x) for x in row["Time"].strip().split(":")[:2])
        except ValueError:
            continue
        ko = datetime(d.year, d.month, d.day, hh, mm, tzinfo=UK).astimezone(timezone.utc)
        out.append(AD.Fixture(code, ko, row["HomeTeam"].strip(), row["AwayTeam"].strip()))
    return out


def odds_rows(events: list[dict], code: str, aliases: dict[str, str]) -> list[AD.Fixture]:
    return [AD.Fixture(code, datetime.fromisoformat(e["commence_time"].replace("Z", "+00:00")), aliases.get(e["home_team"], e["home_team"]),
                       aliases.get(e["away_team"], e["away_team"])) for e in events if e.get("home_team") and e.get("commence_time")]


def main() -> int:
    now = datetime.now(timezone.utc)
    key = os.environ.get("THE_ODDS_API_KEY", "")
    aliases = fd.load_settlement_aliases()
    leagues = [lg for lg in FC.load() if lg.paper_state != "SHADOW" and lg.sport_key]
    log: dict = {"generated_at": now.isoformat(), "credits_charged": 0, "warnings": [], "leagues": {}}
    try:
        fixtures_text = get(FIXTURES_URL)[0].decode("utf-8", errors="replace")
    except Exception as exc:  # noqa: BLE001
        fixtures_text = ""
        log["warnings"].append(f"fixtures.csv unavailable: {exc}")
    charged = False
    proposals = []
    for lg in leagues:
        events: list[dict] = []
        if key and not charged:
            try:
                body, hdr = get(f"{ODDS}/{lg.sport_key}/events/?{urllib.parse.urlencode({'apiKey': key})}")
                last = hdr.get("x-requests-last", "0")
                if last not in ("0", "", None):
                    charged = True
                    log["credits_charged"] += int(last)
                    log["warnings"].append(f"/events reported a charge ({last}); no further calls this run")
                events = json.loads(body)
            except Exception as exc:  # noqa: BLE001
                log["warnings"].append(f"{lg.code} events unavailable: {exc}")
        for f in sorted((REPO / "settlement_archive").glob(f"odds_api_scores_{lg.sport_key}_*.json")):
            events += json.loads(f.read_text())
        seen, uniq = set(), []
        for e in events:
            k = (e.get("home_team"), e.get("away_team"), e.get("commence_time"))
            if k not in seen:
                seen.add(k)
                uniq.append(e)
        fdx = fd_rows(fixtures_text, lg.code)
        try:
            fdx += fd_rows(get(fd.fd_url(lg.code, now.date()))[0].decode("utf-8-sig", errors="replace"), lg.code)
        except Exception as exc:  # noqa: BLE001
            log["warnings"].append(f"{lg.code} results unavailable: {exc}")
        ods = odds_rows(uniq, lg.code, aliases)
        odds_names = {n for e in ods for n in (e.home, e.away)}
        known = {raw: aliases[raw] for raw in {n for f in fdx for n in (f.home, f.away)} if raw in aliases and aliases[raw] in odds_names}
        d = AD.derive(fdx, ods, known)
        log["leagues"][lg.code] = {"fd_fixtures": len(fdx), "odds_events": len(ods), "known": len(known), "proposed": d.aliases,
                                   "method": d.method, "evidence": d.evidence, "unresolved": d.unresolved,
                                   "fd_fixtures_without_odds_slot": len(d.fixtures_without_slot), "rejected": d.rejected,
                                   "odds_names_not_in_alias_table": sorted(n for n in odds_names if n not in aliases)}
        proposals += [{"competition": lg.code, "fd_raw": x, "odds_name": y, "method": d.method[x], "n_fixtures": len(d.evidence[x])}
                      for x, y in sorted(d.aliases.items())]
    (OUT / "alias_evidence").mkdir(parents=True, exist_ok=True)
    (OUT / "alias_evidence" / f"{now:%Y%m%dT%H%M%SZ}.json").write_text(json.dumps(log, indent=1) + "\n")
    with open(OUT / "PROPOSED_ALIASES.csv", "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=["competition", "fd_raw", "odds_name", "method", "n_fixtures"])
        w.writeheader()
        w.writerows(proposals)
    print(json.dumps({c: {k: v for k, v in x.items() if k not in ("evidence",)} for c, x in log["leagues"].items()}, indent=1)[:6000])
    for w_ in log["warnings"]:
        print(f"::warning::{w_}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
