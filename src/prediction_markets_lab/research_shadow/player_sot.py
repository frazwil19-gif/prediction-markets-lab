"""Player SOT research pipeline (no model is fitted here without a pre-registration).

Canonical player-match table -> data audit -> targets (1+ / 2+ SOT) -> leakage-safe prior features ->
chronological splits -> simple non-market baselines -> evaluation -> one-shot holdout guard.
Bookmaker / exchange odds are NEVER inputs (Model A is sports-only).

Storage rule: data whose licence does not allow publication (e.g. API-Football) lives only under
`data/private/` (gitignored). Openly licensed data (e.g. Wyscout public dataset, CC BY 4.0) may be committed as a
derived table with its attribution file.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

FIELDS = ["source", "competition", "season", "match_id", "date", "team_id", "opponent_id", "home", "player_id", "player_name",
          "role", "starter", "minute_in", "minute_out", "minutes", "shots", "sot", "goals"]
ROLES = ("GK", "DF", "MD", "FW")
FULL_MATCH = 90
TARGETS = {"sot_1plus": 1, "sot_2plus": 2}
PRIOR_WINDOW = 10            # prior appearances used by rolling features
SHRINK_MINUTES = 450.0       # empirical-Bayes shrinkage strength (minutes) toward the role x league rate


# ------------------------------------------------------------------ audit
def audit(df: pd.DataFrame) -> dict:
    """Data-quality audit and target base rates. Pure description: no model, no tuning."""
    out: dict = {"rows": int(len(df)), "matches": int(df.match_id.nunique()), "players": int(df.player_id.nunique()),
                 "competitions": sorted(df.competition.unique().tolist()), "seasons": sorted(map(str, df.season.unique().tolist()))}
    out["missing_share"] = {c: round(float(df[c].isna().mean()), 4) for c in FIELDS if c in df}
    out["duplicates_match_player"] = int(df.duplicated(["match_id", "player_id"]).sum())
    st = df[df.starter]
    per_team = st.groupby(["match_id", "team_id"]).size()
    out["starters_per_team_match"] = {"eq_11": round(float((per_team == 11).mean()), 4), "min": int(per_team.min()), "max": int(per_team.max())}
    tm = df.groupby("match_id").team_id.nunique()
    out["matches_without_two_teams"] = int((tm != 2).sum())
    out["violations"] = {"sot_gt_shots": int((df.sot > df.shots).sum()), "goals_gt_sot": int((df.goals > df.sot).sum()),
                         "minutes_out_of_range": int(((df.minutes < 0) | (df.minutes > FULL_MATCH)).sum()),
                         "events_with_zero_minutes": int(((df.minutes == 0) & (df.shots > 0)).sum())}
    teams_per_player_season = df.groupby(["player_id", "season"]).team_id.nunique()
    out["players_with_2plus_teams_in_season"] = int((teams_per_player_season > 1).sum())
    out["role_distribution_starters"] = {k: int(v) for k, v in st.role.value_counts().items()}
    out["starter_minutes"] = {"mean": round(float(st.minutes.mean()), 2), "share_full_90": round(float((st.minutes >= FULL_MATCH).mean()), 4)}
    out["base_rates_starters"] = {t: round(float((st.sot >= k).mean()), 4) for t, k in TARGETS.items()}
    out["base_rates_starters_by_role"] = {r: {t: round(float((g.sot >= k).mean()), 4) for t, k in TARGETS.items()} | {"n": int(len(g))}
                                          for r, g in st.groupby("role")}
    out["base_rates_starters_by_competition"] = {c: {t: round(float((g.sot >= k).mean()), 4) for t, k in TARGETS.items()} | {"n": int(len(g))}
                                                 for c, g in st.groupby("competition")}
    out["starter_observations"] = int(len(st))
    return out


# ------------------------------------------------------------------ targets / features (leakage-safe)
def add_targets(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    for t, k in TARGETS.items():
        df[t] = (df.sot >= k).astype(int)
    return df


def prior_features(df: pd.DataFrame) -> pd.DataFrame:
    """Per player, features from STRICTLY EARLIER matches only (sorted by date, then match_id): prior appearances,
    minutes, shots, SOT over the last PRIOR_WINDOW appearances, plus the team's and opponent's prior SOT for /
    against per match. Same-day rows never see each other."""
    d = df.sort_values(["date", "match_id"]).reset_index(drop=True)
    g = d.groupby("player_id", sort=False)
    for c in ("minutes", "shots", "sot"):
        d[f"p_{c}_prior"] = g[c].transform(lambda s: s.shift(1).rolling(PRIOR_WINDOW, min_periods=1).sum())
    d["p_apps_prior"] = g.cumcount().clip(upper=PRIOR_WINDOW)
    d["p_starts_prior"] = g["starter"].transform(lambda s: s.astype(float).shift(1).rolling(PRIOR_WINDOW, min_periods=1).sum())
    team = d.groupby(["match_id", "team_id", "date"], as_index=False).agg(t_sot=("sot", "sum")).sort_values(["date", "match_id"])
    opp = team.rename(columns={"team_id": "opponent_id", "t_sot": "o_sot"})
    team = team.merge(opp, on=["match_id", "date"]).query("team_id != opponent_id")
    tg = team.groupby("team_id", sort=False)
    team["team_sot_for_prior"] = tg.t_sot.transform(lambda s: s.shift(1).rolling(PRIOR_WINDOW, min_periods=1).mean())
    team["team_sot_against_prior"] = tg.o_sot.transform(lambda s: s.shift(1).rolling(PRIOR_WINDOW, min_periods=1).mean())
    d = d.merge(team[["match_id", "team_id", "team_sot_for_prior", "team_sot_against_prior"]], on=["match_id", "team_id"], how="left")
    opp_def = team[["match_id", "team_id", "team_sot_against_prior"]].rename(columns={"team_id": "opponent_id", "team_sot_against_prior": "opp_sot_conceded_prior"})
    d = d.merge(opp_def, on=["match_id", "opponent_id"], how="left")
    return d


def chronological_split(df: pd.DataFrame, cuts: list[str]) -> list[pd.DataFrame]:
    """Split by date at the given ISO cut dates: [<c1], [c1, c2), ..., [>= last]."""
    edges = [pd.Timestamp.min] + [pd.Timestamp(c) for c in cuts] + [pd.Timestamp.max]
    dates = pd.to_datetime(df.date)
    return [df[(dates >= a) & (dates < b)] for a, b in zip(edges, edges[1:])]


# ------------------------------------------------------------------ baselines (non-market, no fitting beyond rates)
def baseline_role_rate(train: pd.DataFrame, test: pd.DataFrame, target: str) -> np.ndarray:
    """B0: starter base rate by competition x role from the training block."""
    rates = train.groupby(["competition", "role"])[target].mean()
    overall = train[target].mean()
    return np.array([rates.get((c, r), overall) for c, r in zip(test.competition, test.role)], dtype=float)


def baseline_player_rate(train: pd.DataFrame, test: pd.DataFrame, target: str) -> np.ndarray:
    """B1: player's prior SOT per 90 (prior appearances only) shrunk to the role rate, mapped to P(>=k) by Poisson
    over a full 90. Uses only prior_features columns, so no future information."""
    k = TARGETS["sot_1plus" if target == "sot_1plus" else "sot_2plus"]
    role_rate = (train.groupby("role").sot.sum() / train.groupby("role").minutes.sum() * FULL_MATCH).to_dict()
    lam = []
    for r in test.itertuples():
        prior = role_rate.get(r.role, 0.3)
        mins = r.p_minutes_prior or 0.0
        lam.append(((r.p_sot_prior or 0.0) + prior * SHRINK_MINUTES / FULL_MATCH) / ((mins + SHRINK_MINUTES) / FULL_MATCH))
    lam = np.array(lam)
    from scipy import stats
    return np.clip(1 - stats.poisson.cdf(k - 1, lam), 1e-6, 1 - 1e-6)


# ------------------------------------------------------------------ evaluation
def evaluate(y: np.ndarray, p: np.ndarray) -> dict:
    p = np.clip(p, 1e-6, 1 - 1e-6)
    ll = -(y * np.log(p) + (1 - y) * np.log(1 - p))
    x = np.log(p / (1 - p))
    X = np.column_stack([np.ones_like(x), x])
    b = np.array([0.0, 1.0])
    for _ in range(50):
        q = 1 / (1 + np.exp(-(X @ b)))
        b = b + np.linalg.solve(X.T @ (X * (q * (1 - q))[:, None]) + 1e-9 * np.eye(2), X.T @ (y - q))
    return {"n": int(len(y)), "base_rate": round(float(y.mean()), 4), "mean_p": round(float(p.mean()), 4), "logloss": round(float(ll.mean()), 5),
            "brier": round(float(((p - y) ** 2).mean()), 5), "cal_intercept": round(float(b[0]), 4), "cal_slope": round(float(b[1]), 4)}


@dataclass(frozen=True)
class HoldoutGuard:
    """One-shot holdout: requires a committed spec file; writes a marker; refuses a second opening."""
    spec: Path
    marker: Path

    def open(self, is_committed) -> dict:
        if not self.spec.exists() or not is_committed(self.spec):
            raise PermissionError("frozen spec missing or not committed -- holdout stays sealed")
        if self.marker.exists():
            raise PermissionError("holdout already opened once")
        self.marker.write_text(json.dumps({"opened": True}) + "\n")
        return json.loads(self.spec.read_text())
