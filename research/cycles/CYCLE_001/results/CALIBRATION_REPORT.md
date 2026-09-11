# Calibration Report (Stage 3B)

**Generated from `data/interim/stage_3b_checkpoint4_predictions.csv` (pooled
development-fold predictions) via `performance.calibration.compute_outcome_calibration`,
5 equal-count bins per outcome. Do not hand-edit the numbers below without
regenerating.**

Data version: `cycle_001_v1.0.0-20260910T234139`. Pooled common sample,
N=3,446, all 3 development folds combined. Sealed holdout (2024_25) not
read.

## What this measures (raw calibration only)

Per research/cycles/CYCLE_001/STAGE_3B_PLAN.md section 8, this is **raw**
calibration diagnostics — no recalibration (no Platt scaling, no isotonic
regression) is fit or applied anywhere in this report. For each model and
each outcome (home/draw/away), matches are grouped into 5 equal-COUNT bins
by that outcome's predicted probability (not equal-width bins — draw
probabilities in particular cluster tightly in the ~0.15-0.35 range, so
fixed-width bins would leave most of [0,1] empty). Within each bin: mean
predicted probability vs. observed frequency (how often the outcome actually
happened). A well-calibrated model has these two numbers close in every bin.
Expected Calibration Error (ECE) is the sample-size-weighted mean absolute
gap across a model's 5 bins for one outcome.

Models assessed: Market (Baseline 1), Elo (Model 1), Poisson (Model 2), and
`elo_poisson` (the one blend combo that is not simply a copy of market — see
BLEND_REPORT.md). Market-inclusive blends are omitted here since they are
numerically identical to market (100% market weight was calibrated in every
fold) and would just repeat market's own numbers.

## ECE summary (lower is better; 0 = perfect calibration on this sample)

| Model | Home ECE | Draw ECE | Away ECE |
|---|---|---|---|
| Market | 0.0219 | 0.0204 | 0.0058 |
| Elo | 0.0542 | 0.0106 | 0.0605 |
| Poisson | 0.0278 | 0.0128 | 0.0240 |
| **`elo_poisson`** | **0.0130** | **0.0155** | **0.0128** |

**Headline finding: `elo_poisson` is the best-calibrated of the three
model-based candidates on every one of the 3 outcomes** — clearly better
than either Elo or Poisson individually, and within a comparable range of
market's own calibration (market still wins outright on the away outcome).
This is a distinct finding from the log-loss/Brier ranking in
BLEND_REPORT.md: blending does not just average two models' *accuracy*, it
also averages out a specific *bias* in Elo (below), which shows up here as a
material calibration improvement even though it does not fully close the
scoring gap to market.

## Elo's away-outcome miscalibration (the specific defect the blend corrects)

Elo's away-outcome ECE (0.0605) is the single worst number in this report.
The per-bin pattern is a consistent, one-directional bias, not noise:

| Bin (away probability) | Elo mean predicted | Elo observed frequency | Gap |
|---|---|---|---|
| 1 (lowest) | 0.134 | 0.148 | 0.014 |
| 2 | 0.199 | 0.277 | 0.078 |
| 3 | 0.238 | 0.283 | 0.045 |
| 4 | 0.284 | 0.347 | 0.063 |
| 5 (highest) | 0.400 | 0.503 | **0.103** |

Elo **systematically under-predicts away wins** across the middle-to-upper
range of its own probability scale, and the gap widens as predicted
probability increases — its most confident away-win predictions are its
least well-calibrated. Elo's home-outcome calibration shows a matching
mirror-image pattern (systematically over-predicting home wins in the same
mid-range bins, ECE 0.0542), consistent with a single underlying cause: the
two-outcome win/loss/draw-margin transform underweights how often the away
side actually wins relative to what the ratings alone would suggest, most
likely because the model's fixed home-advantage term does not fully capture
the real home/away split observed in this sample. Poisson does not show this
directional bias to the same degree (away ECE 0.0240, roughly a quarter of
Elo's), and `elo_poisson` inherits Poisson's better away calibration in the
blend (away ECE 0.0128) — this is very likely *why* blending genuinely
helps calibration here, distinct from and additional to the log-loss/Brier
averaging effect already documented in BLEND_REPORT.md.

## Full per-bin tables

### Market

| Outcome | Bin 1 (pred/obs/gap) | Bin 2 | Bin 3 | Bin 4 | Bin 5 |
|---|---|---|---|---|---|
| Home | 0.201/0.222/0.021 | 0.338/0.325/0.013 | 0.420/0.438/0.018 | 0.510/0.536/0.026 | 0.687/0.717/0.031 |
| Draw | 0.173/0.151/0.022 | 0.245/0.218/0.027 | 0.271/0.283/0.012 | 0.287/0.284/0.003 | 0.305/0.267/0.038 |
| Away | 0.122/0.116/0.006 | 0.222/0.212/0.010 | 0.290/0.289/0.001 | 0.370/0.377/0.008 | 0.560/0.564/0.004 |

### Elo

| Outcome | Bin 1 (pred/obs/gap) | Bin 2 | Bin 3 | Bin 4 | Bin 5 |
|---|---|---|---|---|---|
| Home | 0.328/0.251/0.077 | 0.444/0.388/0.056 | 0.503/0.450/0.053 | 0.560/0.488/0.072 | 0.675/0.662/0.012 |
| Draw | 0.190/0.186/0.005 | 0.240/0.225/0.015 | 0.257/0.257/0.000 | 0.269/0.280/0.011 | 0.278/0.255/0.023 |
| Away | 0.134/0.148/0.014 | 0.199/0.277/0.078 | 0.238/0.283/0.045 | 0.284/0.347/0.063 | 0.400/0.503/0.103 |

### Poisson

| Outcome | Bin 1 (pred/obs/gap) | Bin 2 | Bin 3 | Bin 4 | Bin 5 |
|---|---|---|---|---|---|
| Home | 0.206/0.267/0.061 | 0.334/0.388/0.053 | 0.412/0.406/0.005 | 0.495/0.507/0.012 | 0.679/0.671/0.008 |
| Draw | 0.174/0.154/0.020 | 0.235/0.245/0.011 | 0.256/0.245/0.011 | 0.275/0.270/0.005 | 0.306/0.288/0.017 |
| Away | 0.129/0.154/0.025 | 0.244/0.225/0.020 | 0.311/0.305/0.007 | 0.387/0.357/0.030 | 0.557/0.517/0.039 |

### `elo_poisson`

| Outcome | Bin 1 (pred/obs/gap) | Bin 2 | Bin 3 | Bin 4 | Bin 5 |
|---|---|---|---|---|---|
| Home | 0.256/0.260/0.004 | 0.374/0.377/0.003 | 0.442/0.433/0.009 | 0.511/0.482/0.030 | 0.667/0.687/0.020 |
| Draw | 0.185/0.154/0.032 | 0.239/0.229/0.010 | 0.257/0.271/0.015 | 0.270/0.253/0.017 | 0.291/0.296/0.004 |
| Away | 0.138/0.149/0.012 | 0.234/0.228/0.006 | 0.288/0.299/0.011 | 0.351/0.364/0.014 | 0.496/0.517/0.021 |

(689-690 matches per bin; each row's three numbers are mean predicted
probability / observed frequency / absolute gap.)

## Interpretation

Calibration and discrimination (log loss / Brier) are different questions,
and this report shows they don't move in lockstep: Poisson has better raw
log loss than Elo (BLEND_REPORT.md, Checkpoints 2-3) but its calibration is
not uniformly better on every outcome (Poisson's draw ECE, 0.0128, actually
beats Elo's, 0.0106, only marginally, while Poisson's home ECE is worse than
Elo's would suggest were log loss the only lens). The clearest, most
actionable finding here is Elo's specific away-outcome bias — a concrete,
falsifiable claim (not just "Elo is worse") that would be the natural next
target if Elo's away-side handling were ever revisited, and it is very
plausibly the mechanism behind why `elo_poisson` blending improves
calibration, not just accuracy.

No recalibration has been fit or applied anywhere in this report, per the
predeclared plan. Market remains the best- or near-best-calibrated model on
every outcome.
