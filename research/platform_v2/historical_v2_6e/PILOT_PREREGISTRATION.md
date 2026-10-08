# V2-6E — Controlled Historical Tennis Pilot: Pre-registration and Purchase Checklist (2026-09-29)

**Status: PREPARED, NOT EXECUTED.** No subscription, no purchase and no paid call has happened. Execution needs (1) Fraser to buy
the plan himself, (2) his separate explicit authorisation, and (3) the `PILOT_AUTHORISED` token in his own shell.
Code: `scripts/v2_6e_historical_pilot.py` (guards tested in `tests/unit/test_v2_6e_pilot.py`).

## 1. Verified provider terms (official pages, read 2026-09-29)
| item | verified fact | source |
|---|---|---|
| Plan | **20K: $30/month, 20,000 credits**; historical odds included on all paid plans; not on the free Starter | the-odds-api.com (plans) |
| Billing | "Payment then happens automatically each month thereafter, on the same day of the month that the subscription started": **auto-renews** | /manage/faqs.html |
| Cancel | cancel any time; the subscription "remains active until the end of the billing cycle"; "The free subscription always remains active" afterwards | /manage/upgrade-downgrade-cancel-a-subscription.html |
| API key | on upgrade "The API key stays the same"; "Credits become available immediately" | same page |
| Credit reset | "Usage credits are automatically reset on the first of every month" | /manage/faqs.html |
| Quota exhausted | error `OUT_OF_USAGE_CREDITS`; no overage charge is described (blocking, not billing) | /liveapi/guides/v4/api-error-codes.html |
| Historical cost | sport odds snapshot = **10 × markets × regions**; "Responses with empty data do not count" | /liveapi/guides/v4/ |
| Snapshots | 10-min from 2020-06-06, 5-min from Sep 2022; the returned snapshot is the closest ≤ the requested `date` | /liveapi/guides/v4/ |
| Refunds | "case-by-case … at our discretion" | /terms-and-conditions.html |
| Not verified | VAT or currency conversion on a GBP card; whether the 1st-of-month reset shortens the first period; historical availability of each 2024 tennis key and of `betfair_ex_uk` lay quotes (only a paid call can verify these) | — |

**Implication:** live and historical requests draw on **one shared quota and one key** (the production key). The pilot's 510
credits come from the 20K pool, so production is unaffected. After cancellation the account falls back to the free 500/month.

## 2. Purchase checklist (Fraser, manual; Claude never handles payment)
1. Log in to the existing The Odds API account (the one whose key is the `THE_ODDS_API_KEY` GitHub secret).
2. Subscribe to **20K ($30)**. Confirm the invoice amount (plus any VAT or FX) before paying.
3. **Cancel immediately** via the accounts portal. Access stays until the end of the cycle, and this stops the renewal. Keep
   the confirmation email.
4. Tell Claude "subscription active, cancellation confirmed, pilot authorised".
5. On your **Mac terminal** (not in chat; never paste the key into a conversation):
   ```
   cd ~/Projects/prediction-markets-lab && git pull --ff-only origin master
   PILOT_AUTHORISED=V2-6E-PILOT-APPROVED-BY-FRASER THE_ODDS_API_KEY=<your key> \
     python scripts/v2_6e_historical_pilot.py execute
   ```
   The raw snapshots are written to `research/platform_v2/historical_v2_6e/pilot_raw/`, and the log to `pilot_execution_log.json`.
6. Claude runs `analyse` offline and reports. The **full 2024–25 replay needs a separate approval.**

## 3. Frozen pilot design
- **Scope:** Wimbledon 2024 (ATP 12 and WTA 12 match days) and US Open 2024 (ATP 14, WTA 13), taken from the hash-verified
  tennis-data 2024 schedule. That is **51 key-days**.
- **Request:** `GET /v4/historical/sports/{key}/odds?regions=uk&markets=h2h&oddsFormat=decimal&date=<D−1 20:00:00Z>`. One call per
  key-day; the snapshot at 20:00 UTC on the evening before mirrors production's actual evening board, ≤ 24 h before day-D matches.
- **Cost:** 51 × 10 = **510 credits maximum**. Empty responses are free. **HARD CAP 700**, enforced before every call from the actual
  `x-requests-used` delta. The run aborts if any call costs more than 10.
- **Validation gate (first call = ATP Wimbledon, snapshot 2024-06-30 20:00Z).** STOP (10 credits spent) unless all of these hold:
  a snapshot timestamp is present; there is ≥ 1 event with `betfair_ex_uk` **h2h and h2h_lay**; ≥ 50% of events have ≥ 2 non-exchange
  UK books; every quote has `last_update`. Nothing is inferred.
- **Idempotent:** a key-day already saved is never re-bought.

## 4. Analysis (offline, frozen)
1. P = the production tennis engine `predict(q, now = snapshot timestamp)`: EXCHANGE_MID from `betfair_ex_uk` back and lay, 6 h
   staleness, research-only consensus never bet. There are no parameter changes and nothing closing-derived.
2. Executable prices: named UK books plus Betfair back in the **same** snapshot; quote age ≤ 240 min from `last_update`; 5%
   commission on Betfair; Matchbook rejected. Best net-EV within the snapshot only.
3. `bsv2-1` gates unchanged. The first validated snapshot per event is canonical.
4. Settlement: the hash-verified tennis-data 2024 winner via the validated structural name matcher (0 ambiguous, 99.95% agreement
   on 20k matches). Retirements and walkovers are excluded. Unmatched or ambiguous rows are counted and never guessed.
5. Report: validated predictions, the net-EV distribution, the PAPER_BET-equivalent count and rate per 100, estimated EV, realised
   ROI with bootstrap 95% CI, and a breakdown by tournament and tour.
6. Label: *historical simulation*. It is kept separate from `paper_betting_v2/` (enforced by a test). Nothing is tuned.

## 5. Stop and expansion rules
- Stop if the validation gate fails, if the cap is hit or an unexpected cost appears, or if < 50% of events can be settled.
- **Expansion to the full 2024–25 replay (~16,240 credits) is NOT authorised.** A separate decision is made after the pilot report.
- A pilot of ~51 key-days (~300–400 matches) can show **how often** value appears at decision time and whether the data is
  suitable. It **cannot** establish profitability (too few bets).
