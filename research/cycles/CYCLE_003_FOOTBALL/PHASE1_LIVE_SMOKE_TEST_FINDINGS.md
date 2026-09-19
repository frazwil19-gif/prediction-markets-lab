# Phase 1 Live Smoke Test Findings — The Odds API, First Real Request

**Date:** 2026-09-19
**Context:** operator's "MAJOR NEXT PHASE — LIVE COMMISSIONING + BACKTEST/PAPER-TRADING VALIDATION" instruction, Phase 1 ("Perform the minimum sensible REAL request first. Do not waste API credits.").
**Script:** `scripts/phase1_smoke_test_odds_api.py`. Raw responses saved to `reports/audits/the_odds_api_v4_sports_smoke_test_2026-09-19.json` and `reports/audits/the_odds_api_soccer_epl_odds_smoke_test_2026-09-19.json`.

## 1. API success

Yes. `THE_ODDS_API_KEY` (set locally via a gitignored `.env` file, never pasted into chat or committed) authenticated successfully against both `/v4/sports` and `/v4/sports/soccer_epl/odds`.

## 2. Sports/competitions available

82 total sports/competitions returned by `/v4/sports`. All three configured `sport_key` values are **confirmed real and active**, resolving the one caveat flagged in the prior checkpoint:

| sport_key | live title | active |
|---|---|---|
| `soccer_epl` | EPL | true |
| `soccer_efl_champ` | Championship | true |
| `soccer_spl` | Premiership - Scotland | true |

## 3. Fixtures returned

24 fixtures for `soccer_epl` alone in the single-league smoke test call. Scaling to the full 3-league scan (Phase 2, run immediately after): 39 fixtures, 77 markets (1X2 + O/U 2.5 combined across all fixtures), 193 individual candidate propositions.

## 4. Bookmakers returned

20 distinct bookmakers seen for EPL alone: LeoVegas, Betfred (UK), Sky Bet, Paddy Power, Betfair, 888sport, William Hill, Smarkets, Unibet (UK), BoyleSports, Virgin Bet, Grosvenor, LiveScore Bet, Coral, Ladbrokes, Betway, Casumo, Betano (UK), Bet Victor, Matchbook. **Bet365 is not present** in the `regions=uk` panel — confirming the earlier documented uncertainty; this project should not assume Bet365 coverage.

## 5. UK-relevant bookmaker coverage

Strong. Every fixture had at least 5 bookmakers quoting 1X2 (most had 13–20); the market has genuine price dispersion to compare, not a thin single-source feed.

## 6. 1X2 coverage

Full — every fixture across all three leagues produced a valid 1X2 canonical market (24/24 for EPL alone; 39/39 across all three leagues before market-type filtering).

## 7. Over/Under 2.5 coverage

Real, but thinner and uneven — this is a genuine market characteristic, not an adapter defect. Some fixtures had only 1 bookmaker offering exactly the 2.5 line (others quote 2.75/3.0/3.25 instead and were correctly excluded, never interpolated). This directly explains why most O/U 2.5 candidates in the first real scan were rejected for "data quality is insufficient" (below the configured `min_bookmakers: 3` threshold) rather than for a bad price — an honest, expected outcome of the existing data-quality gate working as designed, not a bug.

## 8. Timestamps

All bookmaker quotes were fresh — zero quotes older than 60 minutes in the smoke test's staleness check.

## 9. Decimal prices

Confirmed correctly formatted decimal odds throughout (`oddsFormat=decimal` as configured); no unit or format ambiguity.

## 10. Team-name consistency

Clean. All 20 distinct EPL team names in the sample matched expected current Premier League club names with no normalisation issues, and `_h2h_selection`'s exact-match logic correctly mapped every outcome without a single "unrecognised outcome" warning across all three leagues.

## 11. Duplicates

None found. No bookmaker quoted the same market twice for the same fixture in the real response.

## 12. Missing prices

Handled correctly and transparently: 14 warnings across the smoke test's single league were bookmakers with an incomplete outcome set for a market (e.g., quoting Over/Under at a non-2.5 line) — every one was skipped with a specific warning rather than silently dropped or guessed.

## 13. Stale prices

None found (see §8).

## 14. API quota/credits before and after

Before this session's first call: 500/500 remaining (fresh account). After `/v4/sports` (quota-free): still 500/500, 0 used. After the single-league `soccer_epl` odds smoke test: 498/500 remaining, 2 used. After the full 3-league Phase 2 scan (see below): 492/500 remaining, 8 used total this session.

## 15. Actual request cost

Exactly as predicted in the prior checkpoint's documentation-based audit: 2 credits per league per scan (`markets=2 × regions=1`), 6 credits for the full 3-league scan. **The documented formula is now empirically confirmed, not just cited from documentation.**

## 16. Adapter bugs discovered/fixed

**One genuine real-world structural discovery, not a bug**: exchange-style bookmakers (Betfair, Smarkets, Matchbook) return a second market keyed `h2h_lay` (their lay price) alongside `h2h` (their back price) for the same fixture. `build_canonical_odds_and_metadata` only matches `market.key == "h2h"`, so `h2h_lay` was already correctly ignored without any code change needed — but this had never been exercised against real data before, so a regression test (`test_h2h_lay_market_key_is_ignored_not_treated_as_h2h`) was added to lock this behaviour in, per the instruction's "create regression tests from real structural discoveries." No other adapter defect was found: `parse_odds_response` and `build_canonical_odds_and_metadata` both ran cleanly against the real, messy response with zero exceptions.

## 17. First REAL Daily Bet Card

Produced immediately after this smoke test — see the message this findings doc accompanies for the full card pasted directly into chat, per the instruction. Card also written to `daily_cards/2026-09-19/card.json` / `card.csv` / `card.md`.

## Test suite status

**795/795 passing** (one new regression test added this session).
