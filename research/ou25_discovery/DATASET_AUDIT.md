# Gate 1b (Football O/U 2.5) -- Dataset Audit

**Source file (only file read, unmodified)**: `data/processed/football/cycle_002_discovery_features.csv`
-- Cycle 2's existing leakage-safe pre-match feature build (`scripts/run_cycle_002_leakage_safe_features.py`),
already frozen and used by Gate 1 (1X2), Phase 2, and the Outcome Discovery cycle. Nothing was refetched,
recomputed upstream, or purchased to build this cycle's dataset.

## Coverage

- Total rows: 5,800 (E0/E1/SC0, 2020/21-2024/25)
- Rows with a resolvable match result (home/away full-time goals present): 5800 (100%)
- Rows usable for the full three-way model comparison (market probability present AND all 19
  fundamentals features present AND result present): 5,759 (99.3%) -- the small shortfall is entirely
  missing fundamentals coverage in a team's earliest appearances in the window (last-10 rolling
  features need history to exist), not missing outcomes or market data
- By partition: discovery (2020/21-2022/23) 3480, validation (2023/24)
  1160, holdout (2024/25) 1160

## Target construction

`target = 1 if (outcome_full_time_home_goals + outcome_full_time_away_goals) > 2.5 else 0`. Both goal
columns are 100% present for every row in this file (0 missing) -- Over/Under 2.5 is a strictly easier
target to build than 1X2's three-way outcome, needing no join beyond this single file. Base rate: Over
2.5 occurred in 50.10% of all 5,800 matches (2,906/5,800) -- a well-balanced target, favourable for a
clean AUC/log-loss comparison.

## Fields used

**Market-only (Model A), research-grade, thin-panel**: `market_ou25_closing_source_avg_over_probability`
(a de-vigged average across whichever 2-3 bookmakers quoted a closing O/U 2.5 price for that match --
already computed and stored in this file by Cycle 2's own richer-extraction step, `individual_bookmaker_
count` field confirms the panel depth per match). This is EXPLICITLY a research-grade probability, not
the production-grade `min_bookmakers=3` consensus the live daily scanner requires -- see
`research/data_expansion/EXHAUSTED_VS_OPEN_RESEARCH.md` for why the production consensus file for this
market (`cycle_002_consensus_ou25.csv`) is 0 bytes. Never conflated with a production consensus anywhere
in this cycle's code or documentation.

**Fundamentals (Model B), 19 features**: home/away team last-10-match rolling averages of goals for,
goals against, shots for, shots against, shots-on-target for, shots-on-target against, corners for,
corners against, and points-per-game (18 features), plus the pre-match Elo rating gap including home
advantage (1 feature) -- all already leakage-safe by construction in the source file (see Leakage
Audit). Cards and the last-5 window were deliberately excluded (weakest, least goal-relevant signal per
the Outcome Discovery cycle's own winner/loser findings on the same underlying features).

**Combined (Model C)**: the 19 fundamentals features plus the market probability as a 20th feature.

## Data quality notes

- No fabricated or imputed values anywhere -- a candidate missing any required field for a given model
  is excluded from that model's fit/evaluation (not zero-filled), following this project's standing
  no-silent-imputation rule.
- Season coverage stops at 2024/25 -- the same gap already documented for 1X2 in the Outcome Discovery
  cycle (`research/outcome_discovery/HOLDOUT_REPORT.md`): 2025/26 raw match/statistics files exist in
  the repository (untracked) but have not yet been run through the upstream Cycle 1/Cycle 2 acquisition
  and feature-engineering pipeline. This was NOT fixed in this cycle (out of scope -- extending that
  pipeline is a separate, already-identified future task, not a Phase-4 market-selection question).
