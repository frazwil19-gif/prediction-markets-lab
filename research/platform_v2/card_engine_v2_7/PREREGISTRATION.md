# V2-7 Card Engine (singles / doubles / trebles) — Research Pre-registration (2026-09-30, before any joint result was computed)

Research only. No production change, no threshold change, no paid data, no merge. Evidence classes: **A** probability-only outcome
simulation · **B** indicative historical-odds diagnostic · **C** executable-odds backtest (not possible, see audit) · **D** prospective
paper evidence.

## Legs (frozen historical estimators, no refitting)
Favourite side only (P ≥ 0.50), one leg per event:
- **Tennis ATP / WTA:** multiplicative de-vig of Betfair LTP at T−30 (`data/interim/v2_*_market_dataset.csv`); 2021–25.
- **NBA:** proportional de-vig of the OddsPortal average close; 2016-17 → 2025-26 on disk.
- **Football 1X2:** closing multi-book median consensus (≥ 3 books); E0/E1/SC0 2020/21–2025/26; the favourite is the highest-P outcome if it is ≥ 0.50.
- Decision day = UTC date of the scheduled start.

## A1 — Joint calibration (the core question: is P_joint = ∏P_i right?)
- **Deterministic, bounded enumeration.** Within each sport and day, sort legs by (start time, event id) and cut them into consecutive
  **disjoint** groups of 2 (doubles) and 3 (trebles). Each leg is used at most once per card size, so cards are independent samples.
  The search space is recorded; there is no selection on outcomes.
- **Per card size × joint-P band (50–65, 65–80, 80+):** n, mean predicted P_joint, actual hit rate with a Wilson 95% CI, and
  actual/predicted. Singles are reported in the same bands as the baseline.
- **Periods:** development vs already-opened holdout years, reported separately (tennis 2024–25; NBA 2024-25 and 2025-26; football
  2024/25 and 2025/26). Nothing is fitted or tuned, so no holdout is used for selection.
- **Dependence strata (tennis):** legs from the same tournament vs different tournaments on the same day.

## A2 — Correlated failure (over-dispersion)
For each sport-day, compare favourite losses L against the Poisson-binomial expectation E = Σ(1−P) and variance V = ΣP(1−P).
Dispersion index D = mean((L−E)²/V) over days with V > 0, with a day-level bootstrap 95% CI (2,000 resamples, seed 20260930).
D ≈ 1 is consistent with independence; D > 1 means "upset days" cluster.

## A3 — Uncertainty propagation (analytic, not a haircut)
For independent legs, Var(log P_joint) ≈ Σ Var(log P_i). Per-leg uncertainty comes from the band-level calibration CI
(historical), plus half the exchange book width when live P is a Betfair midpoint (bsv2-3 ≤ 0.03 ⇒ ±0.015).
EV sensitivity is ∂EV/∂P_i = O_joint · ∏_{j≠i} P_j.

## B — Indicative odds diagnostic (tennis only)
tennis-data Bet365 closing (the same book for every leg), with P from the Pinnacle close (time-aligned reference, not the frozen engine).
Enumerate same-day doubles and trebles in which **every leg** has positive net EV at Bet365. Report counts and realised hits.
Labelled **INDICATIVE**: closing, untimestamped, no accumulator-rule verification.

## D — Live snapshot (latest production scan, descriptive)
From the 20:11 UTC 29 Sep scan: legs with positive same-scan EV at a named book (bsv2-3 gates). Count the doubles and trebles with every
leg positive **at the same bookmaker**, and their dependency flags (`multi.py`).

Code: `scripts/v2_7_card_engine_research.py`. Outputs: `research/platform_v2/card_engine_v2_7/`.
