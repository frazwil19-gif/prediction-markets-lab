"""Corners prospective collector — Model A (corners-A-1.0) predictions, outcomes and (later) market quotes.

Pre-registered: research/platform_v2/corners_abc/PREREGISTRATION.md. Research only: nothing here feeds Stage A, bet
selection, grades, stakes or the Money Card. Zero API credits: fixtures and results come from football-data.co.uk.

Market quotes are written only by an ENABLED price adapter (none is enabled: every row carries
market_status = NO_PRICE_SOURCE_ENABLED). MARKET_CONSENSUS, BEST_EXECUTABLE and DECISION prices are separate columns
and are never substituted for one another.
"""
from __future__ import annotations

import csv
import io
import json
from dataclasses import dataclass
from datetime import date, datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import special, stats

DIVS = ("E0", "E1", "SC0", "N1", "D1", "F1", "SP1", "I1", "P1", "B1")
# divisions loaded only for team history (promoted/relegated teams), as Matches.csv did
HISTORY_DIVS = ("E2", "E3", "SC1", "SC2", "SC3", "SP2", "D2", "I2", "F2")
TOTAL_LINES = (7.5, 8.5, 9.5, 10.5, 11.5, 12.5, 13.5)
TEAM_LINES = (3.5, 4.5, 5.5, 6.5)
WINDOW = 20
LOW_HISTORY = 10
NO_PRICE = "NO_PRICE_SOURCE_ENABLED"
PRED_FIELDS = (["run_ts", "model_version", "competition", "kickoff_date", "kickoff_time", "home", "away", "event_key",
                "mu_home", "mu_away", "rho", "mean_total"]
               + [f"p_total_over_{L}" for L in TOTAL_LINES] + [f"p_home_over_{L}" for L in TEAM_LINES] + [f"p_away_over_{L}" for L in TEAM_LINES]
               + ["h_cf20", "h_ca20", "a_cf20", "a_ca20", "lm_H", "lm_A", "n_hist_home", "n_hist_away", "uncertainty_flag",
                  "market_status", "consensus_line", "consensus_p_over", "consensus_venues", "best_exec_over_odds", "best_exec_over_venue",
                  "best_exec_under_odds", "best_exec_under_venue", "decision_price"])
OUTCOME_FIELDS = ["event_key", "competition", "match_date", "home", "away", "home_corners", "away_corners", "total_corners", "recorded_at", "source"]


# ------------------------------------------------------------------ football-data parsing
def parse_fd(text: str, div: str) -> pd.DataFrame:
    df = pd.read_csv(io.StringIO(text), encoding_errors="replace")
    if df.empty or "HomeTeam" not in df:
        return pd.DataFrame()
    df = df.rename(columns={"HC": "HomeCorners", "AC": "AwayCorners"})
    out = pd.DataFrame({"Division": div, "MatchDate": pd.to_datetime(df["Date"], dayfirst=True, format="mixed"),
                        "HomeTeam": df["HomeTeam"], "AwayTeam": df["AwayTeam"],
                        "HomeCorners": df["HomeCorners"] if "HomeCorners" in df else np.nan,
                        "AwayCorners": df["AwayCorners"] if "AwayCorners" in df else np.nan})
    return out.dropna(subset=["HomeTeam", "AwayTeam"])


def parse_fixtures(text: str) -> pd.DataFrame:
    df = pd.read_csv(io.StringIO(text), encoding_errors="replace")
    df = df.rename(columns={df.columns[0]: "Div"}) if "Div" not in df.columns else df   # file may start with a BOM
    df = df[df["Div"].isin(DIVS)].copy()
    df["MatchDate"] = pd.to_datetime(df["Date"], dayfirst=True, format="mixed")
    df["Time"] = df.get("Time", "")
    return df[["Div", "MatchDate", "Time", "HomeTeam", "AwayTeam"]].rename(columns={"Div": "Division"})


# ------------------------------------------------------------------ features (same definitions as Matches.csv build)
def team_states(played: pd.DataFrame, minp: int, league_win: int, league_minp: int) -> tuple[dict, dict, dict]:
    """State AFTER each team's last played match: rolling-WINDOW corners for/against (min `minp`), the division
    fill means, and division home/away league means (last `league_win` matches, min `league_minp`)."""
    p = played.dropna(subset=["HomeCorners", "AwayCorners"]).sort_values(["MatchDate", "Division", "HomeTeam"])
    h = pd.DataFrame({"date": p.MatchDate, "div": p.Division, "team": p.HomeTeam, "cf": p.HomeCorners, "ca": p.AwayCorners, "v": 0})
    a = pd.DataFrame({"date": p.MatchDate, "div": p.Division, "team": p.AwayTeam, "cf": p.AwayCorners, "ca": p.HomeCorners, "v": 1})
    L = pd.concat([h, a]).sort_values(["date", "v"], kind="stable")
    state = {}
    for team, g in L.groupby("team", sort=False):
        last = g.tail(WINDOW)
        n = len(g)
        state[team] = {"cf": float(last.cf.mean()) if len(last) >= minp else None,
                       "ca": float(last.ca.mean()) if len(last) >= minp else None, "n": int(n)}
    div_fill = {d: (float(g.cf.tail(2 * league_win).mean()) if len(g) >= league_minp else None) for d, g in L.groupby("div")}
    league = {d: {"H": float(g.HomeCorners.tail(league_win).mean()), "A": float(g.AwayCorners.tail(league_win).mean())}
              for d, g in p.groupby("Division") if len(g) >= league_minp}
    global_mean = float(L.cf.mean())
    for d in list(div_fill):
        if div_fill[d] is None:
            div_fill[d] = global_mean
    return state, div_fill, league


def fixture_features(fx: pd.DataFrame, state: dict, div_fill: dict, league: dict) -> pd.DataFrame:
    rows = []
    for r in fx.itertuples():
        fill = div_fill.get(r.Division)
        sh, sa = state.get(r.HomeTeam, {}), state.get(r.AwayTeam, {})
        lg = league.get(r.Division)
        if lg is None or fill is None:
            continue
        rows.append({"competition": r.Division, "kickoff_date": r.MatchDate.date().isoformat(), "kickoff_time": str(r.Time or ""),
                     "home": r.HomeTeam, "away": r.AwayTeam,
                     "h_cf20": sh.get("cf") or fill, "h_ca20": sh.get("ca") or fill, "a_cf20": sa.get("cf") or fill, "a_ca20": sa.get("ca") or fill,
                     "lm_H": lg["H"], "lm_A": lg["A"], "n_hist_home": sh.get("n", 0), "n_hist_away": sa.get("n", 0)})
    return pd.DataFrame(rows)


# ------------------------------------------------------------------ model (identical maths to the frozen script; tested)
def grid(max_k: int) -> np.ndarray:
    return np.arange(0, max_k + 1)


def nb_pmf_grid(mu: np.ndarray, alpha: float, g: np.ndarray) -> np.ndarray:
    r = 1 / alpha
    y = g[None, :].astype(float)
    m = mu[:, None]
    return np.exp(special.gammaln(y + r) - special.gammaln(r) - special.gammaln(y + 1) + r * np.log(r / (r + m)) + y * np.log(m / (r + m)))


def convolve_rows(ph: np.ndarray, pa: np.ndarray) -> np.ndarray:
    n = ph.shape[1]
    out = np.zeros((ph.shape[0], 2 * n - 1))
    for k in range(n):
        out[:, k:k + n] += ph[:, [k]] * pa
    return out[:, :n] / out[:, :n].sum(axis=1, keepdims=True)


def copula_total_pmf(ph: np.ndarray, pa: np.ndarray, rho: float, draws: int, seed: int, mix: float) -> np.ndarray:
    rng = np.random.default_rng(seed)
    z = rng.standard_normal((draws, 2))
    z[:, 1] = rho * z[:, 0] + np.sqrt(1 - rho ** 2) * z[:, 1]
    u = stats.norm.cdf(z)
    n = ph.shape[1]
    ch, ca = np.cumsum(ph, axis=1), np.cumsum(pa, axis=1)
    out = np.zeros((ph.shape[0], n))
    for i in range(ph.shape[0]):
        hh = np.minimum(np.searchsorted(ch[i], u[:, 0]), n - 1)
        aa = np.minimum(np.searchsorted(ca[i], u[:, 1]), n - 1)
        out[i] = np.bincount(np.minimum(hh + aa, n - 1), minlength=n)[:n] / draws
    return (1 - mix) * out + mix * convolve_rows(ph, pa)


def p_over(pmf: np.ndarray, line: float) -> np.ndarray:
    return np.clip(1 - pmf[:, : int(np.floor(line)) + 1].sum(axis=1), 1e-9, 1 - 1e-9)


@dataclass(frozen=True)
class ModelA:
    params: dict

    @classmethod
    def load(cls, path: Path) -> "ModelA":
        return cls(json.loads(path.read_text()))

    def predict(self, feats: pd.DataFrame) -> dict[str, np.ndarray]:
        c = self.params["constants"]
        g = grid(c["GRID_MAX"])
        mus, pm = {}, {}
        for side, base in (("H", "lm_H"), ("A", "lm_A")):
            s = self.params["sides"][side]
            cols = [np.ones(len(feats)), np.log(feats[base].to_numpy(float))]
            cols += [np.log(np.clip(feats[col].to_numpy(float), c["log_floor"], None)) for grp in self.params["groups"] for col in self.params["columns"][grp]]
            mus[side] = np.exp(np.column_stack(cols) @ np.array(s["coef"]))
            pm[side] = nb_pmf_grid(mus[side], s["alpha"], g)
        tot = copula_total_pmf(pm["H"], pm["A"], self.params["rho"], c["MC_DRAWS"], c["MC_SEED"], c["MC_MIX"])
        return {"mu_H": mus["H"], "mu_A": mus["A"], "pmf_T": tot, "pmf_H": pm["H"], "pmf_A": pm["A"], "grid": g}


# ------------------------------------------------------------------ rows / files
def event_key(div: str, kickoff_date: str, home: str, away: str) -> str:
    return f"football|{div}|{home} v {away}|{kickoff_date}"


def prediction_rows(feats: pd.DataFrame, model: ModelA, run_ts: datetime) -> list[dict]:
    if feats.empty:
        return []
    out = model.predict(feats)
    rows = []
    for i, r in enumerate(feats.itertuples()):
        row = {"run_ts": run_ts.isoformat(), "model_version": model.params["version"], "competition": r.competition,
               "kickoff_date": r.kickoff_date, "kickoff_time": r.kickoff_time, "home": r.home, "away": r.away,
               "event_key": event_key(r.competition, r.kickoff_date, r.home, r.away),
               "mu_home": round(float(out["mu_H"][i]), 4), "mu_away": round(float(out["mu_A"][i]), 4), "rho": round(model.params["rho"], 4),
               "mean_total": round(float((out["pmf_T"][i] * out["grid"]).sum()), 4)}
        for L in TOTAL_LINES:
            row[f"p_total_over_{L}"] = round(float(p_over(out["pmf_T"][[i]], L)[0]), 5)
        for L in TEAM_LINES:
            row[f"p_home_over_{L}"] = round(float(p_over(out["pmf_H"][[i]], L)[0]), 5)
            row[f"p_away_over_{L}"] = round(float(p_over(out["pmf_A"][[i]], L)[0]), 5)
        for k in ("h_cf20", "h_ca20", "a_cf20", "a_ca20", "lm_H", "lm_A"):
            row[k] = round(float(getattr(r, k)), 4)
        row.update({"n_hist_home": int(r.n_hist_home), "n_hist_away": int(r.n_hist_away),
                    "uncertainty_flag": "LOW_HISTORY" if min(r.n_hist_home, r.n_hist_away) < LOW_HISTORY else "OK",
                    "market_status": NO_PRICE})
        rows.append({k: row.get(k, "") for k in PRED_FIELDS})
    return rows


def outcome_rows(played: pd.DataFrame, since: date, known: set[str], now: datetime) -> list[dict]:
    p = played[(played.Division.isin(DIVS)) & (played.MatchDate.dt.date >= since)].dropna(subset=["HomeCorners", "AwayCorners"])
    out = []
    for r in p.itertuples():
        k = event_key(r.Division, r.MatchDate.date().isoformat(), r.HomeTeam, r.AwayTeam)
        if k in known:
            continue
        out.append({"event_key": k, "competition": r.Division, "match_date": r.MatchDate.date().isoformat(), "home": r.HomeTeam, "away": r.AwayTeam,
                    "home_corners": int(r.HomeCorners), "away_corners": int(r.AwayCorners), "total_corners": int(r.HomeCorners + r.AwayCorners),
                    "recorded_at": now.isoformat(), "source": "football-data.co.uk"})
    return out


def read_csv(path: Path) -> list[dict]:
    if not path.exists():
        return []
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def append_csv(path: Path, fields: list[str], rows: list[dict]) -> int:
    if not rows:
        return 0
    path.parent.mkdir(parents=True, exist_ok=True)
    new = not path.exists()
    with path.open("a", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        if new:
            w.writeheader()
        w.writerows(rows)
    return len(rows)


def utcnow() -> datetime:
    return datetime.now(timezone.utc)
