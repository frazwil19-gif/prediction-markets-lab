# V2-11 — Spread-gate bypass on the unified-ledger price path (proposed bet-selection rule `bsv2-4`)

Status: prepared on branch `v2-11-spread-gate-ledger-path` (from master `2ba3cac`, i.e. after the V2-10 merge). **NOT merged.**
Reproduce: `python scripts/v2_11_reconstruct_spread_path.py` → `RECONSTRUCTION.json` (every bsv2-3 production run, inputs
via `git show`, no outcomes, 0 API calls).

## 1. Root cause and data path

1. **Origin.** The tennis engine writes one ledger row per event at its first scan (`tennis_predictions/ledger_predictions.csv`), including `raw_prices` (`ex_back=…;ex_lay=…`) and `source` (EXCHANGE_MID / EXCHANGE_BACK).
   - The unified adapter (`prediction_platform/adapters.tennis_from_ledger`) keeps only the Betfair **back** price of the predicted side as `live_price` / `live_price_source = "betfair_ex_uk back (odds_api)"`.
   - It drops `raw_prices` and `source`.
2. **Fields carried.** `bet_selection_v2/prices.from_ledger_row` turns that into a `PriceSnapshot` with:
   - price = ledger back odds;
   - `observed_at` = `prediction_timestamp`;
   - `p_same_snapshot` = the ledger P (same snapshot, correct);
   - but `p_same_spread = None` and `p_same_source = None`.
3. **Why the spread is absent.** The unified row schema never had width or source columns, and bsv2-3 added the width only to the tennis *price-snapshot* path (`tennis_from_snapshots` → `same_scan_details`).
4. **Bypassing code path.** `evaluate._price_candidate` applies the width gate only when `p_same_source == "EXCHANGE_MID"`. For the ledger snapshot the source is `None`, so the gate is **skipped rather than failed closed**.
5. **Outputs affected:**
   - `reports/bet_selection_v2_candidates.csv` / `.md` / `.json` (decision + reasons);
   - `paper_betting_v2/price_snapshots.csv` (per-quote decision records);
   - `paper_betting_v2/evaluation_runs.csv` (decision counts);
   - `diagnose` (retrospective, manual).
   - Not affected: V2-7 (cer-2 reads exchange/price snapshots only, never the ledger path), the Money Card, and the unified board (Stage A already overrides; V2-10).

## 2. Historical decision impact (all 4 bsv2-3 runs)

Harness A reproduces every committed candidates CSV exactly (decisions and reason codes).

| run | universe | bsv2-3 actual | bsv2-4 | changed rows | decision changes |
|---|---|---|---|---|---|
| 29 Sep 20:11 | 97 | PB 1 · MULTI 8 · WATCH 5 · REJ 83 | PB 1 · MULTI 6 · WATCH 5 · REJ 85 | 4 | MULTI→REJECT: Dart, Storm Hunter |
| 30 Sep 12:54 | 46 | MULTI 10 · WATCH 2 · REJ 34 | MULTI 6 · WATCH 2 · REJ 38 | 14 | MULTI→REJECT: Noskova, Muchova, Samsonova, Andreeva |
| 30 Sep 13:26 | 46 | as 12:54 | as 12:54 | 14 | same 4 |
| 30 Sep 20:16 | 49 | MULTI 6 · WATCH 4 · REJ 39 | MULTI 5 · WATCH 4 · REJ 40 | 2 | MULTI→REJECT: Sabalenka |

- **Other changes are reason codes only.** `NET_EV_NOT_POSITIVE` becomes `EXCHANGE_SPREAD_TOO_WIDE|NET_EV_NOT_POSITIVE`, or `+EXCHANGE_SPREAD_UNKNOWN` for stale ledger quotes that were already rejected as PRICE_STALE.
- **PAPER_BET:**
  - The only bsv2-3 paper bet (Bai @ betway 1.73, 29 Sep 20:11) is **unchanged**. It used the tennis price-snapshot path with a same-scan width of 0.0097.
  - No WATCH changed.
  - No new candidate arises anywhere.
- **Spread-quality failures on decided rows:** 9→13, 0→14, 0→14, 14→16. The zero in the morning was the symptom V2-10 noticed.

## 3. Can the defect create a false financially-qualified candidate?

**Yes, in principle. Not so far.**
- The ledger quote is the self-source Betfair back price. Against a midpoint P it is usually negative-EV, but not by construction.
- On wide books, odds-space midpoints can inflate the de-vigged P (V2-9: up to 7pp). A back price can then show positive net EV.
- **Observed once:** Storm Hunter, 29 Sep 20:11. Back 1.02, P 0.98256 from a 9.1pp-wide book, net EV **+0.12%**. It passed into the soft-gate path and was labelled MULTI_RESEARCH_ELIGIBLE.
- With EV ≥ 2%, odds ≥ 1.33 and within 24h, the same path would have produced a **PAPER_BET on an unreliable P**.
- So the defect can alter actual decisions (it did, for MULTI labels), not only reason codes.

## 4. Invariant and fix (smallest robust)

**Invariant:** no financial assessment may use a Betfair-derived probability for which bsv2 requires exchange-book quality, unless the width of the same snapshot is known and within limits. Otherwise it **fails closed**.

**Fix:**
- `prices.from_ledger_row(row, prob_rows)` attaches, for tennis rows, the engine source and width of the **same scan**. That means the exchange-probability row whose scan timestamp equals the ledger `prediction_timestamp`, with the same event id and players, validated.
- If there is not exactly one such row, the snapshot is marked `UNRESOLVED_LEDGER_SNAPSHOT`. A width from another scan or another event is never used, and a narrow book is never assumed.
- `evaluate` requires the width for `EXCHANGE_MID` **and** `UNRESOLVED_LEDGER_SNAPSHOT`, so a missing width gives `EXCHANGE_SPREAD_UNKNOWN` (HARD).
- The EXCHANGE_BACK fallback remains exempt, as in bsv2-3.
- Football bookmaker quotes are unaffected.
- **Call sites:** `run_bet_selection_v2` (evaluate + diagnose) and `run_unified_prediction_board` (Stage A) pass the probability rows they already read.
- **Stage A:** the prediction stays visible (`STRONG_PREDICTION_PRICE_QUALITY_FAIL`; tested).

## 5. Versioning

- **bet-selection: `bsv2-3` → `bsv2-4`.** Its decision semantics change (MULTI→REJECT cases), so the version changes. Gate values are unchanged (test-asserted).
  - bsv2-4 applies only from its deployment commit, and rows written under bsv2-3 are never re-labelled.
  - Pre/post analysis splits on `rule_version` in `selections.csv`, `evaluation_runs.csv` and the candidates' run time.
- **Carry-forward annotation.** One append-only row in `paper_betting_v2/selection_annotations.csv` marks the single bsv2-3 PAPER_BET (Bai) `VALID_SAME_SNAPSHOT`, with the reconstruction evidence.
  - Without it, the version bump would drop that bet from the current paper results, and its prediction would no longer count as existing exposure.
  - This is the established mechanism from bsv2-1→bsv2-3.
- **cer-2 (V2-7): no change needed.**
  - It never uses the ledger path.
  - Its scan records already store `bsv2_rule_version` from config, so post-deployment V2-7 records will say `bsv2-4` automatically. That gives exactly the required separability.
  - One research test hard-coded `"bsv2-3"`. It now reads the value from config. No V2-7 code, config (sha `9e52b67df08691d0`) or record changed.
- **Stage A (`stage-a-1`): unchanged.** Its width override from V2-10 already produced the corrected classification.

## 6. Reconstruction of the 30 Sep scans (A actual → B bsv2-4, old universe; C = est-1 universe + bsv2-4)

| | morning A → B | afternoon A → B | C morning | C afternoon |
|---|---|---|---|---|
| Stage A strong | 24 (unchanged; V2-10) | 26 (unchanged) | 24 | 26 |
| Stage A quality failures (strong) | 8 | 9 | 8 | 9 |
| spread failures on decided | 0 → 14 | 14 → 16 | — | — |
| WATCH | 2 → 2 | 4 → 4 | 2 | 4 |
| MULTI_RESEARCH | 10 → 6 | 6 → 5 | 7 | 7 |
| PAPER_BET / final candidates | 0 → 0 | 0 → 0 | 0 | 0 |

## 7. Tests

`tests/unit/test_v2_11_spread_ledger_path.py`, 13 tests:
- config is bsv2-4 with gates unchanged;
- narrow width is attached and assessed normally;
- wide width → TOO_WIDE;
- missing width → UNKNOWN;
- stale width (other scan) never used;
- mismatched-event width never used;
- no probability rows → fail closed;
- EXCHANGE_BACK exempt;
- football bookmaker ledger quote unaffected;
- tennis bookmaker snapshot path unchanged;
- no false candidate through the ledger path (+26% looking quote rejected in every unresolved/wide case, still assessable when narrow);
- the real Storm Hunter case;
- prediction visible on Stage A despite failure.

**Suites:**
- production: 1219 passed, 8 skipped (master after V2-10: 1206; +13);
- research: 54 passed.
- A smoke run (`build` + `evaluate`) in a scratch worktree gives rule_version bsv2-4, 0 PAPER_BET, and 16 width rejections.

## 8. Production diff (proposed)

| file | change |
|---|---|
| `config/bet_selection_v2.yaml` | rule_version + dated note |
| `src/.../bet_selection_v2/prices.py` | `from_ledger_row` same-scan resolution; `UNRESOLVED_SOURCE` |
| `src/.../bet_selection_v2/evaluate.py` | `SPREAD_REQUIRED_SOURCES` |
| `scripts/run_bet_selection_v2.py` | pass probability rows (evaluate, diagnose) |
| `scripts/run_unified_prediction_board.py` | pass probability rows (Stage A) |
| `paper_betting_v2/selection_annotations.csv` | +1 append-only row |
| `tests_research/test_card_research_shadow.py` | version read from config |
| new | test file, reconstruction script, this folder |

No threshold, V2-7, V2-8, settlement, multi or money change. No new network calls.

## 9. Other observations

- `scripts/v2_10_reconstruct_30sep.py` (a historical record) calls `from_ledger_row(p)` without probability rows. Re-running it after this change would mark ledger quotes UNRESOLVED; its committed JSON is the V2-10 record and stays as is.
- The Stage A width override (V2-10) is now redundant for the ledger path but kept as defence in depth.
