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

### Diagnostic run #3 findings (2026-09-11): first TLS fix insufficient

Run #3 (with both prior fixes applied) showed the retry-loop and
diagnostic-step fixes both working correctly, but the TLS fix did
NOT resolve Tennis-data.co.uk -- the identical
`[SSL: TLSV1_ALERT_INTERNAL_ERROR]` recurred on every target.
`build_legacy_tolerant_ssl_context()` now stacks two more independent,
individually-documented compatibility relaxations on top of the
original `@SECLEVEL=0`: capping `maximum_version` at TLS 1.2 (some old
servers choke on a modern client's TLS 1.3 ClientHello extensions and
answer with this same generic alert), and enabling
`OP_LEGACY_SERVER_CONNECT` where the Python/OpenSSL build exposes it
(this project's pinned Python 3.11 does not; guarded with `getattr`).
Certificate verification remains untouched throughout. Not yet
confirmed against the real site -- next run is the test.

### Diagnostic run #4 findings (2026-09-11): the Sackmann repos are genuinely gone

The upgraded diagnostic (`git ls-remote --symref` plus a real
`git clone`) settled it: both `git` (talking directly to GitHub's git
servers, no CDN, no cache, no rate limit) and `api.github.com` report
a clean `Repository not found` for `JeffSackmann/tennis_atp` and
`/tennis_wta` at that exact path. This is not CDN flakiness, not a
rate limit, and not a wrong branch name -- two full diagnostic
attempts and this blog post's worth of hedging were wrong. The repos
do not exist there any more (deleted, renamed, transferred, or made
private -- indistinguishable from outside).

Independent check: Jeff Sackmann's own site
(https://www.jeffsackmann.com/) still points to `github.com/JeffSackmann`
as the home of his tennis database, and the account is referenced
elsewhere as still active, so this is very likely a rename/
restructure rather than the whole project disappearing. A new
diagnostic script, `scripts/_diagnose_sackmann_repos.py` (run via the
workflow's "Find where JeffSackmann's tennis repos actually live now"
step), checks whether the account still exists and searches GitHub's
API for whatever tennis-named repos it owns today, so
`config/cycle_002_tennis_data.yaml` can be pointed at wherever this
data actually lives now rather than guessing again. Not yet run --
next real trigger is the test.

### Diagnostic run #5 findings (2026-09-11): replacement source validated, acquisition re-pointed

Per explicit instruction: do not keep patching a source confirmed
unavailable, and do not switch URLs without validating the replacement
against real content first. Search for a current authoritative
location/mirror/fork of Sackmann's ATP data turned up
**Tennismylife/TML-Database** (github.com/Tennismylife/TML-Database),
which states in its own README that it is "Based on Jeff Sackmann's
work: tennis_atp" and is actively updated. Validated before switching,
not assumed:

- Fetched and inspected `2021.csv`, `2024.csv`, and `2025.csv` directly
  from `raw.githubusercontent.com/Tennismylife/TML-Database/master/`.
- Confirmed the column schema is identical to Sackmann's original
  (`tourney_id, tourney_name, surface, ..., winner_rank,
  winner_rank_points, ..., w_ace, w_df, ...`), and that every match row
  already carries winner/loser rank, rank_points, age, height, hand,
  and country — the fields that previously required Sackmann's
  separate `rankings_*.csv` / `players.csv` files. That separate
  acquisition step is dropped entirely rather than re-pointed at a new
  URL, because there is nothing left for it to fetch.
- No actively-maintained free WTA equivalent was found in a reasonably
  bounded search of Tennismylife's other repos and a handful of public
  Kaggle mirrors (the only WTA datasets found were stale, ~2019, or
  required Kaggle auth to verify). **Decision: descope WTA from
  Checkpoint 1**, proceed ATP-only. This is a deliberate, reasoned
  descope, not a silent drop — ATP alone is a complete, decades-deep
  tour, sufficient for a real Match Winner research cycle. WTA is
  queued for a follow-up phase if/when a comparable live source turns
  up; nothing in the loader code hardcodes a single tour, so re-adding
  it later is a config change, not a redesign.

`config/cycle_002_tennis_data.yaml` was rewritten around this:
`sources.tml_database_atp` replaces `sackmann_atp`/`sackmann_wta`;
`tml_database_match_files.filename_template` (`"{season}.csv"`)
replaces the three separate Sackmann match/ranking/player file
sections; `tours` is now ATP-only; `expected_raw_file_count` dropped
from 28 to 10 (5 ATP match-file seasons + 5 Tennis-data.co.uk odds
seasons). `tennis_data_loader.py`'s `sackmann_match_file_url` /
`sackmann_ranking_file_url` / `sackmann_player_file_url` were removed
and replaced with a single `tml_database_match_file_url`;
`run_cycle_002_tennis_data_acquisition.py`'s `plan_targets()` was
rewritten to match (the `sackmann_repo_key`/`sackmann_tour_slug`
helpers and the ranking/player target loops are gone). Full test suite
passes (422/422) and `--dry-run` against the live config produces
exactly the expected 10 targets with correctly-built URLs for both
source families.

Tennis-data.co.uk's TLS situation is unchanged from diagnostic run #3
above: the strengthened `build_legacy_tolerant_ssl_context()` fix
(SECLEVEL=0 + TLS 1.2 ceiling + legacy renegotiation flag) has not yet
been re-confirmed against the real site by an actual acquisition run.
Per explicit instruction, this gets **one** further sensible automated
attempt (the next real trigger of the acquisition workflow); if it
still fails, the response is the simplest safe fallback — a one-time
manual download of the (now only 5, ATP-only) `.xlsx` files, hashed
and dropped into the existing raw/manifest structure so provenance is
preserved exactly as if acquired automatically — not another round of
SSL-context tweaking.

**Status at end of this pivot**: acquisition code and config are
believed acquisition-ready for a real GitHub Actions run against
Tennismylife/TML-Database (ATP match data) and Tennis-data.co.uk (odds,
TLS fix unconfirmed). No real download of either source has happened
yet from an environment with real internet access — everything above
is validated via direct content inspection (TML-Database) and via
unit tests + a local `--dry-run` (target-planning logic), not via a
completed acquisition run. The next real trigger of
`.github/workflows/cycle_002_tennis_data_acquisition.yml` is the actual
test of both the TML-Database source and the TLS fix.

### Fallback tooling prepared ahead of need (2026-09-12)

Per explicit instruction to design the simplest safe fallback rather
than wait to discover mid-run that TLS still doesn't work:
`scripts/import_manual_tennis_data_co_uk_files.py` now exists,
committed (`82c9471`) alongside 10 new unit tests (432/432 project-wide
passing). It validates manually-downloaded `.xlsx` files against the
exact checks an automated fetch would apply (real xlsx ZIP magic
number, not an HTML error page, no silent overwrite of differing
content), places them at the precise raw path
`run_cycle_002_tennis_data_acquisition.py`'s `plan_targets()` expects,
and prints the follow-up `--resume` command. The orchestrator's
manifest now also records an `acquisition_method` column
(`automated_fetch` vs. `resumed_existing_file`) so provenance stays
honest about which rows came from a live fetch this run versus a
pre-existing file. Verified end-to-end in a scratch directory (not
committed, cleaned up after): 5 synthetic `.xlsx` files imported ->
orchestrator `--resume` picked up all 10 targets (5 TML-Database + 5
Tennis-data.co.uk) with 0 failures -> manifest correctly recorded
`acquisition_method=resumed_existing_file` for every row. Not yet
needed for real — this is prepared in advance, not a sign the TLS fix
has failed again; the real GitHub Actions trigger (TML-Database +
current TLS fix) has not yet run.


### Diagnostic runs #6-#8 (2026-09-13, 2026-09-15): tennis-data.co.uk confirmed server-side broken, made optional

The first real GitHub Actions trigger (run 34766536563, 2026-09-13)
gave the first genuine test of both the pivot and the TLS fix
together: TML-Database fetched all 5 ATP season files cleanly (0
failures) -- the pivot itself is now confirmed working against live
internet, not just mocks. Tennis-data.co.uk failed all 5 odds files
with the identical `[SSL: TLSV1_ALERT_INTERNAL_ERROR]` diagnostic run
#3 first saw, meaning the "strengthened" `build_legacy_tolerant_ssl_context()`
fix had not actually been fully exercised: its third mitigation,
`ssl.OP_LEGACY_SERVER_CONNECT`, was only added to Python's `ssl` module
in 3.12 and silently no-op'd under the workflow's pinned Python 3.11
(commit `f0cb675` bumped the workflow to 3.12 to let it actually run).

A second real trigger (run 34999310740, 2026-09-15, on Python 3.12)
failed the exact same way -- `TLSV1_ALERT_INTERNAL_ERROR` on every
Tennis-data.co.uk file, unchanged. At that point three independent,
genuinely unblocked TLS attempts had now failed identically: this
GitHub Actions run, Anthropic's own separate web-fetch infrastructure
(`WebFetch` tool, hit the identical `TLSV1_ALERT_INTERNAL_ERROR`
fetching the site's robots.txt), and an unmodified, real Chrome browser
manually opening `https://www.tennis-data.co.uk/2021/2021.xlsx`
(`ERR_SSL_PROTOCOL_ERROR`). Chrome failing is the decisive signal --
browsers tolerate almost any legacy-server TLS quirk, so if Chrome
cannot complete the handshake either, the server itself is currently
broken, not a client-compatibility gap. This also means the
manual-download fallback built in diagnostic run's "Fallback tooling
prepared ahead of need" section above cannot currently be exercised
for real either -- it depends on a browser being able to reach the
site, and right now none can.

Per the project's explicit "one final sensible TLS attempt, then
fall back rather than keep engineering around it" instruction, and
per Fraser's own line that a persistently broken source should not
block all tennis progress: `tennis-data.co.uk` is now listed in
`config/cycle_002_tennis_data.yaml`'s new `optional_source_families`.
`run_cycle_002_tennis_data_acquisition.py` (commit `01dabec`) exits 0
when only optional-family targets fail, as long as required-family
targets (`tml_database_match`) succeed -- the failure is still fully
recorded (never hidden, never fabricated as present) in the manifest
and the data-version summary's new `files_failed_optional` /
`failed_optional_source_keys` fields, and the optional family now gets
a much smaller retry budget (1 vs. the required default of 4) so a
run against a source already confirmed broken fails in seconds per
file rather than burning the full ~2.5min/file backoff schedule. 6 new
tests added (`tests/unit/test_cycle_002_tennis_acquisition_orchestration.py`,
the first for this script); full suite 453/453 passing.

This is not a permanent removal: `tennis-data.co.uk` stays configured
and gets attempted (briefly) on every run, so an actual server-side
recovery would be picked up automatically. Odds/consensus work
(Checkpoint 2's market-consensus benchmark) stays blocked until either
the site recovers, or a validated alternative source is wired in (two
candidates surfaced by web search 2026-09-15 -- a Kaggle dataset and a
GitHub mirror, both ultimately re-publishing tennis-data.co.uk's own
data in a consolidated, not per-season, shape -- neither validated
against real content yet, per this project's "never blindly swap a
source" rule). Checkpoint 1's match-result data (`tml_database_match`)
is unaffected and can proceed now.


### Diagnostic run #9 (2026-09-15): optional-source retry budget silently never applied on a real run, fixed

Run 35002551488 (the first real trigger after `01dabec`) confirmed the
"don't block the run" half of that fix worked -- the log correctly showed
`[tennis_data_co_uk:...] FAILED (optional source, not blocking the run): ...`
for each odds-file failure, and TML-Database's 5 files kept fetching
normally alongside it. But the run still took ~11-12 minutes instead of the
intended ~1-2, meaning the reduced retry budget (`pacing.optional_source_max_retries`)
was not actually taking effect. Cause: `01dabec`'s code only switched to the
reduced budget `if args.max_retries is not None else <reduced>` -- reasoning
that an explicit CLI override should win uniformly for both families. But
the workflow's own "Build acquisition command" step *always* appends
`--max-retries` with its `workflow_dispatch` input's current value (that
input has a default of `"4"`, and unlike the boolean/list inputs this one
has no `if` guard around the flag), so `args.max_retries` is never actually
`None` on any real run -- the reduced-budget branch could only ever be
exercised by a direct Python invocation, which is exactly how the original
tests (passing, but not representative of real usage) missed it.

Separately, that same run was cancelled on its last item
(`[tennis_data_co_uk:ATP:2025] fetching...`) before finishing, so no
manifest or data-version file was written at all -- a design fragility
(everything is written only at the very end of `run()`) worth a future look,
not addressed here, since it's orthogonal to the retry-budget bug itself.

Fix (commit `51fbaf5`): added an independent `--optional-max-retries` CLI
flag, fully decoupled from `--max-retries`. The optional family's budget now
always defaults to `config.pacing.optional_source_max_retries` regardless of
what `--max-retries` carries, and is only raised by explicitly passing
`--optional-max-retries` too (kept as a deliberate escape hatch for a
diagnostic pass that wants everything uniform). The now-stale test asserting
`--max-retries` applied to both families was replaced with two tests: one
confirming `--max-retries` affects only the required family, one confirming
`--optional-max-retries` independently controls the optional family. Full
suite: 454/454 passing. Not yet re-verified against a real GitHub Actions
run as of this writing -- awaiting Fraser's push and a re-trigger.

## 4. Checkpoint 2 (partially prepared) — player-identity resolution and market-consensus construction

Scoped here so it is pre-registered rather than invented later: match
Tennis-data.co.uk's abbreviated name-string records to TML-Database's
full-name records (surname + first-initial matching, disambiguated by
tournament/date/round where names collide); parse the `.xlsx` odds
columns (an empirical schema inventory, not an assumed one, exactly as
Checkpoint 1's manifest records for the CSV sources); build a
fair-odds/consensus benchmark analogous to football's
`probability.consensus` + `probability.margin_removal` pipeline. This
checkpoint is where football's real "no assumed schema" discipline
matters most for tennis, given the odds file format could not be
independently verified in this environment (see §3's open item above).

**Prepared ahead of real data (2026-09-12, commit `9492a90`)**: the
name-matching piece is the one part of Checkpoint 2 that doesn't
require having seen real acquired files first, so it's built and
tested now rather than waiting —
`src/prediction_markets_lab/normalisation/player_names.py` (previously
a Stage-1 placeholder with no logic) implements
`parse_abbreviated_name`, `full_name_matches_abbreviated`, and
`match_abbreviated_name_to_candidates`. It matches structurally
(surname suffix + first-initial, diacritic/case-insensitive) rather
than via a static alias table the way `team_names.py` does for
football's small fixed team set, because tennis has thousands of
players across decades. Critically, it never guesses: when more than
one candidate matches a given "Surname I." string (e.g. two different
"Zverev A."s), the result surfaces `ambiguous_matches` rather than
picking one, so real disambiguation-by-tournament/date/round can be
wired in once real match-level context exists. 15 new tests, built and
verified against synthetic data reflecting the publicly documented
convention -- NOT yet checked against a real downloaded Tennis-data.co.uk
file (every automated fetch attempt against that site has failed so
far), exactly as `tennis_data_loader.py`'s own HTTP primitives were
built and tested against mocks before ever touching a real network
connection. **Still not started**: the `.xlsx` odds-column schema
inventory (cannot be done responsibly without real files -- this is
exactly the kind of "discover, don't assume" step this project's
instructions require), and wiring the matcher + parsed odds +
`probability.consensus`/`probability.margin_removal` (both already
sport-agnostic and reusable as-is) into an actual per-match consensus
benchmark. Full project suite: 447/447 passing.

## 5. Out of scope (unchanged from Stage 3B's framing, applied fresh to this sport)

Staking, EV thresholds, odds bands, favourite systems, and bet sizing
remain out of scope until well after a probability-model validation
result exists for tennis — this project has not yet established that
it has an edge in any sport to stake against.
