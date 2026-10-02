# Betfair schema discovery — run 1 (2026-10-02 15:22 UTC, Fraser's Mac, delayed key, 28 read-only calls)

This is SCHEMA DISCOVERY only. The sample was the 25 busiest football events within 36 hours, mostly UEFA Nations
League fixtures plus English League Two. **It is NOT coverage evidence for the project's 10 leagues.** That is the
10 October matchday audit.

## Market types found (real Betfair codes)
| Family | Code | Structure | Two-sided (back + lay) | Matched (delayed key) |
|---|---|---|---|---|
| Corners | `OVER_UNDER_85_CORNR`, `OVER_UNDER_105_CORNR` | 2 runners: Under / Over X.5 Corners | Yes on all 5 sampled books | £0–£439 |
| Corners | `CORNER_ODDS` ("Corners Number") | 3 bands: 9 or less / 10–12 / 13 or more | Yes | £0–£182 |
| Cards | `OVER_UNDER_25_CARDS`, `OVER_UNDER_35_CARDS` | Under / Over X.5 Cards | Partial | up to £1,075 |
| Cards | `BOOKING_ODDS` ("Cards Bookings Points") | 3 bands of points | Partial | small |
| Cards | `SENDING_OFF` | Yes / No | Partial | 0 |
| Player SOT | `SHOTS_ON_TARGET_P1` ("Player Shots on Target 1 or More") | One runner per player (43–50); each runner is a yes/no proposition (back = yes, lay = no) | Only France v Italy (about 3 h before kickoff) had real two-sided runners: 32 of 48, £263 matched; elsewhere back-only | thin |
| Player SOT | `SHOTS_ON_TARGET_P2` ("2 or More") | Same structure | France v Italy only (31 of 48) | £9 |
| Player card | `SHOWN_A_CARD` | One runner per player | Back-only | 0 |
| Goalscorer | `TO_SCORE`, `FIRST_GOAL_SCORER`, `TO_SCORE_2_OR_MORE`, `TO_SCORE_HATTRICK` | One runner per player | Two-sided mainly close to kickoff | up to £275 |

## What this changes
**Corners:**
- Betfair exchange corners markets exist as two-sided O/U lines (8.5 and 10.5 seen) and as 3-band markets.
- They are present from about a day before kickoff, including in English League Two.
- Spreads are wide (median lay/back about 15–23%) and volume is thin. Under the pre-registered 10% spread rule many
  quotes would fail, which the A/B/C exclusion counts will show.

**Player SOT:**
- The market exists with the exact targets the pilot modelled (1+ and 2+).
- Each player is a separate yes/no runner. The fair P per player is the back/lay mid (no de-vig across runners), but
  only where both sides exist.
- Two-sided depth appeared only on the biggest event, near kickoff. Liquidity is the likely binding constraint.

**Timing:** prop markets were listed 0.6–27 hours before kickoff. Two-sided prices clustered on the highest-profile
fixture closest to kickoff.

**Classifier fix:** the original summary column ("two-sided" = every runner two-sided) is misleading for player
markets. A per-runner two-sided share and median matched volume were added.

**10 October:** answers whether these markets exist, with usable depth, for the project's 10 leagues on a normal
matchday.
