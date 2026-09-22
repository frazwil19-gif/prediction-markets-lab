# Gate 1b (Football O/U 2.5) -- Live Data Collection Note (Section 21)

This cycle's own research needs are already met by the existing `cycle_002_discovery_features.csv` and
its already-live production wiring -- no NEW live data collection is required specifically for O/U 2.5.

This section instead reaffirms and narrowly extends the Phase 3 cycle's own live-data-preservation
finding (`research/data_expansion/LIVE_DATA_PRESERVATION_PLAN.md`, still NOT implemented, described
only): the raw per-bookmaker O/U 2.5 panel the live scanner already fetches every day is reduced to
consensus/best-price fields and the full panel is discarded, unrecoverable after each scan. Everything
that finding recommended for 1X2 (persist the raw per-bookmaker panel verbatim, add a genuine near-
kickoff closing-price snapshot, retain bookmaker-panel composition over time) applies identically and
with equal value to O/U 2.5 -- no separate recommendation is needed, and none is duplicated here.

**Not implemented this cycle** (same discipline as Phase 3: describe, do not silently change
production). If and when Fraser approves that preservation work, it should cover both 1X2 and O/U 2.5
panels in the same change, since the exact same code path (`the_odds_api_loader.py` /
`storage.schemas.MarketRecord`) handles both markets already.
