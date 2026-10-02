"""H2 PRE_CLOSE_VALUE measurement (pre-registered: research/platform_v2/track_a/H2_PREREGISTRATION.md).

Diagnostic only: never enters qualification, grading or staking; decision-time fields are copied, never modified.
Pure functions here; network + budget handling lives in scripts/capture_pre_close.py.
"""
from __future__ import annotations

import csv
import statistics
from datetime import datetime, timedelta, timezone
from pathlib import Path

FIELDS = ["selection_id", "prediction_id", "rule_version", "sport", "event_key", "event_name", "selection",
          "decision_probability", "decision_bookmaker", "decision_odds", "commission", "decision_at", "price_observed_at",
          "capture_at", "event_commence_api", "minutes_before_start", "reference_basis", "p_ref", "best_uk_odds",
          "best_uk_book", "median_uk_odds", "n_uk_books", "pre_close_value", "pre_close_price_ratio", "clv_proxy_quality",
          "reference_quote_at", "best_uk_quote_at", "commission_basis"]
MISSED_FIELDS = ["selection_id", "event_key", "event_start", "decision_at", "logged_at", "status", "reason"]
ATTEMPT_FAILED, NOT_CAPTURED = "ATTEMPT_FAILED", "NOT_CAPTURED_BEFORE_START"     # missing data; never imputed
EXCHANGES = ("betfair_ex_uk", "betfair_ex_eu", "smarkets", "matchbook")
NEAR_CLOSE_MIN = 10.0


def ts(s: str) -> datetime:
    d = datetime.fromisoformat(str(s).replace("Z", "+00:00"))
    return d if d.tzinfo else d.replace(tzinfo=timezone.utc)


def sport_key_for(sel: dict, football_keys: dict[str, str]) -> str | None:
    """tennis|<sport_key>|<event_id> ; nba|<event_id> ; football|<competition>|<event>|<kickoff>."""
    parts = str(sel["event_key"]).split("|")
    if parts[0] == "tennis" and len(parts) >= 3:
        return parts[1]
    if parts[0] == "nba":
        return "basketball_nba"
    if parts[0] == "football" and len(parts) >= 2:
        return football_keys.get(parts[1])
    return None


def event_id_for(sel: dict) -> str | None:
    parts = str(sel["event_key"]).split("|")
    if parts[0] == "tennis" and len(parts) >= 3:
        return parts[2]
    if parts[0] == "nba" and len(parts) >= 2:
        return parts[1]
    return None


def due(selections: list[dict], done: set[str], now: datetime, window_min: float) -> list[dict]:
    """Selections not yet captured whose (ledger) start is within (now, now + window]. Never after start."""
    out = []
    for s in selections:
        if s["selection_id"] in done:
            continue
        try:
            start = ts(s["event_start"])
        except (KeyError, ValueError):
            continue
        if now < start <= now + timedelta(minutes=window_min):
            out.append(s)
    return out


def find_event(raw: list, sel: dict) -> dict | None:
    eid = event_id_for(sel)
    if eid:
        return next((e for e in raw if e.get("id") == eid), None)
    name = str(sel.get("event_name", ""))
    if " v " not in name:
        return None
    home, away = (x.strip().lower() for x in name.split(" v ", 1))
    hits = [e for e in raw if str(e.get("home_team", "")).lower() == home and str(e.get("away_team", "")).lower() == away]
    return hits[0] if len(hits) == 1 else None      # never guess between several


def outcome_names(event: dict, sel: dict) -> tuple[list[str], str] | None:
    """Ordered outcome names for the market and the name of our selection (football home/draw/away mapped)."""
    s = str(sel["selection"])
    if str(sel["event_key"]).startswith("football|"):
        names = [event["home_team"], "Draw", event["away_team"]]
        target = {"home": names[0], "draw": "Draw", "away": names[2]}.get(s.lower())
        return (names, target) if target else None
    for b in event.get("bookmakers", []):
        for m in b.get("markets", []):
            if m.get("key") == "h2h":
                names = [o["name"] for o in m.get("outcomes", [])]
                return (names, s) if s in names else None
    return None


def reference(event: dict, names: list[str]) -> tuple[str, dict[str, float], dict[str, dict[str, float]], dict[str, str]] | None:
    """(basis, p_ref by name, uk book prices, quote last_update by 'book:market'). Exchange mid (back/lay) de-vig if available, else median UK fair."""
    back, lay, uk = {}, {}, {}
    seen: dict[str, str] = {}
    for b in event.get("bookmakers", []):
        for m in b.get("markets", []):
            prices = {o["name"]: float(o["price"]) for o in m.get("outcomes", []) if float(o.get("price", 0)) > 1}
            if set(prices) != set(names):
                continue
            seen[f"{b['key']}:{m['key']}"] = m.get("last_update") or b.get("last_update") or ""
            if b["key"] == "betfair_ex_uk" and m["key"] == "h2h":
                back = prices
            elif b["key"] == "betfair_ex_uk" and m["key"] == "h2h_lay":
                lay = prices
            elif m["key"] == "h2h" and b["key"] not in EXCHANGES:
                uk[b["key"]] = prices
    if back and lay:
        mid = {n: 2.0 / (1 / back[n] + 1 / lay[n]) for n in names}          # mid of implied probabilities
        inv = {n: 1 / mid[n] for n in names}
        s = sum(inv.values())
        return "EXCHANGE_MID", {n: inv[n] / s for n in names}, uk, seen
    if uk:
        fair = []
        for q in uk.values():
            inv = {n: 1 / q[n] for n in names}
            s = sum(inv.values())
            fair.append({n: inv[n] / s for n in names})
        return "UK_MEDIAN_FAIR", {n: statistics.median(f[n] for f in fair) for n in names}, uk, seen
    return None


def measure(sel: dict, event: dict, now: datetime) -> dict | None:
    on = outcome_names(event, sel)
    if not on:
        return None
    names, target = on
    ref = reference(event, names)
    if not ref:
        return None
    basis, p_ref, uk, seen = ref
    start = ts(event["commence_time"])
    if start <= now:
        return None                                                     # never measure after start
    o, c, p = float(sel["decimal_odds"]), float(sel.get("commission") or 0.0), p_ref[target]
    uk_prices = sorted(((q[target], k) for k, q in uk.items()), reverse=True)
    mins = (start - now).total_seconds() / 60
    best = uk_prices[0] if uk_prices else (None, "")
    return {"selection_id": sel["selection_id"], "prediction_id": sel["prediction_id"], "rule_version": sel["rule_version"],
            "sport": sel["sport"], "event_key": sel["event_key"], "event_name": sel["event_name"], "selection": sel["selection"],
            "decision_probability": sel["probability"], "decision_bookmaker": sel.get("source", ""), "decision_odds": o,
            "commission": c, "decision_at": sel.get("decision_at", ""), "price_observed_at": sel.get("price_observed_at", ""),
            "capture_at": now.isoformat(), "event_commence_api": event["commence_time"], "minutes_before_start": round(mins, 1),
            "reference_basis": basis, "p_ref": round(p, 6), "best_uk_odds": best[0], "best_uk_book": best[1],
            "median_uk_odds": statistics.median(x for x, _ in uk_prices) if uk_prices else None, "n_uk_books": len(uk_prices),
            "pre_close_value": round(p * (o - 1) * (1 - c) - (1 - p), 6),
            "pre_close_price_ratio": round(o / best[0] - 1, 6) if best[0] else None,
            "clv_proxy_quality": "NEAR_CLOSE" if mins <= NEAR_CLOSE_MIN else "PRE_CLOSE",
            "reference_quote_at": (max(v for k, v in seen.items() if k.startswith("betfair_ex_uk:")) if basis == "EXCHANGE_MID"
                                   else ";".join(f"{k.split(':')[0]}={v}" for k, v in sorted(seen.items()) if not k.startswith(EXCHANGES))),
            "best_uk_quote_at": seen.get(f"{best[1]}:h2h", "") if best[1] else "",
            "commission_basis": "decision-time commission copied from the selection row; exchange reference is a mid, no commission"}


def read_rows(path: Path) -> list[dict]:
    if not path.exists():
        return []
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def append_rows(path: Path, rows: list[dict]) -> int:
    done = {r["selection_id"] for r in read_rows(path)}
    new = [r for r in rows if r["selection_id"] not in done]
    if not new:
        return 0
    path.parent.mkdir(parents=True, exist_ok=True)
    header = not path.exists()
    with path.open("a", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        if header:
            w.writeheader()
        w.writerows(new)
    return len(new)


def log_missed(path: Path, sel: dict, now: datetime, status: str, reason: str) -> None:
    """Append-only log of capture attempts that failed and of selections never captured before start."""
    path.parent.mkdir(parents=True, exist_ok=True)
    header = not path.exists()
    with path.open("a", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=MISSED_FIELDS)
        if header:
            w.writeheader()
        w.writerow({"selection_id": sel["selection_id"], "event_key": sel.get("event_key", ""), "event_start": sel.get("event_start", ""),
                    "decision_at": sel.get("decision_at", ""), "logged_at": now.isoformat(), "status": status, "reason": reason})


def never_captured(selections: list[dict], captured: set[str], already: set[str], now: datetime, active_from: datetime) -> list[dict]:
    """Selections decided on/after H2 go-live whose start has passed with no capture (e.g. cron did not fire in the window)."""
    out = []
    for s in selections:
        if s["selection_id"] in captured or s["selection_id"] in already:
            continue
        try:
            if ts(s["event_start"]) <= now and ts(s.get("decision_at") or s["event_start"]) >= active_from:
                out.append(s)
        except ValueError:
            continue
    return out
