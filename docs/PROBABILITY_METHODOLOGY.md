# Probability Methodology

## 1. Odds conversion

Convert each bookmaker's decimal odds `O_i` into a raw implied
probability:

```
q_i = 1 / O_i
```

Implemented in `probability/odds_conversion.py`. This includes the
bookmaker's margin (overround) and is not yet a fair probability.

## 2. Margin removal

**V1 default method: proportional.**

```
p_i = q_i / Σ_j q_j
```

Implemented in `probability/margin_removal.py`. This is the only
margin-removal method implemented in Stage 1.

### Future methods (not implemented — do not use without validation)

- **Shin's method** — models the presence of informed bettors; more
  accurate for markets with long-shot bias but harder to validate.
- **Power method** — raises implied probabilities to a fitted power to
  remove margin non-proportionally.
- **Odds-ratio method** — Cheung/other odds-ratio-based transforms.

Per project instructions section 8, alternative methods must not be
used until validated against historical data (see
`docs/VALIDATION_PLAN.md`), and any future implementation should be
added as a separate function in `margin_removal.py` rather than
replacing the proportional method.

## 3. Consensus probability

For each outcome, across bookmakers:

1. Convert each bookmaker's odds to raw implied probability (step 1).
2. Remove that bookmaker's margin (step 2).
3. Aggregate the resulting fair probabilities across bookmakers.

**V1 default aggregator: median** — chosen for robustness to stale or
unusual individual prices. `probability/consensus.py` also reports
mean, weighted mean (if weights supplied), standard deviation, min,
max, interquartile range, and bookmaker count, all of which should be
inspected before trusting the median (e.g. a very wide IQR or very low
bookmaker count is itself a data-quality signal — see
`docs/RISK_MANAGEMENT.md`).

## 4. Model probability (Stage 3+, not yet implemented)

Category-specific. Planned baselines:

- **Football:** bookmaker consensus prior, Elo rating, simple Poisson
  scoring model, home advantage, recent form with decay, goals
  for/against, optional team-news adjustment.
- **Tennis:** bookmaker consensus prior, overall Elo, surface Elo,
  recent form, match load, injury/retirement concerns, format and
  tournament level.

Every adjustment to a model probability must be bounded, documented,
linked to a specific feature, timestamped, and auditable. No arbitrary
subjective probability adjustments are permitted.

## 5. Final probability (Stage 3+, not yet implemented)

```
P_final = w_c * P_consensus + w_m * P_model
```

Weights are configuration-driven (`config/model_weights.yaml`), never
hard-coded, and start conservative (see that file for current
defaults and rationale). Later weights should be estimated from
historical out-of-sample performance, not chosen by hand.

In Stage 1, since no model probability exists yet, `P_final` is not
implemented; only `P_consensus` is available end-to-end.
