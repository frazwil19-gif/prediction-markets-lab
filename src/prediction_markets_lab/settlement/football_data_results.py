"""Free football results from football-data.co.uk for settlement (V2-4 settlement migration).

SHADOW MODE ONLY until the migration gate in research/platform_v2/SETTLEMENT_MIGRATION.md passes.
It never writes to the paper ledger itself; it resolves fixtures deterministically and reports.

Matching rule (never guesses):
  * both team names must resolve through the frozen config/football_team_aliases.yaml plus the settlement-only
    overlay config/settlement_team_aliases.yaml (exact aliases only; the frozen file is never edited);
  * a result must exist in the same competition with the same canonical home/away pair within
    +/- DATE_WINDOW_DAYS of the scheduled kickoff date (handles small reschedules);
  * exactly one candidate -> MATCHED; several -> AMBIGUOUS; none -> NOT_FOUND (still pending, or
    postponed -- football-data only lists played matches); unknown name -> UNRESOLVED_NAME.
"""
from __future__ import annotations

import csv
import io
from dataclasses import dataclass
from pathlib import Path
from datetime import date, datetime, timedelta

import yaml

from prediction_markets_lab.normalisation.team_names import load_alias_table, normalise_team_name

OVERLAY_PATH = Path(__file__).resolve().parents[3] / "config" / "settlement_team_aliases.yaml"


def load_settlement_aliases(overlay: Path = OVERLAY_PATH) -> dict[str, str]:
    """Frozen research alias table + settlement overlay. A raw name mapped to two canonicals is an error."""
    table = dict(load_alias_table())
    data = yaml.safe_load(overlay.read_text()) if overlay.exists() else {}
    for canonical, names in (data or {}).items():
        for raw in [canonical, *(names or [])]:
            if table.get(raw, canonical) != canonical:
                raise ValueError(f"settlement alias conflict: {raw!r} -> {table[raw]!r} vs {canonical!r}")
            table[raw] = canonical
    return table

DATE_WINDOW_DAYS = 3
SEASON_START_MONTH = 7
FD_BASE = "https://www.football-data.co.uk/mmz4281"


def season_code(d: date) -> str:
    """football-data season folder, e.g. 2026-09-24 -> '2627'."""
    y = d.year if d.month >= SEASON_START_MONTH else d.year - 1
    return f"{y % 100:02d}{(y + 1) % 100:02d}"


def fd_url(competition_code: str, d: date) -> str:
    return f"{FD_BASE}/{season_code(d)}/{competition_code}.csv"


@dataclass(frozen=True)
class FDResult:
    competition: str
    match_date: date
    home_raw: str
    away_raw: str
    home: str | None
    away: str | None
    home_goals: int
    away_goals: int
    full_time_result: str


def _parse_date(s: str) -> date:
    s = s.strip()
    for fmt in ("%d/%m/%Y", "%d/%m/%y"):
        try:
            return datetime.strptime(s, fmt).date()
        except ValueError:
            continue
    raise ValueError(f"unrecognised football-data date {s!r}")


def parse_fd_csv(text: str, competition: str, aliases: dict[str, str]) -> list[FDResult]:
    """Rows without both full-time goals (unplayed/abandoned placeholders) are skipped."""
    out = []
    for row in csv.DictReader(io.StringIO(text.lstrip("﻿"))):
        try:
            hg, ag = row.get("FTHG", ""), row.get("FTAG", "")
            if hg == "" or ag == "" or not row.get("HomeTeam") or not row.get("AwayTeam"):
                continue
            out.append(FDResult(
                competition=competition, match_date=_parse_date(row["Date"]),
                home_raw=row["HomeTeam"], away_raw=row["AwayTeam"],
                home=normalise_team_name(row["HomeTeam"], aliases), away=normalise_team_name(row["AwayTeam"], aliases),
                home_goals=int(float(hg)), away_goals=int(float(ag)), full_time_result=row.get("FTR", "")))
        except (KeyError, ValueError):
            continue
    return out


@dataclass(frozen=True)
class FixtureMatch:
    status: str  # MATCHED / AMBIGUOUS / NOT_FOUND / UNRESOLVED_NAME
    result: FDResult | None
    detail: str = ""


def match_fixture(competition: str, home_name: str, away_name: str, kickoff: date,
                  results: list[FDResult], aliases: dict[str, str]) -> FixtureMatch:
    h, a = normalise_team_name(home_name, aliases), normalise_team_name(away_name, aliases)
    if h is None or a is None:
        missing = [n for n, c in ((home_name, h), (away_name, a)) if c is None]
        return FixtureMatch("UNRESOLVED_NAME", None, "unmapped: " + ", ".join(missing))
    lo, hi = kickoff - timedelta(days=DATE_WINDOW_DAYS), kickoff + timedelta(days=DATE_WINDOW_DAYS)
    hits = [r for r in results if r.competition == competition and r.home == h and r.away == a and lo <= r.match_date <= hi]
    if len(hits) == 1:
        return FixtureMatch("MATCHED", hits[0])
    if len(hits) > 1:
        return FixtureMatch("AMBIGUOUS", None, f"{len(hits)} results in window")
    return FixtureMatch("NOT_FOUND", None)


def fd_consistent(r: FDResult) -> bool:
    """Internal consistency check: the FTR letter must agree with the goals."""
    expect = "H" if r.home_goals > r.away_goals else ("A" if r.home_goals < r.away_goals else "D")
    return r.full_time_result in ("", expect)
