"""Player SOT cycle 2 (pre-registered: research/platform_v2/player_sot/cycle2/PREREGISTRATION.md + IMPLEMENTATION_ADDENDUM.md).

  python scripts/player_sot_cycle2.py gate    <raw_dir> <Matches.csv>   -> cycle2/PHASE1_GATE.json (aggregates only)
  python scripts/player_sot_cycle2.py develop <raw_dir>                 -> cycle2/DEVELOPMENT.json + FROZEN_SPEC.json
  python scripts/player_sot_cycle2.py holdout <raw_dir>                 -> cycle2/HOLDOUT.json (ONCE; committed FROZEN_SPEC required)
gate/develop read ONLY 2022/23 files (players_2022_*.json.gz, fixtures_39_2022.json.gz). Player-level rows are never written to the
repo. No odds are used.
"""
from __future__ import annotations

import gzip
import importlib.util
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

from prediction_markets_lab.research_shadow import player_sot as PS

REPO = Path(__file__).resolve().parents[1]
OUT = REPO / "research/platform_v2/player_sot/cycle2"
SEASON = 2022
DEV_START = "2023-02-01"
MIN_PRIOR_APPS = 3
SEL_GAIN = 0.0005
STRUCT_TOL = 0.0005
RIDGE = 1e-6
FD_NAME = {"Manchester City": "Man City", "Manchester United": "Man United", "Nottingham Forest": "Nottm Forest"}  # run 1 used "Nott'm Forest" (Football-Data odds-file spelling); Matches.csv spells it "Nottm Forest"
FAMILIES = ["F_player", "F_starts", "F_role", "F_team", "F_opp", "F_home"]


def acquire_module():
    spec = importlib.util.spec_from_file_location("apif", REPO / "scripts/api_football_acquire.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def load_json(p: Path) -> dict:
    with gzip.open(p, "rt", encoding="utf-8") as f:
        return json.load(f)


def build_rows(raw: Path, seasons: tuple[int, ...] = (SEASON,)) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Canonical player-match rows + fixture table, from the given seasons' files only (default: 2022/23)."""
    files = sorted(f for s_ in seasons for f in raw.glob(f"players_{s_}_*.json.gz"))
    A = acquire_module()
    rows, fx = [], []
    for f in files:
        d = load_json(f)
        rows += A.rows_from_fixture(d, int(f.name.split("_")[1]))
        fx.append({"match_id": d["fixture"]["id"], "date": d["fixture"]["date"][:10], "home_id": d["teams"]["home"]["id"],
                   "away_id": d["teams"]["away"]["id"], "home_name": d["teams"]["home"]["name"], "away_name": d["teams"]["away"]["name"]})
    df = pd.DataFrame(rows, columns=PS.FIELDS)
    return df, pd.DataFrame(fx)


# ------------------------------------------------------------------ Phase 1
def gate(raw: Path, matches_csv: str) -> dict:
    df, fx = build_rows(raw)
    listed = len(load_json(raw / f"fixtures_39_{SEASON}.json.gz")["response"])
    aud = PS.audit(df)
    n = len(df)
    viol = (aud["violations"]["sot_gt_shots"] + aud["violations"]["goals_gt_sot"]) / max(n, 1)
    minutes_cov = float((df.minutes.notna() & (df.minutes > 0)).mean())
    # team SOT vs Football-Data HST/AST
    team = df.groupby(["match_id", "team_id"]).sot.sum().rename("api_sot").reset_index()
    fdm = pd.read_csv(matches_csv, usecols=["Division", "MatchDate", "HomeTeam", "AwayTeam", "HomeTarget", "AwayTarget"], parse_dates=["MatchDate"])
    fdm = fdm[(fdm.Division == "E0") & (fdm.MatchDate >= "2022-07-01") & (fdm.MatchDate < "2023-07-01")]
    pairs, unmatched = [], []
    for r in fx.itertuples():
        h, a = FD_NAME.get(r.home_name, r.home_name), FD_NAME.get(r.away_name, r.away_name)
        d = pd.Timestamp(r.date)
        m = fdm[(fdm.HomeTeam == h) & (fdm.AwayTeam == a) & ((fdm.MatchDate - d).abs() <= pd.Timedelta(days=1))]
        if len(m) != 1:
            unmatched.append(f"{r.date} {r.home_name} v {r.away_name}")
            continue
        m = m.iloc[0]
        for tid, fd_val in ((r.home_id, m.HomeTarget), (r.away_id, m.AwayTarget)):
            api = team[(team.match_id == r.match_id) & (team.team_id == tid)].api_sot
            pairs.append((float(api.iloc[0]) if len(api) else 0.0, float(fd_val)))
    p = np.array(pairs) if pairs else np.zeros((0, 2))
    ratio = float(p[:, 0].mean() / p[:, 1].mean()) if len(p) else None
    matched_share = 1 - len(unmatched) / max(len(fx), 1)
    checks = {
        "fixtures_files_vs_listed": f"{len(fx)}/{listed}",
        "starters_eq_11_share": aud["starters_per_team_match"]["eq_11"], "gate_starters": aud["starters_per_team_match"]["eq_11"] >= 0.99,
        "duplicates": aud["duplicates_match_player"], "gate_duplicates": aud["duplicates_match_player"] == 0,
        "violation_share": round(viol, 5), "gate_violations": viol < 0.001,
        "minutes_coverage": round(minutes_cov, 5), "gate_minutes": minutes_cov >= 0.99,
        "fd_matched_fixture_share": round(matched_share, 4), "fd_unmatched": unmatched[:20],
        "team_sot_ratio_api_over_fd": None if ratio is None else round(ratio, 4),
        "team_sot_exact_agreement_share": round(float((p[:, 0] == p[:, 1]).mean()), 4) if len(p) else None,
        "team_sot_mean_abs_diff": round(float(np.abs(p[:, 0] - p[:, 1]).mean()), 4) if len(p) else None,
        "gate_team_sot": ratio is not None and 0.95 <= ratio <= 1.05 and matched_share >= 0.95}
    passed = all(v for k, v in checks.items() if k.startswith("gate_"))
    return {"season": "2022-23", "audit": aud, "checks": checks, "verdict": "PASS" if passed else "FAIL"}


# ------------------------------------------------------------------ Phase 2
def prepare(raw: Path) -> pd.DataFrame:
    df, _ = build_rows(raw)
    d = PS.add_targets(PS.prior_features(df))
    d["date"] = pd.to_datetime(d.date)
    return d[d.starter & d.role.isin(["DF", "MD", "FW"]) & (d.p_apps_prior >= MIN_PRIOR_APPS)].copy()


def role_rates(train: pd.DataFrame) -> dict:
    g = train.groupby("role")
    return {"sot90": (g.sot.sum() / g.minutes.sum() * PS.FULL_MATCH).to_dict(),
            "shots90": (g.shots.sum() / g.minutes.sum() * PS.FULL_MATCH).to_dict(),
            "team_sot": float(train.groupby(["match_id", "team_id"]).sot.sum().mean())}


def family_cols(d: pd.DataFrame, r: dict) -> dict[str, dict[str, np.ndarray]]:
    w = PS.SHRINK_MINUTES / PS.FULL_MATCH
    mins90 = d.p_minutes_prior.fillna(0).to_numpy() / PS.FULL_MATCH
    prior_sot = np.array([r["sot90"].get(x, 0.3) for x in d.role]) * w
    prior_sh = np.array([r["shots90"].get(x, 1.0) for x in d.role]) * w
    sot90 = (d.p_sot_prior.fillna(0).to_numpy() + prior_sot) / (mins90 + w)
    sh90 = (d.p_shots_prior.fillna(0).to_numpy() + prior_sh) / (mins90 + w)
    return {"F_player": {"sot90": np.log1p(sot90), "sh90": np.log1p(sh90)},
            "F_starts": {"starts": (d.p_starts_prior / d.p_apps_prior.clip(lower=1)).to_numpy(float)},
            "F_role": {"MD": (d.role == "MD").astype(float).to_numpy(), "FW": (d.role == "FW").astype(float).to_numpy()},
            "F_team": {"team": np.log(d.team_sot_for_prior.fillna(r["team_sot"]).clip(lower=0.5).to_numpy(float))},
            "F_opp": {"opp": np.log(d.opp_sot_conceded_prior.fillna(r["team_sot"]).clip(lower=0.5).to_numpy(float))},
            "F_home": {"home": d.home.astype(float).to_numpy()}}


INTERACT = {"F_player": "sot90", "F_team": "team", "F_opp": "opp"}


def design(d: pd.DataFrame, r: dict, fams: list[str], structure: str) -> np.ndarray:
    fc = family_cols(d, r)
    cols = [np.ones(len(d))]
    for f in fams:
        if structure == "S3" and f == "F_role":
            continue
        cols += list(fc[f].values())
    if structure == "S2":
        md, fw = fc["F_role"]["MD"], fc["F_role"]["FW"]
        if "F_role" not in fams:
            cols += [md, fw]
        for f in fams:
            if f in INTERACT:
                x = fc[f][INTERACT[f]]
                cols += [x * md, x * fw]
    return np.column_stack(cols)


def irls(X: np.ndarray, y: np.ndarray) -> np.ndarray:
    b = np.zeros(X.shape[1]); b[0] = np.log(y.mean() / (1 - y.mean()))
    for _ in range(100):
        mu = 1 / (1 + np.exp(-np.clip(X @ b, -15, 15)))
        w = np.clip(mu * (1 - mu), 1e-9, None)
        new = np.linalg.solve(X.T @ (X * w[:, None]) + RIDGE * np.eye(X.shape[1]), X.T @ (w * (X @ b + (y - mu) / w)))
        if np.max(np.abs(new - b)) < 1e-9:
            return new
        b = new
    return b


def fit_predict(tr: pd.DataFrame, te: pd.DataFrame, fams: list[str], structure: str, target: str) -> np.ndarray:
    r = role_rates(tr)
    if structure != "S3":
        b = irls(design(tr, r, fams, structure), tr[target].to_numpy(float))
        return 1 / (1 + np.exp(-(design(te, r, fams, structure) @ b)))
    out = np.zeros(len(te))
    for role in ("DF", "MD", "FW"):
        mtr, mte = (tr.role == role).to_numpy(), (te.role == role).to_numpy()
        b = irls(design(tr[mtr], r, fams, "S3"), tr[mtr][target].to_numpy(float))
        out[mte] = 1 / (1 + np.exp(-(design(te[mte], r, fams, "S3") @ b)))
    return out


def ll(y, p) -> float:
    p = np.clip(p, 1e-6, 1 - 1e-6)
    return float(-(y * np.log(p) + (1 - y) * np.log(1 - p)).mean())


def baselines(tr: pd.DataFrame, te: pd.DataFrame, target: str) -> dict[str, np.ndarray]:
    b0 = PS.baseline_role_rate(tr.assign(competition="EPL"), te.assign(competition="EPL"), target)
    b1_te, b1_tr = PS.baseline_player_rate(tr, te, target), PS.baseline_player_rate(tr, tr, target)
    x_tr = np.log(b1_tr / (1 - b1_tr))
    c = irls(np.column_stack([np.ones_like(x_tr), x_tr]), tr[target].to_numpy(float))
    x_te = np.log(b1_te / (1 - b1_te))
    b2 = 1 / (1 + np.exp(-(c[0] + c[1] * x_te)))
    return {"B0": b0, "B1": b1_te, "B2": b2}


def develop(raw: Path) -> tuple[dict, dict]:
    d = prepare(raw)
    tr, dv = d[d.date < DEV_START], d[d.date >= DEV_START]
    y = dv.sot_1plus.to_numpy(float)
    res = {"n_train": int(len(tr)), "n_dev": int(len(dv)), "base_rate_dev_1plus": round(float(y.mean()), 4), "selection_path": []}
    chosen: list[str] = []
    cur = ll(y, np.full(len(dv), tr.sot_1plus.mean()))
    res["selection_path"].append({"families": [], "dev_logloss": round(cur, 6)})
    while True:
        trial = {f: ll(y, fit_predict(tr, dv, chosen + [f], "S1", "sot_1plus")) for f in FAMILIES if f not in chosen}
        if not trial:
            break
        f, v = min(trial.items(), key=lambda kv: kv[1])
        res["selection_path"].append({"candidates": {k: round(x, 6) for k, x in trial.items()}, "best": f, "gain": round(cur - v, 6)})
        if cur - v < SEL_GAIN:
            break
        chosen.append(f)
        cur = v
    res["families_selected"] = chosen
    st = {s: ll(y, fit_predict(tr, dv, chosen, s, "sot_1plus")) for s in ("S1", "S2", "S3")}
    best = min(st.values())
    structure = next(s for s in ("S1", "S2", "S3") if st[s] <= best + STRUCT_TOL)
    res["structures_dev_logloss"] = {k: round(v, 6) for k, v in st.items()}
    res["structure_selected"] = structure
    res["targets"] = {}
    for t in PS.TARGETS:
        yt = dv[t].to_numpy(float)
        pa = fit_predict(tr, dv, chosen, structure, t)
        bl = baselines(tr, dv, t)
        res["targets"][t] = {"model": PS.evaluate(yt, pa), "baselines": {k: PS.evaluate(yt, v) for k, v in bl.items()},
                             "by_role": {r_: {"n": int((dv.role == r_).sum()), "model_ll": round(ll(yt[(dv.role == r_).to_numpy()], pa[(dv.role == r_).to_numpy()]), 6)}
                                         for r_ in ("DF", "MD", "FW")}}
    comp = min(("B0", "B1", "B2"), key=lambda b: res["targets"]["sot_1plus"]["baselines"][b]["logloss"])
    res["comparator"] = comp
    res["delta_dev_sot_1plus"] = round(res["targets"]["sot_1plus"]["model"]["logloss"] - res["targets"]["sot_1plus"]["baselines"][comp]["logloss"], 6)
    spec = {"cycle": 2, "families": chosen, "structure": structure, "comparator": comp, "targets": list(PS.TARGETS),
            "population": "outfield starters, >=3 prior appearances", "refit_rule": "refit on all 2022-23 rows, then score the sealed holdout once",
            "shrink_minutes": PS.SHRINK_MINUTES, "ridge": RIDGE, "prior_window": PS.PRIOR_WINDOW,
            "verdict_rules": "PREREGISTRATION.md 'Verdict (fixed)'", "addendum_commit": "464da1b"}
    return res, spec


HOLDOUT_SEASONS = (2023, 2024)
HOLDOUT_START = "2023-07-01"
BOOT, BOOT_SEED, MATERIAL, MIN_ROLE_N, MIN_N = 1000, 7, -0.004, 1000, 5000


def boot_ci(diff: np.ndarray, groups: np.ndarray) -> list[float]:
    rng = np.random.default_rng(BOOT_SEED)
    ug = np.unique(groups)
    idx = {g: np.where(groups == g)[0] for g in ug}
    m = [np.concatenate([diff[idx[g]] for g in rng.choice(ug, len(ug))]).mean() for _ in range(BOOT)]
    return [round(float(np.percentile(m, 2.5)), 6), round(float(np.percentile(m, 97.5)), 6)]


def lls(y, p) -> np.ndarray:
    p = np.clip(p, 1e-6, 1 - 1e-6)
    return -(y * np.log(p) + (1 - y) * np.log(1 - p))


def holdout(raw: Path) -> dict:
    """Scored ONCE. TRAIN = all 2022/23 (refit rule); HOLDOUT = 2023/24 + 2024/25. Priors computed on the full sequence
    (strictly earlier matches only)."""
    spec = PS.HoldoutGuard(OUT / "FROZEN_SPEC.json", OUT / "HOLDOUT_OPENED.marker").open(_committed)
    df, _ = build_rows(raw, (SEASON,) + HOLDOUT_SEASONS)
    d = PS.add_targets(PS.prior_features(df))
    d["date"] = pd.to_datetime(d.date)
    d = d[d.starter & d.role.isin(["DF", "MD", "FW"]) & (d.p_apps_prior >= MIN_PRIOR_APPS)].copy()
    tr, te = d[d.date < HOLDOUT_START], d[d.date >= HOLDOUT_START].sort_values("date")
    half = te.date.iloc[len(te) // 2]
    res = {"spec": spec, "n_train": int(len(tr)), "n_holdout": int(len(te)), "half_split_date": str(half.date()), "targets": {}}
    for t in PS.TARGETS:
        y = te[t].to_numpy(float)
        pa = fit_predict(tr, te, spec["families"], spec["structure"], t)
        pb = baselines(tr, te, t)[spec["comparator"]]
        diff = lls(y, pa) - lls(y, pb)
        res["targets"][t] = {"model": PS.evaluate(y, pa), "comparator": PS.evaluate(y, pb), "delta": round(float(diff.mean()), 6),
                             "ci95_match_bootstrap": boot_ci(diff, te.match_id.to_numpy()),
                             "by_role": {r_: {"n": int((te.role == r_).sum()), "delta": round(float(diff[(te.role == r_).to_numpy()].mean()), 6)} for r_ in ("DF", "MD", "FW")},
                             "halves": {"first": round(float(diff[(te.date < half).to_numpy()].mean()), 6), "second": round(float(diff[(te.date >= half).to_numpy()].mean()), 6)},
                             "by_season": {s_: round(float(diff[(te.season == s_).to_numpy()].mean()), 6) for s_ in sorted(te.season.unique())}}
    p1 = res["targets"]["sot_1plus"]
    if len(te) < MIN_N:
        res["verdict"] = "REPORT_ONLY"
        return res
    crit = {"1_material_ci": p1["delta"] <= MATERIAL and p1["ci95_match_bootstrap"][1] < 0,
            "2_calibration": 0.85 <= p1["model"]["cal_slope"] <= 1.15 and abs(p1["model"]["cal_intercept"]) <= 0.10,
            "3_positions": all(v["n"] >= MIN_ROLE_N and v["delta"] < 0 for v in p1["by_role"].values()),
            "4_halves": p1["halves"]["first"] < 0 and p1["halves"]["second"] < 0, "5_n": len(te) >= MIN_N}
    res["criteria"] = crit
    res["verdict"] = "MODERN_VALIDATED" if all(crit.values()) else "NOT_VALIDATED"
    return res


def _committed(p: Path) -> bool:
    import subprocess
    rel = p.relative_to(REPO).as_posix()
    return (subprocess.run(["git", "ls-files", "--error-unmatch", rel], cwd=REPO, capture_output=True).returncode == 0
            and subprocess.run(["git", "diff", "--quiet", "HEAD", "--", rel], cwd=REPO).returncode == 0)


def main() -> int:
    mode = sys.argv[1]
    raw = Path(sys.argv[2])
    if mode == "gate":
        res = gate(raw, sys.argv[3])
        (OUT / "PHASE1_GATE.json").write_text(json.dumps(res, indent=1, default=str) + "\n")
        print(json.dumps(res["checks"], indent=1, default=str), res["verdict"])
    elif mode == "holdout":
        res = holdout(raw)
        (OUT / "HOLDOUT.json").write_text(json.dumps(res, indent=1, default=str) + "\n")
        print(json.dumps({k: v for k, v in res.items() if k != "spec"}, indent=1, default=str)[:6000])
    else:
        g = json.loads((OUT / "PHASE1_GATE.json").read_text())
        assert g["verdict"] == "PASS", "Phase 1 gate must PASS before development"
        res, spec = develop(raw)
        (OUT / "DEVELOPMENT.json").write_text(json.dumps(res, indent=1, default=str) + "\n")
        (OUT / "FROZEN_SPEC.json").write_text(json.dumps(spec, indent=1) + "\n")
        print(json.dumps({k: v for k, v in res.items() if k != "targets"}, indent=1, default=str))
        print(json.dumps(res["targets"]["sot_1plus"], indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
