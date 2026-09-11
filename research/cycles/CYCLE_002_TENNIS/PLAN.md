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

### Diagnostic run #1 findings (2026-09-11) and resolution

The first real run against GitHub Actions (diagnostic pass,
`max_retries=1`) failed all 28 targets, in two distinct, unrelated
ways:

1. **All 18 Sackmann targets (both tours): uniform `HTTP Error 404`.**
   Investigated by independently corroborating the URL convention
   (branch `master`, `{tour}_matches_{season}.csv` etc.) against a
   search-engine-indexed GitHub page for this exact repo/path/branch
   combination, and by finding that `raw.githubusercontent.com`
   returning spurious 404s for files (and sometimes entire
   repositories) that genuinely exist is a real, recurring,
   GitHub-side CDN bug -- see
   [community discussion #169205](https://github.com/orgs/community/discussions/169205)
   (open, ongoing as of Feb 2026) and
   [#53538](https://github.com/orgs/community/discussions/53538)
   (GitHub confirmed "errant code has been rolled back for the 404s"
   after an August 2025 episode affecting whole repositories). This
   matches our symptom exactly: every file in both repos failing
   uniformly, at a single point in time, is far more consistent with a
   repo-wide raw-serving outage than with 18 independently wrong
   filenames across two repos. **No code or config change made** for
   this half of the failure -- `config/cycle_002_tennis_data.yaml`'s
   Sackmann `base_url`/filename templates are believed correct as
   written. The next real run should simply be retried; if it 404s
   again at the same uniform, whole-repo scale, treat that as evidence
   against this explanation and re-open the investigation.
2. **All 10 Tennis-data.co.uk targets: `[SSL: TLSV1_ALERT_INTERNAL_ERROR]`.**
   A TLS-handshake-level failure, not an HTTP-level one -- the
   connection was rejected before any HTTP request completed. Root
   cause: OpenSSL 3.x's default security level refuses the legacy
   signature algorithms tennis-data.co.uk's old server still uses; this
   is a well-documented OpenSSL 3.0 behaviour, not a wrong URL --
   see [bpo-43791](https://bugs.python.org/issue43791). **Fixed** in
   `tennis_data_loader.py` via `build_legacy_tolerant_ssl_context()`,
   which lowers the cipher security level (`DEFAULT@SECLEVEL=0`) while
   leaving certificate verification (`CERT_REQUIRED`,
   `check_hostname=True`) untouched; `HttpClient` uses this context by
   default. Not host-scoped (also used for the Sackmann fetches) since
   raw.githubusercontent.com has never shown this failure and a lower
   security floor doesn't force weak ciphers there -- it only permits
   falling back to them if a server insists. Covered by
   `tests/unit/test_tennis_data_loader.py`'s
   `test_build_legacy_tolerant_ssl_context_*` and
   `test_http_client_*` tests.

The Tennis-data.co.uk file-naming convention itself
(`{year}/{year}.xlsx` for ATP, `{year}w/{year}.xlsx` for WTA) remains
unverified against an actual successful download (the TLS failure
happened before any content was received) -- the acquisition
workflow's schema-inventory step and the validator's zip-magic-number
check are still the real check for that, on the next run.

### Diagnostic run #2 findings (2026-09-11): the real bug behind the Sackmann 404s

A second real run (this time with the TLS fix applied and the full
`max_retries=4` budget) reproduced the identical uniform 404 across
Sackmann targets, which is what it took to stop treating "recurring
CDN flakiness" as sufficient and find the actual bug: `HttpClient`
uses `urllib.request.urlopen`, which -- unlike the `requests` library
-- raises `urllib.error.HTTPError` for *any* non-2xx response rather
than returning it as a normal response object. `HTTPError` is a
subclass of `URLError`, so `_retry_loop`'s
`except (urllib.error.URLError, TimeoutError, OSError)` clause was
catching every real HTTP error status -- including a plain 404 --
and misclassifying it as a transient network error: retried
`max_retries` times with full exponential backoff (~2.5 minutes
wasted per failing file) and finally reported as `"network error:
HTTP Error 404: Not Found"`, masking the real, immediate,
no-retry-needed `http_error` outcome the status-code branching was
designed to produce. **This is a real, previously latent bug**, not a
tennis-specific one -- the identical pattern exists in
`football_data_loader.py`'s `HttpClient.get`; it simply never
manifested there because Cycle 1's real acquisition run never hit a
genuine 404 (worth a follow-up fix there too, tracked separately, not
bundled into this fix).

**Fixed** in `tennis_data_loader.py`: `HttpClient._get_raw` now catches
`urllib.error.HTTPError` explicitly and converts it back into the
normal `(status, content_type, body)` tuple shape, restoring
`_retry_loop`'s intended branching (429/5xx retry; everything else,
404 included, fails immediately with the correct status and message).
Covered by three new regression tests in
`tests/unit/test_tennis_data_loader.py` that mock `urllib.request.urlopen`
directly (the only way to reach this code path) rather than going
through the higher-level `FakeClient` the rest of the suite uses.

This bug fix does not, by itself, prove the Sackmann URL convention is
correct -- it only means a genuine 404 will now be reported instantly
and honestly instead of being disguised as a 2.5-minute-per-file
"network error". To settle the URL question directly rather than
continuing to reason about it from outside GitHub's network, the
workflow now runs a lightweight, non-blocking diagnostic step
(`Diagnose Sackmann repo/branch access from this runner`) immediately
after checkout: it queries `api.github.com`'s repo metadata for the
real `default_branch` and does a direct status check of the exact URL
the acquisition will use, from the same runner and network context
that produced the 404s -- in seconds, before committing to the full
paced 28-file run. The next run's log should be read for that step's
output first.

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
