"""H1 research shadow: power de-vig football consensus alongside the frozen production consensus.

Research only (pre-registered: research/platform_v2/track_a/H1_PREREGISTRATION.md). Never feeds the ledger, Stage A,
bet selection, grades, stakes or money logic. Pure functions + an append-only CSV writer.
"""
from __future__ import annotations

import csv
import json
import statistics
from pathlib import Path

OUTCOMES = ("home", "draw", "away")
FIELDS = ["scan_timestamp", "market_id", "competition", "event", "kickoff", "n_books",
          "p_frozen_home", "p_frozen_draw", "p_frozen_away", "p_power_home", "p_power_draw", "p_power_away",
          "pn_frozen_home", "pn_frozen_draw", "pn_frozen_away", "pn_power_home", "pn_power_draw", "pn_power_away",
          "book_odds_json"]
_TOL, _MAX_IT = 1e-12, 200


def power_devig(odds: list[float]) -> list[float]:
    """Solve sum((1/o_i)^k) = 1 for k (bisection; the sum decreases in k when every 1/o_i < 1) and return (1/o_i)^k."""
    inv = [1.0 / o for o in odds]
    if any(not 0 < x < 1 for x in inv):
        raise ValueError("odds must all be > 1")
    lo, hi = 1e-6, 1.0
    while sum(x ** hi for x in inv) > 1:      # overround > 0 -> k > 1
        hi *= 2
        if hi > 1e6:
            raise ValueError("power de-vig did not bracket")
    for _ in range(_MAX_IT):
        mid = (lo + hi) / 2
        if sum(x ** mid for x in inv) > 1:
            lo = mid
        else:
            hi = mid
        if hi - lo < _TOL:
            break
    k = (lo + hi) / 2
    return [x ** k for x in inv]


def proportional_devig(odds: list[float]) -> list[float]:
    inv = [1.0 / o for o in odds]
    s = sum(inv)
    return [x / s for x in inv]


def _norm(p: list[float]) -> list[float]:
    s = sum(p)
    return [x / s for x in p]


def shadow_row(scan_ts: str, market_id: str, meta: dict, book_odds: dict[str, dict[str, float]],
               frozen: dict[str, float]) -> dict | None:
    """frozen: the production consensus per outcome (copied). Uses only books with a complete H/D/A quote, exactly
    the set the production consensus accepts. Returns None if no complete book."""
    books = {b: [float(q[o]) for o in OUTCOMES] for b, q in book_odds.items()
             if all(o in q for o in OUTCOMES) and len(q) == len(OUTCOMES) and all(float(q[o]) > 1 for o in OUTCOMES)}
    if not books or not all(o in frozen for o in OUTCOMES):
        return None
    per_book = [power_devig(v) for v in books.values()]
    p_power = [statistics.median(pb[i] for pb in per_book) for i in range(3)]
    p_frozen = [float(frozen[o]) for o in OUTCOMES]
    row = {"scan_timestamp": scan_ts, "market_id": market_id, "competition": meta.get("competition", ""),
           "event": meta.get("event", ""), "kickoff": meta.get("commence_time", ""), "n_books": len(books),
           "book_odds_json": json.dumps(books, sort_keys=True)}
    for name, vals in (("p_frozen", p_frozen), ("p_power", p_power), ("pn_frozen", _norm(p_frozen)), ("pn_power", _norm(p_power))):
        for o, v in zip(OUTCOMES, vals):
            row[f"{name}_{o}"] = round(v, 6)
    return row


def append_rows(path: Path, rows: list[dict]) -> int:
    """Append-only; header written once. Rows are never rewritten."""
    if not rows:
        return 0
    path.parent.mkdir(parents=True, exist_ok=True)
    new = not path.exists()
    with path.open("a", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        if new:
            w.writeheader()
        w.writerows(rows)
    return len(rows)
