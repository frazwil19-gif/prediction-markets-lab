# Phase 2 -- Independent Feature Inventory (Section 4)

**Written 2026-09-22, in response to the operator's "PHASE 2 -- INDEPENDENT FOOTBALL PROBABILITY
MODEL RESEARCH" instruction, relayed by Fraser immediately after Backtest Phase 1 (§22 of the master
research directive).** Audits actual repository files, not assumed availability, per the instruction's
explicit "do not assume availability -- audit actual files."

## Headline finding

**Almost everything this section asks to inventory already exists, was already built for Gate 1
(§15 of the master research directive, 2026-09-18), and was already tested end-to-end in a
chronological walk-forward comparison against market consensus.** This audit does not discover new
raw material; it confirms what is already there and what is genuinely still missing.

## Feature-by-feature inventory

| Predictor | Available? | Source file | Coverage | Leakage-safe? | Known before kickoff? | Already tested? |
|---|---|---|---|---|---|---|
| Team Elo (pre-match rating, home advantage, draw margin) | YES | `src/prediction_markets_lab/models/football_elo.py` (`simulate_pre_match_ratings`) | All 6,960 matches, E0/E1/SC0, 2020/21-2025/26 | YES -- continuous chronological replay, pre-match snapshot only, mechanically tested (`tests/unit/test_football_elo.py`) | YES | YES -- Gate 1 Model 1, and originally Stage 3B |
| Poisson attack/defence lambdas | YES | `src/prediction_markets_lab/models/football_poisson.py` (`simulate_pre_match_lambdas`) | Same as Elo | YES -- same replay discipline (`tests/unit/test_football_poisson.py`) | YES | YES -- Gate 1 Model 1, Stage 3B |
| Rolling goals for/against (last 5, last 10) | YES | `data/processed/football/cycle_002_discovery_features.csv` (built by `features/football_leakage_safe_features.py`) | All 5,800 Cycle 1 matches with >=10 (or 5) prior matches for both teams | YES -- expanding/rolling prior-observations-only, snapshot-before-push discipline, mechanically tested | YES | YES -- Gate 1 Model 2/3 |
| Rolling shots for/against | YES | same file | same | YES | YES | YES -- Gate 1 Model 2/3 |
| Rolling shots on target for/against | YES | same file | same | YES | YES | YES -- Gate 1 Model 2/3 |
| Rolling corners for/against | YES | same file | same | YES | YES | YES -- Gate 1 Model 2/3 |
| Rolling cards for/against (yellow+red combined) | YES | same file | same | YES | YES | YES -- Gate 1 Model 2/3 |
| Rolling conversion rate, points-per-game, goal-diff volatility | YES | same file | same | YES | YES | Points-per-game used in Gate 1; conversion rate and goal-diff volatility built but NOT used in Gate 1's 9-feature set |
| Home/away split context (separately for home-context and away-context rolling windows) | YES | same file (`*_homecontext_*`, `*_awaycontext_*` columns) | same | YES | YES | NOT used in Gate 1 -- Gate 1 used only the `*_overall_*` rolling windows |
| Recent form (last 5 vs last 10 window) | YES | same file | same | YES | YES | Only last-10 used in Gate 1; last-5 columns exist but untested |
| League position computed from only prior matches | NO -- not built as its own feature | -- | -- | would be leakage-safe if built (table-before-match is a standard, well-understood construction) | YES | NOT tested anywhere in this repo |
| Goal difference computed from only prior matches | PARTIAL -- `goal_diff_volatility` (a rolling dispersion measure) exists; a running seasonal goal-difference-to-date does not | -- | -- | -- | -- | NOT tested |
| Rest days / fixture congestion | NO -- not built anywhere in this repository | -- | -- | -- | -- | Explicitly flagged as unbuilt by Gate 1's own point 33 |
| Promoted-team status | NO -- not built | -- | -- | would be leakage-safe (known at season start) | YES | NOT tested |
| Season stage (early/mid/late) | NO -- not built as a feature, though `home_team_appearance_number`/`away_team_appearance_number` (an ordinal match count within the dataset) exists and could proxy it crudely | -- | -- | -- | -- | Appearance number used only for eligibility filtering (has this team got 10 prior matches yet), never as a model input |
| Referee identity | RAW DATA ONLY | `data/processed/football/cycle_002_match_statistics.csv` (`referee` column) | All matches with statistics | Known before kickoff for real fixtures (referees are usually appointed a few days ahead) -- but in this repo the field is same-match metadata, never turned into a referee-level historical statistic (e.g. "this referee's cards-per-game rate") | Nominally yes in reality, though the appointment timing itself is not modelled here | NOT built into any feature, NOT tested |
| Opponent strength (distinct from Elo) | NO -- Elo rating gap already captures this; no separate opponent-strength feature exists | -- | -- | -- | -- | -- |
| xG (expected goals) | NO -- not acquired anywhere in this repository | -- | -- | -- | -- | Explicitly flagged as not-acquired by Gate 1's own point 33 |
| Poisson/Dixon-Coles style scoreline model | YES (Poisson; no Dixon-Coles low-score correlation adjustment) | `models/football_poisson.py` | same as Elo | YES | YES | YES -- Gate 1 Model 1 |
| Existing Elo/Poisson blend (production-frozen weights) | YES | `models/football_blended.py` | same | YES | YES | YES -- Gate 1 Model 1, Stage 3B |

## What this means for Phase 2

The instruction's Section 4-10 ask (inventory features, separate model families A/B/C/D, target the
actual match outcome, chronological design, avoid leakage, test sensible models) describes **exactly
the experiment Gate 1 already ran**, using precisely the fundamentals feature subset that was
justified and available at the time (9 features: Elo gap, 5 rolling-differential stats over a
last-10 window, points-per-game differential, 2 competition dummies). Re-running that same comparison
from scratch, on the same data, with the same feature set, would be repeated retesting on an
already-answered question -- exactly what the project's own scientific-method discipline (master
directive §7) warns against ("avoid... repeated retesting until something passes").

**What genuinely was NOT tested by Gate 1, and is listed above as available-but-unused:**
home/away-context-specific rolling windows (rather than combined overall form), the last-5 window
(only last-10 was used), conversion rate, and goal-diff volatility. These represent a legitimate,
narrower FUTURE research question ("does a richer slice of the SAME already-available data close any
of the gap"), not the Phase 2 question as asked ("can independent pre-match information improve
probability estimation") -- that question already has an answer (see `EXPERIMENT_PLAN.md` and
`PHASE2_RETURN_CHECKPOINT.md`).

**What is genuinely unavailable and would require new acquisition:** xG, rest-days/fixture-congestion,
promoted-team status as an explicit flag, league-position-before-match as an explicit feature,
referee-level historical statistics, and a Dixon-Coles low-score correlation adjustment to the Poisson
model. None of these were purchased or acquired in this phase, per the instruction's explicit "do not
purchase anything" and "audit actual files" instructions.
