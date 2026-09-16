# Workstream B — Linkage-Integrity Audit and Freeze (2021-2025)

**Date:** 2026-09-16
**Status:** Gate passed. Linkage specification frozen below.
**Scope:** An outcome-blind audit of the frozen 14-day-tolerance TML<->Betfair
linkage (`scripts/link_betfair_2021_2025.py`), run exactly as the operator
required before any 2021-2025 outcome/market-edge data may be opened:

> "Audit linkage accuracy by tournament-date-distance band, especially:
> 0-2 days / 3-7 days / 8-10 days / 11-14 days ... Check player pair,
> tournament identity, market identity, round if available, and whether
> there are competing plausible markets ... If the 11-14 day group
> remains clean, freeze the linkage algorithm. Do not modify it once
> outcomes are opened."

This audit reads no outcome (`outcome_a_won` was never touched), reads no
result, and decides nothing by who won. Every check below uses only
information public before a ball is struck: the published round label, the
published tourney start date, and the Betfair market's own scheduled date.
Script: `scripts/audit_linkage_integrity_2021_2025.py`. Detail rows:
`data/interim/workstream_b_linkage_integrity_audit_rows.csv` (12,956 MATCHED
rows, one per row, gitignored per `data/interim/*`).

## 1. Band sizes

| Band (days) | N | % of MATCHED |
|---|---|---|
| 0-2 | 7,313 | 56.5% |
| 3-7 | 5,126 | 39.6% |
| 8-10 | 376 | 2.9% |
| 11-14 | 141 | 1.1% |

The 11-14 day tail the operator singled out for scrutiny is small (141 of
12,956 MATCHED rows, 1.1%) — reassuring on its own: the 14-day tolerance is
not doing most of its work at the extreme edge, it is resolving a long thin
tail.

## 2. Check 1 — round-chronology consistency (outcome-blind)

For every pair of MATCHED rows sharing a `tourney_id` where the published
round labels imply a strict order (R128<R64<R32<R16≈RR<QF<SF<F≈BR), checked
whether the earlier-round match's Betfair market date is <= the
later-round match's Betfair market date. A violation is attributed to the
later match's band.

| Band (days) | Violations / pairs checked | Rate |
|---|---|---|
| 0-2 | 26 / 38,798 | 0.07% |
| 3-7 | 103 / 164,054 | 0.06% |
| 8-10 | 0 / 27,970 | 0.00% |
| 11-14 | 0 / 13,361 | 0.00% |

**The two most-scrutinized bands (8-10, 11-14 days) show zero round-order
violations.** The small number of violations in the 0-2 and 3-7 day bands
were manually inspected and are all explained by real-world scheduling
overlap, not false links:

- `2021-422`/`2023-422` (Cincinnati Masters) and similar: an R32 match dated
  one day before an R64 match in the same draw — normal when a big draw runs
  multiple courts across days, so an early-finishing R64 match's winner can
  start their R32 tie before every R64 match on other courts has finished.
- `2021-8888` (ATP Cup): a team round-robin event where TML's schema labels
  the round-robin group stage "R128" and the knockout stage "SF"/"F" — group
  matches in different groups genuinely run on overlapping days, so a
  same-day group match after the semi-final has started is a labelling
  artifact of the round-robin format, not a chronology error.

No violation involved an implausible player pairing.

## 3. Check 2 — competing-candidate proximity (outcome-blind)

For every MATCHED row, computed the distance (days) to the nearest OTHER
usable MATCH_ODDS market anywhere in the 2021-2025 corpus between the same
two named players (a purely structural fact: which other markets exist for
this pair, never which one is "correct").

| Band (days) | N | Has >=1 other same-pair market anywhere | Has one within 30 days | Median nearest distance (of those with any) |
|---|---|---|---|---|
| 0-2 | 7,313 | 4,044 (55.3%) | 215 (2.94%) | 248 days |
| 3-7 | 5,126 | 3,403 (66.4%) | 251 (4.90%) | 212 days |
| 8-10 | 376 | 306 (81.4%) | 19 (5.05%) | 175 days |
| 11-14 | 141 | 129 (91.5%) | 15 (10.64%) | 117 days |

The rate of a same-pair market existing within 30 days roughly doubles from
the easiest band (2.94%) to the hardest (10.64%), and the median
nearest-other distance shrinks correspondingly (248 -> 117 days). This is
real signal, but not the signal it might first appear to be: because
`classify_tennis_betfair_match` already resolves ambiguity within the
actual 14-day window (a genuine same-pair conflict inside +-14 days would
have produced AMBIGUOUS, not MATCHED, and been excluded already), a "nearby
other market" outside that window mechanically reflects a mundane fact —
**top players who reach SF/F of majors and Masters (exactly the match types
concentrated in the 11-14 day band, see section 4) play each other repeatedly
across a season.** A 117-day median gap is consistent with "these two met
again at a different tournament a few months later," not "this specific
link is a coin-flip."

## 4. Manual spot-check of the 11-14 day band

Pulled `tourney_level` and `round` for every 11-14 day MATCHED row:

| tourney_level | share of 11-14 band |
|---|---|
| G (Grand Slam) | 39.0% |
| M (Masters 1000) | 59.6% |
| D (Davis Cup) | 1.4% |

Round breakdown: SF=68, F=38, R32=15, QF=11, R16=7, RR=2.

This is exactly the mechanistically expected pattern: Grand Slams run ~14
days, so a Slam final genuinely occurs 13 days after `tourney_date`
(confirmed: distance=13 for every Slam final sampled); Masters 1000 events
run ~9-11 days, so their finals land at the very edge of the window. A
random sample of the actual rows is a roll-call of real, dated tennis
history — e.g. `2021-580:127` (Australian Open F, distance=13, Djokovic vs
Medvedev), `2021-520:125` (Roland Garros SF, distance=11, Djokovic vs
Nadal), `2021-540:127` (Wimbledon F, distance=13, Djokovic vs Berrettini),
`2021-560:127` (US Open F, distance=13, Djokovic vs Medvedev) — every 2021
Slam final is present and correctly dated. **The 11-14 day band is not a
noisy edge case; it is disproportionately the marquee late-round matches of
majors and Masters, correctly placed at exactly the calendar distance those
events' real durations predict.**

## 5. Check 0 — sign sanity (not requested by the operator, added as an extra structural check)

321/12,956 (2.48%) of MATCHED rows have a Betfair market dated *before*
`tourney_date` — structurally odd since no match should predate its own
tournament's start. Breakdown:

- 272/321 (84.7%) are exactly -1 day — consistent with a timezone/day-
  boundary convention difference between TML's recorded start date and
  Betfair's UK-time market date, not a false link.
- The remaining 49 rows (0.38% of all MATCHED) are concentrated in
  round-robin-format events (`RR` round, e.g. ATP Cup/Next Gen Finals
  ties, id `...-9900`, and Davis Cup ties) plus a handful of Slam/Masters
  `R128` rows — all round-robin or opening-round matches where TML's
  single `tourney_date` field is a nominal draw date that does not bind
  every match to start on or after it. Manually inspected every row with
  distance < -1 (49 rows, listed in the audit CSV): every player pairing
  is a plausible, real ATP pairing for the named event — no implausible
  or nonsensical pairing was found.

This is a known limitation of TML's `tourney_date` field (already
documented in the discovery/scale-up protocol), not a new linkage defect.
It affects only 0.38% of MATCHED rows beyond the benign -1-day case and is
recorded here for transparency, not hidden.

## 6. Verdict

**PASS.** The 11-14 day tail — the band the operator asked to scrutinize
most closely — has zero round-chronology violations and, on manual
inspection, consists overwhelmingly of correctly-dated marquee matches
whose calendar distance is exactly what those events' known real-world
durations predict. The two soft signals found (a small round-chronology
violation rate in the 0-2/3-7 day bands, and a small negative-distance tail)
are both explained by real, external causes (multi-court scheduling
overlap, round-robin date-field conventions) rather than by any evidence of
false pairing, and neither concentrates in the tail band under scrutiny.

## 7. Frozen linkage specification

Per the operator's explicit instruction ("freeze the linkage algorithm...
do not modify it once outcomes are opened, except to fix a genuine,
transparently-documented defect"), the following is now FROZEN as of this
report and commit:

- **Script:** `scripts/link_betfair_2021_2025.py`
- **Matching logic:** `tennis_betfair_linkage.classify_tennis_betfair_match`
  / `names_are_equivalent` / `_fold` (unmodified since Tennis Cycle 1;
  covered by existing unit tests in `tests/unit/test_tennis_betfair_linkage.py`)
- **`date_tolerance_days = 14`**
- **Candidate filter:** `market_type == "MATCH_ODDS"` and `n_price_points > 0`
  (excludes the 928 "ghost" zero-price duplicate markets found in Phase 1)
- **Output:** `data/interim/workstream_b_2021_2025_linkage.csv` — 12,956
  MATCHED / 500 AMBIGUOUS / 1,108 UNMATCHED (88.96% / 3.43% / 7.61%)
- **Integrity audit:** this document + `scripts/audit_linkage_integrity_2021_2025.py`
  + `data/interim/workstream_b_linkage_integrity_audit_rows.csv`
- **Git commit this freeze is recorded against:** see the commit that adds
  this file (next commit after `f4c85e7`).

No further changes to the linkage method, tolerance, candidate filter, or
output are authorised now that this is frozen, except to fix a genuine
implementation defect discovered later — and any such fix must be
transparently documented as a correction, exactly like the two real bugs
found and fixed during Phase 1, never as a silent edit.

AMBIGUOUS and UNMATCHED rows remain excluded from all downstream analysis
and are never resolved using outcome knowledge, per standing instruction.

## 8. Next gate

Phase 2 discovery (Task #20: price-coverage/selection-bias audit, then
Task #21-22: build the 2021-2023 discovery dataset and run the 13
pre-registered families) may now proceed. No 2021-2025 outcome or
market-edge value has been computed, read, or inspected in this audit or at
any point before it.
