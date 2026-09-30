"""V2-7 research-only card engine (singles / doubles / trebles). OFFLINE SHADOW LOGGER.

Never writes any production ledger (paper bets, predictions, settlements). Reads same-scan engine probabilities
(`tennis_predictions/exchange_probability_snapshots.csv`) and same-scan per-book prices (`tennis_predictions/price_snapshots.csv`).
Combined odds are INDICATIVE / NOT EXECUTION-VERIFIED (product of one book's leg prices in one snapshot).
Report: research/platform_v2/card_engine_v2_7/PHASE1_REPORT.md + AUDIT_AND_LOGGER.md (cer-1, offline).
Prospective shadow integration (cer-2, config-gated, inert until approved): shadow.py, shadow_settle.py,
scripts/run_card_shadow.py, config/card_research_shadow.yaml; SHADOW_INTEGRATION_AUDIT.md, PROSPECTIVE_ANALYSIS_PLAN.md.
"""
RULE_VERSION = "cer-1"
