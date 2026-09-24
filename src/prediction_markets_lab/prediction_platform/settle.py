"""Settlement for the unified ledger (separate append-only file; first settlement wins).

Only final outcomes are written. Unresolvable cases (AMBIGUOUS / UNRESOLVED_NAME / NOT_FOUND) are returned as
pending-review items and never written, so a later correct settlement is not blocked.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from prediction_markets_lab.settlement import football_data_results as fd

COMP_TO_FD = {"Premier League": "E0", "Championship": "E1", "Scottish Premiership": "SC0"}
SETTLE_AFTER_KICKOFF = timedelta(hours=3)


def _ts(s: str) -> datetime:
    d = datetime.fromisoformat(s.replace("Z", "+00:00"))
    return d if d.tzinfo else d.replace(tzinfo=timezone.utc)


def football_outcome(market: str, selection: str, hg: int, ag: int) -> int:
    """1 if the selection won, else 0. Raises on an unknown market/selection (never guesses)."""
    res = "home" if hg > ag else "away" if ag > hg else "draw"
    if market == "1x2" and selection in ("home", "draw", "away"):
        return int(res == selection)
    if market == "double_chance" and selection in ("1X", "X2", "12"):
        return int({"1X": res != "away", "X2": res != "home", "12": res != "draw"}[selection])
    if market == "over_under_2_5" and selection in ("over", "under"):
        return int((hg + ag > 2.5) == (selection == "over"))
    raise ValueError(f"unknown football market/selection {market}/{selection}")


def settle_football(preds: list[dict], done: set[str], results: list, aliases: dict[str, str],
                    now: datetime) -> tuple[list[dict], list[dict]]:
    new, review = [], []
    for p in preds:
        if p["sport"] != "football" or p["prediction_id"] in done:
            continue
        if now < _ts(p["event_start"]) + SETTLE_AFTER_KICKOFF:
            continue
        code = COMP_TO_FD.get(p["competition"])
        home, _, away = p["event_name"].partition(" v ")
        if code is None or not away:
            review.append({"prediction_id": p["prediction_id"], "status": "UNRESOLVED_NAME", "detail": "competition/event"})
            continue
        m = fd.match_fixture(code, home, away, _ts(p["event_start"]).date(), results, aliases)
        if m.status != "MATCHED" or m.result is None:
            review.append({"prediction_id": p["prediction_id"], "status": m.status, "detail": m.detail})
            continue
        r = m.result
        new.append({"prediction_id": p["prediction_id"], "settlement_status": "SETTLED", "result": f"{r.home_goals}-{r.away_goals}",
                    "correct": football_outcome(p["market"], p["selection"], r.home_goals, r.away_goals),
                    "settlement_timestamp": now.isoformat(), "settlement_source": "football_data_co_uk", "mapping_status": "MATCHED"})
    return new, review


def mirror_tennis(tennis_settlements: dict[str, dict], unified_ids: set[str], done: set[str]) -> list[dict]:
    out = []
    for pid, s in tennis_settlements.items():
        if pid not in unified_ids or pid in done:
            continue
        st = s.get("status")
        if st in ("SETTLED_CORRECT", "SETTLED_INCORRECT"):
            out.append({"prediction_id": pid, "settlement_status": "SETTLED", "result": s.get("winner", ""),
                        "correct": 1 if st == "SETTLED_CORRECT" else 0, "settlement_timestamp": s.get("settlement_timestamp", ""),
                        "settlement_source": s.get("result_source", "TennisCourtLog"), "mapping_status": "MIRRORED"})
        elif st == "VOID":
            out.append({"prediction_id": pid, "settlement_status": "VOID", "result": s.get("score", ""), "correct": "",
                        "settlement_timestamp": s.get("settlement_timestamp", ""),
                        "settlement_source": s.get("result_source", "TennisCourtLog"), "mapping_status": "MIRRORED"})
    return out


def settle_from_odds_api_scores(preds: list[dict], done: set[str], scores: list[dict], now: datetime) -> list[dict]:
    """NBA: settle by provider event id from an Odds API /scores payload (completed events only, no draws)."""
    by_id = {e["id"]: e for e in scores if e.get("completed") and e.get("scores")}
    out = []
    for p in preds:
        if p["sport"] != "basketball" or p["prediction_id"] in done or p["event_id"] not in by_id:
            continue
        sc = {s["name"]: float(s["score"]) for s in by_id[p["event_id"]]["scores"]}
        if len(sc) != 2 or len(set(sc.values())) != 2:
            continue
        winner = max(sc, key=sc.get)
        out.append({"prediction_id": p["prediction_id"], "settlement_status": "SETTLED", "result": winner,
                    "correct": int(winner == p["selection"]), "settlement_timestamp": now.isoformat(),
                    "settlement_source": "odds_api_scores", "mapping_status": "EVENT_ID"})
    return out
