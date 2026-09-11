# Cycle 2 (Tennis Match Winner) — Plan

**STATUS: Checkpoint 1 (raw data acquisition) drafted, not yet run
against live sources. Written 2026-09-11, following Stage 3B's closure
on football (MARKET DOMINATES / NULL RESULT using public results/odds
alone — see research/cycles/CYCLE_001/results/STAGE_3B_FINAL_REPORT.md).
This is a new research cycle with its own pre-registration, per Fraser's
explicit instruction to expand into Tennis while keeping football active
as a second stream (see `claude/cycle-2-research-roadmap.md` in the
Claude Project for the full cross-sport survey behind this choice).**

## 1. Research question

Using only information that would have been available before each
match, can transparent statistical models produce well-calibrated
Match Winner probabilities for professional tennis that contain useful
predictive information beyond simple historical frequencies and beyond
the betting market itself?

This mirrors Stage 3B's framing exactly (probability-model validation,
not betting-strategy optimisation), applied to a new sport with its own
pre-registration, folds, and sealed holdout — nothing here inherits or
reuses football's fold definitions, hyperparameters, or thresholds.

## 2. Why Tennis, and why now

Per the Cycle 2 roadmap: Tennis is the lowest-risk, highest-confidence
next step because a near-exact structural analogue of the football
pipeline exists for free (Jeff Sackmann's tennis_atp/tennis_wta repos
for results/rankings, Tennis-data.co.uk for the market-consensus
benchmark, same CSV/Excel convention as football-data.co.uk), and it
opens a genuinely new, untested hypothesis space rather than re-testing
football's already-answered question. Football Cycle 2 (xG/weather/
fixture-congestion features) runs as a second, parallel stream — see
`claude/cycle-2-research-roadmap.md` §2 — not abandoned in favour of
Tennis.

## 3. Checkpoint 1 — raw data acquisition (this document's scope)

Two independent source families, deliberately NOT joined to each other
at this stage:

1. **Jeff Sackmann's tennis_atp / tennis_wta GitHub repos** — match
   results, tournament metadata, serve stats (where available), player
   rankings, player bios. License: CC BY-NC-SA 4.0 (non-commercial
   only — see `config/cycle_002_tennis_data.yaml`'s licensing block).
   Player-id-keyed, not name-string-keyed — a real structural
   improvement over football's team-name-matching problem for this
   half of the data.
2. **Tennis-data.co.uk** — per-season, per-tour bookmaker/exchange odds
   files (`.xlsx`, unlike football-data.co.uk's plain `.csv`). Same
   publisher and general convention as the football source already
   used in Cycle 1.

**Scope boundary, deliberate and important**: this checkpoint acquires
raw files only. It does NOT parse the odds `.xlsx` files, does NOT
attempt to match Tennis-data.co.uk's abbreviated name strings (e.g.
"Djokovic N.") against Sackmann's full player records, and does NOT
build a consensus benchmark. That cross-source player-identity
resolution is a genuine, nontrivial problem in its own right — the
tennis analogue of football's team-name normalisation — and is
Checkpoint 2, not acquisition. Bundling it into the acquisition script
would risk the same kind of rushed, unreviewed design Stage 3A/3B's
discipline was built to avoid.

Scope, seasons, and split (calendar-year, unlike football's Aug–May
seasons): 2021–2025, five years, mirroring Cycle 1's 5-season / 1-sealed
structure over the same real-world period. **Provisional** — not
confirmed until acquisition completes and real per-season match counts
are known, exactly as Cycle 1 treated its own split plan at this stage.

| | Trains on | Provisional role |
|---|---|---|
| Training seasons | 2021, 2022, 2023 | Model development |
| Validation season | 2024 | Walk-forward evaluation |
| Final test season | 2025 | Provisional sealed holdout — not touched until Checkpoint 2+ pre-registration is written |

### Artifacts (Checkpoint 1)

- This plan.
- `config/cycle_002_tennis_data.yaml` — no magic numbers; every value
  the acquisition run needs is read from here, per project coding
  standards.
- `src/prediction_markets_lab/ingestion/tennis_data_loader.py` — paced,
  retrying HTTP primitives, reconciled against
  `football_data_loader.py`'s conventions (same
  AcquisitionConfig/FetchResult/HttpClient/fetch_one/
  write_raw_file_atomic shape, urllib-based, same retry/backoff/
  HTML-error-page rejection safeguard), extended with a binary (`_bytes`)
  counterpart to every text primitive because Tennis-data.co.uk serves
  `.xlsx`, not plain CSV.
- `scripts/run_cycle_002_tennis_data_acquisition.py` — orchestrator:
  paced download → manifest → per-source-family schema inventory
  (empirically recording actual CSV column headers found, the same
  "discover, don't assume" philosophy Cycle 1 used for bookmaker-column
  prefixes) → data-version metadata.
- `scripts/validate_cycle_002_tennis_data_bundle.py` — post-acquisition
  integrity gate: every manifest row's file exists, hash matches, no
  empty files, no HTML error pages, xlsx files carry the real ZIP magic
  number.
- `.github/workflows/cycle_002_tennis_data_acquisition.yml` — manually
  triggered only (never on push/schedule), mirroring Cycle 1's
  phone-triggerable acquisition workflow. **Required**, not optional:
  as of 2026-09-11 both the cloud research sandbox and this project's
  own development machine are proxy-blocked from
  `raw.githubusercontent.com` and `tennis-data.co.uk` (confirmed via
  direct `curl` from both environments); GitHub's own runners have
  unrestricted internet access to both, which is exactly the same
  constraint that motivated Cycle 1's acquisition workflow in the first
  place.
- `tests/unit/test_tennis_data_loader.py` — 23 tests, entirely mocked
  HTTP (no live network access from the test suite, per project
  instructions section 19), covering: URL construction for both source
  families, HTML-error-page detection for both text and binary
  payloads, retry/backoff on 429/5xx and on transient network errors,
  no-retry on a plain non-transient HTTP error, atomic-write
  idempotency, and the hash-mismatch overwrite refusal. All 23 pass; a
  local end-to-end smoke test (a throwaway local HTTP server standing
  in for the real hosts) additionally exercised the full orchestrator
  run, `--resume`, a partial-failure path, and the validator.

### Known open item before the acquisition is actually run for real

The exact Tennis-data.co.uk file-naming convention encoded in
`config/cycle_002_tennis_data.yaml`
(`{year}/{year}.xlsx` for ATP, `{year}w/{year}.xlsx` for WTA) is a
well-documented public convention, not independently re-verified
against a live fetch by this project — the site is currently
unreachable from every environment available to this session
(proxy-blocked cloud sandbox and development machine; `robots.txt`
itself failed to fetch when queried through the research assistant's
web tools, so even a read-only page fetch could not confirm it). The
acquisition workflow's schema-inventory step, and the validator's
zip-magic-number check, are both designed to surface a wrong URL
pattern loudly (a 404/HTML-error-page rejection, or a missing PK zip
header) rather than silently accepting bad data — but the very first
real run against GitHub Actions should be treated as also validating
this assumption, not just producing data.

## 4. Checkpoint 2 (not started) — player-identity resolution and market-consensus construction

Deferred, scoped only at a high level here so it is pre-registered
rather than invented later: match Tennis-data.co.uk's name-string
records to Sackmann's player_id-keyed records (surname + first-initial
matching, disambiguated by tournament/date/round where names collide);
parse the `.xlsx` odds columns (an empirical schema inventory, not an
assumed one, exactly as Checkpoint 1's manifest records for the CSV
sources); build a fair-odds/consensus benchmark analogous to football's
`probability.consensus` + `probability.margin_removal` pipeline. This
checkpoint is where football's real "no assumed schema" discipline
matters most for tennis, given the odds file format could not be
independently verified in this environment (see §3's open item above).

## 5. Out of scope (unchanged from Stage 3B's framing, applied fresh to this sport)

Staking, EV thresholds, odds bands, favourite systems, and bet sizing
remain out of scope until well after a probability-model validation
result exists for tennis — this project has not yet established that
it has an edge in any sport to stake against.
