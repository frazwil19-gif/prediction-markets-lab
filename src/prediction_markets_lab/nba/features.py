"""Leakage-safe NBA team-state features and Elo (research only).

All features for games on date D are computed from games strictly before D (a team plays
at most once per date, and date-grouped processing guarantees no same-day leakage)."""
from __future__ import annotations

import math
from collections import defaultdict, deque
from dataclasses import dataclass
from datetime import date

import pandas as pd

REST_CAP = 5
ROLL = 10
SHRINK_GAMES = 5.0
WINDOW_7D = 7


@dataclass(frozen=True)
class EloParams:
    k: float = 20.0
    hca: float = 75.0
    mov: bool = False
    carry: float = 0.75
    mean: float = 1505.0
    init: float = 1500.0


def mov_multiplier(margin: float, winner_elo_edge: float) -> float:
    """538-style margin-of-victory multiplier (winner_elo_edge includes home advantage)."""
    return ((abs(margin) + 3) ** 0.8) / (7.5 + 0.006 * winner_elo_edge)


def elo_probabilities(games: pd.DataFrame, p: EloParams) -> list[float]:
    """Pre-game P(home win) for every row, in input order (input must be date-sorted)."""
    if not games["date"].is_monotonic_increasing:
        raise ValueError("games must be sorted by date")
    r: dict[str, float] = defaultdict(lambda: p.init)
    last_season: dict[str, str] = {}
    out = []
    for g in games.itertuples(index=False):
        for t in (g.home, g.away):
            if t in last_season and last_season[t] != g.season:
                r[t] = p.carry * r[t] + (1 - p.carry) * p.mean
            last_season[t] = g.season
        edge = r[g.home] + (0.0 if g.neutral else p.hca) - r[g.away]
        ph = 1.0 / (1.0 + 10 ** (-edge / 400.0))
        out.append(ph)
        y = 1.0 if g.home_score > g.away_score else 0.0
        mult = 1.0
        if p.mov:
            margin = g.home_score - g.away_score
            winner_edge = edge if y == 1.0 else -edge
            mult = mov_multiplier(margin, winner_edge)
        delta = p.k * mult * (y - ph)
        r[g.home] += delta
        r[g.away] -= delta
    return out


def team_state_features(games: pd.DataFrame) -> pd.DataFrame:
    """Rest, back-to-back, congestion, rolling form and season point differential for both
    sides, from strictly earlier dates only."""
    if not games["date"].is_monotonic_increasing:
        raise ValueError("games must be sorted by date")
    last_date: dict[str, date] = {}
    recent_dates: dict[str, deque] = defaultdict(lambda: deque(maxlen=10))
    roll_pd: dict[str, deque] = defaultdict(lambda: deque(maxlen=ROLL))
    roll_w: dict[str, deque] = defaultdict(lambda: deque(maxlen=ROLL))
    season_pd: dict[tuple, float] = defaultdict(float)
    season_n: dict[tuple, int] = defaultdict(int)
    rows = []
    for d, day in games.groupby("date", sort=True):
        feats = {}
        for g in day.itertuples():
            f = {}
            for side, t in (("home", g.home), ("away", g.away)):
                ld = last_date.get(t)
                rest = REST_CAP if ld is None else min((d - ld).days, REST_CAP)
                f[f"{side}_rest"] = rest
                f[f"{side}_b2b"] = int(ld is not None and (d - ld).days == 1)
                f[f"{side}_games_7d"] = sum(1 for x in recent_dates[t] if 0 < (d - x).days <= WINDOW_7D)
                f[f"{side}_roll10_pd"] = sum(roll_pd[t]) / len(roll_pd[t]) if roll_pd[t] else 0.0
                f[f"{side}_roll10_win"] = sum(roll_w[t]) / len(roll_w[t]) if roll_w[t] else 0.5
                key = (t, g.season)
                f[f"{side}_season_pd"] = season_pd[key] / (season_n[key] + SHRINK_GAMES)
                f[f"{side}_season_games"] = season_n[key]
            feats[g.Index] = f
        for idx, f in feats.items():
            rows.append((idx, f))
        for g in day.itertuples():  # only now add this date's results
            margin = g.home_score - g.away_score
            for t, m in ((g.home, margin), (g.away, -margin)):
                last_date[t] = d
                recent_dates[t].append(d)
                roll_pd[t].append(m)
                roll_w[t].append(1 if m > 0 else 0)
                season_pd[(t, g.season)] += m
                season_n[(t, g.season)] += 1
    f = pd.DataFrame([r for _, r in rows], index=[i for i, _ in rows]).reindex(games.index)
    out = pd.concat([games, f], axis=1)
    out["rest_diff"] = out.home_rest - out.away_rest
    out["games_7d_diff"] = out.home_games_7d - out.away_games_7d
    out["roll10_pd_diff"] = out.home_roll10_pd - out.away_roll10_pd
    out["roll10_win_diff"] = out.home_roll10_win - out.away_roll10_win
    out["season_pd_diff"] = out.home_season_pd - out.away_season_pd
    out["season_game_number"] = out[["home_season_games", "away_season_games"]].min(axis=1) + 1
    return out


def logit(p: float, eps: float = 1e-6) -> float:
    p = min(max(p, eps), 1 - eps)
    return math.log(p / (1 - p))
