"""Settle tennis paper predictions against published results (labels consistent with the
historical engines: retirements count with the official winner; walkovers are VOID)."""
from __future__ import annotations

import re
from datetime import date, datetime, timedelta

from prediction_markets_lab.normalisation.tennis_betfair_linkage import names_are_equivalent

RESULT_WINDOW_DAYS = 21
WALKOVER = re.compile(r"W/O|\bWO\b|walkover", re.IGNORECASE)


def _same_player(a: str, b: str) -> bool:
    return names_are_equivalent(a, b) or names_are_equivalent(b, a)


def settle_one(pred: dict, results: list[dict], now: datetime) -> dict | None:
    """results: dicts with winner_name, loser_name, score, result_date (date).
    Returns a settlement row, or None if no result is found yet."""
    start = datetime.fromisoformat(pred["commence_time"]).date()
    hits = []
    for r in results:
        d = r["result_date"]
        # TML/TennisCourtLog dates are tournament START dates, so allow the start to precede the match
        if not (start - timedelta(days=RESULT_WINDOW_DAYS) <= d <= start + timedelta(days=RESULT_WINDOW_DAYS)):
            continue
        pa, pb = pred["player_a"], pred["player_b"]
        if (_same_player(pa, r["winner_name"]) and _same_player(pb, r["loser_name"])) or \
           (_same_player(pb, r["winner_name"]) and _same_player(pa, r["loser_name"])):
            hits.append(r)
    if len(hits) != 1:  # none yet, or ambiguous (e.g. a rematch in the window): never guess
        return None
    r = hits[0]
    base = {"prediction_id": pred["prediction_id"], "winner": r["winner_name"], "score": r.get("score", ""),
            "result_source": r.get("source", ""), "settlement_timestamp": now.isoformat()}
    if WALKOVER.search(str(r.get("score", ""))):
        return {**base, "status": "VOID", "correct": ""}
    correct = _same_player(pred["predicted_winner"], r["winner_name"])
    return {**base, "status": "SETTLED_CORRECT" if correct else "SETTLED_INCORRECT", "correct": int(correct)}


def parse_result_date(s: str) -> date:
    s = str(s).strip()
    if len(s) == 8 and s.isdigit():
        return datetime.strptime(s, "%Y%m%d").date()
    return datetime.fromisoformat(s.replace("/", "-")[:10]).date()
