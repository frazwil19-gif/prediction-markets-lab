# NBA Live Compatibility (documentation only; no credits spent)

- The Odds API `basketball_nba` supports `h2h` (moneyline) in the `uk` region: 1 credit per call for all games. It was
  listed as active on 2026-09-23 (pre-season/outright listings); the 2026-27 regular season starts in late October.
- Historical estimator = **OddsPortal average closing odds across bookmakers**, proportionally de-vigged. The faithful
  live analogue is: average the UK bookmakers' decimal h2h odds per side, then de-vig. That is a bookmaker average,
  not an exchange price. Whether `betfair_ex_uk` quotes NBA in this account's UK panel is unverified; it would be
  logged as a secondary source.
- Timing: the validated number is a *closing* price. A 1–2 scans/day board would use earlier prices. The first prospective
  test should use a scan close to typical tip-off (00:00–03:00 UK) or accept and measure the timing difference.
- Credit estimate: 1 credit per scan (a single key covers all games) → 30–60 credits/month in season. It fits
  alongside football (~180) and tennis (≤240) under the 150-credit guard, but the headroom is getting tight. A
  prospective NBA board should share the guard.
- Prospective-board readiness: **engine validated (gate A)**, adapter not built (per the brief: historical research
  first). Estimated build is small, reusing the tennis board/ledger pattern.
