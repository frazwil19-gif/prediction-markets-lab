# Settlement hardening (2026-10-02)

Infrastructure maintenance only. Unchanged: Corners Model A, corners A/B/C, Player SOT pilot and cycle 2, all
probability models, thresholds, grades, staking, Track A/H2, the Odds API probe and the 10 October Betfair experiment.
0 Odds API credits, no paid data, no new market family. Merged 06bab30 (full clean suite 1356 passed, 8 skipped).

## 1. D1 / N1 team resolution — mechanism built; aliases NOT yet created (no evidence exists yet)
- All 36 names are football-data.co.uk 2026/27 spellings (18 D1 + 18 N1). The other half of each mapping, the Odds
  API spelling, has never been observed in this repo: D1/N1 were added on 1 Oct, during the international break, so no
  D1/N1 odds, events or scores were ever stored. Fixture identity therefore cannot be established today, and no alias
  was guessed.
- Built `settlement/alias_derivation.py`: maps a football-data name to an Odds API name only from the same fixtures in
  both listings (same competition, same kickoff slot, same home/away role, opponent consistent, one-to-one,
  eliminations propagate). Name tokens are used only to separate simultaneous fixtures inside a slot, and only when
  exactly one fixture-consistent candidate shares a token. Ambiguity stays unresolved; contradictions reject the
  league. Every proposal records its method and supporting fixtures. 4 regression tests.
- `settlement_alias_evidence.yml` (daily 06:23 UTC, free /events only; stops if any response reports a charge) writes
  `alias_evidence/<utc>.json` + `PROPOSED_ALIASES.csv`. Nothing is applied automatically.
- Timing: football-data `fixtures.csv` currently lists only lower divisions (international break). The 17–19 Oct
  D1/N1/F1 round should appear by ~14 Oct; a check-in on 15 Oct reviews the evidence and commits the overlay aliases
  with tests, before those matches need settling.

## 2. F1 coverage — root cause fixed; no source blocker
- Root cause: `scripts/run_football_settlement_shadow.py` used a hand-maintained 5-league dict (E0/E1/SC0/N1/D1).
  The actual settlement path (`prediction_platform/settle.py`) already reads every league, F1 included, from
  `config/football_coverage.yaml` and football-data publishes `F1.csv` in the same format.
- Fix: the shadow now derives its leagues from the same config (all 16 observed leagues). F1 team names will need the
  same fixture-identity aliases as D1/N1 (covered by the evidence collector). No incompatible substitute source used.

## 3. Four stuck football bets (kickoff 2026-09-20) — path repaired; settles on the next normal run
- Root cause: they are card.json backfill rows with no Odds API provider id, and the scores endpoint only covers the
  last 3 days, so the primary path could never settle them (the old instruction was "settle by hand").
- Fix: `run_settlement.py` now sends rows the scores API can never settle (NO_PROVIDER_ID or OUTSIDE_SCORES_WINDOW)
  through a deterministic football-data path: explicit aliases, MATCHED only, same result/P&L/ledger functions, one
  audit row each in `settlement_archive/legacy_football_data_settlements.csv`. Rows the scores API can still settle
  are untouched (football-data is not promoted to primary; the migration gate is unchanged). Idempotent (tested).
- Nothing was marked by hand. The workflow could not be dispatched from this session (GitHub 403), so the four rows
  settle in the scheduled 21:00 UTC run on 3 Oct; a verification check-in is scheduled for 21:40 UTC.

## 4. Settlement completeness monitor — live
`scripts/settlement_completeness.py` (runs inside settlement_and_performance; diagnostic only) classifies every record
in the unified ledger, the legacy paper ledger and the bsv2 paper selections as NOT_STARTED / NORMAL_SOURCE_LAG /
SETTLED / UNRESOLVED_AFTER_EXPECTED_LAG / SOURCE_UNAVAILABLE by ledger, sport, competition and source, writes
`status/settlement_completeness.json` + `reports/settlement_completeness.md`, and emits a GitHub warning per affected
group. Expected lags are config (`config/settlement_monitor.yaml`): football-data 120h, TennisCourtLog 240h, Odds API
scores 96h.

First run (2026-10-02 22:13 UTC): NOT_STARTED 56 · NORMAL_SOURCE_LAG 129 · SETTLED 12 ·
UNRESOLVED_AFTER_EXPECTED_LAG 4 (the four legacy bets) · SOURCE_UNAVAILABLE 0.

## 5. Tennis
Not treated as a defect: all unsettled tennis records are inside the 240h TennisCourtLog lag (NORMAL_SOURCE_LAG).
Any record that outlives the lag will now be flagged automatically. Source unchanged.

## 6. H2
GitHub hourly cron has demonstrated insufficient reliability for time-sensitive pre-close capture (2 runs of
`pre_close_capture` between 29 Sep and 2 Oct against ~90 scheduled). Track A/H2 unchanged; no migration now. If H2
remains useful, a Mac-side or always-on capture runner should be evaluated separately.

## Remaining genuine blockers
- D1/N1/F1 aliases need the first listing of the same fixtures in both sources (expected ~14 Oct). Until then any
  D1/N1/F1 result would be UNRESOLVED_NAME and stay pending (flagged, never guessed).
- The settlement migration gate (≥100 comparisons) accrues only when legacy bets start inside the scores window; it
  is still 0. Reported, unchanged.
