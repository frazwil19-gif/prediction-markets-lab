# Running Cycle 1 Data Acquisition From Your Phone

**Prerequisite: the repository must already be on GitHub.** If it
isn't yet, stop here and complete
[`docs/PHONE_ONLY_GITHUB_HANDOFF.md`](PHONE_ONLY_GITHUB_HANDOFF.md)
first, including its verification checklist. Everything below assumes
that checklist is already ticked off.

This is the one part of the project that needs a genuine internet
fetch of ~15 files, paced a few seconds apart, taking several minutes
total. You do not need a laptop for this — it runs on GitHub's own
servers, triggered by a single tap from the GitHub mobile app or
mobile Safari.

## Steps

1. **Open the GitHub app** (or github.com in Safari/Chrome) and go to
   the `prediction-markets-lab` repository.
2. Tap **Actions** (usually in the bottom tab bar or the "..." menu on
   mobile web).
3. In the workflow list, tap **Cycle 1 Data Acquisition**.
4. Tap **Run workflow**.
5. **Leave every option at its default** for the first full run:
   - `dry_run`: leave unchecked (off)
   - `competitions`: leave blank (acquires all of E0, E1, SC0)
   - `seasons`: leave blank (acquires all 5 target seasons)
   - `request_delay_seconds`: leave at `6`
   - `resume_existing`: leave checked (on) — safe even on a first run
6. Tap the green **Run workflow** button to confirm.
7. **Wait for completion.** With 15 files paced 6 seconds apart plus
   retries, expect roughly 5–15 minutes. You can close the app; the
   job keeps running on GitHub's servers. Come back later and check
   **Actions** again — a green checkmark means it finished.
8. **Open the completed run** (tap it in the Actions list).
9. Scroll to **Artifacts** at the bottom of the run page. You'll see:
   - `cycle_001-manifest-and-version` (small — the file list and data
     version)
   - `cycle_001-audit-reports` (the quality/coverage reports)
   - `cycle_001-processed-data` (the processed match/odds/consensus
     tables and CSV samples)
   - `cycle_001-raw-files` (the original downloaded CSVs — kept as an
     artifact only, not committed to the repository, to keep it small)
   Tap any artifact to download it as a zip, or just note that it
   exists — you don't need to download it yourself unless you want to
   inspect it.
10. **Check the validation result.** The workflow uploads
    `reports/audits/CYCLE_001_DATA_BUNDLE_VALIDATION.md` as part of the
    `cycle_001-audit-reports` artifact — download that artifact and
    open the file, or check the "Validate the acquired bundle" step's
    log output directly in the Actions run for the printed summary.
    The result will be exactly one of:
    - **`VALID`** — no issues found. Safe to hand off for Stage 3B
      review (Stage 3B itself — Elo/Poisson baseline models — is a
      separate, not-yet-started task; a `VALID` bundle does not start
      it automatically).
    - **`VALID_WITH_NONCRITICAL_WARNINGS`** — usable, but read the
      warnings list first and use judgement before treating the
      dataset as ready.
    - **`INVALID`** — **stop. Do not proceed to modelling.** Read the
      critical issues listed, and see "If the run fails" below.
11. **Return the results for independent review.** Whichever verdict
    you get, copy back the validation result, the critical
    issues/warnings list, and the acquisition summary JSON (see
    "What to send back" below) before anyone — human or AI — treats
    the dataset as ready for the next stage.

## If the run fails

- **Red X on "Run the complete test suite first"**: something in the
  codebase itself is broken — this should not happen if you haven't
  edited any Python files; report it back for review.
- **Red X on "Run acquisition"**: check the log for which file failed
  and why (rate limit, network error, or an HTML error page rejected).
  Re-run with `resume_existing` checked — it will skip files already
  downloaded and only retry what failed.
- **Red X on "Validate the acquired bundle"**: the run downloaded
  something, but the bundle didn't pass validation (e.g. fewer files
  than expected, or a data-quality problem). Check the log output for
  the specific critical issue(s) listed.

## Avoiding duplicate downloads

`resume_existing` (on by default) makes the workflow skip any file
already present with a matching content hash — so re-running the
workflow after a partial failure is always safe and won't re-download
everything from scratch. Only uncheck `resume_existing` if you
deliberately want to force a fresh re-download of everything (e.g. you
suspect a file was corrupted).

## What to send back to Claude or ChatGPT for review

After a run completes, copy back:
1. The final validation result (`VALID` / `VALID_WITH_NONCRITICAL_WARNINGS` / `INVALID`).
2. The summary JSON printed at the end of the "Run acquisition" step
   log (files attempted/acquired/failed, total matches, rate-limit
   events).
3. Any critical issues or warnings listed by the validator step.

With that, Claude/ChatGPT can confirm whether Cycle 1's dataset is
genuinely ready for Stage 3B (Elo/Poisson baseline models) — this
workflow only acquires and validates data; it never trains a model or
places a bet.
