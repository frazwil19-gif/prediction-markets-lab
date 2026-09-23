# Platform V2 — Current System vs Target Architecture (audited 2026-09-23 from the repo, not memory)

Repo state at audit: `8f3a17c` (origin in sync), 1,015 tests passing.

## A. What exists today
| layer | component | status |
|---|---|---|
| Ingestion | `ingestion/the_odds_api_loader.py` (h2h + totals 2.5, 3 football leagues), `the_odds_api_scores.py`, football-data.co.uk loaders, tennis TML + Betfair-archive pipeline | LIVE (football) / research (tennis) |
| Probability | `probability/market_pipeline.py` → **proportional** margin removal per bookmaker, then consensus mean; `consensus.py` (IQR/dispersion) | LIVE |
| Probability research | Gate 1 (1X2), Gate 1b (O/U 2.5), Phase 5 BTTS (`research/btts_outcome_prediction.py`, market-implied Poisson), football Elo/Poisson, tennis Elo/surface-Elo | research only |
| Decision | `decisions/grading.py` (A+/A/B/C/Reject by **net EV + probability edge**), `confidence.py` (bookmaker count + dispersion heuristic), `data_quality.py`, `payout_policy.py` (1.33 floor, 1.40–2.50 preferred), `money_qualification.py` (24h window, P floors 0.50/0.60, EV floors 0.02/0.05) | LIVE |
| Risk | `risk/bankroll.py`, `staking.py` (fixed £ by grade), `exposure.py`, `loss_locks.py`, `decision_gates.py` | exists; **gates not wired into the live scan** (known since Backtest Phase 1) |
| Output | `reports/daily_bet_card.py` (full research card), `money_card.py` (Daily Money Card), `system_status.py` | LIVE |
| Ledgers | `paper_ledger/` (auto), `real_bets/` + `record_real_bet.py` | LIVE |
| Settlement/perf | `settlement/`, `performance/paper_performance.py` (Brier, log loss, calibration, ROI, drawdown, by band) | LIVE |
| Automation | GitHub Actions: `daily_scan.yml` 07:00 UTC, `settlement_and_performance.yml` 21:00 UTC, tests, weekly report | LIVE, unattended since 2026-09-20 |
| Research record | Research Atlas v1.1 (`research/multi_market_expansion/`) | exists |
| Multis | none. No code, config or schema | missing |

## B. Conflicts with the V2 directive
1. **Grading ranks by EV and probability edge, not probability.** `grading.py` grades are value-first, so the card is
   ordered by value, the reverse of the V2 hierarchy (probability, then support, then value). Refactor so grade =
   f(probability tier, support, uncertainty) and value becomes a separate gate. Keep the old grade as a
   `research_grade` for continuity.
2. **"Confidence" is a vague HIGH/MEDIUM label.** It is built from bookmaker count and dispersion, not probability
   uncertainty (V2 §16). It should split into quote quality (what it really measures) and a proper probability
   interval.
3. **Probability and value share one source.** Consensus is both P and the value reference. Phase 5 showed this makes
   EV conservative, not inflated, but claimed EV does not become realised return. Independent references are still
   needed (Phase 5 R1–R4).
4. **Proportional margin removal is miscalibrated at the extremes** (new evidence below). This matters most in exactly
   the high-probability region V2 cares about.
5. **The prediction and betting outputs are fused.** The daily card mixes candidates and bets. There is no separate
   Prediction Board that shows prediction quality independently of betting.

## C. What is missing
Daily Prediction Board · per-market probability-engine registry (estimator id/version/support/calibration) ·
probability uncertainty intervals · current-context inputs (none automated; the card's `current_context` is empty by
design) · multi engine (eligibility, dependency, joint P, grading, exposure) · risk gates wired live · raw
per-bookmaker quote archive and closing snapshots (Phase 3 recommendation, still unbuilt) · BTTS/AH/other-sport
adapters · cross-sport comparison framework (started here: `CROSS_MARKET_*`).

## D. Keep unchanged
Odds API ingestion adapter pattern (source-agnostic canonical records) · consensus pipeline (extend, don't replace) ·
money-qualification gate and payout policy values (V2 §20: do not change) · paper ledger + settlement + performance ·
GitHub Actions split (Claude builds, GitHub runs, ChatGPT operates, Fraser executes) · all research records, frozen
datasets and hashes.

## E. Needs eventual refactor (not now)
`grading.py` (probability-first), `confidence.py` (→ quote quality + interval), `market_pipeline.py` (pluggable
margin-removal method), `storage/schemas.py` (engine id, uncertainty, multi fields), `reports/daily_bet_card.py`
(→ Prediction Board + Bet Card), `risk/` (wire into scan, add multi exposure).
