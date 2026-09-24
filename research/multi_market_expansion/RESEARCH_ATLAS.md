# Research Atlas -- Multi-Market Expansion for Outcome Prediction (Phase 4, 2026-09-22)

Machine-readable companion: `RESEARCH_ATLAS.json`. This atlas exists so future research (any Claude
session, any operator instruction) can check a market's status here before proposing a cycle, rather
than accidentally repeating exhausted research -- the whole point Section 26 of the Phase 4 instruction
asked for.


## Best Available Probability Estimator by market (added Phase 5, 2026-09-22)

This atlas records the **best available estimator**, not the best model that beats the market. Market consensus is a
legitimate estimator. See `research/btts_outcome_prediction/PROBABILITY_ENGINE_ARCHITECTURE.md`.

| market | best probability estimator | outcome-prediction | betting replay | live |
|---|---|---|---|---|
| Football 1X2 | de-vigged consensus | EXHAUSTED (validated) | EXHAUSTED | LIVE |
| Football O/U 2.5 | de-vigged consensus | VALIDATED | BLOCKED (thin panel) | LIVE |
| Football BTTS | market-implied Poisson (1X2 + O/U 2.5) | VALIDATED | BLOCKED (no odds) | available, not wired |
| Football Asian Handicap | not researched | UNEXPLORED | BLOCKED (thin panel) | available (spreads), not wired |
| Tennis Match Winner | Betfair-archive consensus | edge-hunting EXHAUSTED | open (money-qualification) | not wired |

## V2 cross-market high-probability view (added 2026-09-23)

See `research/platform_v2/CROSS_MARKET_RESEARCH_STATUS.md`. Share of events whose top pick is at least 80%: football
1X2 3.3%, O/U 2.5 0.1%, BTTS 0%, **tennis Betfair market 20.7%** (calibrated within ±0.6 pp from 65–90%).
Proportional de-vig under-predicts strong favourites. Multis remain disabled (`MULTI_ENGINE_SPEC.md`).

## V2-3 update (2026-09-24)

- **NBA Moneyline: VALIDATED (gate A)** on the sealed 2024-26 holdout (n = 2,629, never analysed before). The market
  (OddsPortal average closing odds) is best: log loss 0.581, slope 1.05. At ≥80%: 20.9% of games, 85.5% predicted vs
  87.5% won. At ≥90%: 2.6%. Elo is less informative; schedule and form add nothing beyond the market. No
  injury/lineup history exists. `research/platform_v2/nba/`.
- Cross-sport ≥80% share (predicted → actual): ATP 19.8% (87.6 → 87.4), WTA 17.7% (86.9 → 87.0), NBA 20.9% (85.5 →
  87.5), football 1X2 3.3%, O/U 0.1%, BTTS 0%.
- Next recommended family: **Football Double Chance** (≥80% in ~33% of matches descriptively).

## V2-2 update (2026-09-23)

- **Tennis WTA Match Winner: VALIDATED** (a never-analysed population; sealed 2024–25 holdout, n = 4,339). Betfair
  market log loss 0.5967, slope 0.979. At ≥80%: 17.7% of matches, 86.9% predicted vs 87.0% won. It becomes the
  second tennis probability engine. Watch items: 2025 and grass at ≥80%.
- **ATP + WTA paper Prediction Board is live** (The Odds API covered universe; `tennis_predictions/`). The first 6
  WTA predictions are ledgered. Live-source decision **A**. Betfair Delayed: free, but GitHub runners are blocked
  (USA is a restricted IP region), so it is a local complement only.
- Next research family: **Basketball Moneyline**, starting with a Stage-0 data audit.

## V2-1 update (2026-09-23)

- **De-vig study: decision C.** Retain proportional. Power/additive fix football's slightly flat probabilities on
  exposed seasons (not significant, and reversed on 2025/26). For tennis the method is irrelevant.
  `research/platform_v2/calibration/`.
- **Tennis ATP Match Winner: VALIDATED on the sealed 2024–25 holdout, gate B.** Betfair market log loss 0.5883,
  slope 0.986. At ≥80%: 19.8% of matches, 87.6% predicted vs 87.4% won (n = 1,001). Elo is overconfident, and adding
  Elo to the market does not help. The live source is unsolved. `research/platform_v2/tennis/`.
- **Tennis WTA:** unexplored. Free data is already available (TML WTA CSVs plus WTA markets inside the Betfair
  archive). Recommended next family.

## Football 1X2

- **Status**: EXHAUSTED -- CURRENT INFORMATION SET
- **Research cycles completed**: Stage 3B (2026-09-11, naive/Elo/Poisson/blends vs market, sealed
  holdout), Gate 1 (2026-09-18, market vs fundamentals-logistic vs Elo+Poisson vs combined, 5-fold
  walk-forward), Backtest Phase 1 (2026-09-22, frozen-V1 money-qualification backtest, 17,328
  candidates), Phase 2 (2026-09-22, high-probability-region and disagreement-band diagnostics), Outcome
  Discovery cycle (2026-09-22, winner/loser + conditional-market analysis, 16,893 candidates)
- **Best probability estimator**: de-vigged multi-bookmaker closing consensus (market)
- **Sample size**: 5,776-5,800 matches (E0/E1/SC0, 2020/21-2025/26 depending on the specific cycle's
  data cut)
- **Calibration status**: well-calibrated (ECE 0.0099, calibration slope 1.07, AUC 0.70 across 17,328
  candidates, Backtest Phase 1)
- **Holdout status**: sealed 2024/25 holdout run in Stage 3B and reproduced independently in Gate 1's
  walk-forward; NOT a fully blind holdout relative to the whole span of research this project has now
  run on the same seasons (documented honestly since Phase 2)
- **Betting-overlay status**: zero money-qualified bets under current V1 thresholds (Backtest Phase 1,
  both closing and opening snapshots) -- a real, mechanically explained negative result, not a bug
- **Live support**: LIVE, operational since 2026-09-19 (`the_odds_api_loader.py`, EPL/Championship/
  Scottish Premiership)
- **Known limitations**: football-data.co.uk provides only one opening + one closing snapshot per
  bookmaker per match (no intraday series) -- historical backtesting is PROXY-only, never exact replay
- **Next action**: none recommended -- do not reopen without a materially new information source (xG,
  rest days, referee history) or a genuinely new market family

## Football Over/Under 2.5 Goals

- **Status**: OUTCOME-PREDICTION READY -- COMPLETED THIS CYCLE (Gate 1b, 2026-09-22).
  MONEY-QUALIFICATION BACKTEST remains BLOCKED BY HISTORICAL DATA (see below) -- these are two
  separate statuses per Section 8/20 of the Phase 4 instruction, and must not be conflated.
- **Research cycles completed**: Gate 1b (this cycle) -- market-only vs fundamentals-only vs
  market+fundamentals vs naive-frequency, 4-fold expanding walk-forward, 2020/21-2024/25
- **Best probability estimator**: the thin-panel (2-3 bookmaker) research-grade de-vigged market
  probability already carried in `cycle_002_discovery_features.csv`. Pooled OOS log loss 0.6755
  (market) vs 0.6866 (fundamentals) vs 0.6806 (market+fundamentals) vs 0.6964 (naive frequency);
  pooled AUC 0.60 (market) vs 0.57 (fundamentals) vs 0.59 (combined). Paired bootstrap: fundamentals
  worse than market by 0.0111 log-loss points (95% CI [0.0070, 0.0151], excludes zero);
  market+fundamentals worse than market by 0.0051 (95% CI [0.0027, 0.0074], excludes zero).
  Fundamentals DOES beat the naive frequency baseline (by 0.0097, CI excludes zero) -- the engineered
  features carry real signal, just less than the market already prices in.
- **Sample size**: 5,800 matches total, 5,759 (99.3%) usable for the full three-way comparison
  (E0/E1/SC0, 2020/21-2024/25)
- **Calibration status**: market well-calibrated across probability bands (calibration error 0.5-1.6pp
  in every band with adequate sample, 50-79.9%); fundamentals shows larger, sometimes overconfident
  errors in the higher bands (e.g. -11.8pp in 70-79.9%, n=28) -- the same overconfidence pattern Phase
  2 already found for the 1X2 fundamentals model
- **Holdout status**: 2024/25 evaluated as the walk-forward's final fold under decisions frozen in
  advance (feature set, L2 penalty) -- same ranking held (market best) on validation (2023/24) AND
  holdout (2024/25) independently. No further prospective holdout exists yet (2025/26 not in the
  feature file -- same data gap the Outcome Discovery cycle already documented for 1X2)
- **Betting-overlay status**: NOT run retrospectively -- the historical bookmaker panel (2-3
  bookmakers/match) is below the production `min_bookmakers=3` consensus floor, confirmed measured
  fact from Phase 3 (`research/data_expansion/EXHAUSTED_VS_OPEN_RESEARCH.md`), not assumed. The LIVE
  production system already scans real Odds API O/U 2.5 markets with adequate bookmaker depth and has
  recorded at least one real paper bet on this market already -- prospective (not retrospective)
  evaluation is already running via the live paper ledger
- **Live support**: LIVE, operational since 2026-09-19, using de-vigged multi-bookmaker consensus --
  this cycle's finding VALIDATES that existing production design choice with actual analysis rather
  than assumption (market beats a from-scratch fundamentals model here too)
- **Known limitations**: same football-data.co.uk single-snapshot limitation as 1X2; same 2025/26
  feature-pipeline gap as 1X2 (Outcome Discovery cycle, `research/outcome_discovery/HOLDOUT_REPORT.md`)
- **Next action**: no production change recommended (market already used in production, now with
  evidence behind it); optionally extend the feature pipeline to 2025/26+ for a genuine prospective
  check (shared recommendation with the 1X2 Outcome Discovery cycle)

## Football Both Teams To Score (BTTS)  — updated Phase 5, 2026-09-22

| field | value |
|---|---|
| OUTCOME PREDICTION STATUS | **VALIDATED** (dev walk-forward 2021/22–2023/24 + sealed 2024/25 holdout, opened once) |
| BEST PROBABILITY ESTIMATOR | **market_implied_poisson**: λ from de-vigged 1X2 + O/U 2.5 prices, P = (1−e^−λh)(1−e^−λa), 0 fitted params. Market-derived, not a BTTS price |
| HISTORICAL SAMPLE | 5,800 matches, E0/E1/SC0, 2020/21–2024/25, YES base rate 50.5% (45.6% → 55.0% drift by season) |
| CALIBRATION STATUS | good: slope 1.06 dev / 0.93 holdout, ECE 1.2% / 1.7%; bands with n≥100 within about ±4.5 pp |
| SEALED HOLDOUT STATUS | DONE: log loss 0.6857, Brier 0.2463, AUC 0.563, top-pick accuracy 55.9%. Data-only model REJECTED (AUC 0.496) |
| HISTORICAL BETTING-REPLAY STATUS | BLOCKED_BY_HISTORICAL_DATA (no BTTS odds exist in the archive) |
| LIVE MARKET STATUS | AVAILABLE: Odds API `btts`, per-event endpoint, 1 credit/event, 9 UK books incl. Betfair Exchange (probe 2026-09-22). Not wired |
| PROSPECTIVE PAPER STATUS | NOT STARTED (needs approval: credit budget + adapter) |
| KNOWN LIMITATIONS | BTTS is intrinsically low-confidence: P spans 0.31–0.72, ≥60% picks on only 7–10% of matches, never ≥75%. No direct BTTS-consensus benchmark historically |
| NEXT ACTION | live quote preservation, then paper-only BTTS wiring under the unchanged money policy |

Full package: `research/btts_outcome_prediction/`.

## Football Asian Handicap

- **Status**: PARTIALLY EXPLORED / BLOCKED BY HISTORICAL DATA for money-qualification;
  REQUIRES-NEW-INFORMATION for outcome-prediction
- **Why outcome-prediction is harder than O/U2.5/BTTS**: unlike O/U 2.5 (fixed 2.5 line) or BTTS (no
  line at all), the Asian Handicap line itself varies match-to-match (confirmed:
  `market_ah_closing_line` is a per-match field, not a constant) -- so "the AH outcome" is not one
  binary target across the whole dataset the way Over/Under 2.5 is. A defensible study needs the
  candidates pooled by handicap line (or re-expressed as a continuous margin-of-victory target), which
  is a materially different, larger piece of feature/target engineering than reused directly here.
  Section 6.C of the Phase 4 instruction explicitly warns never to merge different handicap lines.
- **Money-qualification feasibility**: BLOCKED BY DATA, same measured 2-3-bookmaker-per-match shortfall
  as O/U 2.5 (Phase 3 finding, `cycle_002_consensus_ah.csv` also 0 bytes)
- **Next action**: not pursued this cycle; would need its own line-pooling design before Stage A is
  even well-defined

## Tennis Match Winner

- **Status**: PARTIALLY EXPLORED (money-qualification); EXHAUSTED for edge-hunting (Workstream B,
  CLOSED, 13/13 pre-registered hypothesis families rejected)
- **Data**: TML Database ATP 2021-2026 (14,564 canonical matches), Betfair Historical Data BASIC tier
  (already downloaded: `Downloads/tennis data/data.tar` 4.17GB + `Downloads/BASIC/2026/` 746MB),
  12,956/14,564 matches linked (88.96%), intraday last-traded-price ticks (materially finer-grained
  than football's single-snapshot data)
- **Live support**: NOT wired into `decisions/recommendation.py` or `scripts/run_daily_scan.py` -- no
  live tennis daily-card candidates exist today
- **Next action**: STRONGEST remaining candidate for a Phase-1-style frozen money-qualification
  backtest (every prerequisite already satisfied per the parallel Phase 3 data-expansion decision,
  `research/data_expansion/PHASE3_RETURN_CHECKPOINT.md`) -- explicitly NOT selected this Phase 4 cycle
  per the operator's own Section 5 instruction not to default to tennis without fresh justification,
  and because it answers a genuinely different question (money-qualification, not outcome-prediction
  discovery) from what this cycle was scoped to build

## Basketball / Cricket / other sports

- **Basketball**: UNEXPLORED. No data of any kind exists in the repository (confirmed, Phase 3).
- **Cricket**: BLOCKED -- paused per master directive Section 14 (2026-09-18). Not reopened by this
  cycle.
- **Other Odds-API-supported sports/markets**: UNEXPLORED, not yet surveyed beyond football and tennis.
