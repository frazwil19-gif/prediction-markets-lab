# NHL free-data inventory and settlement definitions (web-verified 2026-10-01)

Items marked **UNVERIFIED** could not be confirmed. No data was downloaded into the repository and nothing was purchased.

The sandbox egress proxy refused direct access to `api-web.nhle.com` (CONNECT 403), so the NHL API was read through a web-fetch tool. A pipeline needs a runner that can reach `nhle.com`.

## Sources

| Source | Data | Years | Access / licence | Known issues | Leakage risk | Cost |
|---|---|---|---|---|---|---|
| NHL web API `https://api-web.nhle.com/v1` (endpoint reference: https://github.com/Zmalski/NHL-API-Reference) | `/schedule/{date}`, `/score/{date}`, boxscore, play-by-play. Verified fields: `gameType` (2 = regular season), `gameState`, `gameOutcome.lastPeriodType` REG/OT/SO, `periodDescriptor`, `otPeriods` (e.g. https://api-web.nhle.com/v1/score/2025-04-12). Boxscore goalies carry a `starter` boolean (https://api-web.nhle.com/v1/gamecenter/2024021269/boxscore) | Many seasons (earliest UNVERIFIED) | Unofficial, no key, no published terms or rate limit (clients handle 429) | Schema can change. **No pre-game starting-goalie field**: a FUT landing page has only season goalie stats | `starter` is post-game; season aggregates must be rebuilt as-of | Free |
| NHL stats REST `https://api.nhle.com/stats/rest` (e.g. `/en/team/summary?cayenneExp=seasonId=20242025 and gameTypeId=2`) | Team W, L, OTL, SO wins, regulation+OT wins | Many | As above | `homeRoad` filter syntax UNVERIFIED | Season totals leak in-season | Free |
| MoneyPuck https://moneypuck.com/data.htm | Skater/goalie/line/team season and game-by-game files; shot-level xG (124 attributes) | Shots 2007/08–2026/27; game 2008/09+ | "Free to use for non-commercial purposes", credit required; non-approved scraping blocked | xG model may be revised (UNVERIFIED) | Lag xG; possible retroactive refits | Free (non-commercial) |
| Natural Stat Trick https://www.naturalstattrick.com/ | Corsi, scoring chances, xG | UNVERIFIED | Scraping policy page exists but its content is unread; assume **no automated scraping** | — | — | Not used |
| Hockey-Reference https://www.hockey-reference.com/leagues/NHL_2025_games.html | Game lists (OT/SO as text) | Decades | Terms (https://www.sports-reference.com/data_use.html) prohibit scrapers and AI training use; bot jail >20 req/min | — | Low | Not used (manual only) |
| Evolving-Hockey https://evolving-hockey.com/evolving-hockey-subscription-faq/ | RAPM/GAR | — | Paid ($5/month) | — | — | **Not used** |
| Kaggle martinellis/nhl-game-data | Games, plays | About 2013/14–2019/20 (stale, Dec 2020) | Licence "Other" | Superseded | Low | Free |
| Kaggle jonathanncoletti/nhl-historical-game-data | ESPN game stats plus `favourite_moneyline`, spread, O/U | 2004–Dec 2025 | **CC0** | Odds timing, bookmaker and OT inclusion UNVERIFIED | Odds timestamp unknown | Free |
| SBRO archive https://www.sportsbookreviewsonline.com/scoresoddsarchives/nhl/nhloddsarchives.htm | Open/Close moneyline (American), puck line, totals, period scores | **2007/08–2022/23** ("will not be updated") | Free download; terms UNVERIFIED | Date is MMDD with no year; bookmaker unknown; US lines | Benchmark only | Free |
| The Odds API historical (https://the-odds-api.com/historical-odds-data/) | h2h/spreads/totals snapshots from June 2020 | 2020+ | Paid-plan only; cost 10 × markets × regions | — | Low if a pre-game snapshot is used | Credits |
| DailyFaceoff https://www.dailyfaceoff.com/starting-goalies/2026-10-01 | Starters marked Confirmed/Likely/Unconfirmed, with timestamps | Archive exists | © The Nation Network; terms UNVERIFIED (assume no scraping) | Archive shows the **final** state, not as-of | **High** unless snapshotted live | Free |

No free, structured, timestamped injury feed was found.

## UK moneyline settlement

**Includes overtime and shootout:**
- William Hill: "money line, match result and match betting … including overtime and shootouts"; "60 minutes betting … overtime and shootouts don't count". https://help.williamhill.com/hc/en-gb/articles/29630369847069-Ice-Hockey
- Sky Bet: US Money Line "Includes overtime and any subsequent shootout". https://support.skybet.com/app/answers/detail/ice-hockey-rules/
- Betfair Sportsbook: same wording as Sky Bet. https://support.betfair.com/app/answers/detail/ice-hockey-rules/
- Betfair Exchange: "Moneyline" markets include OT and SO. https://support.betfair.com/app/answers/detail/exchange-ice-hockey-rules/
- bet365: "All bets include overtime/shootouts unless otherwise stated". https://help.bet365.com/s/en/sportsrules/ice-hockey

**Exclude overtime and shootout:**
- Sky Bet and Betfair Sportsbook Match Odds (3-Way).
- Betfair Exchange "Regular Time" markets.
- bet365 Money Line (3-Way).
- Whether a Betfair Exchange market titled "Match Odds" includes OT is UNVERIFIED; check each market's rules tab.

**The Odds API `icehockey_nhl` (https://the-odds-api.com/sports/nhl-odds.html):** "EU bookmakers typically feature regular time odds (includes draw), whilst US bookmakers typically feature the overtime odds (excludes draw)". The UK region must therefore be checked per bookmaker for a Draw outcome.

## Season facts

| Item | Value | Source / confidence |
|---|---|---|
| 2026/27 opening night | 29 Sep 2026 | https://www.nhl.com/news/nhl-home-openers-for-2026-27-season |
| Games per team | 84 | Wikipedia only (https://en.wikipedia.org/wiki/2026%E2%80%9327_NHL_season) |
| Total games | 1,344 | Derived: 84 × 32 / 2 |
| Regular season end | 10 Apr 2027 | Wikipedia |
| Games decided in OT/SO, 2024/25 | 20.7% (1,312 games) | Computed from NHL stats REST team summaries |
| Games decided in OT/SO, 2025/26 | 24.8% (1,312 games) | Computed from NHL stats REST team summaries |
| Historical home win rate incl. OT | 54.5% (1979/80–2011/12) | https://www.sfu.ca/~tswartz/papers/hca.pdf |
| Recent-season home win rate | UNVERIFIED | — |
