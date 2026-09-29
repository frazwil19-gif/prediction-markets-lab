# V2-6D — Free tennis-data.co.uk Closing-Price Diagnostic: Pre-registration (2026-09-29, before any EV/ROI was computed)

**Status label, applied to every output: CLOSING-TIME DIAGNOSTIC. Not an executable backtest, not paper betting, not prospective
evidence.** A negative result does not prove that earlier opportunities were absent. A positive result is not evidence of an
achievable edge. The frozen engines, thresholds, holdouts and ledgers are unchanged. No paid data.

## Data
- tennis-data.co.uk ATP/WTA 2021–2025 (10 files, SHA-256 in `tennis_data_co_uk/SHA256SUMS`). Odds are "most recent before play
  starts" (provider notes), so they are **closing and untimestamped**. Columns: B365 (UK book), PS (Pinnacle, not verifiably
  UK-available), BFE (Betfair Exchange, **2025 only**), Max/Avg (Oddsportal aggregates, **never executable**).
- Our Betfair BASIC datasets: frozen historical P = multiplicative de-vig of the LTP **at or before T−30 min**.

## Linkage
- Match on the same tour, |date difference| ≤ 3 days, and both players matched by the project's structural matcher
  (`normalisation/player_names.py`: surname + first initial). Exactly one tennis-data row must match; ambiguous or unmatched rows are
  excluded and counted.
- Orientation comes from our dataset's player A/B (never Winner/Loser), so results are applied only after P and prices are fixed.
- Walkovers and retirements are excluded from ROI (bookmaker retirement rules vary) and counted.

## Variants (all use bsv2-1 gates: P ≥ 0.50, net EV ≥ 2%, odds ≥ 1.33; the horizon gate is n/a)
- **V1 (time-MISALIGNED, frozen P):** frozen Betfair LTP P at T−30 against B365 closing. The price is *later* than P, so the result is
  labelled MISALIGNED and is optimistic-biased (adverse selection on late drifts).
- **V2 (time-ALIGNED, exchange-derived P, 2025 only):** P = multiplicative de-vig of BFE closing (W/L) against B365 closing (same
  collection). This is closest to the frozen engine's source, but it is closing and one year only.
- **V3 (time-ALIGNED, reference P, all years):** P = multiplicative de-vig of Pinnacle closing against B365 closing. This is a sharp-book
  reference, **not** the frozen engine, so it answers only "does Bet365 close above a sharp fair price?".
- Self-check: BFE closing against its own de-vig (2025) must show EV ≤ 0 after 5% commission.

## Time-mismatch sensitivity
The distribution of |P(Betfair T−30) − P(Pinnacle close)| and |P(T−30) − P(BFE close, 2025)|, plus the share of V1 "value" bets where
the closing reference moved against the selection.

## Reporting
For each variant, by tour and year:
- coverage (matched / available);
- the B365 odds distribution;
- counts of favourites, positive EV and qualifying bets;
- frequency per 100 matches;
- mean estimated EV;
- realised ROI with a match-level bootstrap 95% CI (2,000 resamples, seed 20260929).

Nothing is tuned; no threshold search. Code: `scripts/v2_6d_tennis_closing_diagnostic.py`.
