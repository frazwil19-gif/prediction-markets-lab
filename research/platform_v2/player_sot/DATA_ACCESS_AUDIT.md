# Player SOT — data-access verdict and corrected EPL pilot estimate (2026-10-02)

Directive §3A–3B. No account was created, no API call was made, and nothing was downloaded.

## 3A. API-Football terms (ToS last updated 2025-05-21; https://www.api-football.com/terms)

| Question | What the terms say | Verdict |
|---|---|---|
| Betting-related research permitted? | "The use of our data for betting platforms, television broadcasting, fantasy sports platforms, or any mass media distribution may require additional licenses from the relevant rights holders." | **AMBIGUOUS.** Private research for one person's own manual bets is arguably not a "betting platform", but the terms leave responsibility for licences with the user ("It is the responsibility of the user to verify and obtain any necessary authorizations or licenses"). |
| Commercial use needs another licence? | "We do not provide a 'license' for the use and publication of the data … on applications, websites or any other products made by the user." Resale is prohibited. | **AMBIGUOUS** for private profit-seeking use. Clearly prohibited: resale and redistribution. |
| May historical responses be stored? | No clause found. | Not restricted by the terms. Must stay private (next row). |
| Derived probabilities/models permitted? | No clause found. | Not restricted. Publishing derived player data is risky (no publication licence). |
| Automated collection permitted? | Yes, within plan rate limits; breaching per-minute limits is a "material breach"; one account only ("forbidden to have multiple accounts to increase the limit of the free plan"). | Permitted with throttling and a single account. |

**Hard constraint discovered:**
- The project repository is PUBLIC.
- Raw API-Football responses and player-level derived tables must therefore NOT be committed, because that would
  publish the data without a licence.
- Any pilot data must stay on Fraser's machine in a gitignored folder. Only aggregate statistics (base rates,
  metrics) may be committed.

**STOP (as the directive instructs when unclear).** Acquisition waits until Fraser decides to proceed on two points:
1. the private-use interpretation of the betting clause;
2. the private-storage rule.

It also needs a free API-Football account, which only Fraser can create.

## 3B. Endpoint granularity and the corrected estimate
- `GET /fixtures?league=39&season=S&status=FT-AET-PEN` returns every finished fixture of a season in **1 request**.
- `GET /fixtures?ids=id1-…-id20` returns up to **20 fixtures per request**, each "including events, lineups,
  statistics and players statistics" (API-Football tutorial, 2024-12-12).
  - Per-player statistics include minutes, position, substitute flag, shots total and on target, goals and more.
- So a season of 380 EPL fixtures needs **1 + 19 = 20 requests**.

| Item | Estimate |
|---|---|
| Requests per fixture | 0.05 (20 fixtures per request) |
| Requests per season (EPL) | 20 |
| Pilot seasons | 2022-23 and 2023-24 = 40 requests; adding 2024-25 (if the free plan allows season=2024) = 60 |
| Free quota | 100 requests/day. Per-minute limit unpublished, so throttle to about 6/min |
| **Calendar time** | **1 day, under 30 minutes of throttled requests** (the previous 7–10-month estimate assumed per-fixture endpoints across 10 leagues and was wrong) |
| Player rows per request | about 20 × ~30 player entries, roughly 600 |
| Player-match observations | about 11–12k per season (all squad entries); **confirmed starters 380 × 22 = 8,360 per season**, so 16,720 (2 seasons) to 25,080 (3 seasons) |
| Storage (raw JSON) | roughly 1–3 MB per request, so about 50–150 MB for 60 requests, about 10–25 MB gzipped. This is an estimate, to be measured on the first call |
| Free-plan seasons | 2022–2024 according to a third-party report of the API's own error message (2026-09-18); unverified officially. The first `/fixtures` call confirms it |

## Pilot decision
- **Practical:** yes. It is one day of the free quota.
- **Legitimate:** this is the open question; see 3A.

Pilot plan, if Fraser approves:
1. Fraser creates the account.
2. The key is set in Fraser's own terminal environment as `API_FOOTBALL_KEY` and never committed.
3. A throttled collector runs on Fraser's Mac. Raw data goes to `data/raw/api_football/` (gitignored); a compact
   private parquet goes in the same folder.
4. Data audit as directive §3C: base rates P(1+ SOT) and P(2+ SOT) for confirmed starters. Only aggregates are
   committed.
5. Only then is Model A pre-registered.
