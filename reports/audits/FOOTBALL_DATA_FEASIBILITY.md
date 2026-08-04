# Football-Data.co.uk Feasibility Audit

**Date:** 2026-08-04
**Scope:** English Premier League (E0), English Championship (E1),
Scottish Premiership (SC0) — 2024/25 season, as a first probe before
committing to a multi-season download.

**Method:** Direct `web_fetch` of the live CSV URLs
(`https://www.football-data.co.uk/mmz4281/{season}/{code}.csv`), plus
targeted web searches to confirm URL patterns and cross-check column
counts across seasons via third-party notebooks that have already
ingested this data.

## What was actually fetched

| League | Season | URL | Result |
|---|---|---|---|
| Premier League | 2024/25 | `mmz4281/2425/E0.csv` | ✅ Full fetch succeeded |
| Championship | 2024/25 | `mmz4281/2425/E1.csv` | ✅ Fetch succeeded (truncated to first ~90 rows by token limit, header + structure fully visible) |
| Scottish Premiership | 2024/25 | `mmz4281/2425/SC0.csv` | ⚠️ URL confirmed to exist and serve real data (seen via search-engine cache of the file), but a **direct fetch on this attempt hit a 429 rate-limit** from football-data.co.uk after two prior fetches in quick succession |

**This audit does not claim SC0's full column set has been verified
directly in this session — see "Open item" below.**

## Row count, date range (Premier League, confirmed by direct fetch)

- 2024/25 E0 data starts 16/08/2024 and the fetched window (subject to
  the response being truncated by the token limit, not by the source
  file) ran through at least 26/01/2025 — i.e. spans a large majority
  of a full season. A third-party ingestion notebook (see Sources)
  independently confirms **380 matches** for a complete Premier League
  season CSV, which is the expected full-season count (20 teams × 38
  matches).

## Result fields (confirmed present, E0 and E1 — identical schema)

`Div, Date, Time, HomeTeam, AwayTeam, FTHG, FTAG, FTR, HTHG, HTAG,
HTR, Referee, HS, AS, HST, AST, HF, AF, HC, AC, HY, AY, HR, AR`

i.e. full-time and half-time score/result, plus match statistics
(shots, shots on target, fouls, corners, cards) — more than the
minimum needed for Cycle 1 (which only needs date, teams, FT
score/result).

## Bookmaker-specific 1X2 odds (confirmed present)

Multiple named bookmakers, **both opening and closing prices**, for
every match:

- Opening 1X2: `B365H/D/A` (Bet365), `BWH/D/A` (BetWin), `BFH/D/A`
  (Betfair exchange price at the time), `PSH/D/A` (Pinnacle), `WHH/D/A`
  (William Hill), `1XBH/D/A` (1xBet)
- Closing 1X2: same bookmaker codes with a `C` suffix, e.g. `B365CH`,
  `PSCH`, etc.
- Aggregates: `MaxH/D/A`, `AvgH/D/A` (and closing equivalents
  `MaxCH/D/A`, `AvgCH/D/A`), plus a `BFEH/D/A` (Betfair Exchange —
  best odds) field and its closing equivalent

This is materially better than the project instructions assumed
("average odds; maximum odds; market closing odds") — **closing odds
per named bookmaker are available, not just an aggregate**, which
directly enables genuine CLV calculation (entry price vs. that same
bookmaker's closing price), addressing project instructions Part 11's
CLV requirements more rigorously than expected.

## Additional markets present (not required for Cycle 1, noted for completeness)

Over/under 2.5 goals (opening and closing, several bookmakers) and
Asian handicap (opening and closing, several bookmakers, with the
handicap line `AHh`/`AHCh`). These are out of scope for Cycle 1
(1X2 only) but confirm the source could support the "approved totals"
markets mentioned in the original Stage 1 brief later, without a new
data source.

## Missing values / malformed odds (observed directly)

Even within the current, most-complete season (2024/25), **some
matches have blank cells for specific bookmaker columns** — e.g. one
Arsenal match had a blank `1XBH/D/A` field, several December 2024
Premier League matches have blank `WHH/D/A` and related closing
columns (bookmaker apparently stopped quoting or data collection
gap). This is a real, non-hypothetical data-quality issue: **any
loader must treat "blank bookmaker cell" as "this bookmaker did not
quote," not as zero or a parsing error**, consistent with
`docs/DATA_LEAKAGE_RULES.md`/ingestion validation requirements
already designed in `ingestion.schema_validation` (Stage 2) — that
module's `MIN_PLAUSIBLE_OVERROUND` check and completeness logic will
need extending to handle per-bookmaker blanks in a multi-bookmaker CSV
row (it currently assumes a caller has already assembled one clean
odds list; the Football-Data loader will need to build that assembly
step and skip/flag blank bookmakers per match).

## Column-count variation across seasons (from third-party evidence, not yet independently re-verified by direct fetch)

A public data-ingestion notebook (see Sources) that has already
pulled multiple Premier League seasons from this exact source reports:

| Season | Columns (incl. metadata) |
|---|---|
| 2024/25 | 122 |
| 2023/24 | 108 |
| 2022/23 | 108 |
| 2021/22 | 108 |
| 2020/21 | 108 |

This means **older seasons have fewer bookmaker/market columns than
the current season** (2024/25 added more bookmakers/markets). This is
an important constraint: a loader that hard-codes an expected column
set for "the" Football-Data schema will break across seasons. The
loader must be schema-tolerant per season (read whatever columns
exist, and treat a column's absence in an older season as "not
collected," never as missing/blank data for a bookmaker that also
doesn't exist in an older season's file).

## Duplicate matches / inconsistent team names

Not observed in the confirmed fetches (each match appeared exactly
once per file, team names spelled consistently within a season, e.g.
"Nott'm Forest", "Sheffield United" — note the apostrophe-truncated
"Nott'm Forest" is itself a normalisation case
`normalisation.team_names.py` (Stage 3) will need to handle explicitly,
since other sources may spell it "Nottingham Forest").

## Site behaviour / access constraints (operationally important)

- **No authentication required** — plain HTTPS GET, CSV response.
- **Rate limiting observed**: two back-to-back fetches to different
  URLs on football-data.co.uk succeeded; a third fetch (30–60 seconds
  later) returned HTTP 429. **A production loader must pace requests
  (e.g. 1 request every several seconds, possibly with retry/backoff)
  rather than pulling many seasons/leagues in a tight loop.** This is
  a real constraint discovered directly, not a hypothetical one.
- Files are stable, permanent per-season URLs
  (`mmz4281/{season}/{code}.csv`), confirmed for the current season
  and (via search-engine indexing) historically back to 1993/94 for
  English data — so once paced correctly, downloading 3-5 seasons for
  3 competitions (9-15 files total) is a small, one-off, well within
  free-tier / no-cost constraints.

## Open item (not yet resolved — do not scale downloads until this is closed)

**Scottish Premiership (SC0) full column set has not been directly
re-verified in this session** due to the rate limit. A
search-engine-cached fragment of the SC0 2024/25 file shows a
`Hearts vs Rangers` match with what appears to be the *same* header
structure as E0/E1 — but the fragment also shows what looks like an
extra stray comma immediately before the `SC0` row starts, which could
indicate either a minor formatting quirk in how the fragment was
captured, or a genuine column-count difference for the Scottish file
(Scottish Premiership typically has fewer bookmakers quoting than
English top divisions, e.g. William Hill/1xBet coverage may be
thinner). **This must be resolved with one paced, direct fetch before
Scottish Premiership data is used for anything beyond a sanity check.**

## Conclusion

**FEASIBLE_WITH_LIMITATIONS**

The core requirement — multi-season, bookmaker-specific opening and
closing 1X2 odds plus match results for Premier League and
Championship — is confirmed accessible, free, and richer than
originally assumed (true per-bookmaker closing odds, not just an
aggregate). Scottish Premiership access is very likely fine (the file
exists and serves data) but its exact column set needs one more paced
fetch to confirm before it's treated as equivalent to the English
files.

Limitations to design around, not blockers:

1. Per-bookmaker blank cells within a season (handle as "did not
   quote," not zero/error).
2. Column set differs by season (schema-tolerant loader, not a fixed
   expected header).
3. Site rate-limits rapid sequential requests (pace downloads; this
   is a one-off setup cost anyway, not a daily operational dependency).
4. Team name spelling normalisation is required
   (`normalisation.team_names.py`, already scoped for Stage 3).

## Recommendation for Cycle 1 dataset

- **Seasons:** 2020/21 through 2024/25 (5 seasons) for Premier League
  and Championship — all confirmed (by the third-party column-count
  evidence) to include per-bookmaker closing odds, which earlier
  seasons (pre-2005/06 per Football-Data's own documentation) do not
  reliably have. Do not go back further than this for Cycle 1 without
  a separate check.
- **Competitions:** Premier League (E0) and Championship (E1) confirmed
  ready now. Scottish Premiership (SC0) — confirmed to exist; hold as
  "pending" until the column-set re-check above is done; do not block
  Cycle 1 on it, since Premier League + Championship alone already
  gives 5 seasons × 2 competitions × ~40 matches/season ≈ 1,700+
  matches, comfortably above the "≥100 out-of-sample observations"
  Grade A bar in `config/research_thresholds.yaml`.
- **Odds fields usable now:** per-bookmaker opening 1X2, per-bookmaker
  closing 1X2, Max/Avg 1X2 (both opening and closing). Sufficient for
  Baseline 0 (margin-free consensus, using the corrected
  `probability.market_pipeline`), and for genuine CLV (entry vs. that
  bookmaker's own closing price).
- **True entry-vs-closing CLV: yes, feasible** — this was originally
  uncertain; the presence of per-bookmaker closing columns resolves it
  positively, better than the "closing consensus only" fallback the
  project instructions anticipated.
- **Cycle 1 hypotheses remain testable as scoped**, with one caveat:
  H-FB-003 ("exchange prices above margin-free consensus near
  kickoff") explicitly requires near-kickoff *intraday* price
  movement, which this historical end-of-day CSV source does **not**
  provide (it has one opening line and one closing line per bookmaker,
  not a time series). H-FB-003 should remain at `DATA_REQUIRED` status
  and be excluded from Cycle 1's initial four unless near-kickoff data
  collection is separately set up — this matches what was already
  recorded for it in the Hypothesis Registry.

## Sources

- https://www.football-data.co.uk/englandm.php (download page, URL
  pattern confirmation)
- https://www.football-data.co.uk/mmz4281/2425/E0.csv (direct fetch)
- https://www.football-data.co.uk/mmz4281/2425/E1.csv (direct fetch)
- https://www.football-data.co.uk/mmz4281/2425/SC0.csv (existence
  confirmed via search-engine cache; direct fetch rate-limited)
- https://www.football-data.co.uk/notes.txt (bookmaker code key,
  closing-odds "C" suffix convention)
- Third-party notebook independently ingesting this exact source,
  used only to cross-check column counts across seasons:
  https://github.com/Jnyambok/Soca-Scores (data_ingestion.ipynb)
