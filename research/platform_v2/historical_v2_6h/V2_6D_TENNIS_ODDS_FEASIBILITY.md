# V2-6D — Historical Tennis Odds: Provider Audit and Replay Feasibility (2026-09-29)

Nothing was purchased and no paid credits were spent. Each fact below is marked **[V]** (verified from an official or first-party
source, or from our own data) or **[A]** (an assumption or estimate, to be confirmed).

## 1. Provider comparison
| | The Odds API (historical) | tennis-data.co.uk | Betfair Historical Data |
|---|---|---|---|
| Access | paid plans only [V]: "only available on paid usage plans" | free xlsx, ATP + WTA, 2020–2026 files listed [V] | BASIC free; ADVANCED/PRO paid [V] |
| Tennis coverage | 22 ATP + 24 WTA named tournament keys (Slams, Masters 1000s, selected 500s) [V, current list]; whether each key existed in past seasons is **not** verified [A] | all tour-level matches [V, site description] | all Betfair tennis markets |
| Market | h2h (match winner) [V] | match winner [V] | MATCH_ODDS |
| UK books | region `uk`: 20 books incl. exchanges Betfair (`betfair_ex_uk`), Matchbook, Smarkets [V] | notes list Bet365, Pinnacle, others, plus Oddsportal Max/Avg [V]; which columns remain in 2021–2025 files is unverified until download [A] | none (exchange only) |
| Timing | **as-of snapshots**: 10-min intervals from 6 Jun 2020, 5-min from Sep 2022 [V]; the snapshot returned is the latest ≤ the requested `date` [V] | **closing only**: odds "generally represent the most recent before play starts" [V, notes.txt] | BASIC: last traded price, 1-min [V]; ADVANCED: top-3 ladder, 1-s [V]; PRO: full ladder, tick [V] |
| Billing unit | historical sport odds = **10 × markets × regions per call; one call returns every event in that sport key** [V]; empty responses free [V]; historical events list = 1 [V] | £0 | BASIC £0; paid tiers' prices not published [V] |
| Price | 20K credits $30/mo · 100K $59/mo [V, official homepage] | £0 | — |
| Executable? | named-book quotes at a timestamp (availability at stake size not guaranteed) | a single named closing quote; Max/Avg are aggregates, **not executable** | LTP ≠ back price (BASIC); ADVANCED gives real back/lay |
| Match to our data | player names + commence time → the project's tested name matcher [A: matching rate unknown] | winner/loser names + date [A] | market ids (already linked for our datasets) [V] |
| Licence | commercial API ToS (personal research use assumed OK) [A] | free, research use; attribution [A] | personal-use terms [A] |

Sources: Odds API v4 docs (historical endpoints, billing, snapshots): https://the-odds-api.com/liveapi/guides/v4/ ·
historical data page: https://the-odds-api.com/historical-odds-data/ · plans: https://the-odds-api.com/ ·
sports list: https://the-odds-api.com/sports-odds-data/sports-apis.html · UK books: https://the-odds-api.com/sports-odds-data/bookmaker-apis.html ·
tennis-data notes: https://www.tennis-data.co.uk/notes.txt (read via Fraser's in-app browser; blocked from the sandbox) ·
Betfair tiers: https://betfair-datascientists.github.io/data/usingHistoricDataSite/

## 2. Overlap with our historical tennis datasets [V, computed]
| | all matches | in Odds-API-covered events | of which 2024–25 | tournament-days 2024–25 |
|---|---|---|---|---|
| ATP (Betfair BASIC, 2021–25) | 12,202 | 6,564 (54%) | 2,824 | 398 |
| WTA (2021–25) | 10,352 | 6,035 (58%) | 2,710 | 414 |
Name matching was done by tournament-name patterns. Olympics and Finals are excluded.

## 3. Time-alignment finding (decisive for the free-data option)
Our historical P is the Betfair LTP **at or before T−30 min** [V, `TENNIS_ENGINE_PROTOCOL.md`]. tennis-data odds are the **last before
play**, so they are *later* than P. Pairing them would test a decision at T−30 using a price that did not yet exist.
- It is therefore labelled **CLOSING-TIME-ONLY** and must not be described as simulating a real decision.
- The bias is **optimistic**: when a bookmaker's closing price has drifted above our T−30 fair price, it is often because
  late information moved the market (adverse selection), so apparent value is overstated.
- Consequence: a *negative* free-data result is informative; a *positive* one is not evidence.

## 4. Leakage-safe replay architecture (Odds API; designed, not executed)
1. **Decision times are fixed before any data is pulled:** for each covered key-day, snapshot `date` = 20:00 UTC on D−1 and
   12:00 UTC on D. These mirror production's actual board times, not the cron times.
2. **P comes from the same snapshot:** the frozen live hierarchy (EXCHANGE_MID from `betfair_ex_uk` back/lay with a staleness ≤ 6 h
   check, then EXCHANGE_BACK; a bookmaker-consensus row is research-only and never bet). This is exactly the production estimator,
   so no closing-derived P is ever paired with an earlier quote.
3. **Executable price:** named UK books in the *same* snapshot. The quote's `last_update` must be ≤ the snapshot timestamp and
   ≤ 240 min old. Betfair back gets 5% commission; Matchbook is rejected (commission unknown). The best net-EV book is chosen *within*
   the snapshot only, never across snapshots.
4. **One decision per event per rule version**, keyed like production (`sha256(bsv2-1|prediction id)`). The earliest qualifying
   snapshot wins; later snapshots are kept only for CLV.
5. **Gates:** `bsv2-1` unchanged (P ≥ 0.50, net EV ≥ 2%, odds ≥ 1.33, ≤ 24 h to start, engine VALIDATED).
6. **Settlement:** our verified TML / TennisCourtLog outcomes via the tested name matcher. Unmatched or ambiguous rows are excluded
   and counted (fail closed).
7. **Chronology:** report 2024 and 2025 separately. The Betfair P holdout (2024–25) was opened once for calibration; this replay
   tests a different question (value), and nothing may be tuned on it. Reported: frequency per key-day, EV distribution, realised
   ROI with bootstrap CI, drawdown, CLV (first vs last pre-start snapshot).
8. **Pre-registration** is committed before the first paid call (this document + a spec file), mirroring `historical_v2_6h/PREREGISTRATION.md`.

## 5. Sample and cost plans
| plan | cost | credits | sample | evidence gained |
|---|---|---|---|---|
| **A. Free (tennis-data)** | £0 | 0 | 2021–25 ATP+WTA; Bet365 (+Pinnacle) closing per match [A: columns to confirm] | closing-time-only; optimistic bias; one UK book. Can *refute* value cheaply, cannot confirm it |
| **B. Paid pilot** | **$30** (the minimum; no pay-per-call historical access) [V] | ~300–500 used [A] | e.g. Wimbledon + US Open 2024, both tours: ~56 key-days × 10 + events checks | verifies key existence, `betfair_ex_uk` back/lay presence, UK book count, match rate, snapshot timing. The go/no-go for C |
| **C. One-month replay** | same $30 month (credits left after B) | 812 key-days × 2 snapshots × 10 ≈ **16,240** [A: arithmetic on verified billing; assumes 1 call per key per snapshot] | ≤ 5,534 covered 2024–25 matches (match rate unknown [A]) | the exact production pipeline on history: opportunity **frequency**, EV distribution, ROI + CI |
B and C are the same subscription. The rule would be: spend ≤ 500 credits on B, stop, report, and continue to C only if the pilot passes.

## 6. Risks
- Past availability of tournament keys and of `betfair_ex_uk` lay quotes is unverified (the pilot answers both).
- A quote in an API snapshot ≠ availability at stake size (bookmaker limits, palpable-error voids).
- Survivorship: covered events are big tournaments only; results may not transfer to 250s. Survivorship in players is not an issue
  (all matches are in the snapshot).
- Name matching across providers; retirements and walkovers (settled by the official winner, as in production).
- The football precedent (0.27% of favourites qualified) suggests the replay may mainly measure *rarity*, which is still the key
  unknown for the live gate.

## 7. Verdict
Historical replay is **feasible and worthwhile only via the paid snapshots (B → C)**, and costs at most $30. Free data can only
deliver a closing-time-only, optimistic check. It is worth running as a £0 first filter if Fraser downloads the files (or allows
me to download them): if even that biased check shows no value, the paid replay is unlikely to change the conclusion.
