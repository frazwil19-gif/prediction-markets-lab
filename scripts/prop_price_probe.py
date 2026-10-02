"""ONE bounded prop-price probe (approved by Fraser 2026-10-02: <=2 credits, research only, HARD STOP after one run).

1. FREE /events for soccer_epl; pick the soonest EPL match starting > MIN_LEAD_HOURS from now.
2. ONE event-odds call: markets alternate_totals_corners,alternate_totals_cards, region uk (cost = markets returned x
   1 region <= 2 credits).
Writes raw JSON + headers to research_shadow/prop_price_probe/ and a credit-ledger row in that directory (included in
scripts/credit_report.py). Refuses to run if a probe result already exists, so it can never make a second paid call.
The API key comes from the environment (GitHub secret) and is never written.
"""
from __future__ import annotations

import json
import sys
import urllib.parse
from datetime import datetime, timedelta, timezone
from pathlib import Path

from prediction_markets_lab.ingestion import the_odds_api_loader as L
from prediction_markets_lab.ops import credit_ledger as CL

REPO = Path(__file__).resolve().parents[1]
OUT = REPO / "research_shadow/prop_price_probe"
SPORT, REGION = "soccer_epl", "uk"
MARKETS = ("alternate_totals_corners", "alternate_totals_cards")
MAX_CREDITS = 2
MIN_LEAD_HOURS = 2.0
CONSUMER = "prop_price_probe"


def main() -> int:
    if (OUT / "result.json").exists():
        print("probe result already exists -- HARD STOP, no call made")
        return 0
    assert len(MARKETS) * len(REGION.split(",")) <= MAX_CREDITS
    now = datetime.now(timezone.utc)
    cfg = L.TheOddsApiConfig()
    ev_hdr: dict = {}
    events = L.fetch_events_raw(SPORT, cfg, ev_hdr)
    upcoming = sorted((e for e in events if datetime.fromisoformat(e["commence_time"].replace("Z", "+00:00")) > now + timedelta(hours=MIN_LEAD_HOURS)),
                      key=lambda e: e["commence_time"])
    OUT.mkdir(parents=True, exist_ok=True)
    if not upcoming:
        (OUT / "result.json").write_text(json.dumps({"status": "NO_UPCOMING_EVENT", "at": now.isoformat()}) + "\n")
        return 0
    ev = upcoming[0]
    q = urllib.parse.urlencode({"apiKey": cfg.resolve_api_key(), "regions": REGION, "markets": ",".join(MARKETS),
                                "oddsFormat": "decimal", "includeBetLimits": "true"})
    hdr: dict = {}
    try:
        raw = L._get_json(f"{cfg.base_url}/v4/sports/{SPORT}/events/{ev['id']}/odds?{q}", SPORT, cfg, hdr)
    except L.TheOddsApiResponseError as exc:      # message carries status + body only, never the URL/key
        CL.append(OUT / "credit_ledger.csv", CONSUMER, f"event-odds:{SPORT}:{ev['id']}", CL.PAID, None, 0, hdr, f"error: {exc}"[:300], now=now)
        (OUT / "result.json").write_text(json.dumps({"status": "ERROR", "at": now.isoformat(), "event_id": ev["id"], "error": str(exc)[:500]}) + "\n")
        return 1
    charged = int(hdr.get("x-requests-last") or 0)
    CL.append(OUT / "credit_ledger.csv", CONSUMER, f"event-odds:{SPORT}:{ev['id']}", CL.PAID, charged, 0, hdr,
              "approved single prop price probe (<=2 credits)", now=now)
    (OUT / "raw_event_odds.json").write_text(json.dumps(raw, indent=1, sort_keys=True) + "\n")
    meta = {"status": "OK", "requested_at": now.isoformat(), "event": {k: ev[k] for k in ("id", "home_team", "away_team", "commence_time")},
            "markets_requested": MARKETS, "region": REGION, "credits_charged": charged,
            "headers": {k: hdr.get(k) for k in ("x-requests-last", "x-requests-used", "x-requests-remaining")},
            "free_events_listed": len(events)}
    (OUT / "result.json").write_text(json.dumps(meta, indent=1) + "\n")
    print(json.dumps(meta, indent=1))
    return 0 if charged <= MAX_CREDITS else 1


if __name__ == "__main__":
    sys.exit(main())
