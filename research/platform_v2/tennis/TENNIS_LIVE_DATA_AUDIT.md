# Tennis Live-Data Feasibility Audit (research only; nothing integrated, no credentials requested) — 2026-09-23

| source | coverage | markets | delay | cost / terms | identifiers | verdict |
|---|---|---|---|---|---|---|
| **The Odds API** (already integrated for football) | **tournament-level keys only.** ATP: the 4 Slams, the Masters 1000s and selected 500s (e.g. Barcelona, Halle, Queen's, Hamburg, Washington, Dubai, Beijing, Munich); WTA similar. **No ATP 250s, Challengers or ITF.** A key only exists while its tournament runs (on 2026-09-23 exactly one tennis key was active: `tennis_wta_singapore_open`) | h2h (match winner); totals/spreads vary | ~1 min updates | existing free tier (500 credits/month); ~2 credits per tournament per scan | provider event id + player names (the tested name matcher applies) | **usable now for a partial universe.** It includes `betfair_ex_uk` in the UK region, so the same *exchange* price type the engine was validated on is available for covered events (bookmaker-consensus tennis probabilities would need their own validation) |
| **Betfair Exchange API, Delayed app key** | all tennis Betfair lists (ATP, WTA, Challenger, ITF) | MATCH_ODDS and more | variable 1–180 s snapshots (irrelevant for a T−30 min prediction) | free with a Betfair account; `placeOrders` blocked. **Betfair describes it as for "development purposes and any functional testing"**, so its suitability for a standing daily data feed is a terms question to confirm with Betfair before use. Live key: one-off fee (sources cite £299 and £499; unverified which applies now), requires betting activity, and read-only use of a live key is not permitted | Betfair market/selection ids, the **same ids as the historical archive**, so the validated engine maps 1:1 | **best coverage and the exact validated data type**, but has a terms question. Also untested: non-interactive login from GitHub Actions (certificate login; US-hosted runners may hit Betfair's jurisdiction restrictions) |
| odds-api.io, OddsPapi, Apify scrapers | claim ATP/WTA incl. lower tiers | varies | varies | free tiers with limits / pay-per-use; scraping terms vary | provider-specific | not evaluated in depth; no purchase |
| Betfair historical BASIC (monthly purchase-free download) | all tennis | LTP | historical only | free for the BASIC tier | same ids | not live; for research refreshes only |

## Coverage impact (measured on the sealed 2024–25 set, n = 5,066)
Grand Slam + Masters matches were 45% of priced matches but held **61% of the ≥80% predictions** (614 of 1,001). Grand
Slams alone had 39.6% of their matches at ≥80% (best-of-5). So the Odds API's partial coverage keeps a
disproportionately large share of the strong predictions. It misses the 250s, which are also the weakest-calibrated
high-probability subgroup (81.5% won vs 84.5% predicted at ≥80%, n = 135, CI 74–87).

## Recommended live source
**Stage 1 (no new account, no cost):** The Odds API tennis keys for covered tournaments, using the `betfair_ex_uk`
quote where present (bookmaker consensus as a separately tracked second estimator). **Stage 2:** Betfair Delayed key
for full coverage, only after Fraser confirms Betfair's terms allow a standing personal data feed, and after a
login-from-CI feasibility test.

## ATP / WTA
- ATP: validated (this phase).
- **WTA: data exists at zero cost.** TML-Database publishes WTA yearly CSVs 1990–2026 in the same format (MIT
  licence; its maintainer notes WTA reliability is still being debugged). Fraser's Betfair `data.tar` **already
  contains WTA markets** (a sample of 545 MATCH_ODDS files included Sabalenka, Kasatkina, Paolini and others; doubles
  and ITF are present too). ATP and WTA are separate populations and would be validated separately. Nothing
  downloaded or built.

Sources: The Odds API sports list; Betfair Developer Program support articles on delayed vs live keys and read-only
access; BotBlog "Betfair API Key: Delayed vs Live" (modified Aug 2026); TennisMyLife tennis match database page.
