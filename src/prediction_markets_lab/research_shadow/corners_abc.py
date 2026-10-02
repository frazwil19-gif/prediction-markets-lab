"""Corners A / B / C comparison (pre-registered: research/platform_v2/corners_abc/PREREGISTRATION.md).

Inputs (append-only research files):
  research_shadow/corners/model_a_predictions.csv  (collector; Model A)
  research_shadow/corners/quotes.csv               (any enabled price adapter; schema QUOTE_FIELDS)
  research_shadow/corners/outcomes.csv             (collector)
The moment a price source writes quotes, `build_rows` + `evaluate` run unchanged. ROI never selects a model.
"""
from __future__ import annotations

import statistics
from datetime import datetime, timedelta

import numpy as np
import pandas as pd

QUOTE_FIELDS = ["capture_ts", "event_key", "competition", "kickoff_utc", "venue", "is_exchange", "line", "side", "back", "lay", "quote_ts", "source"]
LINES = (7.5, 8.5, 9.5, 10.5, 11.5, 12.5, 13.5)
MIN_MINUTES_BEFORE = 60.0
MAX_QUOTE_AGE_MIN = 30.0
MAX_OVERROUND = 0.15
MAX_EXCHANGE_SPREAD = 0.10
MIN_ODDS = 1.01
FIT_EVENTS = 150
EVAL_TRIGGER = 300
INTERIM = 150
BOOT, SEED = 2000, 7


def _ts(s) -> datetime:
    return pd.Timestamp(s).to_pydatetime()


def valid_two_way(q: pd.DataFrame) -> dict[tuple[str, float], float]:
    """{(venue, line): fair P(over)} from quotes passing the pre-registered quality rules. Exchanges use the back/lay
    mid (spread <= MAX_EXCHANGE_SPREAD each side); sportsbooks the back price; proportional two-way de-vig."""
    out = {}
    for (venue, line), g in q.groupby(["venue", "line"]):
        px = {}
        for r in g.itertuples():
            if r.back is None or not np.isfinite(r.back) or r.back <= MIN_ODDS:
                continue
            if (_ts(r.capture_ts) - _ts(r.quote_ts)).total_seconds() / 60 > MAX_QUOTE_AGE_MIN:
                continue
            if str(r.is_exchange) == "True":
                if not np.isfinite(r.lay) or r.lay / r.back - 1 > MAX_EXCHANGE_SPREAD:
                    continue
                px[r.side] = 2.0 / (1 / r.back + 1 / r.lay)
            else:
                px[r.side] = r.back
        if set(px) != {"over", "under"}:
            continue                                            # never manufacture a missing side
        io, iu = 1 / px["over"], 1 / px["under"]
        if not 0 <= io + iu - 1 <= MAX_OVERROUND:
            continue
        out[(venue, float(line))] = io / (io + iu)
    return out


def build_rows(preds: pd.DataFrame, quotes: pd.DataFrame, outcomes: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    """One row per event at its MAIN line (two-sided line whose consensus P(over) is closest to 0.5; ties -> lower line),
    using the latest capture >= MIN_MINUTES_BEFORE before kickoff and the latest Model A prediction made before it."""
    excluded: dict = {}
    rows = []
    if quotes.empty:
        return pd.DataFrame(), {"no_quotes": 0}
    q = quotes.copy()
    q["mins_before"] = [(_ts(k) - _ts(c)).total_seconds() / 60 for k, c in zip(q.kickoff_utc, q.capture_ts)]
    q = q[q.mins_before >= MIN_MINUTES_BEFORE]
    out_map = outcomes.set_index("event_key").total_corners.to_dict() if not outcomes.empty else {}
    for ek, g in q.groupby("event_key"):
        cap = g.capture_ts.max()
        snap = g[g.capture_ts == cap]
        fair = valid_two_way(snap)
        if not fair:
            excluded["no_valid_two_sided_line"] = excluded.get("no_valid_two_sided_line", 0) + 1
            continue
        by_line: dict = {}
        for (v, line), p in fair.items():
            by_line.setdefault(line, []).append(p)
        cons = {line: statistics.median(ps) for line, ps in by_line.items() if line in LINES}
        if not cons:
            excluded["no_listed_line"] = excluded.get("no_listed_line", 0) + 1
            continue
        main = min(cons, key=lambda L: (abs(cons[L] - 0.5), L))
        pa = preds[(preds.event_key == ek) & (pd.to_datetime(preds.run_ts, utc=True) <= pd.to_datetime(cap, utc=True))]
        if pa.empty:
            excluded["no_model_a_before_capture"] = excluded.get("no_model_a_before_capture", 0) + 1
            continue
        a = pa.assign(_t=pd.to_datetime(pa.run_ts, utc=True)).sort_values("_t").iloc[-1]
        if ek not in out_map:
            excluded["no_outcome_yet"] = excluded.get("no_outcome_yet", 0) + 1
            continue
        rows.append({"event_key": ek, "competition": g.competition.iloc[0], "kickoff_utc": g.kickoff_utc.iloc[0], "capture_ts": cap,
                     "main_line": main, "p_b": cons[main], "n_venues": len(by_line[main]), "p_a": float(a[f"p_total_over_{main}"]),
                     "y": int(out_map[ek] > main)})
    df = pd.DataFrame(rows)
    if not df.empty:
        df = df.sort_values(["kickoff_utc", "event_key"]).reset_index(drop=True)
    return df, excluded


def _ll(y: np.ndarray, p: np.ndarray) -> np.ndarray:
    p = np.clip(p, 1e-6, 1 - 1e-6)
    return -(y * np.log(p) + (1 - y) * np.log(1 - p))


def _logit(p: np.ndarray) -> np.ndarray:
    p = np.clip(p, 1e-6, 1 - 1e-6)
    return np.log(p / (1 - p))


def fit_stack(df: pd.DataFrame) -> np.ndarray:
    """Model C: logit p_C = b0 + b1 logit p_B + b2 logit p_A (IRLS), fitted on the FIT block only."""
    X = np.column_stack([np.ones(len(df)), _logit(df.p_b.to_numpy()), _logit(df.p_a.to_numpy())])
    y = df.y.to_numpy(float)
    b = np.array([0.0, 1.0, 0.0])
    for _ in range(100):
        q = 1 / (1 + np.exp(-(X @ b)))
        new = b + np.linalg.solve(X.T @ (X * (q * (1 - q))[:, None]) + 1e-9 * np.eye(3), X.T @ (y - q))
        if np.max(np.abs(new - b)) < 1e-10:
            return new
        b = new
    return b


def apply_stack(b: np.ndarray, df: pd.DataFrame) -> np.ndarray:
    return 1 / (1 + np.exp(-(b[0] + b[1] * _logit(df.p_b.to_numpy()) + b[2] * _logit(df.p_a.to_numpy()))))


def _ci(d: np.ndarray) -> list[float]:
    rng = np.random.default_rng(SEED)
    n = len(d)
    m = [d[rng.integers(0, n, n)].mean() for _ in range(BOOT)]
    return [round(float(np.percentile(m, 2.5)), 6), round(float(np.percentile(m, 97.5)), 6)]


def evaluate(df: pd.DataFrame, frozen_beta: list[float] | None = None) -> dict:
    """Status + tests per the pre-registration. With fewer than FIT_EVENTS events only A vs B (all events) is reported."""
    n = len(df)
    out: dict = {"n_events": n, "fit_block": min(n, FIT_EVENTS), "evaluation_block": max(0, n - FIT_EVENTS),
                 "stage": "COLLECTING" if n - FIT_EVENTS < INTERIM else ("INTERIM" if n - FIT_EVENTS < EVAL_TRIGGER else "CONFIRMATORY")}
    if n == 0:
        return out
    y = df.y.to_numpy(float)
    d_ab = _ll(y, df.p_a.to_numpy()) - _ll(y, df.p_b.to_numpy())
    out["all_events_A_minus_B"] = {"mean": round(float(d_ab.mean()), 6), "ci95": _ci(d_ab) if n >= 30 else None}
    if n <= FIT_EVENTS:
        return out
    beta = np.array(frozen_beta) if frozen_beta is not None else fit_stack(df.iloc[:FIT_EVENTS])
    ev = df.iloc[FIT_EVENTS:]
    ye = ev.y.to_numpy(float)
    la, lb, lc = _ll(ye, ev.p_a.to_numpy()), _ll(ye, ev.p_b.to_numpy()), _ll(ye, apply_stack(beta, ev))
    out["model_c_beta"] = [round(float(x), 6) for x in beta]
    out["eval_A_minus_B"] = {"mean": round(float((la - lb).mean()), 6), "ci95": _ci(la - lb)}
    out["eval_C_minus_B"] = {"mean": round(float((lc - lb).mean()), 6), "ci95": _ci(lc - lb)}
    return out
