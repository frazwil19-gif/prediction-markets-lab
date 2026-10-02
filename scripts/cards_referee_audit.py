"""Cards — referee data audit (pre-registered: research/platform_v2/props_c1/cards/REFEREE_AUDIT_PREREGISTRATION.md).

Data preparation only; not a cards modelling cycle. Usage:
  python scripts/cards_referee_audit.py <football_data_co_uk root containing E0/E1/SC0/<season>/<DIV>.csv>
Writes research/platform_v2/props_c1/cards/REFEREE_AUDIT.json.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

OUT = Path(__file__).resolve().parents[1] / "research/platform_v2/props_c1/cards/REFEREE_AUDIT.json"
DIVS = ["E0", "E1", "SC0"]
SPLIT = pd.Timestamp("2023-07-01")
K_SHRINK = 10
WIN, MINP, LEAGUE_MIN = 10, 5, 50
MIN_REF_MATCHES = 20
BOOT, SEED = 1000, 7
LINES = (3.5, 4.5)


def norm_ref(s: object) -> str | None:
    if not isinstance(s, str) or not s.strip():
        return None
    x = re.sub(r"[.\s]+", " ", s.strip()).strip().lower()
    return x


def load(root: Path) -> pd.DataFrame:
    frames = []
    for div in DIVS:
        for f in sorted((root / div).glob(f"*/{div}.csv")):
            t = pd.read_csv(f, encoding="latin-1")
            t["Division"], t["season"] = div, f.parent.name
            frames.append(t[["Division", "season", "Date", "HomeTeam", "AwayTeam", "Referee", "HY", "AY", "HR", "AR"]])
    d = pd.concat(frames, ignore_index=True)
    d["date"] = pd.to_datetime(d.Date, dayfirst=True, format="mixed")
    d["ref_raw"] = d.Referee
    d["ref"] = d.Referee.map(norm_ref)
    d["cards"] = d.HY + d.AY + d.HR + d.AR
    return d.sort_values(["date", "Division", "HomeTeam"]).reset_index(drop=True)


def ll(y: np.ndarray, p: np.ndarray) -> np.ndarray:
    p = np.clip(p, 1e-9, 1 - 1e-9)
    return -(y * np.log(p) + (1 - y) * np.log(1 - p))


def irls(X: np.ndarray, y: np.ndarray) -> np.ndarray:
    b = np.zeros(X.shape[1])
    b[0] = np.log(y.mean())
    for _ in range(50):
        mu = np.exp(X @ b)
        new = np.linalg.solve(X.T @ (X * mu[:, None]), X.T @ (mu * (X @ b + (y - mu) / mu)))
        if np.max(np.abs(new - b)) < 1e-10:
            return new
        b = new
    return b


def features(d: pd.DataFrame) -> pd.DataFrame:
    d = d.copy()
    d["league_mean"] = d.groupby("Division").cards.transform(lambda s: s.shift(1).expanding(min_periods=LEAGUE_MIN).mean())
    long = pd.concat([pd.DataFrame({"i": d.index, "team": d.HomeTeam, "div": d.Division, "side": "h", "f": d.HY + d.HR, "a": d.AY + d.AR}),
                      pd.DataFrame({"i": d.index, "team": d.AwayTeam, "div": d.Division, "side": "a", "f": d.AY + d.AR, "a": d.HY + d.HR})]).sort_values("i")
    g = long.groupby(["div", "team"])
    for c in ("f", "a"):
        long["r_" + c] = g[c].transform(lambda s: s.shift(1).rolling(WIN, min_periods=MINP).mean())
    h = long[long.side == "h"].set_index("i")
    a = long[long.side == "a"].set_index("i")
    d["team_f"] = h.r_f + a.r_f
    d["team_a"] = h.r_a + a.r_a
    # referee shrunken prior rate: strictly prior matches of that referee
    rg = d.groupby("ref")
    prior_sum = rg.cards.transform(lambda s: s.shift(1).cumsum()).fillna(0)
    prior_n = rg.cumcount()
    d["ref_prior_n"] = prior_n
    d["ref_rate"] = (prior_sum + K_SHRINK * d.league_mean) / (prior_n + K_SHRINK)
    d.loc[d.ref.isna(), "ref_rate"] = d.league_mean
    d["ref_log_ratio"] = np.log(d.ref_rate / d.league_mean)
    return d


def run(root: Path) -> dict:
    d = load(root)
    out: dict = {"divisions": DIVS, "n_matches": int(len(d))}
    out["referee_missing_by_div_season"] = {f"{k[0]} {k[1]}": round(float(v), 4) for k, v in d.groupby(["Division", "season"]).ref.apply(lambda s: s.isna().mean()).items()}
    variants = d.dropna(subset=["ref"]).groupby("ref").ref_raw.unique()
    out["identity"] = {"distinct_raw": int(d.ref_raw.nunique()), "distinct_normalised": int(d.ref.nunique()),
                       "normalisation_merges": {k: list(map(str, v)) for k, v in variants.items() if len(v) > 1}}
    # possible same-person variants not merged by the normaliser (same surname, different first token)
    sur = pd.Series({r: r.split()[-1] for r in d.ref.dropna().unique()})
    out["identity"]["same_surname_groups_review"] = {s: sorted(g.index) for s, g in sur.groupby(sur) if len(g) > 1}
    m = d.ref.value_counts()
    out["matches_per_referee"] = {"n_referees": int(len(m)), "median": float(m.median()), "p90": float(m.quantile(.9)),
                                  f"n_with_>={MIN_REF_MATCHES}": int((m >= MIN_REF_MATCHES).sum()),
                                  f"share_matches_by_refs_>={MIN_REF_MATCHES}": round(float(m[m >= MIN_REF_MATCHES].sum() / m.sum()), 4),
                                  "refs_officiating_in_multiple_divisions": int((d.dropna(subset=["ref"]).groupby("ref").Division.nunique() > 1).sum())}
    # season-to-season stability of referee card rates (relative to division-season mean)
    d["rel"] = d.cards - d.groupby(["Division", "season"]).cards.transform("mean")
    rs = d.dropna(subset=["ref"]).groupby(["ref", "season"]).agg(rel=("rel", "mean"), n=("rel", "size")).reset_index()
    rs = rs[rs.n >= 10]
    seasons = sorted(d.season.unique())
    pairs = []
    for s0, s1 in zip(seasons, seasons[1:]):
        a = rs[rs.season == s0].set_index("ref").rel
        b = rs[rs.season == s1].set_index("ref").rel
        j = a.index.intersection(b.index)
        pairs += [(a[r], b[r]) for r in j]
    pairs = np.array(pairs)
    rho, pv = stats.pearsonr(pairs[:, 0], pairs[:, 1])
    out["rate_stability"] = {"referee_season_pairs_(n>=10_matches_each)": int(len(pairs)), "pearson_r_t_vs_t+1": round(float(rho), 3),
                             "p_value": float(pv), "sd_referee_season_relative_rate": round(float(rs.rel.std()), 3)}
    # out-of-sample test R0/R1/R2
    f = features(d).dropna(subset=["league_mean", "team_f", "team_a", "cards"])
    tr, te = f[f.date < SPLIT], f[f.date >= SPLIT]
    y = te.cards.to_numpy(float)
    mus = {"R0": te.league_mean.to_numpy()}
    for name, cols in (("R1", ["team_f", "team_a", "league_mean"]), ("R2", ["team_f", "team_a", "league_mean", "ref_log_ratio"])):
        X = lambda t: np.column_stack([np.ones(len(t))] + [np.log(t[c].clip(lower=0.05)) if c != "ref_log_ratio" else t[c] for c in cols])
        b = irls(X(tr), tr.cards.to_numpy(float))
        mus[name] = np.exp(X(te) @ b)
        if name == "R2":
            out["R2_referee_coef"] = round(float(b[-1]), 4)
    rng = np.random.default_rng(SEED)
    res = {"n_train": int(len(tr)), "n_test": int(len(te)), "test_mean_cards": round(float(y.mean()), 3),
           "test_var_over_mean": round(float(y.var() / y.mean()), 3), "lines": {}}
    for L in LINES:
        yb = (y > L).astype(float)
        p = {k: 1 - stats.poisson.cdf(int(L), mu) for k, mu in mus.items()}
        lls = {k: ll(yb, v) for k, v in p.items()}
        diff = lls["R2"] - lls["R1"]
        n = len(diff)
        bs = [diff[rng.integers(0, n, n)].mean() for _ in range(BOOT)]
        res["lines"][str(L)] = {"base_rate": round(float(yb.mean()), 4), **{f"logloss_{k}": round(float(v.mean()), 5) for k, v in lls.items()},
                                "d_logloss_R2_minus_R1": round(float(diff.mean()), 5),
                                "ci95": [round(float(np.percentile(bs, 2.5)), 5), round(float(np.percentile(bs, 97.5)), 5)],
                                "d_logloss_R1_minus_R0": round(float((lls["R1"] - lls["R0"]).mean()), 5)}
    res["referee_adds_information"] = all(v["ci95"][1] < 0 for v in res["lines"].values())
    out["oos_test"] = res
    out["card_counting"] = {"mean_HY_plus_AY": round(float((d.HY + d.AY).mean()), 3), "mean_HR_plus_AR": round(float((d.HR + d.AR).mean()), 3),
                            "note": "Football-Data HY/AY/HR/AR; a second yellow is recorded as a red (whether its first yellow stays in HY "
                                    "is not documented) — bookmaker 'total cards' and 'booking points' definitions must be mapped per venue."}
    return out


def main() -> int:
    out = run(Path(sys.argv[1]))
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(out, indent=1, default=str) + "\n")
    show = {k: v for k, v in out.items() if k not in ("referee_missing_by_div_season",)}
    show["identity"] = {k: v for k, v in out["identity"].items()}
    print(json.dumps(show, indent=1, default=str)[:5000])
    print("missing:", {k: v for k, v in out["referee_missing_by_div_season"].items() if v > 0})
    return 0


if __name__ == "__main__":
    sys.exit(main())
