# Phase V2-2 Workstream B — WTA Match Winner: Pre-registration (2026-09-23, written before any WTA outcome statistic was computed)

## Question
How accurately can WTA match winners be predicted, especially at high probabilities? WTA is a separate population from
ATP; no ATP result is assumed to transfer.

## Exposure status
The project has **never** analysed WTA data. Before this protocol, the only WTA contact was: (a) file structure and
row counts of the downloaded result files (levels, surfaces, counts of RET / W/O strings, duplicate check), and
(b) a 545-market *name-only* sample of the Betfair archive (V2-1). No price or outcome relationship has been computed.
**Therefore 2024–2025 is a genuinely untouched holdout**, opened once after this protocol and `HOLDOUT_SPEC.json` are
committed. 2021–2023 is development.

## Data
- Results: TennisCourtLog `tennis_wta/wta_matches_{2018..2026}.csv` (Jeff Sackmann-derived to 2024,
  tennis-data.co.uk-derived from 2025; CC BY-NC-SA 4.0, used for non-commercial personal research with attribution;
  SHA-256 in `data/raw/tennis/tennis_court_log_wta/SHA256SUMS`). Tour level only (Slams, 1000, 500, 250, Finals,
  BJK Cup, Olympics, United Cup). No player ids, so players are keyed by case-folded full name.
  TML's own WTA files could not be used because `stats.tennismylife.org` is blocked by the network allowlist.
- Markets: Fraser's Betfair BASIC `data.tar`. All singles MATCH_ODDS markets were re-extracted (173,659 markets; the
  extraction covers 12,952 of 12,952 ATP-linked markets, used as a completeness check).

## Target and handling rules (fixed now)
- Player A / B orientation: A = alphabetically first case-folded name (never outcome-dependent). `outcome_a_won` from winner/loser.
- **Walkovers** (score contains W/O): excluded (no match played; consistent with ATP canonical).
- **Retirements** (score contains RET): included, with the official winner as the result (consistent with ATP).
- Missing result / abandoned / market void with no result row: excluded (no label).

## Linkage
The tested `classify_tennis_betfair_match` (unchanged) with the same 14-day tolerance and zero-price-point exclusion
as ATP. MATCHED only; AMBIGUOUS and UNMATCHED are excluded and counted.

## Market probability (identical to the ATP engine)
Both runners' last-traded prices at or before the final market time minus 30 minutes, each at most 1 hour old;
two-runner proportional normalisation.

## Statistical baseline
Global Elo (the project's `tennis_elo`; initial 1500). Ratings are warmed up on 2018–2020 results (update only,
never evaluated). k is chosen from the ATP grid [16, 24, 32, 40, 48, 64] by 2021–2023 log loss, then frozen. Order
within a date: the tournament-date / round order used for ATP. No surface Elo (negative for ATP; not re-attempted).
Stack: logistic regression on [logit(market), logit(Elo)] fitted on 2021–2023, the same single combination as ATP.

## Selection, reporting and gate
Default estimator: market. Replaced only if a candidate's holdout log loss is lower with a paired-bootstrap 95% CI
(seed 20260923, 2,000 resamples) excluding zero. Report everything listed for ATP: bands 50–54.9 … 95%+, thresholds
≥55 … ≥95 (count, share, mean P, expected vs actual, Wilson CI), and year / surface / level subgroups.
Calibration verdict: the slope's 95% bootstrap CI includes 1, **and** band fit is judged with a multiplicity-aware
rule: every band with n ≥ 200 must have its predicted mean inside the realised rate's **99.5%** Wilson interval
(Bonferroni over 10 bands). This lesson comes from ATP V2-1 and is fixed *before* seeing WTA.
