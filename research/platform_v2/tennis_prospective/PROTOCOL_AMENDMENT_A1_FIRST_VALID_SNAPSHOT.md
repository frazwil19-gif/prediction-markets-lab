# Tennis Prospective Protocol — Amendment A1 (2026-09-29, before any affected match started)

## Defect (found in the V2-6 Step 0 production audit)
The frozen protocol (`ATP_PROSPECTIVE_PROTOCOL.md`, "Prediction rules") says: *"The first **valid** snapshot before
`commence_time` is canonical."* The implementation keyed the ledger only on `prediction_id = sha256(engine@version|event_id)`,
so the first snapshot of **any** source took the ID. A research-only BOOKMAKER_CONSENSUS row therefore blocked every later
validated (Betfair exchange) snapshot of the same match.

Observed impact: the 28 Sep 15:30-cron board (run 36485475123, started 21:21 UTC) found 31 China Open matches (ATP + WTA)
~28–55 h before start, before Betfair was quoting them. All 31 were ledgered as research-only. Without the fix, the whole
tournament would have produced **0** validated prospective predictions.

## Amendment (implementation brought into line with the protocol text; no engine change)
- Unchanged: probability hierarchy, sources, staleness rule, engine version, existing rows (byte-identical), settlement.
- If an event's canonical ID is held **only** by research-only row(s), the first validated snapshot before start is appended
  once under `validated_upgrade_id(original) = sha256(original_id|FIRST_VALID_AFTER_RESEARCH)[:16]`.
- A validated row, once present, stays canonical; later snapshots (valid or research) are never added. Retries are idempotent.
- Performance already excludes research-only rows, so no event is double-counted; the research row stays as provenance.
- Outcome-blind: the rule depends only on price-source availability before start, never on results.

Code: `src/prediction_markets_lab/tennis_prospective/ledger.py` (`append_predictions`, `validated_upgrade_id`).
Tests: `tests/unit/test_tennis_prospective.py` (three A1 tests).
