# Football Settlement Migration: Odds API scores → football-data.co.uk (approved in principle; SHADOW stage)

**Why:** football settlement costs up to ~180 Odds API credits/month for information (final scores) that
football-data.co.uk publishes free (twice-weekly updates), and GitHub runners can reach it.

## Built (this phase)
- `settlement/football_data_results.py`: parses football-data CSVs, maps names **only via explicit aliases**
  (`config/football_team_aliases.yaml`; added Charlton, Wrexham AFC, Falkirk F.C., Dundee FC), and matches a
  fixture by competition + exact home/away pair within ±3 days of kickoff. It returns MATCHED / AMBIGUOUS /
  NOT_FOUND (still pending or postponed; football-data lists played matches only) / UNRESOLVED_NAME. **Nothing
  ambiguous or unresolved is ever settled.** 11 tests (aliases, draw, reschedule, postponement, reversed fixture,
  duplicates, wrong competition, FTR consistency, bad dates).
- The existing Odds API settlement now also archives every raw scores payload (`settlement_archive/`, additive;
  behaviour unchanged).
- `scripts/run_football_settlement_shadow.py` runs in `settlement_and_performance` (continue-on-error). It compares every
  completed Odds API fixture with football-data (score + result agreement), lists what football-data *would* settle
  for pending past-kickoff bets, and writes `status/settlement_shadow.json`. **It never writes the ledger. 0 credits.**

## Why shadow first (not historical)
The Odds API scores endpoint returns only the last 3 days, and the existing path has settled **0 bets** so far (the
only past-kickoff bets are provider-id-less backfill rows). So there is no stored historical reference, and the ≥100-
fixture comparison has to accumulate prospectively. Each settlement run archives ~all completed matches in the 3
leagues for the last 3 days (≈20–40 fixtures/run in match weeks), so **≥100 comparisons ≈ 1–2 match weeks** (the
international break delays this).

## Migration gate (mechanical)
Switch football-data to PRIMARY only when: ≥100 MATCHED fixture comparisons · 0 score disagreements · every
UNRESOLVED_NAME resolved by an explicit alias · no AMBIGUOUS auto-settled · postponement cases observed and correctly
left pending · local and clean-clone tests pass. Then: add `settlement_source` / `mapping_status` columns to the
ledger (schema change, a separate approved commit), keep the Odds API path as a **fallback only** for bets unsettled 4
days after kickoff, and log the source per settled bet (`football_data_uk` / `odds_api_fallback` / `manual_review`).
