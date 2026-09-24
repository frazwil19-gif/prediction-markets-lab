# Unified Prediction Board — Specification (V2-5)

**Product boundary.** The Prediction Board answers *what is most likely to happen*. The Money Card answers *which valid
predictions are worth betting*. They are separate in code (`prediction_platform/` never imports `decisions/`, staking or
money qualification) and in outputs (`reports/latest_prediction_board.*` vs `daily_cards/<date>/money_card.*`).

## Components (`src/prediction_markets_lab/prediction_platform/`)
| module | role |
|---|---|
| `schema.py` | canonical `Prediction` (33 fields), deterministic IDs, bands, fair odds, validation |
| `registry.py` | reads `research/platform_v2/PROBABILITY_ENGINE_REGISTRY.json` (single source of truth); validates statuses; decides whether an engine may collect |
| `adapters.py` | football card → 1X2 / O-U / DC; tennis ledger mirror; NBA odds → frozen method. All fail closed |
| `ledger.py` | append-only CSV with header and byte-prefix immutability guards |
| `settle.py` | football-data.co.uk (MATCHED only), tennis mirror, NBA scores; separate settlement file |
| `performance.py` | pooled + sport/engine/market/version metrics, ≥80% decomposition, maturity, alarm, timing buckets |
| `health.py` | component freshness, outage/stale flags, last observed credits |
| `board.py` | ranking and JSON/CSV/MD outputs |
Runner: `scripts/run_unified_prediction_board.py {ingest-football, ingest-tennis, collect-nba, settle, build}`.

## Files
`predictions/unified_ledger.csv` (immutable predictions) · `predictions/unified_settlements.csv` (append-only; first wins) ·
`predictions/platform_state.json` (run bookkeeping) · `predictions/nba_credit_log.csv` · `reports/latest_prediction_board.{json,csv,md}` ·
`reports/latest_prediction_performance.json`.

## Canonical prediction (ledger row)
prediction_id · engine_id · engine_version · sport · competition · event_id (provider, nullable) · event_key · event_name ·
event_start · market · selection · estimated_probability · fair_odds · probability_band · probability_source ·
historical_support · engine_status · data_quality · current_context_status · configured_scan_time · actual_workflow_start ·
prediction_timestamp · minutes_to_event · live_price · live_price_source · paper_status · prediction_valid ·
single_eligible · single_ineligible_reason · multi_research_eligible · snapshot_rule · origin · origin_prediction_id.
Settlement fields (settlement_status, result, correct, settlement_timestamp, settlement_source, mapping_status) live in
the settlement file. The board CSV/JSON shows them joined in. Unknown values are empty, never invented.

**Identity.** `sha256(engine_id@version|event_key|market|selection)[:16]`. The prediction timestamp is deliberately excluded,
so a retry or a later scan maps to the same ID and is ignored (first snapshot wins). Tennis rows keep their original tennis
ledger IDs (also deterministic), so tennis settlements join with no rewrite. The tennis ledger stays the canonical tennis
record and is mirrored, not migrated.

## Ranking
Estimated probability, descending. Evidence status breaks exact ties only
(VALIDATED_HISTORICAL_AND_PROSPECTIVE > VALIDATED_HISTORICAL > PROVISIONAL_PROSPECTIVE). No blended score, no EV, no ROI.
Views: ALL (CSV/JSON), with counts at ≥70…≥95. The Markdown default view is ≥80%.

## Status flags (not synonyms)
- `prediction_valid`: produced by a registered engine from validated inputs before the event.
- `single_eligible`: a **pre-filter only** (engine money_eligible AND fair odds ≥ payout floor 1.33). The Money Card still decides.
- `multi_research_eligible`: engine flag AND valid AND p ≥ 80%. A research pool only; multis stay disabled (same-game combos too).
Example: a DC 1X at 90% is valid = True, single = False (fair 1.11 < 1.33, and not a money engine), multi-research = True.

## ChatGPT handoff
ChatGPT should read `reports/latest_prediction_board.json` (`board_schema_version` 1), `reports/latest_prediction_performance.json`,
`status/latest.json` and `daily_cards/<date>/money_card.json`, and summarise them. It must not recompute probabilities, re-rank,
loosen thresholds, override engine statuses or invent context. If `health.overall` is `DEGRADED`, it must say so first.
