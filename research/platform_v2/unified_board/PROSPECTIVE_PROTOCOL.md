# V2-5 Unified Prospective Prediction Platform — Prospective Protocol (pre-registered 2026-09-24, before any board output)

PAPER / RESEARCH ONLY. No engine is promoted to money by this protocol. Frozen engines are not modified.

## 1. What counts as a prospective prediction
A row in `predictions/unified_ledger.csv`, written **before the event starts**, by an engine@version listed in the registry
with a status that allows collection. Rows are append-only. A probability is never edited. Retries cannot duplicate (deterministic IDs).

## 2. Snapshot rules (fixed now; one canonical snapshot per prediction ID)
| engine | rows recorded per event | snapshot rule | source |
|---|---|---|---|
| atp/wta_match_winner.betfair_market@1 | predicted winner | tennis ledger's existing first-valid-snapshot rule (unchanged) | mirrored from `tennis_predictions/ledger_predictions.csv` (same prediction_id) |
| football_1x2.market_consensus@v1 | H, D, A (3 rows) | **FIRST_SCAN_WITHIN_48H**: first daily_scan whose data timestamp is 0 < minutes_to_event ≤ 2,880 | daily card `estimated_probability` (production consensus) |
| football_ou25.market@v1 | the more likely side (1 row) | FIRST_SCAN_WITHIN_48H | daily card |
| football_double_chance.derived_1x2@1 | 1X, X2, 12 (3 rows) | FIRST_SCAN_WITHIN_48H | pairwise sums of the renormalised 1X2 triplet above (0 credits) |
| nba_moneyline.market@1 | predicted winner | FIRST_SCAN_WITHIN_36H, regular season only (from 2026-10-20) | Odds API basketball_nba h2h: mean decimal odds per side across ≥ 3 books, then proportional (the frozen method) |
| football_btts | none | not wired to live data | — |

Binary markets record the favoured side only (the other side is its complement). 1X2 and DC record every selection.
The 48 h / 36 h windows keep snapshots close to the closing-price basis the engines were validated on. The window is fixed
now and is not tuned later.

## 3. Fail-closed rules
No row is written (it is counted as SKIPPED with a reason) when: the source data is older than 6 h at ingest (STALE), the 1X2 triplet is
incomplete or duplicated or sums outside 1 ± 0.03 (DATA_INVALID), the event identity is duplicated within a scan (REVIEW_REQUIRED),
the engine/version is not in the registry (ENGINE_UNKNOWN), the event has already started, or p is outside (0, 1).

## 4. Settlement
Separate append-only `predictions/unified_settlements.csv`; the first settlement wins. Football is settled from football-data.co.uk
(MATCHED only; AMBIGUOUS / UNRESOLVED_NAME stay pending as REVIEW_REQUIRED), 0 credits. Tennis mirrors the tennis settlement file.
NBA (from the season) uses the Odds API scores fallback only if needed and within budget. Each settlement logs its source and mapping status.

## 5. Maturity (per engine AND per ≥80% subset; sample-based, fixed now; same thresholds as the tennis protocol)
COLLECTING < 50 settled · EARLY ≥ 50 · INTERMEDIATE ≥ 300 settled and ≥ 100 settled at ≥ 80% · MATURE ≥ 1,000 settled and ≥ 300 at ≥ 80%.
For football 1X2/DC, which have 3 dependent rows per match, counts are **matches**, not rows.

## 6. Probability Engine Review (sample-triggered, not date-triggered)
An engine becomes reviewable at INTERMEDIATE. The review assesses: historical validation; prospective slope and 99.5% Wilson band
checks (same criteria as the historical gates); live-source compatibility; operational reliability (share of scheduled
runs producing valid snapshots); ≥80% coverage; minutes-to-event effects; uncertainty; and current-context limits. Only a
review can move an engine toward the Bet-Selection layer. Results seen before INTERMEDIATE are monitoring only; no
action is taken on them, except a pre-declared **alarm**: at ≥ 100 settled ≥80% rows, if realised < mean predicted − 10 pp, the engine
is flagged REVIEW_REQUIRED (not retuned).

## 7. Timing
Every row carries configured schedule time (null when unknown), actual workflow start, prediction timestamp and minutes to event.
Calibration by minutes-to-event bucket (<6 h, 6–24 h, 24–48 h, >48 h) is reported once any bucket has ≥ 100 settled rows. The external
trigger is proposed only if ≥ 10% of eligible events are missed or first snapshotted after kickoff over a rolling 14 days.
