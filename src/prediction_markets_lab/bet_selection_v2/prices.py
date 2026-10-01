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
    # bsv2-2: the engine probability for this selection computed from the SAME snapshot as the price (None = unknown ->
    # the candidate is rejected; a later price is never paired with an earlier probability)
    p_same_snapshot: float | None = None
    # bsv2-3: Betfair back/lay spread (probability points, max over both runners) behind p_same_snapshot, and the
    # engine source. None spread with source EXCHANGE_MID = unknown -> fail closed.
    p_same_spread: float | None = None
    p_same_source: str | None = None


def norm_source(s: str) -> str:
    return str(s).strip().lower()


# bsv2-4: marker for a ledger-path tennis quote whose same-snapshot engine source/spread could not be resolved.
# evaluate treats it exactly like an EXCHANGE_MID probability with unknown spread (fail closed: EXCHANGE_SPREAD_UNKNOWN).
UNRESOLVED_SOURCE = "UNRESOLVED_LEDGER_SNAPSHOT"


def from_ledger_row(row: dict, prob_rows: list[dict] | None = None) -> PriceSnapshot | None:
    """The executable price already recorded on a unified prediction row (tennis exchange back / football best book).

    bsv2-4 (V2-11): a tennis ledger P is a Betfair-derived engine probability, so the exchange-quality information of
    the SAME snapshot is attached from ``prob_rows`` (the row whose scan timestamp equals the prediction timestamp, same
    event and players, validated). If it cannot be resolved the snapshot is marked UNRESOLVED_SOURCE -- never assumed
    narrow, never taken from another scan."""
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
    p = float(row["estimated_probability"]) if str(row.get("prediction_valid")) == "True" else None
    spread, p_src = None, None
    if row.get("sport") == "tennis":
        p_src = UNRESOLVED_SOURCE
        same = [v for k, v in same_scan_details(row, prob_rows or []).items() if ts(k) == t]
        if len(same) == 1:
            _p_scan, spread, p_src = same[0]
            p_src = p_src or UNRESOLVED_SOURCE
    return PriceSnapshot(row["prediction_id"], source, odds, t, t, "unified_ledger.live_price", p, spread, p_src)


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


PROB_SNAPSHOT_FIELDS = ["scan_timestamp_utc", "sport_key", "event_id", "player_a", "player_b", "commence_time", "source",
                        "source_validated", "p_a", "p_b"]


def tennis_probability_rows(preds: list, scan_ts: datetime) -> list[dict]:
    """Every prediction the frozen engine produced in this scan (including events already in the ledger). 0 credits."""
    return [{"scan_timestamp_utc": scan_ts.isoformat(), "sport_key": p.sport_key, "event_id": p.event_id,
             "player_a": p.player_a, "player_b": p.player_b, "commence_time": p.commence_time, "source": p.source,
             "source_validated": p.source_validated, "p_a": p.p_a, "p_b": p.p_b} for p in preds]


EXCHANGE_PROB_FIELDS = PROB_SNAPSHOT_FIELDS + ["raw_prices", "exchange_spread_prob"]


def exchange_spread_prob(raw: str) -> float | None:
    """max over runners of (1/back - 1/lay): width of the exchange book in probability points; None if not parseable."""
    import re
    m = re.search(r"ex_back=([\d.]+)/([\d.]+);ex_lay=([\d.]+)/([\d.]+)", raw or "")
    if not m:
        return None
    ba, bb, la, lb = map(float, m.groups())
    if min(ba, bb, la, lb) <= 1.0:
        return None
    return round(max(1 / ba - 1 / la, 1 / bb - 1 / lb), 6)


def tennis_exchange_probability_rows(preds: list, scan_ts: datetime) -> list[dict]:
    rows = tennis_probability_rows(preds, scan_ts)
    for r, p in zip(rows, preds):
        r["raw_prices"] = p.raw_prices
        r["exchange_spread_prob"] = exchange_spread_prob(p.raw_prices)
    return rows


def append_rows(path: Path, fields: list[str], rows: list[dict]) -> int:
    if not rows:
        return 0
    new = not path.exists()
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        if new:
            w.writeheader()
        w.writerows(rows)
    return len(rows)


def same_scan_details(pred: dict, prob_rows: list[dict]) -> dict[str, tuple[float, float | None, str]]:
    """scan_timestamp -> (P for pred's selection, exchange spread or None, engine source), validated rows only."""
    try:
        pa, pb = pred["event_name"].split(" v ", 1)
    except ValueError:
        return {}
    out = {}
    for r in prob_rows:
        if r.get("event_id") != pred.get("event_id") or str(r.get("source_validated")) != "True":
            continue
        if {r.get("player_a"), r.get("player_b")} != {pa, pb}:
            continue
        try:
            p = float(r["p_a"] if pred["selection"] == r["player_a"] else r["p_b"])
        except (KeyError, ValueError):
            continue
        sp = r.get("exchange_spread_prob")
        out[r["scan_timestamp_utc"]] = (p, float(sp) if sp not in (None, "") else None, r.get("source", ""))
    return out


def same_scan_probability(pred: dict, prob_rows: list[dict]) -> dict[str, float]:
    """scan_timestamp -> validated engine P for pred's selection in that scan."""
    try:
        pa, pb = pred["event_name"].split(" v ", 1)
    except ValueError:
        return {}
    out = {}
    for r in prob_rows:
        if r.get("event_id") != pred.get("event_id") or str(r.get("source_validated")) != "True":
            continue
        if {r.get("player_a"), r.get("player_b")} != {pa, pb}:
            continue
        try:
            out[r["scan_timestamp_utc"]] = float(r["p_a"] if pred["selection"] == r["player_a"] else r["p_b"])
        except (KeyError, ValueError):
            continue
    return out


def tennis_from_snapshots(pred: dict, snap_rows: list[dict], prob_rows: list[dict] | None = None) -> list[PriceSnapshot]:
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
    same_p = same_scan_details(pred, prob_rows or [])
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
                                     "tennis_predictions/price_snapshots.csv",
                                     *(same_p.get(r["scan_timestamp_utc"]) or (None, None, None))))
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
        try:
            p_card = float(c["estimated_probability"])   # same card => same snapshot as the price
        except (KeyError, TypeError, ValueError):
            p_card = None
        if odds > 1.0:
            out.append(PriceSnapshot(pred["prediction_id"], norm_source(c["bookmaker"]), odds, seen, seen, "daily_card", p_card))
    return out
