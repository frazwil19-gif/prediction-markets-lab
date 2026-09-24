"""Canonical NBA game table from free GitHub-published sources (research only).

Sources (downloaded into data/raw/basketball/, SHA-256 manifest committed):
  wippa-studios/wippa-nba-data (MIT): OddsPortal-derived results + average closing decimal
      moneyline odds, 2016-17 .. 2025-26 (2019-20 and 2020-21 embedded in scrape_progress JSON).
  flancast90/sportsbookreview-scraper (MIT): SBR results + closing American moneylines 2011-12 .. 2021-22
      (used here only for Elo warm-up results and as an independent cross-check).
"""
from __future__ import annotations

import json
from datetime import date, datetime
from pathlib import Path

import pandas as pd

FRANCHISE_BY_NICKNAME = {
    "Hawks": "ATL", "Celtics": "BOS", "Nets": "BKN", "NewJersey": "BKN", "Hornets": "CHA", "Bobcats": "CHA", "Bulls": "CHI",
    "Cavaliers": "CLE", "Mavericks": "DAL", "Nuggets": "DEN", "Pistons": "DET", "Warriors": "GSW", "Golden State": "GSW",
    "Rockets": "HOU", "Pacers": "IND", "Clippers": "LAC", "Lakers": "LAL", "Grizzlies": "MEM", "Heat": "MIA",
    "Bucks": "MIL", "Timberwolves": "MIN", "Pelicans": "NOP", "Knicks": "NYK", "Thunder": "OKC", "Magic": "ORL",
    "76ers": "PHI", "Seventysixers": "PHI", "Suns": "PHX", "Trail Blazers": "POR", "Trailblazers": "POR", "Kings": "SAC",
    "Spurs": "SAS", "Raptors": "TOR", "Jazz": "UTA", "Wizards": "WAS",
}
FULL_NAME_TO_FRANCHISE = {
    "Atlanta Hawks": "ATL", "Boston Celtics": "BOS", "Brooklyn Nets": "BKN", "Charlotte Hornets": "CHA",
    "Chicago Bulls": "CHI", "Cleveland Cavaliers": "CLE", "Dallas Mavericks": "DAL", "Denver Nuggets": "DEN",
    "Detroit Pistons": "DET", "Golden State Warriors": "GSW", "Houston Rockets": "HOU", "Indiana Pacers": "IND",
    "Los Angeles Clippers": "LAC", "Los Angeles Lakers": "LAL", "Memphis Grizzlies": "MEM", "Miami Heat": "MIA",
    "Milwaukee Bucks": "MIL", "Minnesota Timberwolves": "MIN", "New Orleans Pelicans": "NOP", "New York Knicks": "NYK",
    "Oklahoma City Thunder": "OKC", "Orlando Magic": "ORL", "Philadelphia 76ers": "PHI", "Phoenix Suns": "PHX",
    "Portland Trail Blazers": "POR", "Sacramento Kings": "SAC", "San Antonio Spurs": "SAS", "Toronto Raptors": "TOR",
    "Utah Jazz": "UTA", "Washington Wizards": "WAS",
}
ROUND_TO_STAGE = {"": "regular", "Playoffs": "playoffs", "Promotion - Playoffs": "play_in"}
EXCLUDED_ROUNDS = {"Pre-season", "All Stars"}
BUBBLE_START = date(2020, 7, 30)
BUBBLE_END = date(2020, 10, 12)


def sbr_franchise(nickname: str, season_start_year: int) -> str | None:
    """SBR uses nicknames. 'Hornets' was New Orleans until 2012-13 and Charlotte from 2014-15."""
    if nickname == "Hornets" and season_start_year <= 2012:
        return "NOP"
    return FRANCHISE_BY_NICKNAME.get(nickname)


def american_to_decimal(ml: float) -> float | None:
    if ml is None or pd.isna(ml) or ml == 0:
        return None
    return 1 + ml / 100 if ml > 0 else 1 + 100 / abs(ml)


def season_label(d: date) -> str:
    # NBA seasons start in mid/late October; the 2020 bubble playoffs ran to 11 Oct 2020
    y = d.year if (d.month > 10 or (d.month == 10 and d.day >= 15)) else d.year - 1
    return f"{y}-{str(y + 1)[2:]}"


def load_wippa(raw_dir: Path) -> pd.DataFrame:
    frames = []
    for f in sorted((raw_dir / "wippa_nba").glob("nba_*_results_odds.csv")):
        d = pd.read_csv(f, dtype={"round": str}, keep_default_na=False)
        d["date"] = pd.to_datetime(d["date"]).dt.date
        frames.append(d)
    for f in sorted((raw_dir / "wippa_nba").glob("scrape_progress_*.json")):
        games = json.loads(f.read_text()).get("games", [])
        d = pd.DataFrame(games)
        if d.empty:
            continue
        d["date"] = pd.to_datetime(d["date"], format="%d %b %Y").dt.date
        frames.append(d)
    d = pd.concat(frames, ignore_index=True)
    d["round"] = d["round"].fillna("").astype(str)
    d = d[~d["round"].isin(EXCLUDED_ROUNDS)]
    d["home"] = d.home_team.map(FULL_NAME_TO_FRANCHISE)
    d["away"] = d.away_team.map(FULL_NAME_TO_FRANCHISE)
    d = d[d.home.notna() & d.away.notna() & (d.home != d.away)].copy()
    d["stage"] = d["round"].map(ROUND_TO_STAGE)
    d = d[d.stage.notna()]
    d["home_score"] = pd.to_numeric(d.home_score, errors="coerce")
    d["away_score"] = pd.to_numeric(d.away_score, errors="coerce")
    d = d[d.home_score.notna() & d.away_score.notna() & (d.home_score != d.away_score)]
    d["home_odds"] = pd.to_numeric(d.home_odds, errors="coerce")
    d["away_odds"] = pd.to_numeric(d.away_odds, errors="coerce")
    d["source"] = "wippa_oddsportal"
    d = d.drop_duplicates(subset=["date", "home", "away"])
    return d[["date", "home", "away", "home_score", "away_score", "home_odds", "away_odds", "stage", "overtime", "source"]]


def load_sbr(raw_dir: Path) -> pd.DataFrame:
    s = pd.DataFrame(json.loads((raw_dir / "sbr" / "nba_archive_10Y.json").read_text()))
    s = s[s.date.notna()].copy()
    s["date"] = pd.to_datetime(s.date.astype(int).astype(str), format="%Y%m%d").dt.date
    s["home"] = [sbr_franchise(str(n), int(y)) for n, y in zip(s.home_team, s.season)]
    s["away"] = [sbr_franchise(str(n), int(y)) for n, y in zip(s.away_team, s.season)]
    s["home_score"] = pd.to_numeric(s.home_final, errors="coerce")
    s["away_score"] = pd.to_numeric(s.away_final, errors="coerce")
    s = s[s.home.notna() & s.away.notna() & s.home_score.notna() & s.away_score.notna() & (s.home_score != s.away_score)]
    s["home_odds"] = s.home_close_ml.map(american_to_decimal)
    s["away_odds"] = s.away_close_ml.map(american_to_decimal)
    s["stage"] = "unknown"
    s["overtime"] = None
    s["source"] = "sbr"
    return s[["date", "home", "away", "home_score", "away_score", "home_odds", "away_odds", "stage", "overtime", "source"]]


def build_games(raw_dir: Path, warmup_until: date = date(2016, 8, 1)) -> pd.DataFrame:
    """Warm-up results (SBR, before 2016-17) + primary games (wippa, 2016-17 onward)."""
    w = load_wippa(raw_dir)
    s = load_sbr(raw_dir)
    s = s[s.date < warmup_until]
    g = pd.concat([s, w], ignore_index=True)
    g["season"] = g.date.map(season_label)
    g["neutral"] = [(BUBBLE_START <= d <= BUBBLE_END) for d in g.date]
    g["home_win"] = (g.home_score > g.away_score).astype(int)
    g = g.sort_values(["date", "home", "away"]).reset_index(drop=True)
    g["game_id"] = [f"NBA-{d.isoformat()}-{h}-{a}" for d, h, a in zip(g.date, g.home, g.away)]
    return g
