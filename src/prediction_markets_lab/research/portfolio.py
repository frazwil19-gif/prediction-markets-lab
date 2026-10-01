"""V2-8 bet-portfolio / card-allocation research: pure functions (research only).

Pre-registration: research/platform_v2/portfolio_v2_8/PREREGISTRATION.md. Legs are ranked 0..N-1 by P (desc). A structure is a
list of lines (tuples of leg indices); daily capital S is split equally across lines. Multi prices are products of leg prices
(INDICATIVE). Exact distributions enumerate all 2^N leg outcomes (N <= 5 here: a computational cap, not a betting rule)."""
from __future__ import annotations

import itertools
import math

import numpy as np


# ---------------------------------------------------------------- structures
def structures(n: int) -> dict[str, list[tuple[int, ...]]]:
    r = list(range(n))
    s: dict[str, list[tuple[int, ...]]] = {"SINGLES": [(i,) for i in r]}
    for k in range(2, n + 1):
        s[f"ACC_{k}"] = [tuple(range(k))]
    s["DBL12+SINGLES"] = [(0, 1)] + [(i,) for i in r[2:]]
    if n == 5:
        s["2DBL+SINGLE"] = [(0, 1), (2, 3), (4,)]
        s["TBL123+SINGLES"] = [(0, 1, 2), (3,), (4,)]
        s["RR_TREBLES"] = list(itertools.combinations(r, 3))
    s["RR_DOUBLES"] = list(itertools.combinations(r, 2))
    s["FULL_COVER"] = [c for k in range(2, n + 1) for c in itertools.combinations(r, k)]
    s["FULL_COVER+SINGLES"] = [c for k in range(1, n + 1) for c in itertools.combinations(r, k)]
    return s


def outcomes(n: int) -> np.ndarray:
    """All 2^n win(1)/loss(0) vectors, shape (2^n, n)."""
    return np.array(list(itertools.product((1, 0), repeat=n)), dtype=int)


def outcome_probs(p: np.ndarray, Y: np.ndarray) -> np.ndarray:
    return np.prod(np.where(Y == 1, p, 1 - p), axis=1)


def line_returns(lines: list[tuple[int, ...]], o: np.ndarray, Y: np.ndarray) -> np.ndarray:
    """Profit per unit TOTAL capital for each outcome row (capital split equally across lines)."""
    w = 1.0 / len(lines)
    ret = np.zeros(len(Y))
    for ln in lines:
        won = Y[:, list(ln)].all(axis=1)
        price = float(np.prod(o[list(ln)]))
        ret += w * np.where(won, price - 1.0, -1.0)
    return ret


def distribution(p: np.ndarray, o: np.ndarray, lines: list[tuple[int, ...]], f: float = 0.02) -> dict:
    """Exact daily P&L distribution per unit capital; expected log growth when capital = f of bankroll."""
    Y = outcomes(len(p))
    pr = outcome_probs(p, Y)
    r = line_returns(lines, o, Y)
    mu = float(pr @ r)
    return {"expected_return": mu, "sd": float(np.sqrt(pr @ (r - mu) ** 2)), "max_loss": float(r.min()),
            "p_full_loss": float(pr[np.isclose(r, -1.0)].sum()), "p_positive": float(pr[r > 1e-12].sum()),
            "p_negative": float(pr[r < -1e-12].sum()), "exp_log_growth": float(pr @ np.log1p(f * r)),
            "n_lines": len(lines)}


def realised(o: np.ndarray, y: np.ndarray, lines: list[tuple[int, ...]]) -> float:
    return float(line_returns(lines, o, y[None, :])[0])


def exposure(lines: list[tuple[int, ...]], n: int) -> dict:
    """Share of daily capital riding on each leg (a leg's loss voids every line containing it)."""
    share = np.zeros(n)
    for ln in lines:
        for i in ln:
            share[i] += 1.0 / len(lines)
    return {"max_share_on_one_leg": float(share.max()), "mean_lines_per_leg": float(sum(len(l) for l in lines) / n)}


# ---------------------------------------------------------------- legs-correct distribution / near misses
def poisson_binomial(p: np.ndarray) -> np.ndarray:
    pmf = np.array([1.0])
    for q in p:
        pmf = np.convolve(pmf, [1 - q, q])
    return pmf          # pmf[k] = P(k correct)


def gof_count(ps: list[np.ndarray], ks: list[int], n_sim: int = 10000, seed: int = 20260930) -> dict:
    """Chi-square GOF of the realised number-correct histogram vs the summed Poisson-binomial expectation; p-value from a
    parametric simulation under the model (independent legs, stated P)."""
    n = len(ps[0])
    exp = np.sum([poisson_binomial(p) for p in ps], axis=0)
    obs = np.bincount(ks, minlength=n + 1).astype(float)

    def chi(o):
        m = exp > 0
        return float((((o - exp) ** 2)[m] / exp[m]).sum())
    stat = chi(obs)
    rng = np.random.default_rng(seed)
    P = np.array(ps)
    sims = (rng.random((n_sim, len(ps), n)) < P[None]).sum(2)
    sim_stats = np.array([chi(np.bincount(s, minlength=n + 1).astype(float)) for s in sims])
    return {"n_sets": len(ps), "expected": [round(x, 2) for x in exp], "observed": [int(x) for x in obs],
            "chi2": round(stat, 3), "p_sim": round(float((sim_stats >= stat).mean()), 4)}


def near_miss(ps: list[np.ndarray], ys: list[np.ndarray], seed: int = 20260930) -> dict:
    """Among failed full accumulators: exactly-one-loser share, loser rank distribution, lowest-P-leg-lost share."""
    n = len(ps[0])
    fail = [(p, y) for p, y in zip(ps, ys) if not y.all()]
    if not fail:
        return {}
    e_one = e_fail = 0.0
    e_rank = np.zeros(n)
    o_rank = np.zeros(n)
    e_low = o_low = 0.0
    o_one = 0
    for p, y in fail:
        pf = 1 - np.prod(p)
        one = np.array([(1 - p[r]) * np.prod(np.delete(p, r)) for r in range(n)])
        e_one += one.sum() / pf
        e_rank += one / pf                        # expected count of 'single loser = rank r' given failure
        e_low += (1 - p[-1]) / pf                 # P(lowest-P leg lost | card failed)
        o_low += int(y[-1] == 0)
        if (y == 0).sum() == 1:
            o_one += 1
            o_rank[int(np.flatnonzero(y == 0)[0])] += 1
    nf = len(fail)
    # binomial tests (normal approx on counts over failures) per rank, Holm
    tests = []
    for r in range(n):
        q = e_rank[r] / nf
        sd = math.sqrt(nf * q * (1 - q)) if 0 < q < 1 else 0
        z = (o_rank[r] - e_rank[r]) / sd if sd else 0.0
        tests.append((r, z, math.erfc(abs(z) / math.sqrt(2))))
    order = sorted(tests, key=lambda t: t[2])
    holm, run = {}, 0.0
    for i, (r, z, pv) in enumerate(order):
        adj = min(1.0, max(run, (n - i) * pv))
        run = adj
        holm[r] = adj
    return {"failed_cards": nf,
            "exactly_one_loser": {"observed": o_one, "expected": round(e_one, 1), "obs_share": round(o_one / nf, 4),
                                  "exp_share": round(e_one / nf, 4)},
            "single_loser_rank": {f"rank{r+1}": {"observed": int(o_rank[r]), "expected": round(e_rank[r], 1),
                                                 "z": round(tests[r][1], 2), "p_holm": round(holm[r], 4)} for r in range(n)},
            "lowest_p_leg_lost": {"observed": int(o_low), "expected": round(e_low, 1), "obs_share": round(o_low / nf, 4),
                                  "exp_share": round(e_low / nf, 4)}}


# ---------------------------------------------------------------- marginal leg / Kelly
def kelly_single(p: float, o: float) -> tuple[float, float]:
    """(Kelly fraction, growth at Kelly) for one binary bet; (0, 0) if EV <= 0."""
    b = o - 1
    ev = p * o - 1
    if ev <= 0 or b <= 0:
        return 0.0, 0.0
    f = ev / b
    return f, p * math.log1p(f * b) + (1 - p) * math.log1p(-f)


def marginal_path(p: np.ndarray, o: np.ndarray, se: np.ndarray, s: float = 0.01) -> list[dict]:
    """ACC_k for k = 1..N (ranks added in order)."""
    out = []
    for k in range(1, len(p) + 1):
        pj, oj = float(np.prod(p[:k])), float(np.prod(o[:k]))
        sig = pj * math.sqrt(float(np.sum((se[:k] / p[:k]) ** 2)))
        fk, gk = kelly_single(pj, oj)
        out.append({"k": k, "p_joint": pj, "fair_odds": 1 / pj, "odds": oj, "ev": pj * oj - 1, "sigma": sig,
                    "implied_margin": 1 / (oj * pj) - 1 if oj * pj > 0 else None,
                    "growth_at_s": pj * math.log1p(s * (oj - 1)) + (1 - pj) * math.log1p(-s),
                    "kelly_fraction": fk, "kelly_growth": gk, "p_full_loss": 1 - pj})
    return out


# ---------------------------------------------------------------- bankroll simulation with stake granularity
def bankroll_path(days: list[dict], lines: list[tuple[int, ...]], bank0: float, f: float, min_line: float,
                  tick: float = 0.10) -> dict:
    """days: [{"p","o","y"}]; capital = f*bankroll split across lines, each rounded DOWN to `tick`; if a line < min_line the
    structure is not bet that day (never scaled up). Ruin: bankroll < 1.0."""
    B = bank0
    path, rets, bet_days, skipped, staked_total, pnl_total = [B], [], 0, 0, 0.0, 0.0
    for d in days:
        if B < 1.0:
            rets.append(0.0)
            path.append(B)
            continue
        line = math.floor((f * B / len(lines)) / tick + 1e-9) * tick
        if line < min_line - 1e-9:
            skipped += 1
            rets.append(0.0)
            path.append(B)
            continue
        cap = line * len(lines)
        pnl = cap * realised(np.array(d["o"]), np.array(d["y"]), lines)
        staked_total += cap
        pnl_total += pnl
        rets.append(math.log((B + pnl) / B))
        B += pnl
        bet_days += 1
        path.append(B)
    arr = np.array(path)
    peak = np.maximum.accumulate(arr)
    losing = [r < 0 for r in rets]
    best = cur = 0
    for x in losing:
        cur = cur + 1 if x else 0
        best = max(best, cur)
    return {"final": round(B, 2), "bet_days": bet_days, "skipped_min_stake": skipped, "ruined": bool(B < 1.0),
            "max_drawdown": round(float(np.max(1 - arr / peak)), 4), "longest_losing_run": best,
            "roi_on_staked": round(pnl_total / staked_total, 5) if staked_total else None, "_rets": np.array(rets)}
