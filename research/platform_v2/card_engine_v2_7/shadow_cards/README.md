# cer-1 offline demo output (29 Sep 2026 20:11 UTC scan)

`cards.csv` (4,857 cards, 9.0 MB) is **excluded from master's tree** (2026-09-30, Fraser's deployment approval): it is not read by any
test or by the cer-2 logger, and its counts are kept in `summary.json` / `search_space.json` and in `AUDIT_AND_LOGGER.md`.
It was **not** removed from history: the full file is at commit `cef7993`,
path `research/platform_v2/card_engine_v2_7/shadow_cards/cards.csv`
(`git show cef7993:research/platform_v2/card_engine_v2_7/shadow_cards/cards.csv`).

Reproduction: its inputs are the append-only production files `tennis_predictions/exchange_probability_snapshots.csv` and
`tennis_predictions/price_snapshots.csv` (rows with `scan_timestamp_utc = 2026-09-29T20:11:50.324947+00:00`), the cer-1 code
(`card_engine/cards.py`, `io.py`) and `RESULTS.json`. Card ids are deterministic; `logged_at` is the only run-dependent field.
The cer-2 equivalent of the same scan is the committed, byte-reproducible
`../dry_run_cer2_scan_2026-09-29T2011/` (see `SHADOW_INTEGRATION_AUDIT.md` §4).
