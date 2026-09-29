"""Executable price snapshots (V2-6). Only prices production already fetched; nothing reconstructed or invented.

Probability-source prices (for example the Betfair back/lay midpoint that produced P) are never used as executable
prices. Synthetic prices (the Double Chance dutch of best 1X2 prices) are not executable and are excluded.
"""
from __future__ import annotations

import csv
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path


def ts(s: str) -> datetime:
    d = datetime.fromisoformat(str(s).replace("Z", "+00:00"))
    return d if d.tzinfo else d.replace(tzinfo=timezone.utc)


@dataclass(frozen=True)
class PriceSnapshot:
    prediction_id: str
    source: str            # normalised book/exchange key, lower case (e.g. "betfair_ex_uk", "william hill")
    decimal_odds: float
    observed_at: datetime  # when production fetched the response
    quote_at: datetime     # provider last_update for the quote (falls back to observed_at)
    origin: str            # which production artefact supplied it


def norm_source(s: str) -> str:
    return str(s).strip().lower()


def from_ledger_row(row: dict) -> PriceSnapshot | None:
    """The executable price already recorded on a unified prediction row (tennis exchange back / football best book)."""
    lp, src = row.get("live_price", ""), row.get("live_price_source", "") or ""
    if lp in ("", None) or src.startswith("SYNTHETIC"):
        return None
    try:
        odds = float(lp)
    except ValueError:
        return None
    if odds <= 1.0:
        return None
    if src.startswith("betfair_ex_uk back"):
        source = "betfair_ex_uk"
    elif src.startswith("odds_api:"):
        source = norm_source(src.split(":", 1)[1])
    else:
        return None  # unknown provenance: never guessed
    t = ts(row["prediction_timestamp"])
    return PriceSnapshot(row["prediction_id"], source, odds, t, t, "unified_ledger.live_price")


# ---------------------------------------------------------------- tennis: prices from the tennis board's own response
TENNIS_SNAPSHOT_FIELDS = ["scan_timestamp_utc", "sport_key", "event_id", "player_a", "player_b", "bookmaker", "market",
                          "odds_a", "odds_b", "last_update"]


def tennis_snapshot_rows(quotes: list, scan_ts: datetime) -> list[dict]:
    """Flatten parsed TennisEventQuotes (already paid for by the board) into snapshot rows. 0 extra credits."""
    out = []
    for q in quotes:
        base = {"scan_timestamp_utc": scan_ts.isoformat(), "sport_key": q.sport_key, "event_id": q.event_id,
                "player_a": q.player_a, "player_b": q.player_b}
        if q.exchange_back:
            out.append({**base, "bookmaker": "betfair_ex_uk", "market": "h2h", "odds_a": q.exchange_back["a"],
                        "odds_b": q.exchange_back["b"],
                        "last_update": q.exchange_last_update.isoformat() if q.exchange_last_update else ""})
        for book, (oa, ob) in sorted(q.bookmaker_h2h.items()):
            lu = q.bookmaker_last_update.get(book)
            out.append({**base, "bookmaker": book, "market": "h2h", "odds_a": oa, "odds_b": ob,
                        "last_update": lu.isoformat() if lu else ""})
    return out


def append_tennis_snapshots(path: Path, rows: list[dict]) -> int:
    if not rows:
        return 0
    new = not path.exists()
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=TENNIS_SNAPSHOT_FIELDS)
        if new:
            w.writeheader()
        w.writerows(rows)
    return len(rows)


def tennis_from_snapshots(pred: dict, snap_rows: list[dict]) -> list[PriceSnapshot]:
    """Prices for the predicted side of one tennis prediction (matched on provider event id + player names)."""
    if pred.get("sport") != "tennis" or not pred.get("event_id"):
        return []
    try:
        pa, pb = pred["event_name"].split(" v ", 1)
    except ValueError:
        return []
    sel = pred["selection"]
    if sel not in (pa, pb):
        return []
    out = []
    for r in snap_rows:
        if r.get("event_id") != pred["event_id"] or r.get("market") != "h2h":
            continue
        if {r.get("player_a"), r.get("player_b")} != {pa, pb}:
            continue
        try:
            odds = float(r["odds_a"] if sel == r["player_a"] else r["odds_b"])
            seen = ts(r["scan_timestamp_utc"])
        except (KeyError, ValueError):
            continue
        quote = ts(r["last_update"]) if r.get("last_update") else seen
        if odds > 1.0:
            out.append(PriceSnapshot(pred["prediction_id"], norm_source(r["bookmaker"]), odds, seen, quote,
                                     "tennis_predictions/price_snapshots.csv"))
    return out


# ---------------------------------------------------------------- football: later daily cards
def football_from_card(pred: dict, card: dict) -> list[PriceSnapshot]:
    """Best price for this exact selection on a daily card (the card the unified row came from, or a later one)."""
    if pred.get("sport") != "football" or pred.get("market") not in ("1x2", "over_under_2_5"):
        return []
    out = []
    for c in card.get("candidates", []):
        if not c.get("kickoff_time"):
            continue
        key = f"football|{c['competition']}|{c['event']}|{ts(c['kickoff_time']).astimezone(timezone.utc).isoformat()}"
        if key != pred["event_key"] or c.get("market") != pred["market"] or c.get("selection") != pred["selection"]:
            continue
        try:
            odds = float(c["available_odds"])
            seen = ts(c.get("price_timestamp") or card["data_timestamp"])
        except (KeyError, TypeError, ValueError):
            continue
        if odds > 1.0:
            out.append(PriceSnapshot(pred["prediction_id"], norm_source(c["bookmaker"]), odds, seen, seen, "daily_card"))
    return out
