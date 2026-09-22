# GitHub-to-ChatGPT Daily Bet Card Handoff Design

**Date:** 2026-09-19
**Context:** operator's "MAJOR NEXT PHASE — TURN THE EXISTING PREDICTION MARKETS LAB INTO AN AUTOMATED DAILY BET-SELECTION PLATFORM" instruction, Phase 6 (handoff design) and Phase 7 (chat output format).
**Status:** Design proposal, one assumption flagged as unverified (see §4). Not yet tested end-to-end because it depends on a real `THE_ODDS_API_KEY` and a live `daily_scan.yml` run, neither of which exist yet this session.

## 1. Roles (unchanged from the operator's target architecture)

- **GitHub** is the single shared source of truth. It is the only channel between this engineering environment (Claude/Cowork) and the daily-interface environment (ChatGPT) — there is no direct Claude-to-ChatGPT communication, and none is invented here.
- **GitHub Actions** (`daily_scan.yml`, added this session) produces and commits `daily_cards/<date>/card.json`, `card.csv`, and `card.md` every morning.
- **ChatGPT** reads that committed output and relays it to Fraser conversationally. It must not re-implement or re-derive any probability/EV/grading — it is a reader and summarizer of a number the engine already computed, never a second calculator.
- **Fraser** retains manual placement authority, unchanged.

## 2. Why the repo being public matters

The repo (`https://github.com/frazwil19-gif/prediction-markets-lab`) is confirmed public (`"private": false` via the GitHub API, checked this session). That means today's card is reachable with **zero credentials, zero GitHub API token, and zero OAuth setup** at a predictable, dated URL:

```
https://raw.githubusercontent.com/frazwil19-gif/prediction-markets-lab/master/daily_cards/<YYYY-MM-DD>/card.md
```

(the `.json` and `.csv` siblings are reachable the same way, for a future integration that wants the structured form). This is the simplest possible retrieval mechanism available — no GitHub connector, no personal access token, no webhook — and is why it is recommended over Phase 6's Option B (a GitHub-triggered push notifying ChatGPT), which would need an integration this project has no evidence exists.

## 3. Recommended design: a ChatGPT scheduled task fetching the raw URL

Configure one ChatGPT **scheduled task** (OpenAI's own recurring-prompt feature, available on paid plans up to once/hour) with:

- **Schedule:** shortly after the GitHub Action's own 07:00 UTC run — e.g. 07:20 UTC, to give the workflow a comfortable margin to finish and commit.
- **Prompt** (adapt the date each time, or ask ChatGPT to compute today's date itself):

  > Fetch this URL: `https://raw.githubusercontent.com/frazwil19-gif/prediction-markets-lab/master/daily_cards/<today's date, YYYY-MM-DD>/card.md`
  > This is today's automated Daily Bet Card from my prediction-markets-lab project. Relay its numbers exactly as given — do not recompute, estimate, or round differently. In your reply to me:
  > 1. One line: date, fixtures scanned, candidates analysed, total recommended exposure.
  > 2. If there are any Grade A+/A/B selections, list each one on its own line: event, market, selection, odds, stake, grade. If none, say so in one line — that is an expected, valid outcome, not an error.
  > 3. If there are any system warnings, summarize them in one line; omit this section entirely if there are none.
  > Do not restate the full Reject/Watch list — I only want the actionable selections and anything that needs my attention.

This keeps the chat-facing output to Phase 7's "concise, non-overwhelming" bar: normally 2–4 lines, growing only when there is something to act on.

## 4. The one unverified assumption — flagged, not glossed over

OpenAI's public documentation for scheduled tasks (checked this session: OpenAI Help Center's "Scheduled tasks in ChatGPT" article) confirms scheduled tasks can use "supported apps, including Gmail, Slack, and GitHub" and can run up to once/hour on paid plans, but **does not explicitly confirm that a scheduled task retains the same general web-fetch capability an interactive ChatGPT conversation has**. Fetching an arbitrary public URL is a completely standard, long-established capability in interactive ChatGPT chat; whether it is available, unchanged, inside a *scheduled* run specifically was not confirmed by the documentation available this session, and this project has no ChatGPT account to test against directly.

**Per the operator's explicit instruction not to invent unverified capabilities, this is flagged rather than assumed.** The concrete next step is for Fraser to create the scheduled task above once and check tomorrow whether it actually fetched the URL and produced a real summary, or fell back to something generic/hallucinated. If scheduled-task browsing turns out not to reliably fetch the URL, the fallback below still works today with zero uncertainty.

## 5. Fallback (works today, no assumptions): manual paste-and-ask

If the scheduled task does not reliably fetch the URL, the same retrieval works with certainty in an ordinary interactive ChatGPT conversation — interactive browsing is well-established and not in question. Fraser (or a one-tap shortcut/bookmark) opens or pastes the same raw URL into any ChatGPT chat with the same relay instruction from §3. This costs Fraser one manual action per day instead of zero, but requires no new integration and cannot silently fail unnoticed the way an automated task might.

## 6. What this design deliberately does not do

- It does not give ChatGPT write access to the repo, or any path to commit, push, or trigger a workflow. It only reads a public file.
- It does not have ChatGPT recompute probability, EV, or grading — those numbers come only from `card.md`/`card.json`, produced by the engine.
- It does not attempt a webhook, GitHub Actions-to-ChatGPT push, or any bespoke integration requiring credentials on either side (Option B/C from the operator's Phase 6) — the public-repo raw-URL approach needs none of that, so it is the simplest reliable option available without new infrastructure.
- It does not touch real-money execution in any way — Fraser still places every bet manually, exactly as before.


## 7. Additional outputs (added 2026-09-20, Production Infrastructure Build)

Two more machine-readable files now exist alongside `card.json`, both at
the repo root so the same public raw-URL pattern from Section 3 works
for them too:

- `reports/latest_performance.json` -- paper-trading (Track B) performance:
  overall win rate, expected win rate, ROI/yield, Brier score, log loss,
  calibration, drawdown, longest losing streak, and breakdowns by grade,
  sport, competition, market, and odds band. ChatGPT should read this
  directly for any "how is the system doing" question rather than trying
  to recompute it from the raw ledger -- see
  `src/prediction_markets_lab/performance/paper_performance.py`'s module
  docstring.
- `status/latest.json` -- system health: last scan status (success/
  failure, not just "did a card exist"), last settlement status, last
  performance update time, and the count of still-unsettled paper bets.
  **This is the file that lets ChatGPT distinguish "no bets qualified
  today" (a valid outcome) from "the scanner failed" (an operational
  problem)** -- see `src/prediction_markets_lab/reports/system_status.py`'s
  module docstring. A future refinement of the morning ChatGPT prompt in
  Section 3 should fetch this file too and surface a scanner failure
  explicitly, rather than only relaying an empty card silently.

Both are produced by scheduled GitHub Actions jobs
(`.github/workflows/daily_scan.yml` for the morning scan's own status;
`.github/workflows/settlement_and_performance.yml`, new this build, for
the evening settlement + performance + status refresh), so ChatGPT never
needs to trigger anything -- it only ever reads.

Real-money (Track A) performance is deliberately NOT in
`latest_performance.json` -- see `real_bets/README.md` on why paper and
real performance are kept separate. A real-performance report is not yet
built.

## Section 8 -- Daily Money Card (2026-09-22 addition)

The "TARGETED PRODUCTION CHANGE -- DAILY MONEY WINDOW + MONEY/PAPER
SEPARATION" instruction added a narrower, actionable sibling to
`card.json`/`card.csv`/`card.md`: `daily_cards/<date>/money_card.json`
and `daily_cards/<date>/money_card.md`. ChatGPT should treat this pair,
not `card.json`, as the day's actionable recommendation surface --
`card.json` remains the complete research/audit output (every candidate,
every grade, regardless of money qualification or event horizon).

**ChatGPT should normally read exactly these three files, in this
order of priority, and never recompute anything from them:**

1. `daily_cards/<date>/money_card.json` (or `.md` for a human-readable
   render) -- the actionable Daily Money Card. Empty
   `money_qualified_candidates` with `money_qualified_count: 0` is a
   valid, expected outcome, not a failure.
2. `status/latest.json` -- whether today's scan/settlement actually
   succeeded (see `money_card_status`, `last_scan_status`), so an empty
   money card is never mistaken for a broken scanner.
3. `reports/latest_performance.json` -- specifically its `money_strategy`
   key for "how has the actual selective strategy performed", as
   distinct from the broader `overall`/`by_grade`/etc. keys at the top
   level, which cover the full paper-research candidate universe. These
   two are deliberately never mixed (see
   `src/prediction_markets_lab/performance/paper_performance.py`'s
   module docstring).

`card.json`/`card.csv`/`card.md` remain available for deeper research
review but are not the day-to-day interface -- see
`research/cycles/CYCLE_003_FOOTBALL/MONEY_WINDOW_AND_MONEY_PAPER_SEPARATION_CHECKPOINT.md`
for the full design.
