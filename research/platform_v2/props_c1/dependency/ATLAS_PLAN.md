# Dependency Atlas expansion — bounded set (written before computation; DESCRIPTIVE ONLY)

No prices, no SGM claims, no betting rules. Post-match outcomes characterise dependency only.
Data: `Matches.csv`, the 10 divisions, seasons 2015-16 … 2025-26 (complete-season rows with corners, cards, SOT,
goals and 1X2 odds for the favourite definition). Favourite = higher proportional implied 1X2 probability.

Fixed set of 8 pairs (A, B):
1. WIN×SOT: favourite wins × favourite team SOT > 4.5
2. WIN×CORNERS: favourite wins × total corners > 9.5
3. WIN×CARDS: favourite wins × total cards > 4.5
4. GOALS×SOT: total goals > 2.5 × total SOT > 8.5
5. GOALS×CORNERS: total goals > 2.5 × total corners > 9.5
6. GOALS×CARDS: total goals > 2.5 × total cards > 4.5
7. SOT×CORNERS: total SOT > 8.5 × total corners > 9.5
8. SOT×CARDS: total SOT > 8.5 × total cards > 4.5
Report per pair: N, P(A), P(B), P(A∩B), P(A)P(B), ratio, P(B|A), P(B|¬A), bootstrap 95% CI of the ratio (1,000,
seed 7), ratio by season (min/max, share of seasons on the same side of 1), ratio by league (min/max, share same side).
