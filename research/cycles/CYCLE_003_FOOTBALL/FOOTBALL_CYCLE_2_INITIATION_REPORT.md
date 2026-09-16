# Football Cycle 2 — Initiation Report

**Date:** 2026-09-16
**Status:** Initiation audit only, per the operator's explicit instruction:
"Do NOT start broad acquisition until this initiation report is complete."
Nothing in this document acquires, links, or analyses any new data. It is
research/planning only, answering the operator's 12-point return list.

---

## 1. Exact final closure record for Tennis Workstream B

Per the operator's Option-C decision, recorded permanently in
`research/cycles/CYCLE_002_TENNIS/WORKSTREAM_B_CLOSURE.md`:

| Item | Status |
|---|---|
| Tennis Cycle 1 predictive modelling | PARTIAL |
| Tennis Workstream B 2021-2023 market-edge discovery | CLOSED — NULL RESULT |
| Families tested | 13 |
| Families promoted | 0 |
| 2024 development validation | NOT OPENED / NOT REQUIRED |
| 2025 market-edge OOS | NOT OPENED / NOT REQUIRED |
| Executable strategies | 0 |
| Paper bets | 0 |
| Live bets | 0 |

Tennis discovery is not being extended with new covariates. Any future
tennis cycle requires a materially new information source and a fresh
pre-registration.

## 2. What Football Cycle 1 already tested and rejected

Full record: `research/cycles/CYCLE_001/results/STAGE_3B_FINAL_REPORT.md`
and `research/cycles/CYCLE_001/results/FINAL_HOLDOUT_PROTOCOL.md`.

Cycle 1 asked: does public historical match-result/goal data, modelled by
transparent statistical methods (naive frequency, Elo, Poisson, and blends
including market-inclusive blends), contain predictive information beyond
a liquid bookmaker closing consensus? Tested on 5,800 matches (E0/E1/SC0,
2020/21-2024/25), with a walk-forward development design (2020/21-2023/24)
and a single sealed 2024/25 holdout (1,160 matches), opened exactly once.

**Result: MARKET DOMINATES / NULL RESULT**, replicated on both development
folds and the sealed holdout:
- Ranking naive < Elo < Poisson < `elo_poisson` blend < market held on
  every fold and on the holdout, every time.
- The only non-trivial candidate not numerically identical to market
  (`elo_poisson`) lost to market by log-loss delta +0.0169 on the holdout,
  95% CI **[+0.0066, +0.0274]**, entirely above zero (market wins).
- Market-inclusive blends (`market_elo`, `market_poisson`,
  `market_elo_poisson`) calibrated to **100% market weight** on every fold
  and on the full training period — the model repeatedly found nothing to
  add on top of market and said so honestly rather than forcing a nonzero
  blend weight.
- One real, replicated defect was found and reported, not fixed
  retroactively: Elo's away-outcome calibration is measurably worse than
  its home-outcome calibration (ECE 0.0605 on development, 0.0470 on
  holdout — same direction, both periods). This is a property of Elo
  itself, not new information; it does not change the overall verdict but
  is worth remembering if Elo is reused as a Cycle 2 baseline input.

Cycle 1's own closing statement (`STAGE_3B_FINAL_REPORT.md` §7) already
anticipated exactly this moment: "Any further work on this question — a
genuinely new information source ... or a materially different modelling
approach — would constitute a new research cycle (Cycle 2) with its own
pre-registration, not a continuation of Cycle 1."

**A leakage/provenance note carried forward from Cycle 1, important for
Cycle 2's design (see §7-8 below): the 2024/25 season's outcomes have
already been compared against model probability at the pooled/season
level** (the log-loss and calibration numbers above). This is a much
weaker form of exposure than the tennis Workstream B case (no
disagreement-bin-vs-outcome relationship was ever examined, no subgroup
was ever looked at against results), but it is not nothing, and per the
same discipline that corrected the tennis holdout classification, it
should be named rather than assumed away.

## 3. Existing football assets we can reuse

**Data (reusable as-is, no re-acquisition needed):**
- `data/processed/football/cycle_001_matches_full.csv` — 5,800 matches,
  E0 (Premier League), E1 (Championship), SC0 (Scottish Premiership),
  5 seasons each (2020/21-2024/25), frozen at
  `cycle_001_v1.0.0-20260910T234139`.
- `data/processed/football/cycle_001_consensus_full.csv` (11,540 rows) —
  margin-removed market-consensus probabilities per match.
- `data/processed/football/cycle_001_bookmaker_markets_full.csv`
  (49,673 rows) — per-bookmaker opening/closing odds.
- `config/football_team_aliases.yaml` — team name normalisation, the join
  key any new source (xG, weather) will need to match against.

**Code (reusable unchanged):**
- `src/prediction_markets_lab/ingestion/football_data_loader.py`,
  `football_bookmaker_extraction.py` — acquisition/parsing, not needed
  again unless new seasons are added.
- `src/prediction_markets_lab/probability/margin_removal.py`,
  `consensus.py`, `market_pipeline.py` — margin-removal and consensus math,
  sport-agnostic, directly reusable for any new football market-comparison
  work.
- `src/prediction_markets_lab/validation/time_splits.py::SplitPlan` and
  `validate_test_period_untouched()` — chronological split enforcement,
  reusable unchanged for Cycle 2's own frozen split.
- `src/prediction_markets_lab/validation/leakage_checks.py` — generic
  leakage-checking utilities.
- Bootstrap/calibration metrics pattern (paired block-by-date bootstrap,
  ECE by bin) demonstrated in `STAGE_3B_FINAL_REPORT.md` — the same
  general pattern already reused across Tennis Cycle 1 and Workstream B;
  no new statistical machinery needs to be invented for Cycle 2.
- `src/prediction_markets_lab/models/football_elo.py`,
  `football_poisson.py`, `football_blended.py`,
  `football_naive_frequency.py` — the frozen Cycle 1 baselines, kept as
  reference/comparison points, **not to be retrained or modified** (same
  discipline as tennis's frozen Global Elo).
- 88 football-specific unit tests, part of the 633/633 passing suite.

**What is NOT reusable / must be newly built:**
- **No Betfair (exchange) football data exists.** Football-Data.co.uk
  provides only two static bookmaker-odds snapshots per match (opening,
  closing), never an intraday exchange price series — this was already
  investigated and explicitly excluded in Cycle 1
  (`DECISION_LOG.md`: "Hypothesis H-FB-003 (exchange-price value) excluded
  from Cycle 1 ... Football-Data.co.uk has no exchange (Smarkets/Betfair)
  price history at all"). The tennis Betfair ingestion/linkage code
  (`betfair_market_index.py`, `tennis_betfair_linkage.py`,
  `betfair_historical_schema.py`) is Betfair-schema-specific and not
  directly reusable for football unless/until a separate Betfair football
  historical download is acquired — a real gap for any eventual net-EV
  work, though not a blocker for discovery (which only needs the existing
  closing-consensus benchmark, exactly as Cycle 1 used it).
- All xG/fixture-congestion/weather ingestion, canonicalisation, and
  linkage-by-team-and-date code — genuinely new, none of it exists yet.

## 4. Highest-value genuinely new information families (ranked)

1. **Expected Goals (xG) + shot-quality data** — highest expected
   information gain; distinguishes match *performance* from match
   *result*, which is exactly the kind of signal a market pricing off
   recent results (not underlying process) could plausibly under- or
   over-react to.
2. **Fixture congestion / rest** — zero new acquisition risk, pure
   feature engineering on data already in hand (match dates already
   exist; needs no new source).
3. **Weather at venue** — clean, simple REST API, no scraping/ToS risk;
   needs a one-time stadium-coordinate lookup table (reusable across all
   three competitions).
4. **Referee assignments/tendencies** — a free by-product of the same xG
   scrape (FBref schedule tables carry a referee column); add only after
   xG is working.
5. **Injuries/suspensions** — real look-ahead-bias risk (return-date
   fields are retrospective); deprioritised per the operator's explicit
   instruction ("ONLY if historical data quality is reliable").

This ranking matches the project's own 2026-09-11 research (roadmap §3)
and was spot-checked again today (§5 below) rather than assumed still
current from five days ago.

## 5. Candidate free data sources for each family — re-verified today, with one real new coverage finding

- **xG**: `soccerdata` (PyPI, actively maintained, current version 1.9.1,
  wraps FBref + Understat + 6 other sources) or `understatapi` as a
  narrower alternative. Both free, no account required.
  **New finding, verified directly against FBref and not merely assumed
  from the 2026-09-11 research**: FBref's xG columns (via its StatsBomb
  partnership) are confirmed present on the **Premier League (E0)** stats
  page but confirmed **absent** on the **Championship (E1)** stats page
  (checked directly: the Championship table has no xG/xGA columns at
  all). Understat's own league list is limited to the "big five" European
  leagues plus the Russian Premier League — it does not cover the
  Championship or the Scottish Premiership at all. **This means xG
  coverage across our existing three-competition dataset is very likely
  E0-only, not E0+E1+SC0** — a real, load-bearing coverage constraint that
  must be confirmed empirically (not assumed) before any acquisition
  decision, and that materially changes what Cycle 2's initial sample
  size will be if E1/SC0 have to be dropped or handled with a different,
  non-xG data family instead.
- **Fixture congestion/rest**: derived directly from
  `cycle_001_matches_full.csv`'s own `match_date` column — no external
  source needed at all.
- **Weather**: Open-Meteo Historical Weather API (re-verified today:
  ERA5 back to 1940, ERA5-Land to 1950, ECMWF IFS at 9km resolution from
  2017+; free for non-commercial use, no explicit rate limit stated on
  the public docs). Needs a one-time ground-truth stadium-coordinates
  table for the ~40-50 grounds across E0/E1/SC0's 5 seasons.
- **Referee assignments**: FBref match-report/schedule tables, same
  scrape as xG (subject to the same E0-only coverage caveat above for any
  competition that lacks a full stats page).

## 6. Historical coverage available

Existing football backbone: 5 seasons (2020/21-2024/25) × 3 competitions
(E0, E1, SC0) = 5,800 matches, already acquired, canonicalised, and
frozen. xG coverage (pending the empirical per-competition check flagged
in §5) is expected to match this window for E0 only, since FBref/Understat
xG partnerships generally extend back several years for top-tier leagues.
Weather coverage comfortably exceeds this window for all venues (ERA5
back to 1940). Fixture-congestion coverage is complete by construction
(derived from data already in hand).

## 7. Expected linkage difficulty

- **xG → existing match backbone**: joins by (team, date), reusing
  `config/football_team_aliases.yaml`'s existing normalisation — the same
  join-key discipline already proven for the bookmaker-odds linkage in
  Cycle 1. Expected difficulty: LOW for E0 (well-structured FBref/
  Understat team names, already partially covered by existing aliases);
  UNKNOWN for E1/SC0 pending the coverage question in §5 (if no xG
  exists for those competitions, there is no linkage to attempt, not a
  hard linkage problem).
- **Weather → existing match backbone**: joins by (venue-coordinates,
  match_date/kickoff_time) — a new, one-time stadium-coordinate lookup
  table is the only new artifact needed; kickoff time (not just date) may
  need separate confirmation since Football-Data.co.uk's schema was not
  audited for a kickoff-time field in Cycle 1 (flagged as a to-check item,
  not assumed present).
- **Fixture congestion**: no linkage needed — pure feature derivation on
  data already joined.

## 8. Leakage/provenance risks

- **The 2024/25-exposure question (see §2)**: Stage 3B already computed
  pooled log-loss/calibration numbers against market on 2024/25 outcomes.
  Per the same standard that corrected the tennis holdout design (looking
  at an outcome-vs-market relationship, even in aggregate, is a form of
  exposure), **2024/25 should not be treated as a pristine, never-touched
  final holdout for Cycle 2** without an explicit decision to accept that
  weaker form of exposure. Two honest options, left open for Fraser/the
  operator rather than decided here (see §10):
  (a) fold 2024/25 into Cycle 2's *development* period (since we already
  know its market log-loss numbers, exactly as we already know the
  training seasons' numbers) and reserve a genuinely untouched period —
  2025/26, once a complete season is available — as the sealed final
  holdout; or
  (b) accept the weaker, aggregate-only prior exposure as immaterial
  (since no xG-specific or subgroup-specific pattern was ever examined
  against 2024/25 outcomes) and keep 2024/25 as the final holdout, on the
  basis that the exposure is qualitatively different in kind, not degree,
  from the tennis case.
- **xG retrospective revision risk**: some providers revise shot-location/
  xG-model outputs after the fact (rare, but real for shot-model version
  changes) — must confirm any acquired xG snapshot is dated/hashed at
  acquisition time, exactly as the Betfair raw downloads were hashed
  before parsing in Workstream B.
- **Referee/injury retrospective fields**: injuries/suspensions carry a
  known look-ahead risk (already flagged in Cycle 1's original football
  source survey) — this is why the family is ranked last and gated on
  "ONLY if historical data quality is reliable," not started by default.
- **Team-name join drift**: promoted/relegated teams across 5 seasons
  mean `football_team_aliases.yaml` is explicitly documented as
  incomplete for the full 5-season window (seeded only from 2024/25) —
  any new source join must re-validate against the full alias list, not
  assume it is complete.

## 9. Recommended first data family to acquire

**xG for E0 (Premier League) only, as a scoped first slice** — highest
expected information gain, free, actively-maintained tooling, and the one
competition where coverage is already confirmed rather than assumed.
E1/SC0 xG availability should be checked empirically (a single scoping
query per competition, not a full acquisition) before deciding whether to
(a) extend xG to those competitions if coverage exists, (b) drop them from
the xG-specific hypothesis family while keeping them in the
congestion/weather families (which have no such competition-specific
coverage constraint), or (c) treat E0-only xG as Cycle 2's full initial
scope. This mirrors the "audit before acquire" discipline used throughout
Workstream B (small-sample audits before every bulk decision) rather than
downloading everything and discovering the gap afterward.

Fixture congestion and weather can be developed in parallel at low
marginal cost/risk once the xG scoping question is resolved, since neither
depends on it.

## 10. Proposed chronological research split

Proposed, not frozen — the 2024/25-exposure question in §8 must be
resolved first, since it changes which seasons fall in which bucket:

| Split | Seasons (if 2024/25 accepted as final holdout, option (b) in §8) | Seasons (if 2024/25 folded into development, option (a)) |
|---|---|---|
| Discovery | 2020/21-2022/23 | 2020/21-2022/23 |
| Development validation | 2023/24 | 2023/24-2024/25 |
| Final historical OOS | 2024/25 | 2025/26 (once complete) |
| Future prospective | 2025/26 onward | 2026/27 onward |

Global Elo/Poisson from Cycle 1 remain frozen reference baselines
throughout, exactly as tennis's Global Elo was reused unmodified in
Workstream B — Cycle 2 is not re-tuning Cycle 1's models, it is testing
whether xG/congestion/weather add anything **on top of** the existing
market/Elo/Poisson benchmark.

## 11. Explicit stop/go criteria

Per the operator's Step 6 (speed-to-edge) and Step 7 instructions:
- **GO**: a data family's coverage/quality audit confirms it is usable
  (non-trivial coverage, verifiable timestamps, no unresolvable leakage
  risk) → proceed to canonicalisation, linkage, and pre-registration of
  specific hypotheses for that family, following the same
  acquire→audit→canonicalise→link→describe→analyse-quality→hypothesise
  pipeline used throughout this project.
- **STOP on a family**: if an audit shows a data family has no credible
  incremental information, or coverage is too thin to test (e.g. if E1/
  SC0 xG genuinely doesn't exist), reject that family and move to the
  next-ranked one rather than spending further time trying to rescue it.
- **STOP on the whole cycle**: if, after testing the pre-registered
  Cycle-2 hypothesis families with the same Bonferroni-corrected,
  mechanism-required, N-gated discipline used in Tennis Workstream B, the
  result is another clean null, immediately prepare the next-ranked
  research stream (Cricket T20, per the existing roadmap ranking) rather
  than expanding Football Cycle 2 with further ad-hoc variables — the
  identical discipline just applied to tennis.
- **No staking, EV-threshold, or execution-strategy work** is authorised
  until a candidate survives discovery, development validation, and a
  sealed final historical OOS confirmation — unchanged from both Cycle 1's
  and Workstream B's standing rule.

## 12. Fastest credible route from today's state to the first football market-edge test

1. Empirical xG-coverage scoping check for E1 and SC0 (a handful of
   `soccerdata`/direct-FBref queries, not a bulk scrape) — resolves the
   real coverage question flagged in §5/§9 before any commitment.
2. Resolve the 2024/25-exposure question (§8/§10) — a short decision, not
   a redesign, needed before any split is frozen.
3. Acquire xG for the confirmed-coverage competition(s) for the discovery
   period only, hash/version it immediately (same discipline as every
   prior acquisition in this project), and run the existing
   audit→canonicalise→link pipeline pattern reused from Workstream B.
4. Build fixture-congestion features in parallel (zero acquisition,
   available immediately from data already in hand).
5. Acquire weather via Open-Meteo for the same discovery-period matches,
   once the stadium-coordinate table exists.
6. Pre-register a small number of specific, falsifiable hypotheses per
   family (mirroring tennis's 13-family discipline) **before** looking at
   any outcome data for the new features.
7. Run the discovery-period analysis with the same Bonferroni-corrected
   bootstrap-CI framework already built and proven in Workstream B
   (`run_discovery_analysis_2021_2023.py`'s statistical core is directly
   adaptable, not football-specific).

Because the market-comparison, chronological-split, and statistical
machinery all already exist and are proven, the genuinely new work is
narrow: acquire/link three new data families and pre-register hypotheses
against them. No new statistical or validation infrastructure needs to be
built from scratch.

---

**Nothing beyond this report has been executed.** No xG, weather, or
congestion data has been acquired, downloaded, linked, or analysed. Per
the operator's explicit instruction, broad acquisition begins only after
this initiation report is reviewed and the two open questions in §8/§9/§12
step 1-2 are resolved.
