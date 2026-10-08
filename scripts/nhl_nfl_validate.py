"""NHL/NFL moneyline consensus validation (pre-registered: research/platform_v2/nhl_nfl/PREREGISTRATION.md, f9ccfd0).
Usage: python scripts/nhl_nfl_validate.py <sbr data dir>  -> research/platform_v2/nhl_nfl/VALIDATION.json (holdout scored once)"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parents[1]
OUT = REPO / "research/platform_v2/nhl_nfl"
HOLDOUT = {"2020", "2021"}
BANDS = [(0.5, 0.6), (0.6, 0.7), (0.7, 0.8), (0.8, 0.9), (0.9, 1.0001)]
BOOT, SEED, MIN_BAND_N, Z995 = 2000, 20261008, 200, 2.807


def dec(ml) -> float | None:
    try:
        m = float(ml)
    except (TypeError, ValueError):
        return None
    if m == 0:
        return None
    return 1 + m / 100 if m > 0 else 1 + 100 / abs(m)


def rows(path: Path) -> list[tuple[str, float, int]]:
    out = []
    for g in json.loads(path.read_text()):
        h, a = dec(g.get("home_close_ml")), dec(g.get("away_close_ml"))
        try:
            hf, af = float(g["home_final"]), float(g["away_final"])
        except (KeyError, TypeError, ValueError):
            continue
        if h is None or a is None or hf == af:
            continue
        book = 1 / h + 1 / a
        if not 1.0 <= book <= 1.15:
            continue
        out.append((str(g["season"]), (1 / h) / book, int(hf > af)))
    return out


def slope(p: np.ndarray, y: np.ndarray) -> float:
    x = np.log(p / (1 - p)); X = np.column_stack([np.ones_like(x), x]); b = np.array([0.0, 1.0])
    for _ in range(50):
        q = 1 / (1 + np.exp(-(X @ b)))
        b = b + np.linalg.solve(X.T @ (X * (q * (1 - q))[:, None]) + 1e-9 * np.eye(2), X.T @ (y - q))
    return float(b[1])


def wilson(k: int, n: int, z: float) -> tuple[float, float]:
    ph = k / n; d = 1 + z * z / n; c = ph + z * z / (2 * n); r = z * np.sqrt(ph * (1 - ph) / n + z * z / (4 * n * n))
    return (c - r) / d, (c + r) / d


def evaluate(rs: list[tuple[str, float, int]], boot: bool) -> dict:
    p = np.clip(np.array([r[1] for r in rs]), 1e-6, 1 - 1e-6); y = np.array([r[2] for r in rs], float)
    out = {"n": int(len(p)), "home_win_rate": round(float(y.mean()), 4), "mean_p_home": round(float(p.mean()), 4),
           "logloss": round(float(-(y * np.log(p) + (1 - y) * np.log(1 - p)).mean()), 5), "brier": round(float(((p - y) ** 2).mean()), 5),
           "cal_slope": round(slope(p, y), 4)}
    if boot:
        rng = np.random.default_rng(SEED)
        s = [slope(p[i], y[i]) for i in (rng.integers(0, len(p), len(p)) for _ in range(BOOT))]
        out["cal_slope_ci95"] = [round(float(np.percentile(s, 2.5)), 4), round(float(np.percentile(s, 97.5)), 4)]
    fav_p, fav_y = np.maximum(p, 1 - p), np.where(p >= 0.5, y, 1 - y)
    out["favourite_bands"] = {}
    for lo, hi in BANDS:
        m = (fav_p >= lo) & (fav_p < hi)
        n = int(m.sum())
        if not n:
            continue
        k = int(fav_y[m].sum()); lo_w, hi_w = wilson(k, n, Z995); mp = float(fav_p[m].mean())
        out["favourite_bands"][f"{int(lo*100)}-{int(min(hi,1)*100)}"] = {"n": n, "mean_p": round(mp, 4), "hit": round(k / n, 4),
                                                                         "wilson995": [round(lo_w, 4), round(hi_w, 4)], "inside": bool(lo_w <= mp <= hi_w)}
    return out


def gate(h: dict) -> str:
    a = h["cal_slope_ci95"][0] <= 1 <= h["cal_slope_ci95"][1]
    b = all(v["inside"] for v in h["favourite_bands"].values() if v["n"] >= MIN_BAND_N)
    return "A" if a and b else "B" if a or b else "C"


def main(d: str) -> int:
    out_p = OUT / "VALIDATION.json"
    assert not out_p.exists(), "holdout already scored once"
    res = {"spec_commit": "f9ccfd0"}
    for sp in ("nhl", "nfl"):
        rs = rows(Path(d) / f"{sp}_archive_10Y.json")
        dev, ho = [r for r in rs if r[0] not in HOLDOUT], [r for r in rs if r[0] in HOLDOUT]
        h = evaluate(ho, True)
        res[sp] = {"development": evaluate(dev, False), "holdout": h, "gate": gate(h)}
    out_p.write_text(json.dumps(res, indent=1) + "\n")
    for sp in ("nhl", "nfl"):
        print(sp, res[sp]["gate"], {k: res[sp]["holdout"][k] for k in ("n", "cal_slope", "cal_slope_ci95", "logloss")})
        print("  bands", res[sp]["holdout"]["favourite_bands"])
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1]))
