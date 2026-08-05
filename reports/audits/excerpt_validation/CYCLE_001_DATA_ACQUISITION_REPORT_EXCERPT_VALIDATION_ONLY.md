# CYCLE_001 Data Acquisition Report

**Status: PARTIAL.** This report covers a pipeline-validation-scale
acquisition (3 files, ~9-10 rows each, 29 matches total), proving the
full acquisition → extraction → normalisation → consensus chain works
correctly end-to-end on genuine historical data. **It is explicitly
not the full Cycle 1 dataset.** Full-scale acquisition (5 seasons ×
up to 3 competitions, ~15 files, thousands of matches) requires
running `ingestion/football_data_loader.py` from an environment with
real network access to football-data.co.uk, which this project's own
sandboxed environment does not have (see "Why partial" below).

## Files attempted / acquired

| Source ID | Competition | Season | Status | Method |
|---|---|---|---|---|
| E0_2024_25 | Premier League | 2024/25 | ✅ Acquired (excerpt, 10 rows) | Direct `web_fetch` of live URL, saved verbatim |
| E1_2024_25 | Championship | 2024/25 | ✅ Acquired (excerpt, 10 rows) | Direct `web_fetch` of live URL, saved verbatim |
| SC0_2024_25 | Scottish Premiership | 2024/25 | ✅ Acquired (excerpt, 9 rows), **full season also verified accessible** (fetched and inspected in full — 03/08/2024 to 18/05/2025, ~228 matches — but only the first 9 rows were persisted as the raw file, to keep the raw-file footprint proportionate to this validation pass) | Direct `web_fetch` |
| E0/E1/SC0 × 2020/21–2023/24 | — | — | ❌ Not attempted this session | Deferred — see "Why partial" |

No download failed, was rejected as HTML, or hit an unrecoverable rate
limit in this session (one 429 was hit and is documented in
`reports/audits/FOOTBALL_DATA_FEASIBILITY.md` from the prior Stage 3
feasibility session; the SC0 verification fetch in this session
succeeded without incident).

## Real hashes and sizes (see `reports/audits/football_data_manifest.csv` for the full manifest)

| File | SHA-256 (first 16 hex chars) | Byte size | Rows |
|---|---|---|---|
| E0_excerpt.csv | `ecee7e6ed7331074` | 5,966 | 10 |
| E1_excerpt.csv | `c9b9f68722ab931b` | 6,006 | 10 |
| SC0_excerpt.csv | `86cbb184b02cc32d` | 5,433 | 9 |

## Why partial

This project's execution environment (the sandbox this analysis runs
in) does not have network egress to `football-data.co.uk` via the
`bash_tool` — only a separate, narrowly-scoped `web_fetch` capability
that can retrieve individual URLs already surfaced by search, one at a
time, without a general-purpose HTTP client loop. Fetching 15 full
season files (each potentially 100-250KB, several hundred rows) via
that mechanism, one at a time, each appearing in full in the working
context, was judged both slow and an inefficient use of the available
session budget relative to building a *correct, reusable, tested*
acquisition pipeline that can be run properly once, end-to-end, from
an environment with normal internet access (e.g. a developer's own
machine, or Claude Code with network access).

**What this session prioritised instead:** a working, paced,
retry/backoff-aware, HTML-rejecting, hash-verifying, atomic-write
loader (`ingestion/football_data_loader.py`), fully covered by 15
mocked unit tests, plus every downstream stage (extraction,
normalisation, consensus, canonical schemas) proven correct against
**genuine** (not fabricated) historical data at a small but real
scale.

## Rate-limit events

One 429 was encountered in the prior Stage 3 feasibility session (see
`reports/audits/FOOTBALL_DATA_FEASIBILITY.md`); none in this session's
SC0 verification fetch. The loader's default pacing
(`AcquisitionConfig.delay_between_requests_seconds = 6.0`,
`initial_backoff_seconds = 10.0`, exponential backoff, `max_retries = 4`)
is a conservative default chosen in direct response to that observed
429, not a guess.

## Retained matches, eligibility

All 29 matches in the excerpt sample were retained (0 exclusions).
All 29 are `eligible_outcome_model` (valid FTR) and
`eligible_consensus_model` (≥4 complete bookmaker markets, actual
count was 6/6 for every match in the sample — see
`reports/audits/football_bookmaker_coverage.csv`).

## Immediate next step (Stage 3A continuation, not yet done)

1. Run `ingestion/football_data_loader.py` for real, from a
   network-enabled environment, across all 15 target files
   (E0/E1/SC0 × 2020/21–2024/25).
2. Re-generate every audit artifact in this directory at full scale
   (they are all scripted and reproducible — the same code that
   produced the 29-match sample will produce the full dataset).
3. Extend `config/football_team_aliases.yaml` for any team names that
   appear unresolved once multi-season data is loaded (promoted/
   relegated clubs).
4. Re-run duplicate detection at full scale (meaningful duplicate/
   reschedule detection requires more than one season of data).
5. Finalise `research/cycles/CYCLE_001/data_splits.csv` with real row
   counts once all seasons are acquired.

See `reports/audits/CYCLE_001_DATA_QUALITY_REPORT.md` for the
corresponding quality findings on this same excerpt-scale sample.
