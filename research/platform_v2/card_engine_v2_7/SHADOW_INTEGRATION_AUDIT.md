# V2-7 Bounded Prospective Shadow Logging (cer-2): Logger Audit, Design and Verification (2026-09-30)

**Status:** prepared and tested on branch `v2-7-shadow-integration`. It is **not merged and not active**:
`logging_enabled: false` and `settlement_enabled: false` in `config/card_research_shadow.yaml`.

- Research only.
- 0 Odds API credits.
- Never writes production ledgers.
- All multi prices are **INDICATIVE / NOT EXECUTION-VERIFIED**.
- Pre-registered analysis: `PROSPECTIVE_ANALYSIS_PLAN.md` (committed `c89e305`, before any prospective card).

## 1. Audit of the cer-1 research logger (done first)
| check | result |
|---|---|
| Joint P / EV algebra | Correct. P_joint = ∏P_i, O = ∏O_i (same book), EV = ∏(1+EV_i) − 1. Unit tests pass. |
| Equal-capital log growth | **Independently verified by Monte Carlo** (2M draws per case, not the code's own formula). Double s = 2%: card 0.001143 vs formula 0.001141, singles 0.000682 vs 0.000688. Treble s = 3%: 0.001293 vs 0.001304, singles 0.000877 vs 0.000877. P(singles all lose) 0.1604 vs 0.1600. Differences are within MC error. |
| Corrected crossovers | Card grows faster only below these total stakes: P .6 @ 1.73 double **4.80%**, treble **4.06%**. P .6 @ 1.70 double 2.64%. P .75 @ 1.40 double 13.7%. |
| Sensitivity | If the true P is 1.5 pp below the model (0.585 vs 0.60), the double's edge at a 2% stake reverses: card 0.000087 vs singles 0.000168. **The card's growth advantage is fragile to probability error.** |
| Same-scan pairing | Correct. Prices and P come only from the same `scan_timestamp_utc`. On the live scan: 0 future-dated quotes, 0 older than 240 min, maximum age 6.8 min. |
| Same bookmaker | Correct. Enumeration is per book, and exchange books are never legs. |
| Append-only | Correct. There is a byte-prefix guard, and reruns are idempotent. |
| **Settlement name matching: DEFECT** | cer-1 compared the raw winner string with the selection. A source spelling difference (e.g. "Viktoria Morvayova" vs "Viktória Morvayová", both present in the live data) would have been recorded as **LOST**. Nothing was settled under cer-1, so there is no impact. **Fixed**: cer-1 `io.settle` and cer-2 both use the production tennis matcher `names_are_equivalent` and never settle an unmatched name. |
| Production settlement ledger | Holds an exact duplicate row for one prediction (harmless). cer-2 accepts identical duplicates, and any disagreement is a CONFLICT that never settles. |
| Scan scope | cer-1 `log` re-processed **every** scan in the file. Wired into a schedule, that would have been backfilling. cer-2 logs only the scan produced by the current run, within 90 min, and excludes legs whose event starts before the logging time. |

**Exact assumptions of the equal-capital comparison.**
- One period. Total stake s is a fraction of the bankroll at the start of the period, placed on the card, compared with s/k on each of
  the same k legs as singles placed at the same time.
- Leg outcomes are independent. Model P is treated as the true P.
- Each leg wins or loses: no voids, dead heats or partial settlement.
- There is no rebalancing between legs, and no compounding within the period.
- Prices are indicative same-book prices. Utility is logarithmic.

**This is hypothetical. It is not evidence of live profitability.**

## 2. cer-2 design
| requirement | implementation |
|---|---|
| 0 credits | No network code in `card_engine/` or `scripts/run_card_shadow.py`. A test forbids requests/urllib/http.client/API-key strings, and another test fails if a socket is opened. The workflow step gets no API key. |
| Reads only same-scan data | `exchange_probability_snapshots.csv` and `price_snapshots.csv` rows with the selected scan's timestamp only. |
| No production writes | `ShadowStore` is the only writer and raises `PermissionError` outside `prospective/`. The workflow step hashes the tree outside `prospective/` before and after, refuses to commit on any change, and runs `git add` on `prospective/` only. |
| Cannot fail, block or delay production | The step runs **after** the production commit-and-push step. It is `continue-on-error: true`, `timeout-minutes: 5`, and commits separately. Research tests live in `tests_research/`, **outside** the production `pytest -q` gate (testpaths = tests), so a research test failure cannot stop the board. |
| Explicit failure | One `scan_runs.csv` record per run: `OK`, `OK_ZERO_CANDIDATES`, `NO_SCAN_THIS_RUN`, `LATE_SCAN_NOT_LOGGED`, `INPUT_MISSING`, `INPUT_INVALID` (e.g. P without same-scan prices), `OUTPUT_CAP_EXCEEDED`, `FAILED_EXCEPTION`, `RESEARCH_TESTS_FAILED` or `PRODUCTION_TESTS_FAILED_NO_SCAN`. The success record is written **last**. Production scans with no shadow record are reported as `MISSING_SHADOW_RUN` at review. |
| Provenance | `run_id`, `commit_sha`, trigger, workflow start, production-test outcome, rule version (cer-2), config sha, bsv2 rule version, engine ids, and input file shas (probabilities, prices, calibration). |
| No backfill | See §1, "Scan scope". |
| Quality gates | Identical to bsv2-3 (width ≤ 0.03, quote ≤ 240 min). `load_config` refuses any weaker value, and a test pins equality. |

**Cohorts and storage policy (all fixed in config before any outcome).**
- **POS_EV:** every distinct per-book card whose every leg is clean and has net EV > 0 at that book in that scan, for k ≤ 3.
  - Each leg-book row is stored.
  - Each multi also stores its equal-capital comparison at 1%, 2% and 5%.
  - Bounds: 12 legs per book. Above 2,000 cards the scan is flagged as an anomaly, only singles are kept, and the dropped cards
    are counted.
- **HIGH_P:** book-agnostic unique leg sets of clean favourites with P ≥ 0.70 (at most 24 events, ordered by P descending; any
  truncation is counted).
  - Singles and doubles are all logged. Trebles use a **fixed 10% hash sample** on the leg set (salt in config) with weight 10.
  - Each card carries P_joint ± σ, a calibration-support label, and a same-book indicative price summary: the number of books
    pricing every leg, min/median/max odds, median EV, and the best book.
  - Event-level legs are stored. Per-book HIGH_P prices remain in the production append-only `price_snapshots.csv`, whose sha is
    recorded.
- **Population counts per scan:**
  - rows, validated events, quality failures by code, exchange quotes skipped, name mismatches;
  - enumerated / logged / sampling-excluded / dependence-unverified counts by k;
  - truncations and anomalies.
- **Exposure diagnostics per scan (`scan_diagnostics.jsonl`), by cohort and k:**
  - unique matches and unique leg sets;
  - top event exposure and maximum player exposure;
  - share of card pairs sharing a match;
  - maximum number of books repeating one leg set;
  - **model-implied Kish effective n** (card correlations computed exactly under leg independence).

## 3. Settlement (prepared, not scheduled)
`shadow_settle.py` reads the verified production tennis settlement ledger read-only and resolves legs from the research legs table
of the same scan record. The rules:
- A card settles only when **every** leg is final. A single lost leg does not settle the card early.
- An unmatched name, conflicting sources or a missing result never settles. Missing results are reported as overdue after 7 days.
- A walkover counts as a VOID leg. If the other legs win, the card becomes `WON_REDUCED_VOID_LEG`, with the void leg at 1.00
  (flagged as an unverified bookmaker rule). Otherwise the card is LOST, or VOID if all legs are void.
- Retirements follow the official winner and are flagged `RETIREMENT_BOOK_RULE_UNVERIFIED`.
- `settlement_id` = hash(card, evidence), so reruns add nothing. A corrected source appends a superseding row, and the original
  is kept.

## 4. Dry run (reproducible replay of the real 29 Sep 20:11 UTC scan)
Command:
```
python scripts/run_card_shadow.py dry-run --scan 2026-09-29T20:11:50.324947+00:00 --now 2026-09-29T20:16:50+00:00 --out <dir>
```
Two runs are byte-identical. The output is committed under `dry_run_cer2_scan_2026-09-29T2011/` (mode `DRY_RUN_REPLAY`), never
in `prospective/`.

- **Population:** 64 validated events; 1,166 price rows; 171 exchange quotes skipped; 995 leg-book pairs, of which 134 failed as
  `EXCHANGE_BOOK_TOO_WIDE` and 861 were clean.
- **HIGH_P:** 14 events. Enumerated 14 / 91 / 364 → logged 14 / 91 / 35 (329 trebles excluded by the sample, 9.6%).
  - Model-implied effective n: singles 14, **doubles 7.9, trebles 5.5**. The 91 doubles carry about 8 independent observations.
- **POS_EV:** 17 legs at 10 books → 17 singles, 8 doubles, 1 treble.
  - 1 `SHADOW_CANDIDATE`: Bai @ Betway 1.73, P 0.599 ± 0.012, EV +3.6% [+1.5, +5.6]. This is the same selection as the
    production paper bet.
  - 25 `SHADOW_WATCH`.
  - Effective n: singles 5.9 (8 unique leg sets repeated across up to 4 books), doubles 2.7.
- **Stored:** 31 leg rows, 166 card rows, **76 KB raw / 13 KB compressed** (cer-1 wrote 9.0 MB for the same scan).

## 5. Storage-growth estimate (2 board scans per day)
| scenario | per scan (raw / compressed) | per day | per month | per year |
|---|---|---|---|---|
| typical, like the demo (14 HIGH_P events) | 76 KB / 13 KB | 0.15 MB / 26 KB | 4.6 MB / 0.8 MB | 55 MB / 9.5 MB |
| heavy (HIGH_P cap of 24 events, about 530 cards) | ≈ 200 KB / 35 KB | 0.4 MB / 70 KB | 12 MB / 2 MB | 145 MB / 25 MB |
| hard ceiling (3,000 rows per scan) | ≈ 1.2 MB | 2.4 MB | 72 MB | not expected |

"Compressed" approximates the cost in git history, since packs are zlib/delta compressed. Files are **sharded by month**, so each
file stays far below GitHub's 50/100 MB limits. The working tree is currently 58 MB.
- **Assessment:** acceptable for a bounded collection period, e.g. to the 30-scan review. The main driver is HIGH_P doubles
  (C(n,2)).
- **Bounded alternative, if needed at review:** log only HIGH_P singles and doubles whose events start within 24 h (removes
  cross-scan repeats), or archive closed months as `.csv.gz`. Either is a new rule version, never a silent change.

## 6. Mathematical and data-quality concerns (open)
1. **Execution is unverified.** Every multi price is the product of one book's prices. Acca availability, restrictions and caps are
   unknown.
2. **Treble calibration is weak.** Historically ±4 pp, and trebles above 0.65 are untested. Labels mark this, but they filter nothing.
3. **Effective n is small.** About 8 per scan for 91 doubles. Months of collection are needed before any doubles claim (plan §5).
4. **Cross-scan repetition.** An event appears in several scans. The primary analysis uses the first logged scan only.
5. **σ is approximate.** It combines the band-level calibration SE with half the exchange width. It is not a per-prediction
   posterior.
6. **Favourite-only legs** and the Odds-API-covered universe limit generality (selection bias, plan §6).
7. **The growth advantage of multis is fragile.** A 1.5 pp probability error reverses it at a 2% stake (§1).
8. **Settlement coverage** depends on TennisCourtLog (weekly updates). Unresolved results are counted, never guessed.

## 7. Reconstructability of card mathematics and exposure (documented, no extra code; 2026-09-30)
Everything below can be recomputed from the prospective ledger plus the append-only production inputs whose shas are in each
`scan_runs.csv` record (`input_shas`). No per-card field is needed beyond what is stored.

| quantity | source |
|---|---|
| component legs | `cards.legset` (event_id:selection) → `legs.csv` rows with the same `record_id` (selection, opponent, start, sport_key) |
| leg P and uncertainty inputs | `legs.p`, `legs.exchange_width`; band calibration SE from `RESULTS.json` (sha recorded); σ_leg = √(SE² + (width/2)²) |
| joint P, σ_joint, fair odds, P(lose whole stake) | `cards.p_joint`, `cards.sigma_joint`; fair = 1/p_joint; P(lose all) = 1 − p_joint |
| same-book same-snapshot indicative odds | POS_EV: `cards.odds_indicative` + per-leg `legs.odds`. HIGH_P: min/median/max/best-book on the card; any single book's product from `price_snapshots.csv` rows of that `scan` |
| central EV and ±1σ EV range | POS_EV: `ev`, `ev_low`, `ev_high`. HIGH_P: `ev_median` on the card; per book = p_joint·O_book − 1 with range (p_joint ± σ)·O_book − 1 |
| equal-capital comparison and log growth at 1/2/5% | POS_EV multis: `equal_capital_json`. Any card: `cards.equal_capital(legs, s)` on the reconstructed legs and one book's prices |
| dependence and eligibility flags; cohort | `dependence`, `dependence_flags`, `calibration_support`, `status`, `reasons`, `cohort`, `sample_weight` |
| exposure by match / player / bookmaker / shared across cards | `legs.event_id`; `legs.selection` and `legs.opponent`; `cards.book` (POS_EV) and `price_snapshots.bookmaker` (HIGH_P); the `legset` overlap between cards. Per-scan summaries are in `scan_diagnostics.jsonl` |
| total hypothetical bankroll exposure | Σ over the cards a staking policy would place × stake fraction. Computed at analysis time for a stated policy; the logger places nothing |

Every multi price stays labelled **INDICATIVE / NOT EXECUTION-VERIFIED**.
