# Layer A — Probability Engine Specification (design, not implemented)

## Contract
Every (sport, market) gets its own registered engine. Each engine returns, per candidate outcome:

| field | meaning |
|---|---|
| `engine_id`, `engine_version` | e.g. `football_btts.market_implied_poisson@1.0` (frozen spec hash) |
| `p` | estimated probability; outcomes of one market sum to 1 |
| `fair_odds` | 1 / p |
| `p_interval` | uncertainty interval (method below), e.g. [0.69, 0.78] |
| `support` | STRONG / ADEQUATE / THIN, derived mechanically from the engine's evidence record (below) plus this candidate's data coverage |
| `calibration_ref` | the engine's measured reliability in this candidate's probability band (n, actual rate, CI) |
| `data_quality` | inputs present, quote count/freshness for market-based engines |
| `context_status` | COMPLETE / PARTIAL / NONE (V1 is always NONE, stated honestly) |
| `prediction_time` | the declared information cut-off (leakage anchor) |

## Engine evidence record (the registry, one per engine version)
historical n · validation n · sealed-holdout n · seasons/leagues covered · log loss / Brier / AUC · calibration
intercept and slope · band table (<50 … 90%+) · ≥60/65/70/75/80/90% threshold table · feature/model stability · live n
(prospective) once available. Stored machine-readably next to the Research Atlas. **An engine without a record cannot
feed the Bet-Selection Engine.**

## Uncertainty (no invented intervals)
Two defensible sources, combined conservatively (wider of the two):
1. **Band-reliability interval.** The Wilson 95% interval of the engine's realised hit rate in this probability band on
   unseen data. This captures "how wrong have predictions like this been?" It is available today for every validated engine.
2. **Input-dispersion interval** for market-based engines: a bootstrap over the bookmakers in the consensus (resample
   books, recompute P). It captures quote disagreement. `probability/uncertainty.py` already has bootstrap machinery.
Model-based engines later add parameter uncertainty (bootstrap refits). Intervals are themselves checked
prospectively: roughly 95% of intervals should contain the realised band rate.

## Support grade (mechanical, configurable, not tuned for profit)
STRONG: sealed-holdout validated, and n ≥ 300 in this band on unseen data, and |calibration error| within the band CI.
ADEQUATE: validated, but band n between 100 and 300. THIN: anything else, which is PAPER_ONLY at most.
(The numbers are initial config values and will be revisited only with prospective evidence.)

## Current engines (see `CROSS_MARKET_RESEARCH_STATUS.md`)
football_1x2.consensus · football_ou25.consensus · football_btts.market_implied_poisson · tennis_winner (Betfair
consensus preferred; Global Elo as a backup, overconfident at the top end).

## First engine-level research item: margin-removal calibration
Evidence (`CROSS_MARKET_PROBABILITY_BANDS.csv`, descriptive, all seasons): football 1X2 favourites the proportional
consensus priced at ≥80% (mean 83.7%) won **88.3%** [82.9, 92.1], n = 188. At ≥75% it was 80.6% priced vs 84.0%
won. Tennis Betfair 30-minute prices show the same direction (≥90%: 93.8% priced vs 96.3% won, n = 458). This is
the classic favourite–longshot pattern that proportional de-vigging leaves in. Power / Shin / odds-ratio methods are
designed to remove it. Because it is descriptive and in-sample, it is a **hypothesis requiring its own pre-registered
chronological test** before any engine changes. Every market-based engine, and every high-probability multi leg,
depends on it.
