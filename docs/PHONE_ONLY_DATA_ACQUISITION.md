# Running Cycle 1 Data Acquisition From Your Phone

This is the one part of the project that needs a genuine internet
fetch of ~15 files, paced a few seconds apart, taking several minutes
total. You do not need a laptop for this — it runs on GitHub's own
servers, triggered by a single tap from the GitHub mobile app or
mobile Safari.

## Prerequisite (one-time only)

The repository must be on GitHub first. If it isn't yet, see "GitHub
handoff" in the latest status report — you'll need to upload it once
(see below for the no-connector fallback method).

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
10. **Check the validation result.** Look at the run's step list for
    "Validate the acquired bundle." If it shows a green checkmark, the
    result was `VALID` or `VALID_WITH_NONCRITICAL_WARNINGS`. If it
    shows a red X, the result was `INVALID` — **do not proceed to
    modelling.** Open `reports/audits/CYCLE_001_DATA_BUNDLE_VALIDATION.md`
    (visible directly in the repository after the run, since that
    report itself does get committed... actually check the workflow
    log output for the validator's printed summary, since the .md
    file lives only in the artifact bundle unless you've configured
    the workflow to commit it back).

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
