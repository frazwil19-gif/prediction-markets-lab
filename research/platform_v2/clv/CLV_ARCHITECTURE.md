# CLV architecture (clv-1, 2026-10-08)

Measurement only. It never changes a decision, grade, stake, threshold or the card.

## Why it is triggered from the Mac
GitHub's scheduled runs on this repo are hours late. The "hourly" H2 pre-close workflow ran 27 times between
2 and 8 October, a median of 5.7 hours apart (max 9.4 hours), so it almost never landed inside its 75-minute
window.

Near-close capture therefore runs on `workflow_dispatch` from a Mac LaunchAgent every 15 minutes
(`scripts/setup_clv_dispatcher_mac.sh`):
- it reuses the token already stored by `setup_dispatcher_mac.sh`;
- GitHub's own `*/30` cron stays as a fallback;
- a run with nothing due makes no paid call and commits nothing.

## Flow (`scripts/clv.py all`, every run)
1. **targets** (0 credits). New rows are appended to `research_shadow/clv/targets.csv`:
   - **PAPER_BET**: every bsv2 PAPER_BET decided from `active_from`, all engines. Live bets are a subset (PAPER_BET +
     money-eligible), so every live bet has a close.
   - **EV_STUDY**: the tennis EV-band cohort, built by the pre-registered rule
     (`EV_BAND_STUDY_PREREGISTRATION.md`).
2. **capture** (paid, surplus-only):
   - targets starting within (now, now + 25 min] are grouped by Odds API sport key;
   - one `/odds` h2h uk call per key costs 1 credit. Betfair back and lay come back with h2h, so tennis gets the
     exchange mid;
   - each target is captured at most once (0–25 min before start);
   - a target that starts with no capture is logged `NOT_CAPTURED_BEFORE_START` and never imputed.
3. **report** (0 credits): `research_shadow/clv/clv_report.{json,md}`.

## Stored per capture (raw kept)
- entry book, odds, commission, P and net EV, plus decision time;
- capture time and minutes before start (NEAR_CLOSE ≤ 10 min, else PRE_CLOSE);
- close basis (EXCHANGE_MID for tennis, UK_MEDIAN_FAIR otherwise) and p_close;
- same-book closing odds;
- best UK closing odds and book;
- number of UK books;
- every quote for the selection with its last_update (`quotes_json`).

## Metrics
| Metric | Definition |
|---|---|
| **price-CLV (directive)** | entry odds / same-book closing odds − 1 |
| best-price CLV | entry odds / best UK closing odds − 1 |
| **fair-CLV (primary for the study)** | (1 + (odds − 1)(1 − commission)) × p_close − 1 |
| closing movement | p_close − p_entry |

For each metric the report gives n, mean, median, positive rate and a bootstrap 95% CI (n ≥ 10). It breaks these
down by sport, engine, market, bookmaker and EV band.

**Live bets.** The weekly report joins Bet Log odds taken to the same target's close, so live CLV uses Fraser's
actual price. Bet Log rows stay private; only aggregates are reported.

## Credits
`config/api_budget.json` has a `clv_capture` block: monthly cap 100 (approved up to 120), daily cap 8.
- It is **surplus-only**: it pays only while remaining credits ≥ the Tier-2 shadow floor. That floor protects tier-1
  football, tennis, NBA and settlement, plus 2.5 credits/day per day left for US sports.
- So it cannot starve a core collector, and no core cap was changed.
- It has its own ledger (`research_shadow/clv/credit_ledger.csv`). `reports/credit_report` shows it, with
  utilisation.
- **Expected spend:** 1 credit per cluster of targets per sport key, about 1–3 a day in tennis season, so about
  20–60 a month (P).

## Frozen experiments
H2 (`scripts/capture_pre_close.py`, `research_shadow/h2_pre_close/`) is untouched: its pure functions are imported,
never edited, and its schedule is unchanged.

## Deferred
- Capturing a second, later close for the same target.
- Multi-region closes.
- Football closes for leagues whose settlement aliases are still pending (the capture works; settlement of those
  predictions waits for the alias review).
