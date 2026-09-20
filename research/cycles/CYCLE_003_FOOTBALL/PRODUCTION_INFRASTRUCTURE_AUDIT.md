# Production Infrastructure Build -- Audit + Commissioning (2026-09-20)

Operator instruction: "MAJOR NEXT PHASE -- PRODUCTION INFRASTRUCTURE
BUILD -- GITHUB AUTOMATION + CHATGPT HANDOFF." This document is Section
1's KEEP/MODIFY/ADD/DEPRECATE audit plus Section 17's commissioning
checklist, for the same build this session's return checkpoint (chat)
summarises at a higher level.

## KEEP / MODIFY / ADD / DEPRECATE

### KEEP (working, not touched)
- `decisions/grading.py` -- tested threshold logic; the payout floor is a
  separate, additive gate (`decisions/payout_policy.py`), not a rewrite.
- `decisions/confidence.py`, `decisions/data_quality.py`,
  `decisions/liquidity.py` -- unchanged.
- `probability/consensus.py`, `probability/market_pipeline.py`,
  `ev/expected_value.py` -- unchanged; the probability/EV core.
- `ingestion/the_odds_api_loader.py` -- unchanged; the odds side of the
  live adapter, already live-tested (2026-09-19).
- `storage/paper_ledger.py` -- unchanged; its immutability-enforcing
  `settle_paper_bet` is *reused*, not reimplemented, by the new
  automated settlement runner.
- `scripts/settle_results.py`, `storage/schemas.BetRecord`,
  `storage/csv_store.py` -- the existing real-money settlement/ledger
  primitives (Section 6/16). Already correct and tested; only their
  *location convention* changes (see MODIFY below), and one new thin
  entry point (`scripts/record_real_bet.py`) is layered on top.
- `performance/calibration.py`'s `compute_calibration_bins` -- generic
  binary calibration, reused as-is for the new performance report rather
  than duplicated.
- `daily_cards/` contract shape (`card.json`/`card.csv`/`card.md`) --
  frozen 2026-09-19, unchanged this build.
- `.github/workflows/daily_scan.yml`'s core scan step and
  `tests.yml` -- unchanged except the additions noted under MODIFY.

### MODIFY (extended additively, tests re-run to confirm no regression)
- `config/thresholds.yaml` -- appended a `payout_policy` section (Section
  3). Nothing existing removed or renumbered.
- `decisions/recommendation.py` -- `build_recommendation` gained one new
  optional kwarg (`payout_policy_thresholds`, defaulted) applied *after*
  `grade_opportunity` returns, demoting an actionable grade to C if the
  price is below the configured floor. Every existing call site and test
  is unaffected by the default.
- `scripts/run_daily_scan.py` -- loads and passes the new payout-policy
  thresholds through; no other behaviour changed.
- `performance/roi.py`, `performance/drawdown.py` -- these were literal,
  explicitly-labelled Stage 1 placeholders ("intentionally contains no
  logic yet"). Filling them in is not a rewrite of working code; it is
  finishing a component the project itself deferred.
- `.github/workflows/daily_scan.yml` -- added a `concurrency` group
  (shared with the new settlement workflow, so their automated commits
  cannot race each other) and a final `if: always()` system-status
  update step, so a scan failure is now visible to ChatGPT as a failure,
  not silently indistinguishable from "nothing qualified."
- Real-money bet ledger location: previously implied to live under
  `data/processed/` (gitignored except `football/`, so a real bet record
  placed there would never reach GitHub). Relocated to `real_bets/` at
  the repo root, the same committed-by-design placement already used for
  `paper_ledger/` and `daily_cards/`. `scripts/settle_results.py` itself
  needed no code change -- it already takes `--bets`/`--bankroll` as
  arguments.
- `docs/GITHUB_TO_CHATGPT_HANDOFF_DESIGN.md` -- extended to reference the
  new `reports/latest_performance.json` and `status/latest.json` outputs.

### ADD (new)
- `decisions/payout_policy.py` -- the minimum-odds/payout-floor policy
  (Section 3).
- `performance/odds_bands.py` -- the odds-band bucketing used by the
  payout policy's own evidence-gathering purpose and by the new
  performance report.
- `performance/paper_bet_metrics.py` -- binary Brier score / log loss for
  a single graded selection (distinct from the existing 3-outcome
  research modules -- see that module's docstring).
- `ingestion/the_odds_api_scores.py` -- the results/scores adapter
  (Section 7), the direct counterpart to the existing odds adapter.
- `settlement/market_settlement.py`, `settlement/settle_paper_ledger.py`
  -- the deterministic, idempotent automated settlement engine (Section
  7), reusing `storage.paper_ledger.settle_paper_bet` for the actual
  write.
- `performance/paper_performance.py` -- builds the
  `reports/latest_performance.json` contract (Section 8).
- `reports/system_status.py` -- the `status/latest.json` contract
  (Section 12).
- `scripts/run_settlement.py`, `scripts/generate_performance_report.py`,
  `scripts/generate_system_status.py`, `scripts/record_real_bet.py` --
  the CLI entry points for the above.
- `.github/workflows/settlement_and_performance.yml` -- the evening
  settlement + performance + status job (Section 9, jobs C/D combined
  into one workflow per "avoid unnecessary workflow complexity").
- `real_bets/README.md` -- documents the Track A / Track B separation.
- `docs/EXECUTION_ARCHITECTURE_FUTURE.md` -- Section 14, documentation
  only, nothing enabled.
- 12 new test files (`tests/unit/test_payout_policy.py`,
  `test_recommendation_payout_floor.py`, `test_odds_bands.py`,
  `test_roi.py`, `test_drawdown.py`, `test_paper_bet_metrics.py`,
  `test_the_odds_api_scores.py`, `test_market_settlement.py`,
  `test_settle_paper_ledger.py`, `test_paper_performance.py`,
  `test_system_status.py`).

### DEPRECATE
- None. Nothing built in prior phases was superseded by this build --
  see the master research directive's own "superseded objectives should
  be marked superseded, never silently deleted" rule; there is nothing
  to mark here because nothing was replaced.

## Section 17 commissioning checklist

1. **Full test suite** -- 852/852 passing (804 pre-existing + 48 new)
   after this build, on the same `.venv` used throughout this project.
2. **Live Odds API smoke test** -- not re-run this session (no new API
   surface was added to the *odds* side; the scores endpoint,
   `ingestion.the_odds_api_scores.fetch_scores_raw`, is NOT YET
   LIVE-TESTED against a real response -- stated in that module's own
   docstring, matching the project's existing honesty discipline for a
   newly-built adapter). The first real `scripts/run_settlement.py` run
   (this evening, via the new scheduled workflow, or manually) is that
   live-test moment.
3. **Real daily scan** -- not re-run this session to avoid spending
   additional API credits; the existing 2026-09-19 real card remains the
   evidence for the scan path, now with the payout floor wired in (not
   exercised against live data yet -- today's real card was generated
   before this build).
4. **Paper bet creation** -- exercised via the full test suite
   (`test_settle_paper_ledger.py`'s fixtures build real
   `RecommendationResult`s through `build_recommendation` and record them
   with `record_qualifying_candidates`), not against a fresh live scan
   this session.
5. **card.json verification** -- unchanged contract, already verified
   2026-09-19; not re-verified this session since the contract itself
   was not modified.
6. **Settlement test with fixtures** -- `test_settle_paper_ledger.py`
   covers: a completed event settling correctly with the right P&L, an
   event not yet completed staying pending, a contract-backfilled bet
   correctly reported as unresolvable, and an event missing from the
   scores window being reported as such.
7. **Idempotency test** -- `test_idempotent_second_run_does_not_resettle`
   confirms a second settlement run does not alter an already-settled
   bet's P&L or double-pay it.
8. **Performance reporting test** -- `test_paper_performance.py` covers
   basic totals, pending-bet exclusion, grade/odds-band breakdowns, void
   handling, and an empty ledger.
9. **System status test** -- `test_system_status.py` covers the
   dataclass-to-dict shape; the CLI's card.json-reading fallback and
   field-carry-forward logic were exercised manually (dry run, see
   below), not unit-tested directly (script-level, not library-level --
   consistent with this project's existing script/library test split).
10. **Manual `workflow_dispatch` test** -- not performed this session
    (requires pushing this commit to GitHub first, which happens after
    this return checkpoint, per the established pattern in this
    project). Flagged as Fraser's next manual action.
11. **Production artefacts verification** -- dry-run performed locally
    this session: `scripts/generate_performance_report.py` against the
    real (all-pending) `paper_ledger/paper_bets.csv` produced a valid,
    honestly-empty `reports/latest_performance.json`;
    `scripts/generate_system_status.py` produced a valid
    `status/latest.json`; `scripts/run_daily_scan.py --source manual`
    (against the existing template files, `--no-paper-ledger`, a
    throwaway `--run-label`, deleted afterward) ran end-to-end without
    error.
12. **No secrets in logs** -- every new script reads `THE_ODDS_API_KEY`
    exclusively via `TheOddsApiConfig.resolve_api_key()` (the same,
    unchanged, environment-only mechanism the existing odds adapter
    uses); no new script prints, logs, or writes the key anywhere.

**Zero qualifying bets, and an unexercised live scores call, are both
valid, honestly-reported states at this checkpoint** -- per Section 17's
own "do not loosen thresholds merely so a paper bet appears" and this
project's standing "negative results must remain recorded" rule.
