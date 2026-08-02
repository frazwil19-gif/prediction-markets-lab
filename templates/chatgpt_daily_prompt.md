Run the Prediction Markets Lab daily analysis.

Primary markets:
- Football pre-match 1X2 and approved totals.
- Tennis pre-match match winner.

Use the configured bankroll, thresholds and commission settings from
this repository's config/ directory (bankroll.yaml, thresholds.yaml,
commissions.yaml).

For every candidate:

1. Validate that bookmaker and exchange markets match exactly.
2. Convert bookmaker odds into raw implied probabilities.
3. Remove each bookmaker's overround (proportional method).
4. Calculate median consensus probability.
5. Calculate mean, standard deviation and bookmaker count.
6. Apply the approved category-specific model, if one exists and is
   at least BACKTEST status; otherwise use the consensus probability
   alone.
7. Calculate final probability.
8. Calculate exchange implied probability.
9. Calculate commission-adjusted EV.
10. Assess data quality, confidence and liquidity.
11. Grade A+, A, B, C or Reject.
12. Recommend a stake only if all risk gates pass.

Do not manufacture a trade. Do not recommend accumulators. Do not
increase stakes after losses. Reject stale or incomplete data. Clearly
state when no market qualifies.

Output using the structure in templates/daily_scan_template.md.
