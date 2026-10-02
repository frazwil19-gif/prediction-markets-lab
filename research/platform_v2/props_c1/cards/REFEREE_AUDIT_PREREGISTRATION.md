# Cards — referee data audit (PRE-REGISTRATION; data preparation only)

Written and committed 2026-10-02 before the referee data were examined. Not a cards modelling cycle.

## Data
Free Football-Data raw CSVs already held on Fraser's machine: E0, E1, SC0, seasons 2020-21 … 2025-26 (`Referee`,
`HY`, `AY`, `HR`, `AR`, date, teams). No downloads, no API calls.

## Questions
1. Coverage and missingness of `Referee` by division/season.
2. Identity consistency: name variants (case, whitespace, initials, punctuation); report the normalisation map.
3. Matches per referee; how many referees have ≥20 prior matches.
4. Card-rate stability: per-referee cards/match in season t vs t+1 (correlation, n referees).
5. Does referee add genuine out-of-sample information? Fixed test: total cards (yellows + reds) Poisson.
   - R0: league-season-to-date mean (prior matches only).
   - R1: R0 + both teams' rolling cards for/against (prior 10, min 5).
   - R2: R1 + referee shrunken prior rate: (sum cards in referee's prior matches + k·league mean)/(n prior + k),
     k = 10 fixed in advance, prior matches only.
   Train < 2023-07-01, test ≥ 2023-07-01, one run. Primary: Δlogloss(R2 − R1) for total cards > 3.5 and > 4.5 with
   match-cluster bootstrap 95% CI (1000, seed 7). "Referee adds information" iff CI upper < 0 at both lines.
6. Settlement mismatch: document Football-Data card counting (second yellow → recorded as red; HY may or may not
   include the first yellow) vs bookmaker "total cards" and "booking points" (10/25) definitions.

Outputs: `REFEREE_AUDIT.md`, `REFEREE_AUDIT.json`, script `scripts/cards_referee_audit.py`. Negative results recorded.
