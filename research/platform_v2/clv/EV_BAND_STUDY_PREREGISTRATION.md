# Tennis EV-band study (0–1 / 1–2 / 2–4 / 4%+) — PRE-REGISTRATION

Registered 2026-10-08, BEFORE any cohort row exists and before any closing price or outcome of a cohort row has been
seen. Directive: ChatGPT/Fraser 2026-10-08 18:37 ("Proceed with the expansion R&D programme"). Research only:
**the live rule stays bsv2-4 (net EV ≥ +2%)**; nothing here can change it. Any threshold change is a separate,
formal, versioned decision by Fraser.

## Question
Is the +2% live EV threshold empirically conservative for the tennis engine, or is the apparent 0–2% volume mostly
noise / cost / slippage?

## Population (fixed rule; no choice of snapshot)
- Engines: `atp_match_winner.betfair_market`, `wta_match_winner.betfair_market` (tennis), as evaluated in production
  by bsv2-4 and recorded in `paper_betting_v2/decision_shadow.csv`.
- A prediction enters the cohort at its **first evaluation at or after the study start** where it is either a
  PAPER_BET or fails **only** EV gates (reasons ⊆ {NET_EV_NOT_POSITIVE, NET_EV_BELOW_PAPER_GATE}); i.e. it passes P ≥
  0.50, odds ≥ 1.33, horizon, price freshness, spread, same-snapshot and commission gates. One row per prediction;
  later evaluations never replace it (no best-snapshot selection).
- Entry = that evaluation's best usable price (`decimal_odds`, `source`, `commission`) and `net_ev`.
- Study start: the first cohort-builder run after this file's commit (recorded as `study_start` in
  `config/clv.yaml`). Evaluations before it are excluded.
- Bands by entry net EV: `<0` (control), `0–1%`, `1–2%`, `2–4%`, `4%+`. The cohort is never bet.

## Closing price (two tiers)
- **Tier A (primary):** paid near-close capture (Odds API uk region, markets h2h + h2h_lay) at 0–25 min before the
  listed start, for every cohort row with entry EV ≥ 0 (and every PAPER_BET). Close fair probability = Betfair
  Exchange back/lay mid, de-vigged (same construction as the engine). Missing captures are logged, never imputed.
- **Tier B (secondary, free):** the last scheduled tennis scan before start and after entry (label: minutes before
  start). Applies to all bands including `<0`.

## Metrics (per band and combined 0–2%)
N; mean/median entry EV; **fair-CLV = (1 + (odds−1)(1−commission)) × p_close − 1 (primary)**; price-CLV vs the same
book's closing odds = entry/close − 1; best-price CLV; mean/median; positive-CLV rate; closing movement
(p_close − p_entry); hypothetical £1 P/L and ROI; Brier; log loss; expected wins (ΣP) vs actual; expected profit
(Σ net EV) vs realised; bookmaker concentration (top-book share); spread / price-age status at entry; capture
coverage (Tier A captured / eligible).

## Arrival rates (measured before registration; decision_shadow 2026-10-01..08, first clean evaluation)
6.6 days of bsv2-4 tennis evaluations: `<0` 136 (≈ 620/month), `0–1%` 5 (≈ 23/month), `1–2%` 0, `2–4%` 0, `4%+` 0.
Planning ranges per in-season month (wide; Poisson noise at n=5 is large): 0–1% ≈ 10–30; 1–2% ≈ 0–8; 2–4% ≈ 0–6;
4%+ ≈ 0–3; combined 0–2% ≈ 10–35. December ≈ 0 (tour off-season; Odds API covers tour-level events only).
(The earlier "~85/month" figure took the best price over repeated scans and omitted production gates; it is withdrawn.)

## Sample size (decided now)
- **300 per sub-band is infeasible** (1–2% may take years). **300 for the combined 0–2% cohort** would take about
  12–18 active tour months.
- Planning SD of fair-CLV: 3–4% (measured first-to-last-scan movement SD 1.8% understates the full close).
  To detect a true mean fair-CLV of +0.75% (≈ mid-band if estimated EV is unbiased) with 80% power, one-sided
  α = 0.025: N ≈ 7.85 × (σ/0.0075)² = 125 (σ = 3%) to 225 (σ = 4%). **Final N = 200 Tier-A captured rows in the
  combined 0–2% cohort.**
- **Looks:** interim at N = 100 (futility only), final at N = 200. Approximate calendar (P, ±2 months): N = 100
  ≈ March–May 2027; N = 200 ≈ July–October 2027.
- Until a look is reached the report shows only counts and data quality for the 0–1% and 1–2% bands (CLV, P/L and
  calibration for those bands stay sealed). PAPER_BET (live-rule) CLV is shown continuously.

## Decision rules
- **Primary hypothesis:** mean fair-CLV of the combined 0–2% cohort > 0.
- **Interim (N = 100), futility only:** if the upper bound of the two-sided 95% bootstrap CI of the mean is < 0, stop
  the 0–2% study (record negative). No efficacy stop at the interim, so no alpha spending is needed; the final test
  uses one-sided α = 0.025 (= lower bound of the two-sided 95% CI > 0).
- **Multiple testing:** one primary hypothesis. Sub-bands (0–1, 1–2) and all secondary metrics are descriptive; any
  inferential claim about sub-bands uses Holm across the four bands.
- **Coverage rule:** if Tier-A coverage of eligible 0–2% rows is < 70%, the result is INCONCLUSIVE (missingness may be
  informative), not positive.

## Evidence required before PROPOSING any live-threshold change (all must hold at the final look)
1. Lower 95% bound of mean fair-CLV (combined 0–2%, Tier A, N ≥ 200) > 0, with coverage ≥ 70%.
2. The proposed new threshold is the lowest band whose own point estimate is > 0 (e.g. if 0–1% is ≤ 0, propose 1%).
3. Probability quality holds on the cohort: calibration slope 95% CI contains 1; Brier/log loss not worse than the
   full tennis engine over the same period.
4. Hypothetical ROI does not contradict (95% CI lower bound > −10%); expected-vs-realised wins |z| < 2.
5. Execution: in the Bet Log structured near-miss price checks, the card price or better was available at Fraser's
   bookmakers in ≥ 50% of sampled rows.
6. Then: a written proposal to Fraser for a versioned rule (bsv2-5) with its own pre-registered prospective
   monitoring and demotion rule. **Never automatic.**

## What would make the study invalid
Any change to the engine, bsv2 gates other than via a registered version (rows are tagged with rule version; the
study is restricted to bsv2-4 rows), back-filled captures, or analysis of sealed bands before a look point.

## Amendment A1 (2026-10-08, before any cohort row or capture exists)
Capture mechanics only, no analysis change: the Odds API `h2h` market already returns Betfair `h2h_lay` prices for
exchanges (the tennis engine depends on this), so Tier-A capture requests market `h2h` alone (1 credit per call), not
`h2h` + `h2h_lay`. Close fair probability is unchanged (Betfair back/lay mid).
