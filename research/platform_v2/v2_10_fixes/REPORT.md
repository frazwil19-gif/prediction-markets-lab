# V2-10 — Approved corrective changes A (start time) and B (Stage A completeness)

Status: implemented on branch `v2-10-start-time-and-stage-a` (from master `18f0747`). **Not merged.**
Scope: exactly the two approved changes. No threshold, engine, V2-7 (cer-2), bsv2-3, V2-8, settlement, multi or money change.
Reproduce the diagnostic: `python scripts/v2_10_reconstruct_30sep.py` → `RECONSTRUCTION_30SEP.json` (inputs read with
`git show` at the production commits; no outcomes; 0 API calls).

## A. Rescheduled start-time defect (rule `est-1`)

**Root cause.**
- The tennis prospective ledger records one prediction per event, with the provider `commence_time` seen at the FIRST scan.
- `predictions/unified_ledger.csv` mirrors that ledger via `append_unique` on `prediction_id`, so the first-seen start is never updated. This is correct, because it is append-only history.
- The Odds API frequently lists a match with a placeholder start (e.g. 02:00) and moves it later.
- Two consumers used the ledger start as the "current" start:
  - `scripts/run_bet_selection_v2.py` (`upcoming = event_start > now`);
  - `prediction_platform/board.py` (same filter).
- A future match whose first-seen placeholder was in the past was therefore silently dropped, with no reason code.
- The same stale value also fed bsv2-3's `minutes_to_event`, so the 24h horizon check could be wrong in either direction.

**Implementation (`src/prediction_markets_lab/prediction_platform/event_times.py`):**
- **Observations.** Every file that records a provider start at a known observation time is a start observation. These are `tennis_predictions/probability_snapshots.csv` and `exchange_probability_snapshots.csv`, both written every scan and append-only. The ledger row itself is also an observation, taken at its `prediction_timestamp`.
- **Current start.** The current start is the start carried by the most recently observed valid observation.
- **Invalid observations** (unparseable times) are ignored and counted, never guessed.
- **Conflicts.** Two different starts at the same latest observation time give `START_TIME_CONFLICT`. The event is excluded with that reason (fail closed).
- **Overlay, never rewrite.** Consumers receive a copy of each prediction with `event_start` set to the current start. `event_start_original`, `start_time_status` (`UNCHANGED | RESCHEDULED | LEDGER_ONLY | START_TIME_CONFLICT`) and `start_time_source` are added alongside. **No ledger row is rewritten.**
- **Explicit exclusions.** Every prediction gets a machine-readable resolution row: `ELIGIBLE`, or `EXCLUDED` with reason `EVENT_STARTED`, `START_TIME_CONFLICT` or `START_TIME_INVALID`.
  - Bet-selection writes these rows to `reports/bet_selection_v2_start_time_resolution.csv`.
  - The unified board JSON carries `start_time_resolution` counts.
- **Old behaviour preserved without provider observations.** When no provider observation exists (`LEDGER_ONLY`), behaviour is identical to the old filter; a test asserts this.

**Wiring (minimal):**
- `run_bet_selection_v2.evaluate` now uses `ET.apply(...)` instead of the old filter, and writes the resolution CSV.
- `board.build` takes an optional `start_index`. The board schema goes 1 → 2, adding three start-time columns and a ⟳ marker in the Markdown.
- `run_unified_prediction_board.build` loads the index once.
- The workflow commit lists gain the new output paths (per-path loop, so an absent file cannot break the step).

**Regression tests** (`tests/unit/test_v2_10_event_times.py`, 17 tests), covering:
- unchanged start;
- reschedule later (original kept);
- reschedule earlier, including earlier-and-already-past → `EVENT_STARTED`;
- placeholder replaced by confirmed time;
- already-started event excluded with reason;
- conflicting update → `START_TIME_CONFLICT`;
- invalid update ignored and counted;
- invalid ledger start → `START_TIME_INVALID`;
- ledger-only behaviour identical to before;
- inputs never mutated (append-only history preserved);
- no future match excluded because of a stale ledger start;
- a newer ledger observation wins;
- index loads from the snapshot files;
- unified board shows the rescheduled match;
- end-to-end `run_bet_selection_v2.evaluate` in a temp repo: restored match evaluated, started match excluded with reason, ledger untouched;
- real ledgers byte-identical after resolution.

## B. Stage A completeness (board version `stage-a-1`)

**Before:**

| component | source | clean-price requirement |
|---|---|---|
| production unified board | ledger P | none, but hidden by defect A |
| V2-7 HIGH_P cohort | — | ≥1 clean book quote (frozen, correct for a *card* logger) |
| V2-8 Stage A (unmerged branch) | V2-7 HIGH_P legs | inherited, so 24→16 and 26→17 strong predictions disappeared |

**After** (`src/prediction_markets_lab/prediction_platform/stage_a.py`, `config/prediction_board_stage_a.yaml`, outputs `reports/latest_stage_a_board.{json,csv,md}`):
- Every valid, upcoming prediction, after est-1, is listed and ranked by probability only.
- The probability is the latest validated same-scan engine P (the one Stage B also uses). The frozen ledger P is kept in `ledger_probability`.
- `strong_prediction_min_probability: 0.70` equals the existing Prediction Board ≥70 count, bsv2-3 `high_probability_threshold` and V2-7 `min_leg_p`. A test asserts they are equal, so this is not a new value.
- Each row carries:
  - event, selection, P, σ (V2-7 formula: band calibration SE and half the exchange width; a test asserts equality with the V2-7 logger's SE);
  - engine / version, prediction timestamp, historical support text;
  - price status, the reason it is not assessable, the best clean quote and net EV;
  - `is_bet_recommendation: false`.
- **Price status (smallest taxonomy, 4 values):**
  - `PRICE_UNAVAILABLE` / `PRICE_QUALITY_FAIL`: not financially assessable.
  - `POOR_PAYOUT`: clean quotes, none above fair.
  - `PRICE_VALID`: a clean quote above fair exists; Stage B decides.
- **Label.** The label is `STRONG_PREDICTION_<status>` when P ≥ 0.70. Stage A's "financially unassessed" is expressed by the `financially_assessable` flag, not as a fifth status.
- **Quality rules** are the unchanged bsv2-3 rules. Stage A calls the bsv2-3 evaluator read-only. One extra condition applies: if the same-scan Betfair width behind the current P exceeds the bsv2-3 limit, the row is `PRICE_QUALITY_FAIL` (see finding F1).
- **Failure isolation.** A Stage A build failure writes `STAGE_A_BUILD_FAILED` and never blocks the production board (tested).
- Tests: `tests/unit/test_v2_10_stage_a.py`, 12 tests.

**Stage B is untouched.** No file under `bet_selection_v2/` or `config/bet_selection_v2.yaml` changed. A test shows Stage B decisions are identical with and without Stage A.

## Reconstruction of the 30 Sep scans

The harness re-ran bsv2-3 at the recorded run times on the committed inputs. It reproduces the production candidates CSV exactly (every decision and every reason code) for both scans.

| | morning (12:54) | afternoon (20:16) |
|---|---|---|
| bsv2-3 universe, old filter → est-1 (prediction rows) | 46 → 71 | 49 → 72 |
| unique events | 43 → 54 | 46 → 56 |
| restored rows (valid + research-only) | 25 (15 + 10) | 23 (14 + 9) |
| Stage B PAPER_BET, before → after | 0 → 0 | 0 → 0 |
| Stage B decisions after | REJECT 58 · MULTI 11 · WATCH 2 | REJECT 60 · MULTI 8 · WATCH 4 |
| existing candidates changed | 1 (Medvedev: +OUTSIDE_EVENT_HORIZON, still WATCH) | 0 |
| **Stage A strong (P ≥ 0.70)** | **24 / 24 scan-board events** (V2-7 HIGH_P: 16) | **26 / 26** (V2-7 HIGH_P: 17) |
| strong, by status | POOR_PAYOUT 14 · QUALITY_FAIL 8 · PRICE_VALID 2 | POOR_PAYOUT 17 · QUALITY_FAIL 9 |

- The QUALITY_FAIL counts (8 / 9) are exactly the predictions V2-7 HIGH_P dropped. They are now visible with the reason `EXCHANGE_SPREAD_TOO_WIDE`.
- The two morning PRICE_VALID rows are Zakharova (+0.55%) and Medvedev (+1.64%). Both remain non-bets in Stage B (below the 2% gate; the V2-7 1σ rule is separate and untouched).
- **Previously hidden matches:** all the matches V2-9 listed are restored, with the current start shown. They include:
  - Alcaraz 02:00→07:00;
  - Tiafoe →03:10;
  - Tsitsipas 03:15 (29 Sep)→03:10 (1 Oct);
  - Shapovalov →05:40;
  - Nakashima, Darderi/Ruud, Rune, Davidovich Fokina and Gao.
- More restorations were found than V2-9 counted: Musetti, Bondár (13:00), Starodubtseva, Ito/Birrell, Kenin/Krueger and Badosa/Kasatkina, plus 10 / 9 research-only duplicates.
- Every restored candidate has net EV ≤ 0 (the best is Halys at 0.0). Alcaraz (both scans) and Tiafoe (afternoon) become MULTI_RESEARCH_ELIGIBLE, a research label only.
- **Stage B candidate count:** it changes only through the defect fix (more events evaluated). The number of qualifying candidates stays 0 in both scans.

## Findings raised during implementation (not fixed; outside the approved scope)

- **F1 — bsv2-3 spread gate is bypassed for the ledger's own exchange-back quote.**
  - `prices.from_ledger_row` gives that quote a probability with no spread information, so `EXCHANGE_SPREAD_TOO_WIDE` cannot fire on it.
  - When the ledger row was created in the same scan, that quote is the latest "usable" one. In the morning scan this happened for all 8 wide books, which is why production showed 0 `EXCHANGE_SPREAD_TOO_WIDE` in the morning and 14 in the afternoon.
  - Impact today: none on decisions. The quote is self-source (the probability venue), with net EV below 0 in every case observed, and all were REJECT on NET_EV_NOT_POSITIVE.
  - It is still a gate inconsistency, and the reason code is misleading. Stage A handles it (above).
  - A Stage B fix needs a new rule version (bsv2-4) and your approval. **Recommend: next fix.**
- **F2 — Erratum to V2-9 §12.** "4 NOT_VALID events with no valid twin (Starodubtseva, Ito/Birrell, Kenin/Krueger, Badosa/Kasatkina) — expected: BOOKMAKER_CONSENSUS-only" was wrong. Their validated rows existed and were hidden by defect A. An erratum is appended to the V2-9 report on its branch.
- **F3 — Unified board vs Stage A probability.** The unified board ranks on the frozen ledger P (27 at ≥70% in the smoke run), while Stage A uses the current same-scan P (26). Both are shown and labelled. The unified board's semantics are unchanged by design.
- **F4 — Tennis settlement** (`run_tennis_settlement.py`) also reads the ledger `commence_time`. Its ±21-day result window makes a 1-day reschedule harmless. It is not changed (settlement is out of scope). **MONITOR.**
- **F5 — Football** event keys include kickoff, so a reschedule creates a new key and prediction. It never hides the match, but leaves a stale sibling row (excluded as started). **MONITOR.**

## Production safety

- **Files changed:**
  - modified: `scripts/run_bet_selection_v2.py` (+6/−1), `scripts/run_unified_prediction_board.py`, `src/prediction_markets_lab/prediction_platform/board.py`, and the three workflow commit lists;
  - new: `event_times.py`, `stage_a.py`, `config/prediction_board_stage_a.yaml`, 2 test files, `scripts/v2_10_reconstruct_30sep.py`, and this folder.
- **Frozen paths:** `git diff origin/master` over the following is **empty**: `config/card_research_shadow.yaml`, `config/bet_selection_v2.yaml`, `config/thresholds.yaml`, `src/.../card_engine`, `src/.../bet_selection_v2`, `src/.../tennis_prospective`, `research/platform_v2/card_engine_v2_7` (all prospective records), `scripts/run_card_shadow.py`, `tennis_predictions/`, `predictions/`, `paper_betting_v2/`, `reports/`.
- **V2-7:** config sha256[:16] is `9e52b67df08691d0` (unchanged, test-asserted).
- **Thresholds and flags:** no threshold changed. No new network code (grep: no urllib/requests/http in new modules). `real_money_enabled: false`, multis `enabled: false`, `settlement_enabled: false`.
- **Tests:**
  - production suite: 1206 passed, 8 skipped (master: 1177 passed, 8 skipped; +29 new);
  - research suite: 54 passed.
- **Smoke run** of `build` + `evaluate` in a scratch worktree of this branch: ledgers byte-identical; outputs as expected.

## Risks / limitations

- The current start is only as good as the latest provider observation. A match dropped by the provider keeps its last known start.
- Stage A rows for events absent from the latest scan use the ledger price and are labelled accordingly (usually `PRICE_QUALITY_FAIL`: PRICE_STALE).
- The Stage A `PRICE_VALID` / `POOR_PAYOUT` split uses central net EV. It is descriptive only, and Stage B stays the sole decision authority.
- V2-8's analyser (unmerged branch) still builds its Stage A from V2-7 HIGH_P legs. Once this merges it should read `latest_stage_a_board` instead (V2-8 financial rules unchanged). Not done here.
- The unified board JSON gains a `start_time_resolution` key and CSV columns (schema v2). Downstream readers that assume v1 columns are unaffected (columns appended).

## Recommendation

Merge when you are satisfied: both changes are narrow, tested, reproduce production exactly where they should, and leave every frozen component byte-identical. After merging, the next scheduled tennis run will be the first live use.

**Verify at that run:**
- `reports/bet_selection_v2_start_time_resolution.csv` exists;
- the Stage A board count matches the scan board's P≥0.70 count;
- V2-7 output is unchanged in form.

Then consider F1 (bsv2-4) as a separate approval.
