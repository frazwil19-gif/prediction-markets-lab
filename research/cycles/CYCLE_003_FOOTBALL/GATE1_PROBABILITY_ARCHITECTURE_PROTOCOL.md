# Gate 1 — Football 1X2 Probability Architecture Comparison: Frozen Protocol

**Written and committed 2026-09-18, BEFORE any Gate 1 comparative result is computed**, per the
operator's explicit "OPERATOR DECISION — CONDITIONAL GO ON FOOTBALL DAILY ENGINE V1" instruction
(relayed by Fraser, 2026-09-18) and this project's standing pre-registration discipline (freeze the
specification, commit it, only then run the comparison — the same order already used for Tennis
Cycle 1's pre-holdout freeze and Football Cycle 2's sealed OOS protocol).

## 0. What this protocol answers, and what it does not

This is **Gate 1 only**: a chronologically-honest, leakage-checked comparison of candidate
architectures for generating a football 1X2 probability, run once the protocol below is frozen and
committed. It does **not** build the production Daily Card, does not test Over/Under 2.5 or Asian
Handicap, does not acquire new data, does not touch Cricket, does not place any bet, does not choose
a betting threshold, and does not reopen or modify any verdict from Football Cycle 2 (H-FB2-001,
H-FB2-002) or Stage 3B. Gate 2 (freezing a single Probability Engine V1 architecture from this
result) requires a separate operator decision after this checkpoint is returned.

## 1. The core question

Where should the daily engine's `model_probability` for a football 1X2 proposition actually come
from? Four candidate architectures are compared, exactly as the operator specified:

- **Model 0 — Market Consensus Baseline.** `P = de-vigged, multi-bookmaker closing consensus`.
  Labelled explicitly as a market-consensus baseline, never as a "model-derived" probability.
- **Model 1 — Existing Frozen Football Model Baseline.** The frozen Elo+Poisson blend from Stage 3B
  (`research/cycles/CYCLE_001/`), re-run unchanged through an extended walk-forward schedule. No
  hyperparameter is retuned; every value below is copied verbatim from the frozen Stage 3B scripts.
- **Model 2 — Fundamentals Probability Model.** A newly-fit multinomial (softmax) logistic
  regression using only pre-match football information already in the repository (Elo gap, rolling
  match-statistic differentials, competition). No market information.
- **Model 3 — Market + Fundamentals.** The same fundamentals features as Model 2, plus the market
  consensus expressed as two logit-space features, fit as one combined multinomial logistic
  regression.

A fifth, non-mandatory comparison point is also computed because the existing blend infrastructure
(`models/football_blended.py`) makes it free: **Model 4 — Calibrated Ensemble (Architecture D)**, a
grid-search-weighted linear blend of Model 0 and Model 2's probabilities, weights chosen on training
data only. This directly operationalises the operator's fourth conceptual architecture ("a calibrated
combination of market consensus and independent model") without requiring new code.

No architecture is assumed to win in advance. Model 2 and Model 3 are not rejected merely for
failing to beat Model 0 on average — see §8.

## 2. Exact datasets used

All data is already present in the repository; **nothing new is acquired for Gate 1**.

| Source file | Seasons | Competitions | Rows | Used for |
|---|---|---|---|---|
| `data/processed/football/cycle_001_matches_full.csv` | 2020/21–2024/25 | E0, E1, SC0 | 5,800 | match identity, date, teams, `full_time_result` |
| `data/processed/football/cycle_002_match_statistics.csv` | 2020/21–2024/25 | E0, E1, SC0 | 5,800 | goals, shots, SOT, corners, cards (raw match-produced stats, used only to build *later* matches' rolling features — never as a same-match feature, per `features/football_leakage_safe_features.py`'s hard rule) |
| `data/processed/football/cycle_001_consensus_full.csv` | 2020/21–2024/25 | E0, E1, SC0 | 11,540 (opening+closing) | Model 0 / Model 3 market input (closing rows only, `price_timing == "closing"`) |
| `data/processed/football/h_fb2_002_sealed_oos_2025_26_matches.csv` | 2025/26 | E0, E1, SC0 | 1,160 | match identity, date, teams, `full_time_result` (acquired and audited for H-FB2-002; **this protocol reuses that already-acquired, already-audited file — it does not re-acquire or re-audit it**) |
| `data/processed/football/h_fb2_002_sealed_oos_2025_26_match_statistics.csv` | 2025/26 | E0, E1, SC0 | 1,160 | goals, shots, SOT, corners, cards |
| `data/processed/football/h_fb2_002_sealed_oos_2025_26_consensus.csv` | 2025/26 | E0, E1, SC0 | 2,320 (opening+closing) | Model 0 / Model 3 market input (closing rows only) |

Combined span: 6,960 raw match rows, 2020/21 through 2025/26, three competitions, all six seasons
already fully completed (today is 2026-09-18; 2025/26 was confirmed a completed season during
H-FB2-002's sealed OOS work).

**Elo, Poisson, and rolling match-statistic features are computed fresh, in one continuous
chronological replay spanning all six seasons together** (using the frozen, tested model code in
`models/football_elo.py`, `models/football_poisson.py`, and
`features/football_leakage_safe_features.py`), rather than mixing the pre-computed
`cycle_002_discovery_features.csv` (2020/21–2024/25 only) with freshly-computed 2025/26 values. This
is a deliberate methodological choice, not a shortcut avoided: a single continuous replay guarantees
2025/26's first rolling/Elo snapshots correctly inherit each team's 2024/25 tail history (no reset at
the season boundary) using exactly one code path, eliminating any risk of a subtle mismatch between
a precomputed file and a freshly-computed extension — the same "cross-season continuity via one
combined replay" principle already established and used for H-FB2-002's SOT feature.

## 3. Exposure classification (per operator instruction — do not pretend these are pristine)

| Period | Exposure status | Why |
|---|---|---|
| 2020/21–2023/24 | EXPOSED — discovery/development | Used in Stage 3B's walk-forward development folds and Football Cycle 2's discovery/development phases (§20/§21 of the roadmap). |
| 2024/25 | EXPOSED — sealed holdout already opened once | Stage 3B's own sealed holdout (model-vs-market comparison already published: Δ log loss +0.0169, 95% CI [+0.0066,+0.0274]). |
| 2025/26 | EXPOSED — H-FB2-002's sealed OOS test already opened it (SOT-differential hypothesis, a different question, but the same season's outcomes and market prices have already been examined once). |

**No period in the existing corpus is a pristine holdout for a 1X2-probability-architecture claim.**
Per the operator's explicit permission ("They can be used for architecture development/research
subject to the existing provenance record"), this protocol uses the full 2020/21–2025/26 span for
**architecture selection** via walk-forward validation (§5) — an explicitly different, lower-stakes
use than a final validated claim. **Decision, stated here before any result is seen**: walk-forward
validation inside this exposed corpus is judged sufficient for choosing BETWEEN the four (or five)
candidate architectures — this mirrors exactly how Stage 3B and Tennis A4 always compared candidate
models against each other on development folds before any sealed test existed. It is explicitly
**not** sufficient to make a final, tradable claim about whichever architecture wins: whatever Gate 1
recommends for Gate 2 will still need its own prospective confirmation before real money is involved
(Gates 7–10), and the first genuinely untouched data available for that is **2026/27** (the current
season, already underway as of today but not yet acquired, downloaded, or inspected in any way by
this project — zero exposure risk, because nothing about it has been looked at). This protocol does
not acquire or inspect any 2026/27 data.

## 4. Exact sample construction and eligibility

A match row is eligible for the full four/five-way comparison if, and only if:

1. `full_time_result` is one of H/D/A (all 6,960 raw rows satisfy this — confirmed by audit).
2. A closing multi-bookmaker consensus exists with **≥4 bookmakers** (the existing
   `MIN_BOOKMAKERS_FOR_CONSENSUS` convention from `config/cycle_001_data.yaml`, reused unchanged).
3. Both the home and away team have a **full 10-match rolling history** available
   (`RollingSnapshot.matches_in_window == 10` for the "overall, window=10" split) at kickoff — i.e.
   both teams have already played at least 10 matches, anywhere in the combined chronological
   replay, before this match. Rows failing this are dropped, **never imputed**, exactly matching this
   project's standing convention ("missing rank is flagged, never imputed" — Tennis Cycle 1; the same
   discipline now applied to football's rolling window).
4. No required Model 2/3 feature (§6) is `None`/NaN for either team (a small residual set of matches
   with missing card/corner data even after 10 matches are played — dropped, count reported).

Model 0 and Model 1 use only conditions 1–2 (they do not depend on the 10-match window), so their
eligible sample is slightly larger than Model 2/3's; **all head-to-head comparisons between models
are computed on the intersection of both models' eligible sets for that fold**, so no model is ever
compared on a more favourable sample than another. Exact eligible counts (raw, dropped-by-reason,
final) are reported per fold in the Gate 1 checkpoint, not assumed here.

## 5. Chronological walk-forward design

Six ordered season labels — `["2020_21", "2021_22", "2022_23", "2023_24", "2024_25", "2025_26"]` —
fed to the existing, already-tested `validation.time_splits.generate_expanding_walk_forward_folds`,
producing exactly 5 expanding-window folds:

| Fold | Train seasons | Evaluate season |
|---|---|---|
| 1 | 2020/21 | 2021/22 |
| 2 | 2020/21–2021/22 | 2022/23 |
| 3 | 2020/21–2022/23 | 2023/24 |
| 4 | 2020/21–2023/24 | 2024/25 |
| 5 | 2020/21–2024/25 | 2025/26 |

No random shuffling anywhere. Every model's hyperparameters (Elo's `draw_margin`, the Elo+Poisson
blend weights, Model 2/3's regression coefficients and feature-standardisation statistics) are fit
**strictly on that fold's training seasons only**, then evaluated, unmodified, on that fold's held-out
evaluation season. Elo ratings and Poisson goal-rate state are each computed via **one continuous
replay across all 6 seasons** (both are leakage-safe by construction — see `simulate_pre_match_ratings`
and `simulate_pre_match_lambdas`), so a fold's "training" ratings are simply that continuous replay's
state as of the end of the training seasons; nothing is re-simulated per fold.

## 6. Exact model specifications

### Model 0 — Market Consensus Baseline
Per-outcome closing median consensus from `cycle_001_consensus_full.csv` /
`h_fb2_002_sealed_oos_2025_26_consensus.csv` (`price_timing == "closing"`), **renormalised** to sum
to exactly 1.0 (the three independently-computed outcome medians do not sum to exactly 1.0 by
construction — see `cycle_001_consensus_full.csv`'s own `probability_sum_check` column, typically
0.99–1.01). No fitting, no hyperparameters. **Labelled `market_consensus_baseline_probability`
throughout — never called a "model" in any output table**, per the operator's explicit instruction.

### Model 1 — Existing Frozen Football Model Baseline (Elo + Poisson blend)
Exactly Stage 3B's frozen `"elo_poisson"` blend combination
(`scripts/run_stage_3b_checkpoint4_blends_and_uncertainty.py`), copied verbatim:
- `EloConfig()` — every field left at its frozen default (`initial_rating=1500.0, k_factor=20.0,
  home_advantage=100.0, season_reversion_fraction=0.25`); only `draw_margin` is re-derived per fold,
  via `calibrate_draw_margin` on that fold's training matches only, from the frozen candidate grid
  `[25.0, 50.0, 75.0, 100.0, 125.0, 150.0, 175.0, 200.0]` (copied verbatim from
  `DRAW_MARGIN_CANDIDATES` in `run_stage_3b_checkpoint2_elo.py`).
- `PoissonConfig()` — every field at its frozen default (`max_goals=15, shrinkage_matches=4.0,
  default_league_avg_home_goals=1.5, default_league_avg_away_goals=1.1`). No fold-specific
  calibration (Poisson has no tunable hyperparameter in this codebase).
- Blend weights: `calibrate_blend_weights({"elo": ..., "poisson": ...}, training_actuals, step=0.1)`
  — the exact frozen grid-search method, `step=0.1` copied verbatim from `BLEND_STEP`.

This is re-run through 5 folds instead of Stage 3B's original 3 (its own historical
2021/22–2023/24-development, 2024/25-holdout result is **not modified or overwritten** — this is a
fresh, separate walk-forward pass over an extended season range, exactly as Tennis's frozen Global Elo
was re-derived-and-confirmed, not retuned, for its own 2025 holdout).

### Model 2 — Fundamentals Probability Model
A newly-built module, `models/multinomial_logistic_regression.py` (full-parameterisation softmax
regression, L2-regularised, Adam-optimised, tested — 9 new unit tests, committed alongside this
protocol), fit per fold on 9 features, each individually justified:

| # | Feature | Justification |
|---|---|---|
| 1 | `elo_rating_gap_incl_home_advantage` = `(elo_home_rating + 100) - elo_away_rating` | Single, already-validated summary of relative team strength including home advantage, from the frozen Elo replay (§5) — reuses the fold's own Elo state, not a separate fit. |
| 2 | `diff_avg_goals_for_last10` (home overall-10 − away overall-10) | Recent scoring output differential. |
| 3 | `diff_avg_shots_for_last10` | Recent attacking-volume differential. |
| 4 | `diff_avg_sot_for_last10` | Recent shot-quality/on-target differential — the same statistic Football Cycle 2's H-FB2-002 already found carries some signal (there, in interaction with price band; here, tested as a plain, direct 1X2 predictor). |
| 5 | `diff_avg_corners_for_last10` | Recent territorial-dominance proxy. |
| 6 | `diff_avg_cards_for_last10` | Recent discipline/control differential. |
| 7 | `diff_points_per_game_last10` | Recent underlying results form, independent of the above process statistics. |
| 8 | `is_E1` (competition dummy, E0 baseline) | Controls for the Championship's own base-rate/style differences. |
| 9 | `is_SC0` (competition dummy, E0 baseline) | Controls for the Scottish Premiership's own documented calibration difference (Football Cycle 2 discovery, §20 of the roadmap). |

Deliberately excluded: fixture congestion/rest (no such feature has been built anywhere in this
repository yet — a real gap, not silently worked around, noted in the checkpoint as a genuine
limitation); the raw 157-column discovery file's every other column (home/away-context splits,
5-match windows, goal-difference volatility, conversion rate) — including all of them would violate
the operator's explicit "do not indiscriminately include all 157 columns" instruction; a future,
separately-justified Gate 1b could test whether any of these adds information once this baseline
architecture comparison is done.

Rows are standardised (z-score, training-fold mean/std only) internally by the fitting function
itself; L2 penalty fixed at the module's documented default (`1e-3`) for every fold — **not tuned
per fold**, since introducing a per-fold hyperparameter search here would itself be a new source of
overfitting this Gate 1 comparison is trying to avoid, and the model class is intentionally simple
enough not to need one.

### Model 3 — Market + Fundamentals
Exactly Model 2's 9 features, plus 2 more:

| # | Feature | Justification |
|---|---|---|
| 10 | `market_home_logit` = `ln(consensus_home_closing / consensus_away_closing)` | Market information expressed in logit space so a linear model can weigh it against the fundamentals features on a comparable scale. |
| 11 | `market_draw_logit` = `ln(consensus_draw_closing / consensus_away_closing)` | As above, for the draw outcome. |

"Away" is used as the reference outcome for both logits arbitrarily — mathematically, any reference
class carries the same information (two independent log-ratios of a 3-outcome vector fully determine
it up to normalisation), so this choice is stylistic, not consequential, and is stated here to
pre-empt exactly that question.

### Model 4 — Calibrated Ensemble (bonus; Architecture D)
`models.football_blended.calibrate_blend_weights({"market": Model0_probs, "fundamentals":
Model2_probs}, training_actuals, step=0.1)` on each fold's training predictions, applied unchanged to
that fold's evaluation predictions. Uses only already-tested blend code (§2, `football_blended.py`);
no new model class.

## 7. Leakage and circularity risks, and how each is controlled

1. **Same-match statistic leakage** (a match's own shots/SOT/corners/cards used to predict its own
   outcome): impossible by construction — `compute_rolling_features` only ever exposes a team's
   PRIOR matches (see its own docstring and `tests/unit/test_football_leakage_safe_features.py`'s
   mechanical perturbation tests, unmodified and reused here).
2. **Cross-fold leakage** (a later season's outcomes influencing an earlier fold's training): impossible
   by construction — expanding walk-forward folds only ever train on seasons strictly before the
   evaluation season; `check_chronological_order` (used inside both `simulate_pre_match_ratings` and
   `simulate_pre_match_lambdas`) raises if any input is out of order.
3. **Hyperparameter leakage** (`draw_margin`, blend weights, or the Model 2/3 regression fit trained on
   data outside that fold's training seasons): controlled by construction — every fitting call in the
   Gate 1 script is passed only that fold's training-season rows; the evaluation season's rows are
   never seen by any `fit_*`/`calibrate_*` call for that fold.
4. **Consensus-vs-target-price circularity** (the specific risk the operator raised: comparing a
   consensus probability to a bookmaker price that helped build that same consensus). **This risk
   does not apply to Gate 1** as scoped: every Gate 1 metric compares a model's probability against
   the REALISED MATCH OUTCOME (log loss, Brier, calibration), never against one specific target
   bookmaker's price. Leave-one-bookmaker-out consensus construction becomes necessary only once this
   architecture is used to size an EV against one specific venue's current price (Gate 5/6 territory,
   not Gate 1) — flagged here explicitly, not silently deferred. Bookmaker panel coverage by season is
   already documented (Football Cycle 2 §20 of the roadmap): the 1X2 consensus uses a 6-bookmaker
   panel with full-corpus coverage; Over/Under 2.5 and Asian Handicap (out of scope for Gate 1) are
   Bet365+Pinnacle only.
5. **Selection-on-the-dependent-variable in feature choice** (choosing Model 2/3's 9 features by
   peeking at which ones predict the outcome well): controlled by fixing the feature list in this
   document, committed BEFORE any fold is evaluated — the 9 features are chosen for their prior
   research/domain justification (§6's table), not by a preliminary correlation screen.
6. **Standardisation leakage** (a feature's mean/std computed using evaluation-season rows): controlled
   inside `fit_multinomial_logistic_regression` itself, which computes `feature_means`/`feature_stds`
   only from the rows passed to it (that fold's training rows) and stores them on the fitted model for
   `predict_proba` to reuse unchanged on evaluation rows.

## 8. Evaluation metrics and what would justify each architecture

Per outcome (home/draw/away) and pooled (multiclass), for every model, on every fold's evaluation
season, and pooled across all 5 folds:

- Multiclass log loss and Brier score (`performance/log_loss.py`, `performance/brier.py` — unchanged).
- Per-outcome (one-vs-rest) calibration: raw equal-count bins, ECE, calibration intercept/slope, AUC
  (`performance/binary_classification.py` — unchanged; applied once per outcome, treating that
  outcome as the binary "did it happen" indicator).
- Temporal stability: the same metric reported separately per fold/evaluation season (not just pooled).
- Competition stability: the same metric reported separately per competition (E0/E1/SC0), pooled
  across all out-of-sample folds.
- Pairwise comparisons with uncertainty: `performance.bootstrap.paired_bootstrap_mean_diff` (new,
  tested — 9 unit tests, committed alongside this protocol), n_resamples=2000, **seed=20260918** fixed
  in advance, on pooled per-match log loss and per-match Brier score, for: Model 1 vs Model 0, Model 2
  vs Model 0, Model 3 vs Model 0, Model 3 vs Model 2, Model 4 vs Model 0.

**Decision rule, stated before any result is seen**: no single metric crowns a winner and no composite
score is invented. Per the operator's explicit instruction, an architecture is not rejected merely for
a small, statistically inconclusive log-loss disadvantage against the market baseline; conversely, a
small improvement is not accepted as proof of a usable architecture without also checking calibration,
temporal stability, and competition stability hold up (an architecture that "wins" pooled log loss by
being erratic across seasons/competitions is a materially different, weaker result than one that wins
consistently). Recommending Gate 2's architecture is therefore a qualitative judgement made in the
checkpoint document, informed by every metric in this section together — not a mechanical largest/
smallest-number rule.

## 9. What is explicitly out of scope for Gate 1 (restated from the operator's instruction)

No production Daily Engine implementation. No Over/Under 2.5 or Asian Handicap modelling. No new paid
or free data acquisition. No Cricket. No bet placed, no paper trade, no betting threshold optimised.
No change to any existing scientific verdict (Stage 3B, H-FB2-001, H-FB2-002, Tennis Cycle 1,
Tennis Workstream B). Gate 2 (freezing a single architecture) requires its own operator approval after
this checkpoint.
