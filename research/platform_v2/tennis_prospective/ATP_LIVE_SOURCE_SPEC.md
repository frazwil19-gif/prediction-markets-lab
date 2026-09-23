# ATP (and WTA) Live Source Spec — The Odds API

- Discovery: `GET /v4/sports` (free), keep `active` keys starting `tennis_atp_` / `tennis_wta_`. Provider-documented
  coverage: ATP: Australian Open, French Open, Wimbledon, US Open, Indian Wells, Miami, Monte-Carlo, Madrid, Italian,
  Canadian, Cincinnati, Shanghai, Paris (1000s), and 500s incl. Barcelona, Halle, Queen's, Hamburg, Washington,
  Dubai, Qatar, China Open, Munich. WTA: the Slams and 1000/500 events incl. Singapore, Wuhan, Guadalajara,
  Monterrey, Stuttgart, Charleston.
- Odds: `GET /v4/sports/{key}/odds?regions=uk&markets=h2h&oddsFormat=decimal`: 1 credit per key; exchange books
  return `h2h_lay` alongside (confirmed live 2026-09-23, 6 of 6 events had Betfair back and lay).
- Parsed per event: provider event id, tournament title, commence_time, player A (provider home_team) / B,
  `betfair_ex_uk` back/lay with `last_update`, and every UK bookmaker's h2h (kept for research only).
- Surface is not provided by the feed. It is recorded when the tournament is known (a later enrichment); the board
  never guesses it.
- Credits: every call logged to `tennis_predictions/credit_log.csv` (`x-requests-used`/`remaining`/`last`);
  tennis fetches stop below 150 remaining.
- Expected usage: 2 board scans/day × active keys. ATP+WTA covered weeks typically have 1–4 keys, and many weeks
  have 0 (e.g. 23 Sep 2026: 1). Projection: **about 60–240 credits/month** (≈ 2 × ~1.5 keys × ~30 days in busy
  months, near zero in off weeks), on top of football's ~180. The guard keeps the total inside 500.
