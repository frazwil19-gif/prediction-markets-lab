#!/usr/bin/env python3
"""Phase 1 smoke test: the first REAL request to The Odds API (2026-09-19).

Operator's "MAJOR NEXT PHASE -- LIVE COMMISSIONING" instruction, Phase 1:
"Perform the minimum sensible REAL request first. Do not waste API
credits." This script therefore does the smallest useful sequence:

  1. GET /v4/sports (quota-free, but still needs a key) -- confirms the
     key itself works, and independently verifies the three configured
     sport_key strings (soccer_epl, soccer_efl_champ, soccer_spl) are
     real, rather than trusting the third-party documentation they were
     sourced from (see the implementation checkpoint's flagged caveat).
  2. ONE real odds call for a SINGLE sport_key (soccer_epl) -- not all
     three leagues -- run through this project's actual production
     adapter (ingestion.the_odds_api_loader.parse_odds_response /
     build_canonical_odds_and_metadata), so this is a genuine first
     validation of code that has, until now, only been tested against
     constructed fixture JSON.

Prints a structural audit covering every item the operator's instruction
asked for: API success, sports/competitions available, fixtures
returned, bookmakers returned, UK bookmaker coverage, 1X2/O-U 2.5
coverage, timestamps, decimal prices, team-name consistency, duplicates,
missing prices, stale prices, quota before/after, and the actual request
cost -- all in one pass, without a second live call.

Does NOT run the probability/EV/grading engine and does NOT write a
Daily Bet Card -- this is a data-audit step only, per the instruction's
"do not waste API credits" and "audit... feed the real response through
the existing canonical adapter" before anything else.
"""

from __future__ import annotations

import json
import sys
import urllib.error
import urllib.parse
import urllib.request
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from prediction_markets_lab.ingestion.the_odds_api_loader import (
    TheOddsApiConfig,
    TheOddsApiCredentialError,
    TheOddsApiResponseError,
    build_canonical_odds_and_metadata,
    parse_odds_response,
)

AUDIT_OUT_DIR = Path(__file__).resolve().parent.parent / "reports" / "audits"


def _get(url: str) -> tuple[int, dict, bytes]:
    request = urllib.request.Request(url, headers={"Accept": "application/json"})
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            return response.status, dict(response.headers), response.read()
    except urllib.error.HTTPError as exc:
        body = exc.read()
        return exc.code, dict(exc.headers or {}), body


def main() -> int:
    config = TheOddsApiConfig()
    try:
        api_key = config.resolve_api_key()
    except TheOddsApiCredentialError as exc:
        print(f"CREDENTIAL GATE: {exc}")
        return 1

    print("=" * 70)
    print("STEP 1: GET /v4/sports (quota-free)")
    print("=" * 70)
    sports_url = f"{config.base_url}/v4/sports/?{urllib.parse.urlencode({'apiKey': api_key})}"
    status, headers, body = _get(sports_url)
    print(f"HTTP status: {status}")
    quota_headers = {k: v for k, v in headers.items() if k.lower().startswith("x-requests")}
    print(f"Quota headers: {quota_headers}")
    if status != 200:
        print(f"FAILED -- body: {body[:500]!r}")
        return 1

    all_sports = json.loads(body)
    print(f"Total sports/competitions returned: {len(all_sports)}")
    by_key = {s["key"]: s for s in all_sports if isinstance(s, dict) and "key" in s}
    for wanted, display_name in config.sport_keys.items():
        found = by_key.get(wanted)
        if found is None:
            print(f"  MISMATCH: configured sport_key {wanted!r} ({display_name}) -- NOT FOUND in live /v4/sports")
        else:
            print(
                f"  CONFIRMED: {wanted!r} -> title={found.get('title')!r}, "
                f"active={found.get('active')}, group={found.get('group')!r}"
            )

    soccer_matches = [s for s in all_sports if isinstance(s, dict) and "soccer" in str(s.get("key", ""))]
    print(f"\nAll 'soccer' sport_keys live (for reference, {len(soccer_matches)} found):")
    for s in sorted(soccer_matches, key=lambda x: x.get("key", "")):
        print(f"  {s.get('key')!r}: {s.get('title')!r} (group={s.get('group')!r})")

    AUDIT_OUT_DIR.mkdir(parents=True, exist_ok=True)
    sports_audit_path = AUDIT_OUT_DIR / "the_odds_api_v4_sports_smoke_test_2026-09-19.json"
    sports_audit_path.write_text(json.dumps(all_sports, indent=2))
    print(f"\nFull /v4/sports response saved to {sports_audit_path}")

    print()
    print("=" * 70)
    print("STEP 2: GET /v4/sports/soccer_epl/odds (ONE real, minimal odds call)")
    print("=" * 70)
    odds_url = (
        f"{config.base_url}/v4/sports/soccer_epl/odds/?"
        + urllib.parse.urlencode(
            {
                "apiKey": api_key,
                "regions": config.regions,
                "markets": ",".join(config.markets),
                "oddsFormat": config.odds_format,
            }
        )
    )
    status, headers, body = _get(odds_url)
    print(f"HTTP status: {status}")
    quota_headers = {k: v for k, v in headers.items() if k.lower().startswith("x-requests")}
    print(f"Quota headers (after this call): {quota_headers}")
    if status != 200:
        print(f"FAILED -- body: {body[:1000]!r}")
        return 1

    raw_events = json.loads(body)
    odds_audit_path = AUDIT_OUT_DIR / "the_odds_api_soccer_epl_odds_smoke_test_2026-09-19.json"
    odds_audit_path.write_text(json.dumps(raw_events, indent=2))
    print(f"Full raw odds response saved to {odds_audit_path}")

    print(f"\nEvents (fixtures) returned: {len(raw_events)}")

    print()
    print("=" * 70)
    print("STEP 3: run the REAL response through this project's own adapter")
    print("=" * 70)
    try:
        events = parse_odds_response(raw_events, sport_key="soccer_epl")
    except TheOddsApiResponseError as exc:
        print(f"ADAPTER REJECTED THE REAL RESPONSE -- this is a genuine bug to fix: {exc}")
        return 1
    print(f"parse_odds_response: OK -- {len(events)} event(s) parsed without error")

    now = datetime.now(timezone.utc)
    all_bookmaker_titles: Counter[str] = Counter()
    market_key_counts: Counter[str] = Counter()
    team_name_set: set[str] = set()
    stale_quotes: list[str] = []
    for event in events:
        team_name_set.add(event.home_team)
        team_name_set.add(event.away_team)
        for bookmaker in event.bookmakers:
            all_bookmaker_titles[bookmaker.title] += 1
            for market in bookmaker.markets:
                market_key_counts[market.key] += 1
            try:
                last_update = datetime.fromisoformat(bookmaker.last_update.replace("Z", "+00:00"))
                age_minutes = (now - last_update).total_seconds() / 60.0
                if age_minutes > 60:
                    stale_quotes.append(f"{bookmaker.title} on {event.id}: {age_minutes:.1f} min old")
            except ValueError:
                pass

    print(f"\nFixtures: {len(events)}")
    print(f"Distinct team names seen: {sorted(team_name_set)}")
    print(f"Market keys returned (count of bookmaker-market pairs): {dict(market_key_counts)}")
    print(f"Bookmakers seen (count of event-bookmaker pairs): {dict(all_bookmaker_titles.most_common())}")
    print(f"Quotes older than 60 minutes: {len(stale_quotes)}")
    for s in stale_quotes[:10]:
        print(f"  STALE: {s}")

    odds, metadata, warnings = build_canonical_odds_and_metadata(events, config)
    print(f"\nCanonical markets produced: {len(odds)}")
    for market_id, meta in metadata.items():
        n_books = len(odds.get(market_id, {}))
        print(f"  {market_id}: {meta['event']} ({meta['market_type']}) -- {n_books} bookmaker(s)")

    print(f"\nAdapter warnings ({len(warnings)}):")
    for w in warnings:
        print(f"  - {w}")

    print()
    print("=" * 70)
    print("SUMMARY")
    print("=" * 70)
    print(f"API call succeeded: yes")
    print(f"Fixtures returned: {len(events)}")
    print(f"Distinct bookmakers: {len(all_bookmaker_titles)}")
    print(f"1X2 markets produced: {sum(1 for m in metadata.values() if m['market_type'] == '1x2')}")
    print(f"O/U 2.5 markets produced: {sum(1 for m in metadata.values() if m['market_type'] == 'over_under_2_5')}")
    print(f"Adapter warnings: {len(warnings)}")
    print(f"Adapter errors: none (parse_odds_response did not raise)")
    print("Raw responses saved for inspection at:")
    print(f"  {sports_audit_path}")
    print(f"  {odds_audit_path}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
