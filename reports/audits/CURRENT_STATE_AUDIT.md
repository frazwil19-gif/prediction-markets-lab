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

**Still NO-GO on Stage 3B, but close.** The manifest (§3 update) is a strong positive signal — real, correct football-league row counts and a season-by-season column-count pattern that matches known source-schema evolution, not something a broken or excerpt-only run would plausibly produce. It is not yet sufficient on its own to declare Stage 3A complete and freeze the dataset per Phase C/D of the project directive.

**Next step:** review the `cycle_001-audit-reports` artifact (duplicate review, missingness by season, team-name resolution, bookmaker coverage, schema inventory) once Fraser shares it. If those check out, declare **STAGE 3A COMPLETE — CYCLE 1 DATASET FROZEN** (with the frozen dataset's provenance being this GitHub Actions run + its artifacts, since raw/processed data is deliberately not committed to git) and only then propose the exact Stage 3B baseline-modelling task (market consensus → Elo → Poisson → blend, each benchmarked against the market, per the directive).

A remaining open item unrelated to data validity: this device's network policy blocks direct GitHub Actions log/artifact access (§3a), so future acquisition-run checks will need the same manual download-and-share step from Fraser, or a different access path if one becomes available.
