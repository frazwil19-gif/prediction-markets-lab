# Tennis Prediction Board Spec (paper; implemented)

Files: `tennis_predictions/<date>/board_<HHMM>.{json,md}`, `tennis_predictions/ledger_predictions.csv`
(append-only, immutable), `tennis_predictions/ledger_settlements.csv` (append-only; first settlement wins),
`tennis_predictions/performance.json`, `tennis_predictions/credit_log.csv`. Workflow: `tennis_prediction_board.yml`
(06:30 and 15:30 UTC boards, 22:30 UTC settlement).

Header: covered tournaments · matches scanned · valid predictions · research-only count · counts at ≥70/75/80/85/90/95%.
Rows (ranked by validated P, then start time): tour · tournament · match · predicted winner · P · band · **the engine's
unseen-data hit rate for that band (n)** · source · start · (JSON adds prediction id, engine@version, timestamps, raw
prices, P(A), P(B), `multi_research_eligible`).
States: PREDICTED → SETTLED_CORRECT / SETTLED_INCORRECT / VOID; DATA_INVALID events are not ledgered; UNRESOLVED after
21 days. **No odds-derived value, EV, stake, or BET/WATCH/REJECT at this layer.** A 94% favourite at 1.08 is shown
like any other prediction.
`multi_research_eligible` = validated source and P ≥ 0.80. It is a research flag only; no multis are constructed.
