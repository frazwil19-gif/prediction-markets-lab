# Tennis Prospective Prediction Protocol: ATP (primary) + WTA (secondary) — frozen 2026-09-23, before the first live prediction

## Purpose
Answer prospectively: **when the engine says 80%, does it happen about 80% of the time on future matches?** Paper
predictions only. No stakes, no bankroll, no Money Card, no bet language.

## Engines (frozen; version 1)
| engine | evidence | status |
|---|---|---|
| `atp_match_winner.betfair_market@1` | V2-1 sealed 2024–25 holdout (n = 5,066, slope 0.986) | PREDICTION engine |
| `wta_match_winner.betfair_market@1` | V2-2 sealed 2024–25 holdout (n = 4,339, slope 0.979, multiplicity-aware rule passed) | PREDICTION engine (ledgered separately from ATP) |
Band evidence is frozen in `config/tennis_engine_registry.json`.

## Universe
`ATP_UNIVERSE` = all ATP tour matches. `ATP_ODDS_API_COVERED_UNIVERSE` = matches in The Odds API tennis sport keys
active at scan time (Grand Slams, ATP 1000, ATP 500 per provider documentation; WTA likewise). Results are only ever
reported for the covered universe and labelled as such. Coverage is logged per scan (active keys, events returned).

## Probability source hierarchy (per event)
1. **EXCHANGE_MID:** `betfair_ex_uk` back (`h2h`) **and** lay (`h2h_lay`) prices for both players. Per-player price =
   midpoint of back and lay, then two-runner proportional normalisation. This is the closest available analogue to the
   historical last-traded price.
2. **EXCHANGE_BACK:** `betfair_ex_uk` back prices for both players only, normalised. Includes the back-lay spread; flagged.
3. **BOOKMAKER_CONSENSUS:** proportional de-vig mean over ≥3 UK bookmakers. **RESEARCH_ONLY.** Not validated for tennis;
   logged in the ledger but excluded from engine performance and shown as not validated.
4. None: DATA_INVALID, no prediction.
Declared difference from the historical estimator: exchange **quote** (back/lay) rather than **last-traded** price, and
a scan-time snapshot rather than exactly T−30 min. Historical evidence that earlier snapshots are also calibrated (ATP
2021–23, exposed data, descriptive): ≥80% predicted/actual 87.2/87.6 at 6 h, 87.2/87.9 at 1 h, 87.2/88.0 at 30 min;
slopes 1.02 / 1.01 / 1.01. Equivalence is **not** claimed; the prospective ledger tests it.

## Prediction rules
- Snapshot: each scheduled scan. An event is predicted **once per engine version**. The first valid snapshot before
  `commence_time` is canonical; later scans never overwrite it. `prediction_id = sha256(engine@version | provider event id)[:16]`.
- Predictions made at or after `commence_time` are rejected (DATA_INVALID).
- Quote staleness: bookmaker `last_update` older than 6 h makes the quote ineligible for levels 1–2.
- The prediction row is append-only and immutable. Settlement is written to a **separate** append-only file keyed by prediction_id.

## Settlement (labels consistent with the historical engines)
Source: TennisCourtLog `atp_matches_2026.csv` and `wta_matches_2026.csv` (media.githubusercontent.com, weekly updates;
CC BY-NC-SA). TML's GitHub repo stopped updating in January 2026, and its site is blocked by the allowlist (checked
2026-09-23, before any prediction). A match is found by case-folded player-name pair (the project's
tested name matcher) with a result date within 21 days of the prediction's start.
- Completed: SETTLED_CORRECT / SETTLED_INCORRECT by the official winner. **Retirements count, with the official
  winner** (as in the historical labels).
- Walkover (W/O) or not played: VOID.
- Not found after 21 days: stays PREDICTED, then UNRESOLVED (never guessed).

## Evidence maturity (fixed now; based on sample counts, never on P&L)
| label | rule (per engine, settled non-void predictions) |
|---|---|
| COLLECTING | < 50 settled |
| EARLY | 50–299 settled |
| INTERMEDIATE | ≥ 300 settled **and** ≥ 100 settled at P ≥ 0.80 |
| MATURE | ≥ 1,000 settled **and** ≥ 300 settled at P ≥ 0.80 |
No calibration verdict below INTERMEDIATE. At INTERMEDIATE and MATURE the verdict uses the same rule as the WTA holdout
(slope CI includes 1 and a 99.5% Wilson band check). The engine is **not changed** in response to prospective results
before MATURE, except to fix a data bug (logged, with a version bump).

## Credit budget
The `/sports` listing is free. Each active covered tennis key costs 1 credit per scan (`regions=uk`,
`markets=h2h`; exchange books return `h2h_lay` alongside `h2h` automatically, as observed for football in Phase 1; verified on the first run and logged).
With 2 scans per day and a typical 0–4 active ATP+WTA keys: about 0–240 credits/month. A guard skips tennis fetches if
`x-requests-remaining` would fall below 150, so the football scan is always protected. Credits
(`x-requests-used`/`remaining`/`last`) are logged per call.
