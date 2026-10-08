"""CLV targets, near-close measurement and metrics (pure functions; network and budget live in scripts/clv.py).

Targets:
  * PAPER_BET  — every bsv2 PAPER_BET selection (all engines; live bets are a subset: PAPER_BET + money-eligible).
  * EV_STUDY   — tennis EV-band cohort (pre-registered): first clean bsv2-4 evaluation per prediction after study start.
Reuses the frozen H2 helpers (research_shadow/pre_close.py) by import only.
"""
from __future__ import annotations

import csv
import json
import math
import random
import statistics
from datetime import datetime, timedelta, timezone
from pathlib import Path

from prediction_markets_lab.research_shadow import pre_close as PC

COHORT_FIELDS = ["target_id", "kind", "prediction_id", "selection_id", "rule_version", "sport", "engine_id",
                 "engine_version", "market", "event_key", "event_name", "event_start", "selection", "entry_p",
                 "entry_odds", "entry_book", "entry_commission", "entry_net_ev", "ev_band", "decided_at",
                 "entry_price_observed_at", "entry_price_age_minutes", "entry_reasons", "logged_at"]
CAPTURE_FIELDS = ["target_id", "kind", "sport", "engine_id", "market", "event_key", "selection", "ev_band",
                  "entry_book", "entry_odds", "entry_commission", "entry_p", "entry_net_ev", "decided_at", "event_start",
                  "capture_at", "minutes_before_start", "capture_quality", "sport_key", "close_basis", "p_close",
                  "close_same_book_odds", "close_best_uk_odds", "close_best_uk_book", "n_uk_books", "quotes_json"]
MISSED_FIELDS = ["target_id", "event_key", "event_start", "logged_at", "status", "reason"]
US_KEYS = {"nfl": "americanfootball_nfl", "nhl": "icehockey_nhl", "nba": "basketball_nba"}


def ts(s: str) -> datetime:
    return PC.ts(s)


def read(path: Path) -> list[dict]:
    return PC.read_rows(path)


def append(path: Path, fields: list[str], rows: list[dict], key: str = "target_id") -> int:
    have = {r[key] for r in read(path)}
    new = [r for r in rows if r[key] not in have]
    if not new:
        return 0
    path.parent.mkdir(parents=True, exist_ok=True)
    header = not path.exists()
    with path.open("a", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        if header:
            w.writeheader()
        w.writerows(new)
    return len(new)


def log_missed(path: Path, t: dict, now: datetime, status: str, reason: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    header = not path.exists()
    with path.open("a", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=MISSED_FIELDS)
        if header:
            w.writeheader()
        w.writerow({"target_id": t["target_id"], "event_key": t.get("event_key", ""), "event_start": t.get("event_start", ""),
                    "logged_at": now.isoformat(), "status": status, "reason": reason})


def band(ev: float, bands: list) -> str:
    for lo, hi, label in bands:
        if float(lo) <= ev < float(hi):
            return str(label)
    return "<0" if ev < 0 else str(bands[-1][2])


# ---------- targets ----------
def paper_bet_targets(selections: list[dict], active_from: datetime, bands: list) -> list[dict]:
    out = []
    for s in selections:
        try:
            if ts(s["decision_at"]) < active_from:
                continue
            ev = float(s["net_ev"])
        except (KeyError, ValueError):
            continue
        out.append({"target_id": f"sel:{s['selection_id']}", "kind": "PAPER_BET", "prediction_id": s["prediction_id"],
                    "selection_id": s["selection_id"], "rule_version": s["rule_version"], "sport": s["sport"],
                    "engine_id": s["engine_id"], "engine_version": "", "market": s["market"], "event_key": s["event_key"],
                    "event_name": s["event_name"], "event_start": s["event_start"], "selection": s["selection"],
                    "entry_p": s["probability"], "entry_odds": s["decimal_odds"], "entry_book": s["source"],
                    "entry_commission": s.get("commission") or "0", "entry_net_ev": s["net_ev"], "ev_band": band(ev, bands),
                    "decided_at": s["decision_at"], "entry_price_observed_at": s.get("price_observed_at", ""),
                    "entry_price_age_minutes": s.get("price_age_minutes", ""), "entry_reasons": s.get("reasons", "")})
    return out


def study_cohort(shadow: list[dict], ledger: dict[str, dict], cfg: dict, rule_of: dict[str, str] | None = None) -> list[dict]:
    """Pre-registered rule: first evaluation at/after study_start that is PAPER_BET or fails ONLY EV gates."""
    st = cfg["study"]
    start, clean = ts(st["study_start"]), set(st["clean_reasons"])
    first: dict[str, dict] = {}
    for r in sorted(shadow, key=lambda r: r["evaluated_at"]):
        if r["sport"] != st["sport"] or r["prediction_id"] in first or ts(r["evaluated_at"]) < start:
            continue
        reasons = {x for x in str(r["bsv2_reasons"]).split("|") if x}
        if r["bsv2_decision"] == "PAPER_BET" or (reasons and reasons <= clean):
            try:
                float(r["net_ev"]); float(r["decimal_odds"])
            except ValueError:
                continue
            first[r["prediction_id"]] = r
    out = []
    for pid, r in first.items():
        led = ledger.get(pid)
        if not led:
            continue
        out.append({"target_id": f"ev:{pid}", "kind": "EV_STUDY", "prediction_id": pid, "selection_id": "",
                    "rule_version": (rule_of or {}).get(r["evaluated_at"], st["rule_version_required"]), "sport": r["sport"],
                    "engine_id": r["engine_id"], "engine_version": r["engine_version"], "market": r["market"],
                    "event_key": led["event_key"], "event_name": led["event_name"], "event_start": r["event_start"],
                    "selection": r["selection"], "entry_p": r["probability"], "entry_odds": r["decimal_odds"],
                    "entry_book": r["source"], "entry_commission": r.get("commission") or "0", "entry_net_ev": r["net_ev"],
                    "ev_band": band(float(r["net_ev"]), st["bands"]), "decided_at": r["evaluated_at"],
                    "entry_price_observed_at": r.get("price_observed_at", ""),
                    "entry_price_age_minutes": r.get("price_age_minutes", ""), "entry_reasons": r["bsv2_reasons"]})
    return [t for t in out if t["rule_version"] == st["rule_version_required"]]


def capture_eligible(t: dict, cfg: dict) -> bool:
    return t["kind"] == "PAPER_BET" or t["ev_band"] in cfg["study"]["capture_bands"]


def sport_key(t: dict, football_keys: dict[str, str]) -> str | None:
    head = str(t["event_key"]).split("|")[0]
    if head in ("nfl", "nhl"):
        return US_KEYS[head]
    return PC.sport_key_for(t, football_keys)


def due(targets: list[dict], done: set[str], now: datetime, window_min: float) -> list[dict]:
    out = []
    for t in targets:
        if t["target_id"] in done:
            continue
        try:
            start = ts(t["event_start"])
        except (KeyError, ValueError):
            continue
        if now < start <= now + timedelta(minutes=window_min):
            out.append(t)
    return out


def find_event(raw: list, t: dict) -> dict | None:
    parts = str(t["event_key"]).split("|")
    if parts[0] in ("nfl", "nhl") and len(parts) >= 2:
        return next((e for e in raw if e.get("id") == parts[1]), None)
    return PC.find_event(raw, t)


def measure(t: dict, event: dict, now: datetime, near_close_min: float, key: str) -> dict | None:
    """Close quotes for the target's selection. Never after start. Tennis: exchange back/lay mid; others: UK median fair."""
    on = PC.outcome_names(event, t)
    if not on:
        return None
    names, target = on
    ref = PC.reference(event, names)
    if not ref:
        return None
    basis, p_ref, uk, _seen = ref
    start = ts(event["commence_time"])
    if start <= now:
        return None
    mins = (start - now).total_seconds() / 60
    quotes = {}
    for b in event.get("bookmakers", []):
        for m in b.get("markets", []):
            for o in m.get("outcomes", []):
                if o.get("name") == target:
                    quotes[f"{b['key']}:{m['key']}"] = {"price": o.get("price"), "last_update": m.get("last_update") or b.get("last_update")}
    uk_prices = sorted(((q[target], k) for k, q in uk.items()), reverse=True)
    same = uk.get(t["entry_book"], {}).get(target)
    if same is None and f"{t['entry_book']}:h2h" in quotes:
        same = quotes[f"{t['entry_book']}:h2h"]["price"]
    best = uk_prices[0] if uk_prices else (None, "")
    return {**{k: t.get(k, "") for k in ("target_id", "kind", "sport", "engine_id", "market", "event_key", "selection",
                                         "ev_band", "entry_book", "entry_odds", "entry_commission", "entry_p",
                                         "entry_net_ev", "decided_at", "event_start")},
            "capture_at": now.isoformat(), "minutes_before_start": round(mins, 1),
            "capture_quality": "NEAR_CLOSE" if mins <= near_close_min else "PRE_CLOSE", "sport_key": key,
            "close_basis": basis, "p_close": round(p_ref[target], 6), "close_same_book_odds": same,
            "close_best_uk_odds": best[0], "close_best_uk_book": best[1], "n_uk_books": len(uk_prices),
            "quotes_json": json.dumps(quotes, sort_keys=True)}


# ---------- metrics ----------
def net_odds(o: float, c: float) -> float:
    return 1 + (o - 1) * (1 - c)


def clv_row(c: dict) -> dict:
    o, com = float(c["entry_odds"]), float(c.get("entry_commission") or 0)
    p_close, p_entry = float(c["p_close"]), float(c["entry_p"])
    same = float(c["close_same_book_odds"]) if c.get("close_same_book_odds") not in (None, "") else None
    best = float(c["close_best_uk_odds"]) if c.get("close_best_uk_odds") not in (None, "") else None
    return {"fair_clv": net_odds(o, com) * p_close - 1, "price_clv_same_book": (o / same - 1) if same else None,
            "price_clv_best": (o / best - 1) if best else None, "p_move": p_close - p_entry}


def bootstrap_ci(xs: list[float], n: int, seed: int) -> tuple[float, float] | None:
    if len(xs) < 2:
        return None
    rng = random.Random(seed)
    means = sorted(statistics.fmean(rng.choices(xs, k=len(xs))) for _ in range(n))
    return means[int(0.025 * n)], means[int(0.975 * n) - 1]


def summarise(xs: list[float], cfg: dict) -> dict:
    xs = [x for x in xs if x is not None]
    if not xs:
        return {"n": 0}
    out = {"n": len(xs), "mean": round(statistics.fmean(xs), 5), "median": round(statistics.median(xs), 5),
           "positive_rate": round(sum(x > 0 for x in xs) / len(xs), 3)}
    if len(xs) >= cfg["min_n_for_ci"]:
        ci = bootstrap_ci(xs, cfg["bootstrap_samples"], cfg["bootstrap_seed"])
        out["ci95"] = [round(ci[0], 5), round(ci[1], 5)] if ci else None
    return out


def outcome_stats(rows: list[dict], settle: dict[str, dict]) -> dict:
    s = [(float(r["entry_p"]), float(r["entry_odds"]), float(r.get("entry_commission") or 0), float(r["entry_net_ev"]),
          settle[r["prediction_id"]]["correct"] == "1") for r in rows
         if settle.get(r["prediction_id"], {}).get("correct") in ("0", "1")]
    if not s:
        return {"settled": 0}
    pnl = [(net_odds(o, c) - 1) if won else -1.0 for p, o, c, ev, won in s]
    eps = 1e-12
    return {"settled": len(s), "wins": sum(w for *_, w in s), "expected_wins": round(sum(p for p, *_ in s), 2),
            "pnl_gbp_at_1": round(sum(pnl), 2), "roi": round(sum(pnl) / len(s), 4),
            "expected_profit_gbp_at_1": round(sum(ev for _, _, _, ev, _ in s), 2),
            "brier": round(statistics.fmean((p - w) ** 2 for p, *_, w in s), 4),
            "log_loss": round(statistics.fmean(-(w * math.log(max(p, eps)) + (1 - w) * math.log(max(1 - p, eps)))
                                               for p, *_, w in s), 4)}


def group_by(rows: list[dict], key) -> dict[str, list[dict]]:
    g: dict[str, list[dict]] = {}
    for r in rows:
        g.setdefault(key(r), []).append(r)
    return dict(sorted(g.items()))


def tier_b_proxy(cohort: list[dict], ex_snaps: list[dict], price_snaps: list[dict]) -> dict[str, dict]:
    """Free proxy: last scheduled tennis scan after entry and before start (exchange mid + same-book price)."""
    ex_by: dict[str, list[dict]] = {}
    for r in ex_snaps:
        ex_by.setdefault(r["event_id"], []).append(r)
    px: dict[tuple, float] = {}
    for r in price_snaps:
        px[(r["scan_timestamp_utc"], r["event_id"], r["bookmaker"], "a")] = r["odds_a"]
        px[(r["scan_timestamp_utc"], r["event_id"], r["bookmaker"], "b")] = r["odds_b"]
    out = {}
    for t in cohort:
        parts = str(t["event_key"]).split("|")
        if len(parts) < 3:
            continue
        eid, entry, start = parts[2], ts(t["decided_at"]), ts(t["event_start"])
        cands = [r for r in ex_by.get(eid, []) if entry < ts(r["scan_timestamp_utc"]) < start
                 and r.get("source_validated") == "True"]
        if not cands:
            continue
        r = max(cands, key=lambda r: r["scan_timestamp_utc"])
        side = "a" if r["player_a"] == t["selection"] else "b" if r["player_b"] == t["selection"] else None
        if not side:
            continue
        p = float(r["p_" + side])
        same = px.get((r["scan_timestamp_utc"], eid, t["entry_book"], side))
        o, c = float(t["entry_odds"]), float(t.get("entry_commission") or 0)
        out[t["target_id"]] = {"proxy_fair_clv": net_odds(o, c) * p - 1, "proxy_p_move": p - float(t["entry_p"]),
                               "proxy_price_clv_same_book": (o / float(same) - 1) if same not in (None, "") else None,
                               "proxy_minutes_before_start": round((start - ts(r["scan_timestamp_utc"])).total_seconds() / 60, 1)}
    return out


def now_utc() -> datetime:
    return datetime.now(timezone.utc)
