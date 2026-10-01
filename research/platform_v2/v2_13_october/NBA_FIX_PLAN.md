# V2-13 Track E — NBA bounded fix plan (implement by 17 Oct; activation stays 20 Oct as configured)

**Scope:**
- Implementation fixes only. The frozen engine `nba_moneyline.market` v1 is unchanged: the estimator is the mean decimal odds per side over ≥3 non-exchange UK books, then 2-way proportional de-vig. The ledger_version is unchanged and the activation date is unchanged.
- Deliver as a separate branch and commit from football, with its own tests.
- Nothing is activated early. Registry `collectable()` already refuses before 2026-10-20 (tested).

| # | Fix | Where | Design | Tests | Effort |
|---|---|---|---|---|---|
| 1 | **Actual bookmaker source encoding** | `adapters.nba_from_odds` | `live_src = f"odds_api:{book_key}"` for the book giving `max(odds)` on the predicted side, ties broken by key. The price snapshot is the same response, so it is same-snapshot by construction. `prices.from_ledger_row` then parses it like football. | Ledger row → `PriceSnapshot` with the right book and odds; Stage B evaluates instead of NO_EXECUTABLE_PRICE. | S |
| 2 | **Uncertainty** | `config/prediction_board_stage_a.yaml` + `stage_a` provider | Band SE from `research/platform_v2/nba/NBA_PROBABILITY_BANDS.csv` (holdout, n = 2,629): Wilson half-width/1.96 per coarse band (50–65 / 65–80 / 80+). Effective N = games, with one row per game. Labelled `HIST_BAND_WILSON_SE (closing estimator; early-snapshot bias excluded)`. Pre-registered before 20 Oct. | Band lookup, label, NOT_ESTIMATED outside the evidence. | S |
| 3 | **Favourite-flip duplicate prevention** | `run_unified_prediction_board.collect_nba` / `record` | `prediction_id` includes the selection, so a later scan with the other favourite appends a second row. Rule `FIRST_SCAN_WITHIN_36H`: skip any game whose `event_key` already has an NBA row (reason `ALREADY_PREDICTED_FIRST_SNAPSHOT_CANONICAL`). | Two scans with a flipped favourite → 1 row; skip counted. | S |
| 4 | **Quote freshness** | `nba_from_odds` | Exclude books whose `last_update` is older than the existing `STALE_AFTER` (6h, the same constant football uses) before the ≥3-book check. | A stale book is excluded; fewer than 3 fresh books → DATA_INVALID. | S |
| 5 | **Minutes-to-tip provenance** | already in schema (`minutes_to_event`) | Add `snapshot_bucket` to the NBA rows' Stage A display, and the performance timing buckets (already reported at n ≥ 100). Record `configured_scan_time` vs actual start (exists). | Bucket assignment. | XS |
| 6 | **Exhibition filtering** | `nba_from_odds` | Accept only events whose home and away teams are both in the 30-franchise list (from `NBA_DATA_SCHEMA.md` team identity map). All-Star, Rising Stars and international exhibitions are skipped (`NOT_REGULAR_COMPETITION`). Preseason is already excluded by the 20 Oct date gate. Playoffs and play-in are kept (they were in the holdout). | All-Star style event skipped; a regular game kept. | S |
| 7 | **Settlement-window resilience** | `run_unified_prediction_board.settle` | Every **2nd** day (`daysFrom=3` gives one day of overlap) instead of every 3rd. Add an overdue report for NBA games unsettled more than 3 days after tip (`REVIEW_REQUIRED`, never guessed). Optional free fallback (needs network allow-listing): NBA public scoreboard JSON, to be evaluated separately. Scores must use final scores, including OT (assert `completed` and that both scores are present). | Cadence; an overdue game is flagged; OT final accepted. | S |

**Credit impact:** odds 1/day plus scores every 2nd day (2 credits) ≈ 30 + 30 = **60/month**, at the cap. Under Plan A (see CREDIT_AUDIT.md) the floor drops to 100.

**Known methodological limits (not fixes):**
- The live snapshot is ~17–21h before tip, while the validated price is the close.
- **The prospective period is the test of the early-snapshot estimator.** The holdout's calibration (≥80%: 85.5% predicted → 87.5% actual, n = 550) is **not** transferred. The registry `calibration_status` says so.
- `money_eligible` stays **false**. Promotion is evidence-based (FOOTBALL_PROSPECTIVE_PREREGISTRATION.md §5 / PROSPECTIVE_PROTOCOL §5–6), never by elapsed time.

**Provenance housekeeping:** add an erratum to `NBA_RETURN_CHECKPOINT.md`. It cites commit hashes `12561fc` and `abc2b87`, which don't exist; the real ones are `a047ab1` → `8083a43` → `1cd2259`.

**Timeline:**

| Date | Step |
|---|---|
| By 10 Oct | Fixes 1, 3, 4 and 6 (+ tests) |
| By 14 Oct | Fixes 2, 5 and 7 + pre-registration |
| By 17 Oct | Review / merge |
| 20 Oct | Automatic activation |
