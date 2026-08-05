# Cycle 1 — Decision Log

Chronological record of decisions made during Cycle 1 planning and
data acquisition. This is a governance record, not a results report.

## Decisions

- **Scottish Premiership (SC0) inclusion**: INCLUDED. Verified via
  direct live fetch of the full 2024/25 season (03/08/2024–18/05/2025,
  identical column schema to E0/E1). Full 5-season acquisition still
  pending.
- **Hypothesis H-FB-003 (exchange-price value) excluded from Cycle 1**:
  Football-Data.co.uk has no exchange (Smarkets/Betfair) price history
  at all, and only two static snapshots (opening/closing) per
  bookmaker, not an intraday series. Confirmed `DATA_REQUIRED`, not
  testable from this source.
- **Popular-favourite hypothesis (H-FB-001) requires a pre-registered
  proxy**: no direct "popularity" field exists in the source data.
  Decision: define the proxy (competition tier, and/or bookmaker
  count as an attention signal) explicitly before any backtesting, to
  avoid defining the test after seeing results.
- **Full acquisition deferred to a manually-triggered GitHub Actions
  workflow** rather than requiring local script execution: this
  project's sandboxed session environment has no general network
  egress to football-data.co.uk (only a narrowly-scoped `web_fetch`
  tool, one URL at a time), and the project must remain operable
  without a laptop. See `research/cycles/CYCLE_001/CYCLE_PLAN.md` and
  `docs/PHONE_ONLY_DATA_ACQUISITION.md`.
- **Excerpt data (29 matches) explicitly quarantined**: all excerpt-
  scale artifacts are placed under `excerpt_validation/` paths and/or
  suffixed `EXCERPT_VALIDATION_ONLY`, and must never be treated as, or
  copied into, the full Cycle 1 dataset paths.
- **Raw historical CSVs will not be committed to Git at full scale**:
  once the full 15-file acquisition runs, raw files will be preserved
  as GitHub Actions workflow artifacts (with a manifest + hashes
  committed to the repo), not committed to Git directly, to avoid
  repository bloat and to keep this decision explicit rather than
  discovered by accident. See
  `docs/PHONE_ONLY_DATA_ACQUISITION.md` for the retrieval process.
