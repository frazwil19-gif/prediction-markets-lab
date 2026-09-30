"""V2-7H historical betting-card backtest: pure, testable functions (research only).

Pre-registration: research/platform_v2/card_backtest_v2_7h/PREREGISTRATION.md. Nothing here reads or writes production state.
Legs frame columns: sport, event, day, period, group, p, participants (tuple), [won]; priced legs add book, odds, comm, ev.
Selection functions never see outcome columns (`strip_outcomes`)."""
from __future__ import annotations

import hashlib
import itertools
import math
from typing import Callable

import numpy as np
import pandas as pd

SALT = "v2-7h"
SEED, N_BOOT = 20260930, 2000
CARD_BANDS = [(0.0, 0.50, "<50%"), (0.50, 0.65, "50-65%"), (0.65, 0.80, "65-80%"), (0.80, 1.01, "80%+")]
FINE_BANDS = [(round(x, 2), round(x + 0.05, 2), f"{int(round(x*100))}-{int(round(x*100))+5}%") for x in np.arange(0.0, 1.0, 0.05)]
LEG_THRESHOLDS = [0.70, 0.75, 0.80, 0.85, 0.90]
OUTCOME_COLS = ("won", "pnl", "outcome", "result")


def h(key: str, salt: str = SALT) -> float:
    return int(hashlib.sha256(f"{salt}|{key}".encode()).hexdigest()[:12], 16) / 16 ** 12


def strip_outcomes(df: pd.DataFrame) -> pd.DataFrame:
    return df.drop(columns=[c for c in df.columns if c in OUTCOME_COLS])


# ---------------------------------------------------------------- U1 disjoint cards
def disjoint_cards(legs: pd.DataFrame, k: int, salt: str = SALT) -> tuple[pd.DataFrame, int]:
    """Within each sport-day, hash-order legs and partition into consecutive disjoint k-tuples. Cards repeating a participant
    are dropped (returned count). Output: one row per card with p_joint, won, legs list."""
    rows, dropped = [], 0
    legs = legs.assign(_h=legs.event.astype(str).map(lambda e: h(e, salt)))
    for (sport, day), g in legs.sort_values(["sport", "day", "_h"]).groupby(["sport", "day"], sort=True):
        g = g.reset_index(drop=True)
        for i in range(0, len(g) - k + 1, k):
            c = g.iloc[i:i + k]
            parts = [x for t in c.participants for x in t]
            if len(set(parts)) < len(parts):
                dropped += 1
                continue
            rows.append({"sport": sport, "day": day, "period": c.period.iloc[0], "k": k, "p_joint": float(np.prod(c.p)),
                         "won": int(c.won.all()), "same_group": int(c.group.nunique() == 1),
                         "events": tuple(c.event), "legset": ";".join(sorted(c.event.astype(str)))})
    return pd.DataFrame(rows), dropped


# ---------------------------------------------------------------- calibration metrics
def logistic_recal(p: np.ndarray, y: np.ndarray, iters: int = 50) -> tuple[float, float]:
    """IRLS fit of y ~ a + b*logit(p). Returns (intercept a, slope b)."""
    p = np.clip(p, 1e-6, 1 - 1e-6)
    x = np.log(p / (1 - p))
    X = np.column_stack([np.ones_like(x), x])
    beta = np.array([0.0, 1.0])
    for _ in range(iters):
        eta = X @ beta
        mu = 1 / (1 + np.exp(-eta))
        w = np.clip(mu * (1 - mu), 1e-9, None)
        z = eta + (y - mu) / w
        new = np.linalg.solve(X.T @ (X * w[:, None]), X.T @ (w * z))
        if np.max(np.abs(new - beta)) < 1e-10:
            beta = new
            break
        beta = new
    return float(beta[0]), float(beta[1])


def _cluster_index(clusters: np.ndarray) -> tuple[np.ndarray, list[np.ndarray]]:
    uniq, inv = np.unique(clusters, return_inverse=True)
    groups = [np.flatnonzero(inv == i) for i in range(len(uniq))]
    return uniq, groups


def calib_metrics(p: np.ndarray, y: np.ndarray, clusters: np.ndarray, seed: int = SEED, n_boot: int = N_BOOT,
                  recal: bool = True, weights: np.ndarray | None = None) -> dict:
    p, y = np.asarray(p, float), np.asarray(y, float)
    n = len(p)
    if n == 0:
        return {"n": 0}
    w = np.ones(n) if weights is None else np.asarray(weights, float)
    pred, act = float(np.average(p, weights=w)), float(np.average(y, weights=w))
    pc = np.clip(p, 1e-6, 1 - 1e-6)
    brier = float(np.average((p - y) ** 2, weights=w))
    brier_clim = float(np.average((act - y) ** 2, weights=w))
    ll = float(-np.average(y * np.log(pc) + (1 - y) * np.log(1 - pc), weights=w))
    _, groups = _cluster_index(np.asarray(clusters))
    sw = np.array([w[g].sum() for g in groups])
    sp = np.array([(w[g] * p[g]).sum() for g in groups])
    sy = np.array([(w[g] * y[g]).sum() for g in groups])
    rng = np.random.default_rng(seed)
    G = len(groups)
    idx = rng.integers(0, G, size=(n_boot, G))
    W, Pb, Yb = sw[idx].sum(1), sp[idx].sum(1), sy[idx].sum(1)
    bias_b = (Yb - Pb) / W
    act_b = Yb / W
    lo, hi = np.percentile(bias_b, [2.5, 97.5])
    se = float(np.std(bias_b, ddof=1))
    var_act = float(np.var(act_b, ddof=1))
    out = {"n": int(n), "clusters": int(G), "pred": round(pred, 5), "actual": round(act, 5), "bias": round(act - pred, 5),
           "bias_ci95": [round(float(lo), 5), round(float(hi), 5)], "ci_halfwidth": round(float(hi - lo) / 2, 5),
           "min_detectable_dev_2se": round(2 * se, 5), "brier": round(brier, 5), "brier_climatology": round(brier_clim, 5),
           "brier_skill": round(1 - brier / brier_clim, 5) if brier_clim > 0 else None, "log_loss": round(ll, 5),
           "n_eff_cluster": round(act * (1 - act) / var_act, 1) if var_act > 0 else None,
           "p_value_normal": round(math.erfc(abs(act - pred) / se / math.sqrt(2)), 6) if se > 0 else None}
    if recal and n >= 200 and 0 < act < 1 and weights is None:
        a, b = logistic_recal(p, y)
        ab = []
        rng2 = np.random.default_rng(seed + 1)
        for _ in range(200):
            gi = rng2.integers(0, G, size=G)
            ii = np.concatenate([groups[j] for j in gi])
            if 0 < y[ii].mean() < 1:
                ab.append(logistic_recal(p[ii], y[ii]))
        ab = np.array(ab)
        out.update({"recal_intercept": round(a, 4), "recal_slope": round(b, 4),
                    "recal_slope_ci95": [round(float(np.percentile(ab[:, 1], 2.5)), 4), round(float(np.percentile(ab[:, 1], 97.5)), 4)]})
    return out


def band_metrics(df: pd.DataFrame, bands, pcol: str = "p_joint", ycol: str = "won", cl: str = "day", min_n: int = 200,
                 recal: bool = False) -> dict:
    out = {}
    for lo, hi, lab in bands:
        x = df[(df[pcol] >= lo) & (df[pcol] < hi)]
        if len(x):
            m = calib_metrics(x[pcol].values, x[ycol].values, x[cl].values, recal=recal)
            m["sparse"] = len(x) < min_n
            out[lab] = m
    return out


# ---------------------------------------------------------------- P2 independence and U2 exhaustive in-the-large
def elem_sym(v: np.ndarray, kmax: int = 3) -> list[float]:
    """Elementary symmetric polynomials e_0..e_kmax of the entries of v."""
    e = [1.0] + [0.0] * kmax
    for x in v:
        for j in range(kmax, 0, -1):
            e[j] += e[j - 1] * x
    return e


def pair_residual_stats(legs: pd.DataFrame, seed: int = SEED, n_boot: int = N_BOOT) -> dict:
    """Mean within-day pairwise residual product E[(y_i-p_i)(y_j-p_j)] for all / same-group / cross-group pairs, with a
    day-cluster bootstrap CI. Under calibration it equals the bias of p_i*p_j for a double."""
    per_day = []
    for day, g in legs.groupby("day"):
        r = (g.won - g.p).values
        n = len(r)
        if n < 2:
            continue
        all_s = (r.sum() ** 2 - (r ** 2).sum()) / 2
        all_n = n * (n - 1) / 2
        same_s = same_n = 0.0
        for _, gg in g.groupby("group"):
            rr = (gg.won - gg.p).values
            m = len(rr)
            same_s += (rr.sum() ** 2 - (rr ** 2).sum()) / 2
            same_n += m * (m - 1) / 2
        per_day.append((all_s, all_n, same_s, same_n))
    a = np.array(per_day)
    if not len(a):
        return {}
    rng = np.random.default_rng(seed)
    idx = rng.integers(0, len(a), size=(n_boot, len(a)))

    def stat(s, c):
        est = a[:, s].sum() / a[:, c].sum() if a[:, c].sum() else float("nan")
        bs = a[idx, s].sum(1) / np.maximum(a[idx, c].sum(1), 1e-12)
        lo, hi = np.percentile(bs, [2.5, 97.5])
        se = float(np.std(bs, ddof=1))
        return {"pairs": int(a[:, c].sum()), "mean_residual_product": round(float(est), 6),
                "ci95": [round(float(lo), 6), round(float(hi), 6)], "z": round(float(est / se), 3) if se > 0 else None}
    cross = a.copy()
    cross[:, 0] -= cross[:, 2]
    cross[:, 1] -= cross[:, 3]
    a_all = stat(0, 1)
    a_same = stat(2, 3)
    a = cross
    idx = rng.integers(0, len(a), size=(n_boot, len(a)))
    a_cross = stat(0, 1)
    return {"days": len(per_day), "all_pairs": a_all, "same_group_pairs": a_same, "cross_group_pairs": a_cross}


def exhaustive_inlarge(legs: pd.DataFrame, k: int, seed: int = SEED, n_boot: int = N_BOOT) -> dict:
    """U2: all within-day k-combinations of distinct events, exactly, via elementary symmetric polynomials.
    (Participants are distinct across events within a day in these data; repeated participants are not removed here.)"""
    rows = []
    for day, g in legs.groupby("day"):
        if len(g) < k:
            continue
        ep = elem_sym(g.p.values, k)[k]
        ey = elem_sym(g.won.values.astype(float), k)[k]
        rows.append((ep, ey, math.comb(len(g), k), len(g)))
    a = np.array(rows)
    if not len(a):
        return {}
    rng = np.random.default_rng(seed)
    idx = rng.integers(0, len(a), size=(n_boot, len(a)))
    bias_b = (a[idx, 1].sum(1) - a[idx, 0].sum(1)) / a[idx, 2].sum(1)
    lo, hi = np.percentile(bias_b, [2.5, 97.5])
    return {"raw_cards": int(a[:, 2].sum()), "days": len(a), "distinct_events": int(a[:, 3].sum()),
            "pred": round(float(a[:, 0].sum() / a[:, 2].sum()), 5), "actual": round(float(a[:, 1].sum() / a[:, 2].sum()), 5),
            "bias": round(float((a[:, 1].sum() - a[:, 0].sum()) / a[:, 2].sum()), 5), "bias_ci95": [round(float(lo), 5), round(float(hi), 5)],
            "cards_per_event": round(float(a[:, 2].sum() * k / a[:, 3].sum()), 1)}


def dispersion_index(legs: pd.DataFrame) -> dict:
    """Variance of daily favourite-loss counts over its Poisson-binomial expectation (1 = independence)."""
    g = legs.assign(l=1 - legs.won, v=legs.p * (1 - legs.p)).groupby("day").agg(L=("l", "sum"), q=("p", lambda s: (1 - s).sum()),
                                                                                  v=("v", "sum"))
    di = float(((g.L - g.q) ** 2).sum() / g.v.sum())
    rng = np.random.default_rng(SEED)
    arr = g[["L", "q", "v"]].to_numpy()
    idx = rng.integers(0, len(arr), size=(N_BOOT, len(arr)))
    b = ((arr[idx, 0] - arr[idx, 1]) ** 2).sum(1) / arr[idx, 2].sum(1)
    return {"days": int(len(g)), "dispersion_index": round(di, 4),
            "ci95": [round(float(np.percentile(b, 2.5)), 4), round(float(np.percentile(b, 97.5)), 4)]}


# ---------------------------------------------------------------- Kish effective n for overlapping cards
def card_corr(a: tuple, b: tuple, p: dict) -> float:
    pa = math.prod(p[e] for e in a)
    pb = math.prod(p[e] for e in b)
    both = math.prod(p[e] for e in set(a) | set(b))
    va, vb = pa * (1 - pa), pb * (1 - pb)
    return (both - pa * pb) / math.sqrt(va * vb) if va > 0 and vb > 0 else 0.0


def kish_neff(cards: list[tuple], p: dict) -> float:
    n = len(cards)
    if n == 0:
        return 0.0
    den = float(n)
    sets = [set(c) for c in cards]
    for i in range(n):
        for j in range(i + 1, n):
            if sets[i] & sets[j]:
                den += 2 * card_corr(cards[i], cards[j], p)
    return n * n / den


# ---------------------------------------------------------------- strategies (selection never sees outcomes)
def _distinct(sel: list[dict], k: int) -> list[dict] | None:
    out, parts, evs = [], set(), set()
    for r in sel:
        ps = set(r["participants"])
        if r["event"] in evs or ps & parts:
            continue
        out.append(r)
        evs.add(r["event"])
        parts |= ps
        if len(out) == k:
            return out
    return None


def pick_top(rows: list[dict], k: int, key: Callable[[dict], float]) -> list[dict] | None:
    return _distinct(sorted(rows, key=lambda r: (-key(r), h(str(r["event"])))), k)


def select_prob(day_legs: pd.DataFrame, k: int, strategy: str, ctx: dict) -> list[dict] | None:
    """HIGH_P strategies on an outcome-free frame. S1: top-k P among P>=0.70; S2: top-k P among dev-supported bands;
    S5: top-k lowest sigma_band/p among P>=0.50."""
    rows = strip_outcomes(day_legs).to_dict("records")
    if strategy == "S1":
        return pick_top([r for r in rows if r["p"] >= 0.70], k, lambda r: r["p"])
    if strategy == "S2":
        ok = ctx["supported_bands"]
        return pick_top([r for r in rows if any(lo <= r["p"] < hi for lo, hi in ok)], k, lambda r: r["p"])
    if strategy == "S5":
        se = ctx["band_se"]
        return pick_top(rows, k, lambda r: -se(r["p"]) / r["p"])
    raise ValueError(strategy)


def select_priced(day_quotes: pd.DataFrame, k: int, strategy: str) -> list[dict] | None:
    """POS_EV strategies. day_quotes: one row per (leg, book) with p, odds, comm, ev (outcome-free). Every leg EV > 0 and all
    legs at ONE book. S3: top-k EV, book with max card EV; S4: top-k Kelly, book with max 1%-stake expected log growth;
    S6: top-k P, book with max P_joint (ties EV)."""
    q = strip_outcomes(day_quotes)
    q = q[q.ev > 0]
    best, best_key = None, None
    for book, g in q.groupby("book", sort=True):
        rows = g.to_dict("records")
        if strategy == "S3":
            c = pick_top(rows, k, lambda r: r["ev"])
        elif strategy == "S4":
            c = pick_top(rows, k, lambda r: r["ev"] / (r["odds_net"] - 1))
        elif strategy == "S6":
            c = pick_top(rows, k, lambda r: r["p"])
        else:
            raise ValueError(strategy)
        if c is None:
            continue
        pj = math.prod(r["p"] for r in c)
        oj = math.prod(r["odds_net"] for r in c)
        ev = pj * oj - 1
        if strategy == "S3":
            key = (ev, pj)
        elif strategy == "S4":
            key = (pj * math.log1p(0.01 * (oj - 1)) + (1 - pj) * math.log1p(-0.01), ev)
        else:
            key = (pj, ev)
        if best_key is None or key > best_key:
            best, best_key = c, key
    return best


# ---------------------------------------------------------------- equal-capital bankroll simulation
def longest_run(losses: np.ndarray) -> int:
    best = cur = 0
    for x in losses:
        cur = cur + 1 if x else 0
        best = max(best, cur)
    return best


def p_run_at_least(q: np.ndarray, L: int) -> float:
    """Exact P(longest run of losses >= L) for independent trials with loss probs q (DP over current run length)."""
    state = np.zeros(L)
    state[0] = 1.0
    hit = 0.0
    for qi in q:
        new = np.zeros(L)
        new[0] = state.sum() * (1 - qi)
        new[1:] = state[:-1] * qi
        hit += state[-1] * qi
        state = new
    return float(hit)


def max_drawdown(bank: np.ndarray) -> float:
    peak = np.maximum.accumulate(np.concatenate([[1.0], bank]))
    return float(np.max(1 - np.concatenate([[1.0], bank]) / peak))


def simulate(days: list[dict], s: float, structure: str, seed: int = SEED, n_boot: int = 1000) -> dict:
    """days: chronological list of {"p": [..], "o": [..] (net decimal odds), "y": [..]}.
    structure 'card': stake s*B on the k-fold at prod(o); 'singles': s*B/k on each leg. Returns realised and model metrics."""
    rets, model_g, won_any, lost_all, card_q, pnl_u = [], [], [], [], [], []
    for d in days:
        p, o, y = np.array(d["p"]), np.array(d["o"]), np.array(d["y"])
        k = len(p)
        if structure == "card":
            oj, pj = float(np.prod(o)), float(np.prod(p))
            r = s * (oj - 1) if y.all() else -s
            model_g.append(pj * math.log1p(s * (oj - 1)) + (1 - pj) * math.log1p(-s))
            won_any.append(bool(y.all()))
            lost_all.append(not y.all())
            card_q.append(1 - pj)
            pnl_u.append((oj - 1) if y.all() else -1.0)
        else:
            r = float(np.sum(np.where(y == 1, s / k * (o - 1), -s / k)))
            g = 0.0
            for wins in itertools.product((1, 0), repeat=k):
                pr = math.prod(pi if wi else 1 - pi for pi, wi in zip(p, wins))
                g += pr * math.log1p(sum(s / k * ((oi - 1) if wi else -1) for oi, wi in zip(o, wins)))
            model_g.append(g)
            won_any.append(r > 0)
            lost_all.append(not y.any())
            card_q.append(float(np.prod(1 - p)))
            pnl_u.append(r / s)
        rets.append(math.log1p(r))
    rets = np.array(rets)
    n = len(rets)
    if n == 0:
        return {"days": 0}
    bank = np.exp(np.cumsum(rets))
    rng = np.random.default_rng(seed)
    idx = rng.integers(0, n, size=(n_boot, n))
    mb = rets[idx].mean(1)
    ub = np.array(pnl_u)[idx].mean(1)
    impaired = float(np.mean(np.cumsum(rets[idx], axis=1).min(axis=1) < math.log(0.5)))
    q = np.array(card_q)
    return {"days": n, "stake": s, "win_share": round(float(np.mean(won_any)), 4),
            "whole_stake_loss_share": round(float(np.mean(lost_all)), 4),
            "model_whole_stake_loss_prob": round(float(q.mean()), 4),
            "roi_per_unit": round(float(np.mean(pnl_u)), 5),
            "roi_ci95": [round(float(np.percentile(ub, 2.5)), 5), round(float(np.percentile(ub, 97.5)), 5)],
            "mean_log_return": round(float(rets.mean()), 7),
            "mean_log_return_ci95": [round(float(np.percentile(mb, 2.5)), 7), round(float(np.percentile(mb, 97.5)), 7)],
            "model_expected_log_growth": round(float(np.mean(model_g)), 7),
            "final_bankroll": round(float(bank[-1]), 4), "volatility": round(float(rets.std(ddof=1)) if n > 1 else 0.0, 6),
            "max_drawdown": round(max_drawdown(bank), 4), "longest_losing_run": longest_run(rets < 0),
            "model_p_losing_run_ge": {L: round(p_run_at_least(q, L), 4) for L in (5, 8, 10)},
            "p_bankroll_below_half_bootstrap": round(impaired, 4), "_rets": rets}


def compare(a: dict, b: dict, seed: int = SEED, n_boot: int = 2000) -> dict:
    """Mean daily log-return difference (card - singles) with a day-bootstrap CI (paired by day)."""
    d = a["_rets"] - b["_rets"]
    rng = np.random.default_rng(seed)
    idx = rng.integers(0, len(d), size=(n_boot, len(d)))
    mb = d[idx].mean(1)
    lo, hi = np.percentile(mb, [2.5, 97.5])
    verdict = "CARD" if lo > 0 else "SINGLES" if hi < 0 else "NO_DIFFERENCE_DETECTED"
    return {"mean_diff_card_minus_singles": round(float(d.mean()), 7), "ci95": [round(float(lo), 7), round(float(hi), 7)],
            "verdict": verdict}


# ---------------------------------------------------------------- stress test
def tolerance(ps: list[float], o: float, target: float = 0.0) -> float:
    """Uniform per-leg overestimate delta (probability points) at which card EV at price o falls to `target`."""
    f = lambda d: math.prod(max(p - d, 0.0) for p in ps) * o - 1 - target   # noqa: E731
    if f(0) <= 0:
        return 0.0
    lo, hi = 0.0, min(ps)
    for _ in range(60):
        m = (lo + hi) / 2
        lo, hi = (m, hi) if f(m) > 0 else (lo, m)
    return lo


def growth_pair(ps: list[float], os_: list[float], s: float) -> tuple[float, float]:
    """(card, singles) one-period expected log growth at equal total stake s."""
    k = len(ps)
    pj, oj = math.prod(ps), math.prod(os_)
    card = pj * math.log1p(s * (oj - 1)) + (1 - pj) * math.log1p(-s)
    sing = 0.0
    for wins in itertools.product((1, 0), repeat=k):
        pr = math.prod(p if w else 1 - p for p, w in zip(ps, wins))
        sing += pr * math.log1p(sum(s / k * ((o - 1) if w else -1) for o, w in zip(os_, wins)))
    return card, sing
