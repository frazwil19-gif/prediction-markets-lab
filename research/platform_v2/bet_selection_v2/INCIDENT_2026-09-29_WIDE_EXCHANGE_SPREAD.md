# Incident 2 (2026-09-29): positive EV is driven by collapsed Betfair books — PROPOSED fix bsv2-3 (NOT deployed)

## Finding (post-merge verification of bsv2-2, before any bsv2-2 production run)
- The frozen tennis engine sets P to the **midpoint** of the Betfair back/lay book. At 13:13 UTC many books were thin:
  width = max over runners of (1/back − 1/lay). Across 113 live exchange quotes: median 0.019, p75 0.068, p90 0.161;
  **34% wider than 0.03**. These are spreads only; no outcome was examined.
- **Every** positive-EV candidate at 13:13 came from a wide book:
  - Rune: 1.13/1.62 and 2.6/8.8, width 0.271, "+26%"
  - Boulter 0.157, Golubic 0.198, Sonmez 0.175, Frech 0.130
  - In each case the midpoint P sat about 8–18 pp above what every UK bookmaker (and Matchbook) implied.
- So the four bsv2-1 bets annotated `VALID_SAME_SNAPSHOT` are same-snapshot but rest on unreliable P. They get superseding
  annotation rows `INVALID_WIDE_EXCHANGE_SPREAD` (append-only; the original rows are untouched). **Valid paper bets to date: 0.**

## Proposed fix (bsv2-3; EV gates unchanged)
- Data-quality gate in the bet-selection layer (the frozen engine is untouched): if the probability source is EXCHANGE_MID and the
  width is > **0.03**, reject with `EXCHANGE_SPREAD_TOO_WIDE`. An unknown width gives `EXCHANGE_SPREAD_UNKNOWN` (fail closed).
- Threshold rationale, fixed before any outcome was examined: the midpoint's error is up to half the width (±1.5 pp), about the size
  of the 2% EV floor in probability terms at typical odds, so a wider book cannot support the EV sign.
- The board also writes `tennis_predictions/exchange_probability_snapshots.csv` (P, raw back/lay, width). The bsv2-2 file is left as is.
- Replay of the real 13:13 scan: 0 PAPER_BET (was 5 under bsv2-2); 9 multi-research, 3 watch.

## Separate issue for Fraser (engine level, not changed)
The prospective **prediction** ledger also stores midpoints from wide books (for example today's 13:13 first snapshots). The
historical validation used last-traded prices, so wide-book midpoints are a protocol deviation that affects calibration evidence.
Proposal: stratify calibration reporting by book width (reporting only; raw_prices is already stored), and decide separately
whether engine v2 should require a maximum width. No frozen engine change without approval.
