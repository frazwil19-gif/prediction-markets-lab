# Daily Prediction Board + Daily Bet Card (design)

## Daily Prediction Board (new; built before any odds-based decision)
`daily_cards/<date>/prediction_board.{json,md}`. It covers every candidate from every registered engine, sorted by p.
It exists to show whether the **prediction platform** works, independently of betting.

Header: date · scan time · engines active (id@version) · events scanned · candidate outcomes · count ≥60/70/80/90%.
Rows: sport · competition · event · kickoff · market · selection · **p** · p_interval · fair odds · support ·
engine · data quality · context status. There are no odds or stakes in the board itself.
Settlement fills in `occurred`, so board-level calibration is tracked daily, **separately from betting P&L**.

## Daily Bet Card (evolves the current Money Card; format change only after approval)
```
DAILY BET CARD — <date>
Bankroll £x · Events scanned n · Markets analysed n · Candidate outcomes n
High-probability predictions (≥70%) n · Money-qualified singles n · Multi-eligible n · Recommended exposure £x

SINGLES
Grade | Sport | Event | Selection | Odds (book) | Est. P [interval] | Fair odds | Support | Stake | Potential profit

OPTIONAL MULTI (PAPER ONLY until promoted)
Legs (P, odds, book) | Dependency: PASS/flags | Joint P [interval] | Fair combined odds | Available combined odds (one book)
| EV | Stake | Potential profit | Risk note

NO BETS QUALIFIED TODAY  ← a valid, successful output
```
Singles are always listed above the multi. A multi is never shown if a better-supported single exists for the same exposure.

---
## Refinement after V2-1 (2026-09-23): Prediction Board ranking rule (design only)

Transparent hierarchical rules, no weighted score:
1. **Exclude** candidates whose engine is not validated, or whose data quality fails (stale or one-sided price,
   unmatched players). They go on a "not ranked" list with the reason.
2. **Status:** PREDICTION_VALID requires a validated engine (sealed holdout passed), a candidate band with ≥200 unseen
   historical predictions in that engine's reliability table, and complete data. Otherwise PAPER_ONLY.
3. **Rank by estimated probability**, descending.
4. **Ties or near-ties (within 1 pp):** break by (a) narrower uncertainty interval, then (b) larger historical band
   sample, then (c) earlier kickoff.
5. **Always show beside P:** the engine's realised hit rate in that band on unseen data with its CI. Example from
   tennis: "80–84.9% band: 82.2% won [78.3, 85.6], n = 411".

Board fields: sport · event · kickoff · market · selection · **P** · band · uncertainty (band Wilson CI; bookmaker
bootstrap for market engines) · historical support (band n, holdout status) · engine@version (for example
`tennis_atp_winner.betfair_market@1`) · data quality · context completeness (NONE today, stated). **No odds, EV or
stake on the board.** A 90% favourite priced at 1.10 appears near the top even though the single-bet layer will reject it.

What the board would look like with today's validated engines: tennis provides most rows ≥70%, since about 40% of
priced ATP matches are ≥70% and about 20% are ≥80%. Football 1X2 provides a few heavy favourites (≈3% of matches
≥80%). Football O/U and BTTS rarely exceed 70%.
