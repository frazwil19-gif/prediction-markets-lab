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
