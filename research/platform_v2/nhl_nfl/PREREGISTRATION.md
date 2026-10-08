# NHL + NFL moneyline consensus engines — historical validation (PRE-REGISTRATION, 2026-10-08)

Written before any probability is computed from the data. Approach identical in spirit to the NBA engine (V2-3), using
the market estimator only. The engine's probability is the bookmaker consensus with the margin removed. No model is
fitted, so nothing can be tuned.

- **Data:** flancast90/sportsbookreview-scraper archives (MIT licence): `nhl_archive_10Y.json` (13,678 games) and
  `nfl_archive_10Y.json` (2,956 games), seasons 2011–2021, with closing American moneylines and final scores. Only
  counts and field names were inspected before writing this file.
- **Probability:** proportional de-vig of the closing home/away moneylines (American → decimal). Excluded: games with
  a missing or zero moneyline, two-way book sum outside [1.00, 1.15], or tied finals.
- **Periods:**
  - DEVELOPMENT (reported only; nothing is chosen on it): seasons 2011–2019;
  - HOLDOUT: seasons 2020 and 2021, scored once.
- **Targets:** home win (all games); also the favourite-side selection (p ≥ 0.5) for the band table.
- **Gate (same rule as NBA V2-3), on the holdout:**
  - A if the calibration slope's 95% bootstrap CI (2,000 resamples, seed 20261008) includes 1 AND every favourite band
    with n ≥ 200 (50–60, 60–70, 70–80, 80–90, 90+%) has its mean predicted P inside the realised 99.5% Wilson interval;
  - B if exactly one of the two holds; C if neither.
- **Consequence:**
  - A → registry status VALIDATED_HISTORICAL. A live bet still needs bsv2-4 PAPER_BET and Fraser's money-eligibility
    approval. Prospective collection from the Odds API (icehockey_nhl / americanfootball_nfl) confirms it on current
    data.
  - B → PROVISIONAL_PROSPECTIVE (paper only).
  - C → not deployed.
- **Stated limitation:** the newest validated season is 2021. Current-season calibration is checked prospectively.
