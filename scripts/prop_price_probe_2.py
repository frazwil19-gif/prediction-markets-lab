"""Prop price probe 2 — SECOND AND FINAL bounded probe (approved by Fraser 2026-10-02; <=2 credits; HARD STOP).

Pre-registered: research/platform_v2/props_c1/price_probe_2/GATE0_PREREGISTRATION.md. Deterministic timing: pays only
if an EPL event kicks off within [MIN_H, MAX_H] hours (preferring [PREF_LO, PREF_HI]); otherwise logs the attempt and
makes NO paid call. Never calls again once probe2/result.json exists. The API key comes from the environment only.
"""
from __future__ import annotations

import csv
import json
import sys
import urllib.parse
from datetime import datetime, timezone
from pathlib import Path

from prediction_markets_lab.ingestion import the_odds_api_loader as L
from prediction_markets_lab.ops import credit_ledger as CL

REPO = Path(__file__).resolve().parents[1]
OUT = REPO / "research_shadow/prop_price_probe/probe2"
SPORT, REGION = "soccer_epl", "uk"
MARKETS = ("alternate_totals_corners", "alternate_totals_cards")
MAX_CREDITS = 2
MIN_H, MAX_H, PREF_LO, PREF_HI = 1.0, 24.0, 6.0, 12.0
CONSUMER = "prop_price_probe"


def hours_to(ev: dict, now: datetime) -> float:
    return (datetime.fromisoformat(ev["commence_time"].replace("Z", "+00:00")) - now).total_seconds() / 3600


def choose(events: list[dict], now: datetime) -> tuple[dict | None, str]:
    timed = sorted(((hours_to(e, now), e) for e in events), key=lambda t: t[0])
    pref = [e for h, e in timed if PREF_LO <= h <= PREF_HI]
    if pref:
        return pref[0], "PREFERRED_6_12H"
    elig = [e for h, e in timed if MIN_H <= h <= MAX_H]
    if elig:
        return elig[0], "ELIGIBLE_1_24H"
    return None, f"NO_EVENT_WITHIN_{MIN_H:g}_{MAX_H:g}H (next: {timed[0][0]:.1f}h)" if timed else "NO_EVENTS_LISTED"


def log_attempt(now: datetime, status: str, detail: str) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    p = OUT / "attempts.csv"
    new = not p.exists()
    with p.open("a", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        if new:
            w.writerow(["at_utc", "status", "detail"])
        w.writerow([now.isoformat(), status, detail])


def main(now: datetime | None = None, fetch_events=None, get_json=None) -> int:
    now = now or datetime.now(timezone.utc)
    if (OUT / "result.json").exists():
        print("probe 2 result already exists -- HARD STOP, no call made")
        return 0
    assert len(MARKETS) * len(REGION.split(",")) <= MAX_CREDITS
    cfg = L.TheOddsApiConfig()
    events = (fetch_events or L.fetch_events_raw)(SPORT, cfg, {})          # FREE
    ev, why = choose(events if isinstance(events, list) else [], now)
    if ev is None:
        log_attempt(now, "NO_PAID_CALL", why)
        print(f"no eligible event ({why}); no paid call; authorisation not consumed")
        return 0
    h = hours_to(ev, now)
    q = urllib.parse.urlencode({"apiKey": cfg.resolve_api_key(), "regions": REGION, "markets": ",".join(MARKETS),
                                "oddsFormat": "decimal", "includeBetLimits": "true"})
    hdr: dict = {}
    OUT.mkdir(parents=True, exist_ok=True)
    meta = {"requested_at": now.isoformat(), "selection_rule": why, "hours_before_kickoff": round(h, 2),
            "event": {k: ev[k] for k in ("id", "home_team", "away_team", "commence_time")}, "markets_requested": MARKETS, "region": REGION}
    try:
        raw = (get_json or L._get_json)(f"{cfg.base_url}/v4/sports/{SPORT}/events/{ev['id']}/odds?{q}", SPORT, cfg, hdr)
    except L.TheOddsApiResponseError as exc:        # message carries status + body only, never the URL/key
        CL.append(OUT / "credit_ledger.csv", CONSUMER, f"event-odds:{SPORT}:{ev['id']}", CL.PAID, None, 0, hdr, f"error: {exc}"[:300], now=now)
        (OUT / "result.json").write_text(json.dumps({**meta, "status": "ERROR", "error": str(exc)[:500]}, indent=1) + "\n")
        log_attempt(now, "PAID_CALL_ERROR", str(exc)[:200])
        return 1
    charged = int(hdr.get("x-requests-last") or 0)
    CL.append(OUT / "credit_ledger.csv", CONSUMER, f"event-odds:{SPORT}:{ev['id']}", CL.PAID, charged, 0, hdr,
              "approved second and final prop price probe (<=2 credits)", now=now)
    (OUT / "raw_event_odds.json").write_text(json.dumps(raw, indent=1, sort_keys=True) + "\n")
    meta.update({"status": "OK", "credits_charged": charged,
                 "headers": {k: hdr.get(k) for k in ("x-requests-last", "x-requests-used", "x-requests-remaining")},
                 "n_bookmakers_returned": len(raw.get("bookmakers", [])) if isinstance(raw, dict) else None})
    (OUT / "result.json").write_text(json.dumps(meta, indent=1) + "\n")
    log_attempt(now, "PAID_CALL_MADE", f"{ev['home_team']} v {ev['away_team']} at T-{h:.2f}h, charged {charged}")
    print(json.dumps(meta, indent=1))
    return 0 if charged <= MAX_CREDITS else 1


if __name__ == "__main__":
    sys.exit(main())
