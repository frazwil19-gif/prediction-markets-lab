# Tennis serve/return model: licensing and feasibility (2026-10-08)

## Current source: NOT usable for a live betting system
- **Jeff Sackmann `tennis_atp` / `tennis_wta`:** removed from GitHub as of the 2026-09-11 check (recorded in
  `config/cycle_002_tennis_data.yaml`).
- **The continuation, `Tennismylife/TML-Database`:** ATP only, same schema including serve stats (w_ace,
  w_svpt, w_1stWon, …).
  - Licence: **CC BY-NC-SA**, recorded in that config as "non-commercial research/paper-trading use only; any
    production use requires separate licensing review".
- **Verdict.** CC "NonCommercial" excludes use "primarily intended for or directed towards commercial advantage
  or monetary compensation". A system built to make betting profit is at best ambiguous under that wording.
  - Following the directive (do not rely on NC data unless clearly permitted), it is **not cleared for live use**.
  - Paper research use is the most it supports.
  - Asking the maintainer for written permission is a free option (Fraser's call).
- I tried to re-verify the licence on GitHub today, but the fetch could not be approved in this session; the
  repo-recorded licence stands.

## Alternatives
| Option | Serve/return stats | Depth | Licence / cost | Assessment |
|---|---|---|---|---|
| Written permission from the TML / Sackmann maintainers | yes (ATP) | decades | free if granted | cheapest route to serve stats; WTA still missing |
| tennis-data.co.uk | **no** (results incl. set scores, odds) | 2000s→ | free; terms not reviewed | enough for a **market-derived** games model (below) |
| Betfair historical BASIC | no (prices only) | 2015→ | free tier | already used |
| Matchstat API (RapidAPI) | yes (aces, serve/return, break points) | odds since 2010 | paid; pricing not visible publicly | candidate if a model validates first |
| API-Tennis, Sportradar, Enetpulse | yes | deep | paid; Sportradar is enterprise-priced (unverified) | not justified now |
| Apify / scraper datasets ("Sackmann format") | yes | — | scraping provenance / ToS risk | **REJECT** |

## A cheaper first model that needs no serve stats
**Market-derived games model:**
1. Back out per-player serve-hold probabilities from the Betfair match-winner mid.
2. Combine them with tour/surface hold priors (estimable from tennis-data set scores).
3. Get the distribution of total games and game handicap from a Markov model.
4. Validate the calibration of over/under games and handicaps on tennis-data set scores, chronologically, with a
   holdout.

**What it is, and what it isn't:**
- It is a cross-market model, not fully independent.
- It finds games-market prices that disagree with the match-winner market.
- Its value depends on UK books quoting games markets, which probe C3 measures from 12 Oct.

## Recommendation
1. No acquisition now.
2. Run probe C3 (tennis games markets, 12–26 Oct).
3. If ≥ 3 UK books quote games markets on ≥ 50% of events, pre-register the market-derived games model (free
   data).
4. Consider paid serve stats only if that model validates and shows real CLV.
