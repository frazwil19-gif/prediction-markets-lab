# Current State Audit — Prediction Markets Lab

Date: 2026-09-10
Performed by: Claude Cowork, working directly in the local repository at `~/Projects/prediction-markets-lab/` (first session under the local-first / GitHub-canonical architecture).

## 1. Repository state

- Branch: `master`.
- Local HEAD: `3b75e14` ("chore: re-register manual acquisition workflow on default branch").
- Remote HEAD (`origin/master`): `3b75e14` — identical, no divergence.
- Working tree: clean, nothing to commit before this audit.
- Repo is public: `github.com/frazwil19-gif/prediction-markets-lab`.

## 2. Test state

- **255 passed, 0 failed, 0 warnings** (`pytest -q`, 2.11s).
- Note: the system Python on this Mac's Cowork workspace is 3.10.12, but `pyproject.toml` requires `>=3.11`, so a plain `pip install -e .` fails immediately with a Python-version error. Resolved for this session by creating a project-local Python 3.11 environment with `uv` (`uv venv --python 3.11 .venv`, then `uv pip install -r requirements.txt -e .`) — `.venv/` is already correctly gitignored. This should be documented (e.g. in `CONTRIBUTING.md`) so it isn't rediscovered each session.

## 3. Stage 3A acquisition state — NOT CONFIRMED VALID (see below)

- GitHub Actions run **31262827699** ("Cycle 1 Data Acquisition", `workflow_dispatch`, triggered 2026-08-08T14:47:26Z) shows **status: completed, conclusion: success**, and every step (checkout, deps, test suite, acquisition, bundle validation, all four artifact uploads) reports `success`.
- However, the artifact sizes are inconsistent with a genuine full acquisition and this could not be independently confirmed:
  - `cycle_001-raw-files`: **8,003 bytes** total for what should be 15 real season CSVs across E0/E1/SC0, 2020/21–2024/25 (the project's own manifest notes state a real season file runs ~228–380 rows). 8KB total is far too small for 15 real files.
  - `cycle_001-audit-reports`: **20,910 bytes** — smaller than the audit reports generated for the earlier 29-match `EXCERPT_VALIDATION_ONLY` pipeline test (~79KB combined). A genuine full 15-file acquisition should produce audit reports at least as large as the excerpt-scale test, not smaller.
  - `cycle_001-processed-data`: 1,397,178 bytes — the one artifact that looks plausibly sized for real processed output, though this alone doesn't confirm the raw inputs were genuine.
- I could not inspect the actual artifact contents or the job's raw logs to resolve this: GitHub's API refused both (`403 Must have admin rights to Repository`) for anonymous/unauthenticated access, even though the repo is public — artifact/log downloads require an authenticated request.
- **The repository itself cannot resolve this either.** By explicit design (see `research/cycles/CYCLE_001/DECISION_LOG.md` and the workflow's own comments), raw and processed Cycle 1 data are *never committed to git* — only uploaded as GitHub Actions artifacts (90-day retention; this run's artifacts expire 2026-11-06, so there's time). The only football data actually committed to the repo is the original 10-row-per-file `EXCERPT_VALIDATION_ONLY` fixtures used for earlier pipeline testing.

**Verdict: UNKNOWN, not VALID** (as of the initial pass — see update below).

### Update (later the same day, 2026-09-10): manifest reviewed, verdict improves to VALID_WITH_NONCRITICAL_WARNINGS

Direct API/log access from this device remained blocked throughout (see §3a below), so Fraser downloaded the `cycle_001-manifest-and-version` artifact himself via his browser and shared `football_data_manifest.csv`. It lists all **15** expected rows (E0/E1/SC0 × 2020/21–2024/25), each `validation_status: OK`:

- E0 (Premier League): 380 rows/season, all 5 seasons — correct for a 20-team league (20×19×2).
- E1 (Championship): 552 rows/season, all 5 seasons — correct for a 24-team league.
- SC0 (Scottish Premiership): 228 rows/season, all 5 seasons — correct for a 12-team league.
- Column counts step up from 106 to 120–121 in the 2024/25 season across all three competitions, consistent with the previously-documented finding that football-data.co.uk added bookmaker columns in later seasons.

Fraser also shared `cycle_001_data_version.json` from the same artifact bundle: `raw_file_count: 15` (matches `expected_raw_file_count: 15`), `total_matches: 5800`, `files_failed: 0`, `rate_limit_events: 0`. The 5,800 figure is an independent cross-check that lines up exactly with the manifest's per-file row counts (380×5 + 552×5 + 228×5 = 5,800) — a second, separately-computed number agreeing with the first strengthens confidence this wasn't a truncated or fabricated run.

This is a materially different picture from the raw-files artifact's 8KB size, which drove the original "UNKNOWN" verdict: 8KB is plausible after all for 15 highly repetitive CSVs (team names, dates, decimal odds) once GitHub's artifact compression is accounted for — that concern is provisionally retracted, not confirmed disproven.

**This manifest alone is not sufficient to declare Stage 3A fully closed.** It confirms row/column counts and a self-reported "OK" status, but not the deeper Phase C checks the project's own directive requires: duplicates, missingness, team-name normalisation, bookmaker-market extraction sanity, chronological ordering, no leakage. The `cycle_001-audit-reports` artifact (the one with `football_duplicate_review.csv`, `unresolved_team_names.csv`, `football_data_quality_by_*.csv`, `football_data_schema_inventory.csv`) is what actually contains those checks — requested from Fraser, pending as of this writing.

### Update 2 (same day): audit-reports reviewed, team-name gap found and fixed

Fraser shared `cycle_001-audit-reports`. The real per-run output is `CYCLE_001_DATA_BUNDLE_VALIDATION.md` (the other files in that zip under `excerpt_validation/` are stale leftovers from the earlier 29-match test, swept up by the upload glob, not new output). Its verdict:

- **Result: VALID_WITH_NONCRITICAL_WARNINGS**
- Critical issues: none
- Warning: **1,623 of 5,800 rows (28%) with unresolved team-name normalisation**

Root cause (confirmed by reading the code): `config/football_team_aliases.yaml` was seeded only from teams visible in the tiny 10-row 2024/25 excerpts used during earlier pipeline testing — its own header says as much. It was missing not only every team relegated/promoted out of/into E0/E1/SC0 across 2020/21-2023/24, but even 4 teams from the *current* 2024/25 Championship season that the excerpt's first few rows happened not to include.

Fraser also shared `cycle_001-raw-files` and `cycle_001-processed-data`. This surfaced a separate, useful finding: **`cycle_001-raw-files` does not actually contain the real downloaded season CSVs** — it's the same stale 3-file excerpt set as before (confirms the original 8KB-size suspicion was directionally correct, just not for the reason first guessed). The real full data survived intact elsewhere: `cycle_001-processed-data` contains `cycle_001_matches_full.csv` (5,800 rows, `home_team_raw`/`away_team_raw`/`*_normalised`/`normalisation_status` columns) — i.e. the actual acquisition succeeded and was processed correctly, but the workflow's raw-file artifact upload step isn't capturing what it should. **Follow-up recommended** (not blocking): fix the raw-files artifact path in `.github/workflows/cycle_001_data_acquisition.yml` so future runs actually preserve the downloaded source CSVs for provenance, not just the excerpts already sitting in the repo.

Using `cycle_001_matches_full.csv`'s `normalisation_status` column, the exact 15 unresolved raw names (and row counts) were identified directly from the real data — no guessing: `Luton` (111), `Burnley` (103), `Birmingham` (92), `Huddersfield` (92), `Livingston` (76), `Reading` (69), `Rotherham` (69), `Sheffield Weds` (69), `Barnsley` (46), `Blackpool` (46), `Plymouth` (46), `Wycombe` (23), `Peterboro` (23), `Wigan` (23), `Hamilton` (19).

**Fix applied**: added all 15 as new canonical entries to `config/football_team_aliases.yaml` (Luton Town, Burnley, Birmingham City, Huddersfield Town, Reading, Rotherham United, Sheffield Wednesday, Barnsley, Blackpool, Plymouth Argyle, Wycombe Wanderers, Peterborough United, Wigan Athletic, Livingston, Hamilton Academical). **Verified against the real data**: re-running the project's own `load_alias_table`/`normalise_team_name` against all 67 distinct raw team names actually present in `cycle_001_matches_full.csv` resolves every one — `still unresolved after fix: []`. Full test suite still 255/255 passing after the change.

**This closes the only open warning.** Combined with the earlier manifest and `total_matches` cross-checks, Stage 3A now has no known outstanding issues.

### 3a. Network access note

Both the GitHub Actions job-log endpoint and the artifact-zip download endpoint are blocked from this device's Cowork VM with `X-Proxy-Error: blocked-by-allowlist` — this is the device's own network egress policy blocking the redirect target (blob storage), not a GitHub permissions issue (confirmed after adding Actions:read to the token; the block persisted identically). Direct API/log/artifact access to this repo from this device is not currently possible; retrieving artifact contents requires Fraser to download them via his own browser and share them here.

## 4. Bundle validation

- The workflow's own "Validate the acquired bundle" step passed, but that verdict is downstream of the same unconfirmed acquisition step — it isn't independent evidence.

## 5. Data coverage

- Committed to git: only `E0_excerpt.csv` / `E1_excerpt.csv` / `SC0_excerpt.csv` under `data/raw/football/football_data_co_uk/{comp}/2024_25/`, each a 9–10 row excerpt, explicitly marked `EXCERPT_VALID_NOT_FULL_SEASON` in the manifest.
- No full-season files, no other seasons (2020/21–2023/24), present in the working copy — expected, given the never-commit-raw-data design, but it means "does the full dataset exist" can only be answered by inspecting the Aug 8 run's artifacts directly.

## 6. Provenance

- The only manifest in git (`data/raw/football/football_data_manifest_EXCERPT_VALIDATION_ONLY.csv`) documents 3 excerpt rows (2024/25 season only, one per competition), each explicitly annotated as not the full season.
- The real manifest (`reports/audits/football_data_manifest.csv`) referenced by the workflow exists only inside the `cycle_001-manifest-and-version` artifact (925 bytes) — small, consistent with a manifest describing few/small files rather than a full 15-file dataset, but not conclusive without opening it.

## 7. Research status

- Hypothesis Registry: 11 hypotheses — 7 `IDEA`, 4 `DATA_REQUIRED`. None validated. Consistent with expected status.
- Behaviour Atlas: header row only, zero populated behaviours. Correctly empty — no premature entries.
- No model trained; Elo/Poisson model files (`src/prediction_markets_lab/models/*`) are present but are thin placeholder implementations, not yet fitted to data.

## 8. Discrepancies vs. prior documented status

- Prior notes (from the ChatGPT session) described run 31262827699 as "IN PROGRESS." It has since finished with a "success" conclusion — but success at the workflow level does not mean the acquisition is scientifically valid; see §3.
- The "255/255 tests passing" status was previously reported and is now independently reconfirmed today, in a fresh environment.

## 9. Recommended next action — GO/NO-GO

**Superseded below (Update 3). The "GO — STAGE 3A COMPLETE" verdict this section originally gave was premature and is retracted.**

### Update 3 (same day): Stage 3A reopened for a freeze-integrity check, per external review

A second review (relayed by Fraser) correctly challenged the GO verdict above: fixing `config/football_team_aliases.yaml` and re-running `load_alias_table`/`normalise_team_name` against the 67 distinct raw names proves the **config and code** now resolve every name. It does **not** prove that `cycle_001_matches_full.csv` itself — generated by the 2026-08-08 run, *before* that fix existed — was ever regenerated with corrected values. Updating the YAML after the fact does not retroactively change rows a prior run already wrote to a workflow artifact.

**Section A finding (confirmed, not assumed):** `git log` shows no commit after `17db644` (the alias fix) until this one. The authoritative processed dataset is deliberately never committed to git (workflow-artifact-only by design), so the only way to know whether it reflects the fix is provenance, not inspection — and the provenance says no: the artifacts reviewed in Update 2 are all from run `31262827699` (2026-08-08), which predates `17db644`. **The alias fix has not yet been propagated into the authoritative dataset.** A fresh acquisition run is required.

**Section B finding (root-caused by reading the actual code, not guessed):** `scripts/run_cycle_001_data_acquisition.py` wrote real downloaded season CSVs to `<output-root>/football/football_data_co_uk/...` (missing a `raw` path segment), while `.github/workflows/cycle_001_data_acquisition.yml`'s "Upload raw source files" step globs `data/raw/football/**`. Since the workflow never passes `--output-root`, real downloads landed at `data/football/football_data_co_uk/...` and were never under `data/raw/` at all — so that glob only ever matched the 3 pre-existing `*_excerpt.csv` stub files committed to the repo for excerpt validation, never a genuine download, on every run to date.

**Fix applied** (commit `edef3f4`): `raw_root` now includes the `raw` segment, matching the `data/raw/football/football_data_co_uk/{E0,E1,SC0}/...` structure the repo already uses for the committed excerpt stubs, and matching the workflow's glob. Updated the two existing unit tests that hardcoded the old path, and added a regression test that ties the script's default raw-output path directly to the workflow's upload glob (parses the workflow YAML and asserts the two agree), so this class of drift cannot silently reoccur. Full suite: **256/256 passing.**

**Current status: NO-GO on Stage 3A closure. Reopened for a bounded freeze-integrity check** (per the external review's framing — this is not a return to open-ended Stage 3A research):

1. Push commit `edef3f4` to `origin/master` (blocked from both the cloud sandbox and this device's Cowork VM by their respective network/proxy policies — pushed instead from Fraser's own local Terminal, same as the two earlier pushes this session).
2. Re-trigger the `Cycle 1 Data Acquisition` workflow (`workflow_dispatch`, defaults are fine — `resume_existing: true` will not skip anything, since no file exists yet at the corrected `data/raw/...` destination path) so the full 15-file/5-competition-season matrix is reacquired and reprocessed from source under both fixes at once.
3. Fraser downloads all 4 resulting artifacts and shares them here for re-validation (Sections C/D of the directive): 0 unresolved team names required (not 1,623 down to 0 after a patch — 0 from the run itself), no alias collisions, no duplicate match identities, full provenance hashes (source/processed/config/alias-table/code commit), and a plain `VALID` bundle-validator verdict (not `VALID_WITH_NONCRITICAL_WARNINGS`).
4. Only once that's confirmed: properly freeze with versioned metadata (data version ID, hashes, code commit, validator result, exclusions, freeze timestamp) and update this document's verdict to STAGE 3A COMPLETE — then proceed to Stage 3B (market baseline → Elo → Poisson → blend, log loss + Brier + calibration, paired bootstrap CIs, strict chronological validation with an untouched final holdout).

**Follow-up, not blocking:** this device's Cowork VM and the cloud sandbox both currently have network paths to GitHub that work for some operations (cloning, in one case) but not others (pushing, API/artifact access) — direct programmatic push/artifact-retrieval from either sandbox cannot be relied on this session; manual push-from-Terminal and manual artifact download-and-share remain the working pattern.
