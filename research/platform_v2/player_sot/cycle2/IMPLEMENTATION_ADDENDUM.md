# Player SOT cycle 2 — implementation addendum (written 2026-10-07, BEFORE any 2022/23 player data is received)

This file pins down details the pre-registration (`PREREGISTRATION.md`) leaves open. It is committed before the 2022/23
API-Football files reach this workspace. Nothing in the pre-registration is changed.

## Data handling
- Only `players_2022_*.json.gz` and `fixtures_39_2022.json.gz` are read. Holdout seasons (2023/24, 2024/25) are not
  present in this workspace; they are processed only at the one-time holdout opening.
- Raw and player-level rows stay private (workspace / `data/private/`, gitignored). Only aggregates are committed.
- Canonical rows are built with the existing `scripts/api_football_acquire.py::rows_from_fixture` (unchanged).

## Phase 1 gate — interpretations
- "11 starters in ≥ 99% of team-matches", "duplicates = 0", "SOT ≤ shots and goals ≤ SOT violations < 0.1%": as
  computed by `research_shadow/player_sot.audit` (unchanged).
- **Minutes coverage ≥ 99%:** the share of player-match rows with a non-missing, positive `minutes` value, among
  players who appeared. Unused substitutes are excluded by construction.
- **Team SOT vs Football-Data HST/AST within ±5%:**
  - Source: Football-Data E0 2022/23, via the xgabora `Matches.csv` `HomeTarget`/`AwayTarget` columns, which are
    Football-Data HST/AST.
  - Fixtures are matched on date (±1 day) and both team names, mapped by an explicit name table written in the code.
    Unmatched fixtures are reported, never guessed.
  - Statistic: the ratio of mean team SOT per team-match (API-Football player sum ÷ Football-Data) over matched
    fixtures must lie within [0.95, 1.05]. The per-team-match exact-agreement share and mean absolute difference are
    reported, not gated.
  - The gate also requires ≥ 95% of the 380 fixtures to be matched.

## Phase 2 — order of operations
1. Population: outfield starters (role ≠ GK, role ≠ UNK) with ≥ 3 prior appearances in the data. TRAIN = 2022/23
   matches before 2023-02-01; DEV = from 2023-02-01.
2. **Family forward selection (structure S1, target sot_1plus):**
   - start from intercept only;
   - at each step add the family giving the largest DEV log-loss reduction;
   - stop when no family improves by ≥ 0.0005.

   Families, as in the pilot:
   - F_player: log1p(shrunk SOT/90), log1p(shrunk shots/90);
   - F_starts: prior starts share;
   - F_role: MD and FW dummies (DF = reference);
   - F_team: log team prior SOT for;
   - F_opp: log opponent prior SOT conceded;
   - F_home.
3. **Structure comparison on the selected families:**
   - S1: one logistic model; role dummies only if F_role was selected.
   - S2: S1 plus role dummies plus role × (each selected one of F_player's SOT/90 term, F_team, F_opp) interactions.
   - S3: separate logistic models per role (DF/MD/FW) on the selected families, minus the role dummies.

   Choose by DEV sot_1plus log loss over all outfield starters. The simpler structure wins within 0.0005
   (S1 < S2 < S3).
4. **Baselines:**
   - B0: role rate;
   - B1: pilot player-rate Poisson;
   - B2: B1 recalibrated by logistic intercept/slope fitted on TRAIN predictions of B1.

   Comparator = the lowest DEV sot_1plus log loss among B0–B2.
5. `sot_2plus` uses the same selected families and structure, fitted separately (reported, not used for selection).
6. **Frozen spec:** FROZEN_SPEC.json records families, structure, comparator and the refit rule (refit on all of
   2022/23 for the holdout). It is committed before the holdout is acquired in full or opened.

Shrinkage, the ridge and the IRLS fitting are identical to the pilot (`scripts/player_sot_pilot.py`):
SHRINK_MINUTES = 450, ridge 1e-6.
