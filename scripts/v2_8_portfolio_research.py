"""V2-8 bet-portfolio / card-allocation research (RESEARCH ONLY; EXPLORATORY on previously examined V2-7H data).
Pre-registration: research/platform_v2/portfolio_v2_8/PREREGISTRATION.md.

Never touches production, bsv2-3, frozen engines or the V2-7 prospective logger. Multi prices are INDICATIVE; SYNTH prices are
synthetic (risk/structure description only).
Usage: python scripts/v2_8_portfolio_research.py --data /mnt/user-data/uploads/prediction-markets-lab/data
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import math
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

from prediction_markets_lab.research import card_backtest as CB
from prediction_markets_lab.research import portfolio as PF

REPO = Path(__file__).resolve().parents[1]
OUT = REPO / "research/platform_v2/portfolio_v2_8"
SEED = 20260930
FRACS = (0.01, 0.02, 0.05)
DELTAS = (-0.05, -0.03, -0.02, -0.015, -0.01, -0.005, 0.005, 0.01, 0.015, 0.02, 0.03, 0.05)
SYNTH = {"SYNTH_M0": lambda p: 1 / p, "SYNTH_M5": lambda p: 1 / (p * 1.05), "SYNTH_EDGE3": lambda p: 1.03 / p}
BANKS, BANK_F, MINS = (20, 30, 50, 100), (0.02, 0.05), (0.10, 1.00)


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


BT = _load("v27h", REPO / "scripts/v2_7h_card_backtest.py")


# ---------------------------------------------------------------- candidate sets (outcome-free selection)
def candidate_sets(legs: pd.DataFrame, n: int, quotes: pd.DataFrame | None = None, pos_ev: bool = False,
                   pmin: float = 0.70) -> tuple[list[dict], dict]:
    """Top-n legs by P (P >= pmin, distinct participants) per sport-day. With quotes: all n legs must be priced at ONE book in
    the same snapshot; the book with the highest product of the n prices is used (V2-7H A2). pos_ev: only legs with EV > 0 at
    that book (then pmin = 0.5)."""
    sets, cnt = [], {"days": 0, "days_with_set": 0, "days_no_single_book": 0}
    qd = dict(tuple(quotes.groupby("day"))) if quotes is not None else {}
    won = legs.set_index("event")["won"]
    for day, g in legs.groupby("day", sort=True):
        cnt["days"] += 1
        rows = CB.strip_outcomes(g).to_dict("records")
        if quotes is None:
            cand = [r for r in rows if r["p"] >= pmin]
            sel = CB.pick_top(cand, n, lambda r: r["p"])
            if sel is None:
                continue
            evs = [r["event"] for r in sel]
            o, book = None, "SYNTH"
        else:
            q = qd.get(day)
            if q is None:
                continue
            q = CB.strip_outcomes(q[q.book.isin(BT.MULTI_BOOKS if n >= 2 else tuple(BT.PRIMARY_BOOKS))])
            best = None
            if pos_ev:
                # POS_EV: per book, top-n by P among EV > 0; the book with the highest JOINT P is used (probability first)
                for bk, gb in q.groupby("book", sort=True):
                    sel = CB.pick_top([r for r in gb.to_dict("records") if r["ev"] > 0], n, lambda r: r["p"])
                    if sel is None:
                        continue
                    key = (math.prod(r["p"] for r in sel), math.prod(r["odds_net"] for r in sel))
                    if best is None or key > best[0]:
                        best = (key, bk, sel)
            else:
                # HIGH_P (erratum E1 fix): fix the n strongest predictions FIRST, then the book pricing all n at the best product
                top = CB.pick_top([r for r in rows if r["p"] >= pmin], n, lambda r: r["p"])
                if top is None:
                    continue
                want = [r["event"] for r in top]
                for bk, gb in q.groupby("book", sort=True):
                    m = {r["event"]: r for r in gb.to_dict("records")}
                    if all(e in m for e in want):
                        sel = [m[e] for e in want]
                        key = (math.prod(r["odds_net"] for r in sel),)
                        if best is None or key > best[0]:
                            best = (key, bk, sel)
            if best is None:
                cnt["days_no_single_book"] += 1
                continue
            _, book, sel = best
            evs = [r["event"] for r in sel]
            o = np.array([r["odds_net"] for r in sel])
        p = np.array([r["p"] for r in sel])
        order = np.argsort(-p, kind="stable")
        evs = [evs[i] for i in order]
        p = p[order]
        o = o[order] if o is not None else None
        y = np.array([int(won.loc[e]) for e in evs])        # outcomes revealed after the set is frozen
        sets.append({"day": day, "period": BT.period_of(legs.sport.iloc[0], g.period.iloc[0]), "events": evs, "p": p, "o": o,
                     "y": y, "book": book})
        cnt["days_with_set"] += 1
    return sets, cnt


# ---------------------------------------------------------------- analyses
def prediction_scoreboard(sets: list[dict]) -> dict:
    n = len(sets[0]["p"])
    out = {}
    for r in range(n):
        p = np.array([s["p"][r] for s in sets])
        y = np.array([s["y"][r] for s in sets])
        out[f"rank{r+1}"] = CB.calib_metrics(p, y, np.array([s["day"] for s in sets]), recal=False)
    p = np.concatenate([s["p"] for s in sets])
    y = np.concatenate([s["y"] for s in sets])
    d = np.concatenate([[s["day"]] * n for s in sets])
    out["all_legs"] = CB.calib_metrics(p, y, d, recal=False)
    return out


def card_size(sets: list[dict]) -> dict:
    n = len(sets[0]["p"])
    out = {}
    for k in range(1, n + 1):
        pj = np.array([np.prod(s["p"][:k]) for s in sets])
        yj = np.array([int(s["y"][:k].all()) for s in sets])
        m = CB.calib_metrics(pj, yj, np.array([s["day"] for s in sets]), recal=False)
        dist = PF.poisson_binomial(np.mean([s["p"][:k] for s in sets], axis=0))
        out[f"ACC_{k}"] = {"calibration": m, "mean_p_joint": round(float(pj.mean()), 4),
                           "mean_legs_correct_pred": round(float(np.mean([s["p"][:k].sum() for s in sets])), 3),
                           "mean_legs_correct_obs": round(float(np.mean([s["y"][:k].sum() for s in sets])), 3),
                           "legs_correct_pmf_at_mean_p": [round(x, 4) for x in dist]}
    return out


def marginal(sets: list[dict], prices: str, se_fn) -> dict:
    rows = []
    for s in sets:
        o = s["o"] if prices == "REAL" else SYNTH[prices](s["p"])
        se = np.array([se_fn(x) for x in s["p"]])
        rows.append(PF.marginal_path(s["p"], o, se))
    n = len(rows[0])
    out = {}
    for k in range(n):
        col = [r[k] for r in rows]
        imp = [col_k["kelly_growth"] > rows[i][k - 1]["kelly_growth"] + 1e-15 for i, col_k in enumerate(col)] if k else None
        worse_s = [col_k["growth_at_s"] < rows[i][k - 1]["growth_at_s"] for i, col_k in enumerate(col)] if k else None
        out[f"ACC_{k+1}"] = {m: round(float(np.mean([c[m] for c in col])), 6) for m in
                             ("p_joint", "fair_odds", "odds", "ev", "sigma", "implied_margin", "growth_at_s", "kelly_fraction",
                              "kelly_growth", "p_full_loss")}
        if k:
            out[f"ACC_{k+1}"]["share_days_leg_improves_kelly_growth"] = round(float(np.mean(imp)), 4)
            out[f"ACC_{k+1}"]["share_days_growth_at_1pct_falls"] = round(float(np.mean(worse_s)), 4)
    return out


def boot_mean_ci(x: np.ndarray, rng, n_boot: int = 2000) -> list:
    if len(x) < 2:
        return [None, None]
    idx = rng.integers(0, len(x), size=(n_boot, len(x)))
    m = x[idx].mean(1)
    return [round(float(np.percentile(m, 2.5)), 7), round(float(np.percentile(m, 97.5)), 7)]


def portfolio_section(sets: list[dict], prices: str, se_fn) -> dict:
    n = len(sets[0]["p"])
    S = PF.structures(n)
    rng = np.random.default_rng(SEED)
    res = {}
    base_rets = {}
    for name, lines in S.items():
        model = {k: [] for k in ("expected_return", "sd", "max_loss", "p_full_loss", "p_positive", "p_negative", "exp_log_growth")}
        realised = []
        sens = {d: [] for d in DELTAS}
        emp = []
        for s in sets:
            o = s["o"] if prices == "REAL" else SYNTH[prices](s["p"])
            d = PF.distribution(s["p"], o, lines, f=0.02)
            for k in model:
                model[k].append(d[k])
            realised.append(PF.realised(o, s["y"], lines))
            for dl in DELTAS:
                sens[dl].append(PF.distribution(np.clip(s["p"] - dl, 1e-4, 1 - 1e-4), o, lines, f=0.02))
            se = np.array([se_fn(x) for x in s["p"]])
            emp.append(PF.distribution(np.clip(s["p"] - se, 1e-4, 1), o, lines, f=0.02)["expected_return"])
        r = np.array(realised)
        entry = {"n_lines": len(lines), **PF.exposure(lines, n),
                 "model_mean": {k: round(float(np.mean(v)), 6) for k, v in model.items()},
                 "realised_mean_return_per_unit": round(float(r.mean()), 5), "realised_ci95": boot_mean_ci(r, rng),
                 "realised_full_loss_share": round(float(np.mean(np.isclose(r, -1.0))), 4),
                 "realised_positive_share": round(float(np.mean(r > 1e-12)), 4),
                 "sensitivity_mean_expected_return": {f"{dl*100:+.1f}pp": round(float(np.mean([x["expected_return"] for x in v])), 5)
                                                      for dl, v in sens.items()},
                 "sensitivity_mean_exp_log_growth_2pct": {f"{dl*100:+.1f}pp": round(float(np.mean([x["exp_log_growth"] for x in v])), 7)
                                                          for dl, v in sens.items()},
                 "empirical_band_se_expected_return": round(float(np.mean(emp)), 5)}
        # delta* where mean expected return hits 0 (overestimate direction)
        def mean_er(dl):
            return float(np.mean([PF.distribution(np.clip(s["p"] - dl, 1e-4, 1 - 1e-4),
                                                  s["o"] if prices == "REAL" else SYNTH[prices](s["p"]), lines)["expected_return"]
                                  for s in sets]))
        if mean_er(0.0) > 0:
            lo, hi = 0.0, 0.10
            for _ in range(25):
                m = (lo + hi) / 2
                lo, hi = (m, hi) if mean_er(m) > 0 else (lo, m)
            entry["delta_star_to_zero_ev_pp"] = round(100 * lo, 3)
        else:
            entry["delta_star_to_zero_ev_pp"] = 0.0
        for f in FRACS:
            lr = np.log1p(f * r)
            bank = np.exp(np.cumsum(lr))
            peak = np.maximum.accumulate(np.concatenate([[1.0], bank]))
            run = best = 0
            for x in lr:
                run = run + 1 if x < 0 else 0
                best = max(best, run)
            idx = rng.integers(0, len(lr), size=(500, len(lr)))
            entry[f"realised_f{f}"] = {"mean_log_return": round(float(lr.mean()), 7), "ci95": boot_mean_ci(lr, rng),
                                       "final_bankroll": round(float(bank[-1]), 4),
                                       "max_drawdown": round(float(np.max(1 - np.concatenate([[1.0], bank]) / peak)), 4),
                                       "longest_losing_run": best,
                                       "p_bankroll_below_half": round(float(np.mean(np.cumsum(lr[idx], 1).min(1) < math.log(0.5))), 4)}
            base_rets[(name, f)] = lr
        res[name] = entry
    # comparisons vs SINGLES (paired days)
    for name in S:
        for f in FRACS:
            d = base_rets[(name, f)] - base_rets[("SINGLES", f)]
            ci = boot_mean_ci(d, rng)
            v = ("INSUFFICIENT_DAYS" if len(d) < 30 else "SAME" if name == "SINGLES" else
                 "STRUCTURE_BETTER" if ci[0] is not None and ci[0] > 0 else "SINGLES_BETTER" if ci[1] is not None and ci[1] < 0
                 else "NO_DIFFERENCE_DETECTED")
            res[name][f"vs_singles_f{f}"] = {"mean_diff": round(float(d.mean()), 7), "ci95": ci, "verdict": v}
        # growth-advantage tolerance vs SINGLES at f = 2% (model), over the delta grid
        adv = {k: res[name]["sensitivity_mean_exp_log_growth_2pct"][k] - res["SINGLES"]["sensitivity_mean_exp_log_growth_2pct"][k]
               for k in res[name]["sensitivity_mean_exp_log_growth_2pct"]}
        res[name]["model_growth_advantage_vs_singles_2pct_by_delta"] = {k: round(v, 7) for k, v in adv.items()}
    res["NO_BET"] = {"model_mean": {"expected_return": 0.0, "p_full_loss": 0.0}, "realised_mean_return_per_unit": 0.0}
    return res


def bankroll_section(sets: list[dict], prices: str) -> dict:
    n = len(sets[0]["p"])
    days = [{"p": s["p"], "o": s["o"] if prices == "REAL" else SYNTH[prices](s["p"]), "y": s["y"]} for s in sets]
    out = {}
    for name, lines in PF.structures(n).items():
        for b in BANKS:
            for f in BANK_F:
                for mn in MINS:
                    r = PF.bankroll_path(days, lines, float(b), f, mn)
                    r.pop("_rets")
                    out[f"{name}|B{b}|f{f}|min{mn}"] = r
    return out


def run_block(label: str, sets: list[dict], prices: str, se_fn, with_bank: bool) -> dict:
    blk = {"label": label, "sets": len(sets)}
    if len(sets) < 5:
        blk["note"] = "too few sets"
        return blk
    blk["prediction_scoreboard"] = prediction_scoreboard(sets)
    blk["card_size"] = card_size(sets)
    blk["marginal_leg"] = marginal(sets, prices, se_fn)
    for per in ("development", "holdout", "all"):
        ss = sets if per == "all" else [s for s in sets if s["period"] == per]
        if len(ss) >= 5:
            blk[f"portfolios_{per}"] = portfolio_section(ss, prices, se_fn)
    if with_bank:
        blk["bankroll_realism_all_days"] = bankroll_section(sets, prices)
    ps, ys = [s["p"] for s in sets], [s["y"] for s in sets]
    blk["legs_correct_gof"] = PF.gof_count(ps, [int(y.sum()) for y in ys])
    blk["near_miss"] = PF.near_miss(ps, ys)
    return blk


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", type=Path, required=True)
    ap.add_argument("--cache", type=Path, default=Path("/tmp/claude-0/v2_7h_cache"))
    a = ap.parse_args()
    a.cache.mkdir(parents=True, exist_ok=True)
    t0 = time.time()
    canon = a.data / "processed/tennis/cycle_002_canonical_matches.csv"
    legs = {"tennis_atp": BT.legs_tennis("atp", canon), "tennis_wta": BT.legs_tennis("wta", canon),
            "nba": BT.legs_nba(a.data / "raw/basketball/wippa_nba")}
    bt, b, m = BT.football_frames(a.data / "processed/football")
    legs["football"], _ = BT.legs_football(bt, b, m, "closing")
    fb_open, fq_open = BT.legs_football(bt, b, m, "opening")
    tn = {t: BT.legs_tennis_closing_diag(t, canon, a.data / "raw/tennis/tennis_data_co_uk", a.cache) for t in ("atp", "wta")}
    res: dict = {"label": "V2-8 portfolio research -- RESEARCH ONLY, EXPLORATORY on previously examined data",
                 "preregistration": "PREREGISTRATION.md", "seed": SEED, "blocks": {}, "set_counts": {}}
    gof_family = []
    for sp, lg in legs.items():
        se_fn = BT.strategy_context(lg[lg.period.map(lambda x, s=sp: BT.period_of(s, x)) == "development"])["band_se"]
        for n in (5, 3):
            sets, cnt = candidate_sets(lg, n)
            res["set_counts"][f"{sp}|HIGH_P|N{n}"] = cnt
            for prices in SYNTH:
                key = f"{sp}|HIGH_P|N{n}|{prices}"
                res["blocks"][key] = run_block(key, sets, prices, se_fn, with_bank=prices != "SYNTH_M0")
                print(key, len(sets), round(time.time() - t0), flush=True)
            if len(sets) >= 5:
                g = res["blocks"][f"{sp}|HIGH_P|N{n}|SYNTH_M0"]["legs_correct_gof"]
                gof_family.append((f"{sp}|N{n}", g["p_sim"]))
    # real-price scenarios
    for key, lg, q, pos in (("football|ASOF-FB|HIGH_P", fb_open, fq_open, False),
                            ("tennis_atp|CLOSE-DIAG|HIGH_P", tn["atp"][0], tn["atp"][1], False),
                            ("tennis_wta|CLOSE-DIAG|HIGH_P", tn["wta"][0], tn["wta"][1], False),
                            ("tennis_atp|CLOSE-DIAG|POS_EV", tn["atp"][0], tn["atp"][1], True),
                            ("tennis_wta|CLOSE-DIAG|POS_EV", tn["wta"][0], tn["wta"][1], True)):
        sp = key.split("|")[0]
        se_fn = BT.strategy_context(lg[lg.period.map(lambda x, s=sp: BT.period_of(s, x)) == "development"])["band_se"]
        for n in ((2, 3) if pos else (5, 3)):
            sets, cnt = candidate_sets(lg, n, quotes=q, pos_ev=pos)
            res["set_counts"][f"{key}|N{n}"] = cnt
            res["blocks"][f"{key}|N{n}|REAL"] = run_block(f"{key}|N{n}|REAL", sets, "REAL", se_fn, with_bank=True)
            print(key, n, len(sets), round(time.time() - t0), flush=True)
    # Holm over the legs-correct GOF family (frozen-engine HIGH_P sets)
    gof_family.sort(key=lambda x: x[1])
    holm, run = {}, 0.0
    for i, (k, pv) in enumerate(gof_family):
        adj = min(1.0, max(run, (len(gof_family) - i) * pv))
        run = adj
        holm[k] = {"p_sim": pv, "p_holm": round(adj, 4), "reject": adj < 0.05}
    res["legs_correct_gof_holm"] = holm
    res["runtime_s"] = round(time.time() - t0)
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "RESULTS.json").write_text(json.dumps(BT.clean(res), indent=1, default=str))
    print("done", res["runtime_s"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
