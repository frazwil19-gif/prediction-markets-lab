# Rejected Ideas / Near Misses / Do Not Retest

These three folders exist to prevent the most common failure mode in
informal research: quietly re-testing the same idea over and over
until, by chance, one test looks good, then treating that test as the
result.

## `research/rejected_ideas/`

A hypothesis or behaviour moves here when it completed a proper test
(out-of-sample, paper, or live) and failed — i.e. evidence grade
`C`/`INSUFFICIENT` after a reasonable testing period, or a negative
out-of-sample/paper/live result. Each entry is a dated Markdown note:
`YYYY-MM-DD_<hypothesis_id>.md` containing the hypothesis statement,
what was tested, the result, and why it was rejected.

**When may a rejected idea be revisited?** Only if there is a genuinely
new reason to believe the underlying market has changed — e.g. a new
data source becomes available, a market structure change (new
exchange, rule change), or a specific, named flaw in the *original
test* (not the conclusion) is found. "I have a feeling about this
again" is not sufficient. Any revisit must be logged as a *new*
hypothesis with a `notes` field explicitly linking back to the
original rejected hypothesis ID and stating the new reason.

## `research/near_misses/`

For hypotheses that did not clear the bar for `VALIDATED` but were
close enough, or interesting enough, that they should stay on the
radar rather than being dismissed outright (evidence grade `C` with a
promising but statistically weak out-of-sample result, for example).
Near-misses can be prioritised for further data collection via
`research_prioritisation.py`, but must not be traded on above paper
scale until they earn a proper grade.

## `research/do_not_retest/`

For ideas that should not be retested at all for the foreseeable
future — not just "didn't work this time" but "this is very unlikely
to ever work, or retesting it is not worth the multiple-testing cost."
Examples: an idea that is logically incoherent on reflection, one that
was tested many times across a hypothesis family and consistently
failed, or one that would require a data source explicitly ruled out
by the project's cost constraints (section 6). Each entry states why
it is here and, if relevant, what would have to change for it to be
reconsidered (e.g. "only revisit if a free source of live line-movement
data becomes available").

## Why this matters (multiple testing)

If ten near-identical hypotheses are tested against the same season of
data, at least one is likely to look significant by chance alone, even
if none of them reflect a real pattern. Recording every rejected and
near-miss idea — not just the ones that eventually "worked" — is what
lets `research_prioritisation.py` and evidence grading account for
`multiple_testing_family` size honestly, and what stops the project
from unconsciously curve-fitting to its own historical data one
retest at a time.
