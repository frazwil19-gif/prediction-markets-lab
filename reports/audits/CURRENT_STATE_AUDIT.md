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

**Verdict: UNKNOWN, not VALID.** The workflow says "success," but the artifact sizes suggest the acquisition may have silently produced excerpt-scale or partial output rather than the full 15-file dataset (e.g. `--resume` matching on filename rather than genuinely comparing content, or a silent early exit). This must be resolved before Stage 3A can be declared complete or Stage 3B can start.

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

**NO-GO on Stage 3B.** Do not begin modelling. The single next bottleneck is resolving whether the Aug 8 acquisition run actually captured the full 15-file dataset or silently produced excerpt/partial output. Two ways to resolve it:

1. **Fraser downloads the artifacts** from the run's GitHub page (Actions → this workflow run → Artifacts section — `cycle_001-manifest-and-version` and `cycle_001-audit-reports` are small and quick) and shares the manifest CSV / acquisition report content back.
2. **Provide a fine-grained, read-only, repo-scoped GitHub personal access token.** This unblocks direct API access to run logs and artifact contents from here, and will keep being useful going forward (checking future acquisition runs, triggering `workflow_dispatch` runs on request) rather than hitting this same anonymous-access wall each time.

Either way, if the full dataset turns out genuinely incomplete/invalid, the fix is to re-run the acquisition workflow (or debug why it under-acquired) — not to proceed to modelling on what's there now.
