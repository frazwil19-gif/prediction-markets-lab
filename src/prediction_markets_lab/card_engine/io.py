"""Loading legs from the live same-scan files, the append-only research card ledger, and fail-closed settlement."""
from __future__ import annotations

import csv
import hashlib
import json
from dataclasses import asdict
from datetime import datetime, timedelta, timezone
from pathlib import Path

from prediction_markets_lab.card_engine.cards import EXCHANGES, Card, Leg

MAX_QUOTE_AGE = timedelta(minutes=240)      # same freshness rule as bsv2-3
MAX_WIDTH = 0.03                             # same exchange-width rule as bsv2-3
CARD_FIELDS = ["card_id", "rule_version", "scan", "book", "group", "k", "status", "reasons", "dependence", "dependence_flags",
               "p_joint", "sigma_joint", "odds_indicative", "fair_odds", "break_even", "ev", "ev_low", "ev_high",
               "all_legs_pos_ev", "all_legs_clean", "legs_json", "provenance", "logged_at"]
SETTLE_FIELDS = ["card_id", "status", "legs_won", "legs_total", "settled_at", "source"]


def _ts(s: str) -> datetime:
    d = datetime.fromisoformat(str(s).replace("Z", "+00:00"))
    return d if d.tzinfo else d.replace(tzinfo=timezone.utc)


def _read(p: Path) -> list[dict]:
    if not p.exists():
        return []
    with p.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def engine_of(sport_key: str) -> str:
    return ("atp_match_winner.betfair_market@1" if sport_key.startswith("tennis_atp_") else
            "wta_match_winner.betfair_market@1" if sport_key.startswith("tennis_wta_") else f"unknown:{sport_key}")


def load_legs(prob_rows: list[dict], price_rows: list[dict], scan: str) -> list[Leg]:
    """Favourite side (P >= 0.5) of every VALIDATED same-scan engine prediction x every named non-exchange book in that scan."""
    scan_t = _ts(scan)
    prices: dict[str, list[dict]] = {}
    for r in price_rows:
        if r["scan_timestamp_utc"] == scan and not r["bookmaker"].startswith(EXCHANGES):
            prices.setdefault(r["event_id"], []).append(r)
    legs = []
    for x in prob_rows:
        if x["scan_timestamp_utc"] != scan or str(x["source_validated"]) != "True":
            continue
        pa = float(x["p_a"])
        sel, opp, p = (x["player_a"], x["player_b"], pa) if pa >= 0.5 else (x["player_b"], x["player_a"], 1 - pa)
        w_raw = x.get("exchange_spread_prob", "")
        width = float(w_raw) if w_raw not in ("", None) else float("nan")
        for r in prices.get(x["event_id"], []):
            if {r["player_a"], r["player_b"]} != {x["player_a"], x["player_b"]}:
                continue
            odds = float(r["odds_a"] if r["player_a"] == sel else r["odds_b"])
            q = []
            if width != width:
                q.append("EXCHANGE_WIDTH_UNKNOWN")
            elif width > MAX_WIDTH:
                q.append("EXCHANGE_BOOK_TOO_WIDE")
            lu = r.get("last_update") or ""
            if not lu or scan_t - _ts(lu) > MAX_QUOTE_AGE:
                q.append("QUOTE_STALE_OR_UNTIMED")
            if _ts(x["commence_time"]) <= scan_t:
                q.append("EVENT_STARTED")
            if odds <= 1.0:
                q.append("INVALID_ODDS")
            legs.append(Leg(scan, r["bookmaker"], x["sport_key"], x["event_id"], f"{x['player_a']} v {x['player_b']}",
                            x["commence_time"], sel, opp, p, odds, lu, width if width == width else 1.0,
                            engine_of(x["sport_key"]), tuple(q)))
    return legs


def card_row(c: Card, logged_at: str, provenance: dict) -> dict:
    f = lambda v: "" if v is None else round(v, 6)
    return {"card_id": c.card_id, "rule_version": c.rule_version, "scan": c.scan, "book": c.book, "group": c.group, "k": c.k,
            "status": c.status, "reasons": "|".join(c.reasons), "dependence": c.dependence,
            "dependence_flags": "|".join(c.dependence_flags), "p_joint": f(c.p_joint), "sigma_joint": f(c.sigma_joint),
            "odds_indicative": round(c.odds_indicative, 4), "fair_odds": f(c.fair_odds), "break_even": round(c.break_even, 6),
            "ev": f(c.ev), "ev_low": f(c.ev_low), "ev_high": f(c.ev_high), "all_legs_pos_ev": c.all_legs_pos_ev,
            "all_legs_clean": c.all_legs_clean, "legs_json": json.dumps([asdict(l) for l in c.legs], sort_keys=True),
            "provenance": json.dumps(provenance, sort_keys=True), "logged_at": logged_at}


def append_unique(path: Path, fields: list[str], key: str, rows: list[dict]) -> int:
    existing = {r[key] for r in _read(path)}
    before = path.read_bytes() if path.exists() else b""
    new = []
    for r in rows:
        if r[key] not in existing:
            existing.add(r[key])
            new.append(r)
    if new:
        path.parent.mkdir(parents=True, exist_ok=True)
        header = not path.exists()
        with path.open("a", newline="", encoding="utf-8") as fh:
            w = csv.DictWriter(fh, fieldnames=fields)
            if header:
                w.writeheader()
            w.writerows(new)
        if not path.read_bytes().startswith(before):
            raise RuntimeError(f"immutability violation in {path}")
    return len(new)


def settle(card_rows: list[dict], ledger_preds: list[dict], ledger_settle: list[dict], done: set[str], now: datetime) -> list[dict]:
    """Fail closed: a card settles only when EVERY leg's event has a verified SETTLED_CORRECT/INCORRECT winner; VOID leg -> VOID."""
    winner_by_event: dict[str, tuple[str, str]] = {}
    sett = {r["prediction_id"]: r for r in ledger_settle}
    for p in ledger_preds:
        s = sett.get(p["prediction_id"])
        if s:
            winner_by_event[p["event_id"]] = (s["status"], s.get("winner", ""))
    out = []
    for c in card_rows:
        if c["card_id"] in done:
            continue
        legs = json.loads(c["legs_json"])
        res = [winner_by_event.get(l["event_id"]) for l in legs]
        if any(r is None for r in res):
            continue
        if any(r[0] == "VOID" for r in res):
            status = "VOID"
            won = 0
        elif all(r[0] in ("SETTLED_CORRECT", "SETTLED_INCORRECT") for r in res):
            # audit fix (cer-2 prep): match winner names with the production tennis matcher and never count an
            # unmatched name as a loss (cer-1 compared raw strings, so an accent/format difference would read as LOST)
            from prediction_markets_lab.card_engine.shadow_settle import _same
            m = [(_same(l["selection"], r[1]), _same(l["opponent"], r[1])) for r, l in zip(res, legs)]
            if any(a == b for a, b in m):
                continue
            won = sum(a for a, _ in m)
            status = "WON" if won == len(legs) else "LOST"
        else:
            continue
        out.append({"card_id": c["card_id"], "status": status, "legs_won": won, "legs_total": len(legs),
                    "settled_at": now.isoformat(), "source": "tennis_predictions/ledger_settlements.csv"})
    return out


def file_sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()[:16] if p.exists() else ""
