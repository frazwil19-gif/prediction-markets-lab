# Expansion R&D programme (adopted 2026-10-08; ChatGPT/Fraser directive 18:37)

## Objective
> Maximise validated expected-profit capacity by increasing the number of independent high-quality betting
> opportunities and, only after sufficient evidence, safely increasing capital deployment, without degrading
> probability quality, calibration, EV, execution or risk controls. 100+ qualified bets/month is an aspirational
> scalability milestone, not a quota.

The earlier objective (`MASTER_OBJECTIVE.md`) is not superseded. This document adds the expansion objective on top
of it.

Three capacities are tracked separately, so the bankroll never steers research:

| Capacity | Measured by | Where |
|---|---|---|
| engine quality | calibration and CLV per engine | weekly report, `research_shadow/clv` |
| opportunity capacity | unique-event executable qualified bets per month | `reports/qualified_capacity` |
| capital capacity | stake accepted and limits per venue | Bet Log `stake_requested`, `stake_accepted`, `max_stake_offered`, `restricted`, `attempt_outcome` |

## Two classes of engine, two standards
| | Consensus-derived | Proprietary |
|---|---|---|
| Probability source | the market (de-vig, exchange mid) | our own model (the market is only a comparator) |
| Expected qualification | about 0.1–1% of candidates (measured) | unknown; could be higher |
| Validation | calibration on chronological held-out seasons | pre-registration, sealed holdout **and** beating the strongest comparator (market-implied where priced) |
| Before money | registry status + bsv2-4 | plus a prospective paper phase (≥ 150 predictions, CLV vs close) |
| Main risk | account limits (soft-book dispersion edge) | overfitting, model error |
| Development budget | near-zero marginal cost only | most of the effort, gated by kill rules |

## Early-kill rules (any one rejects or defers a market)
1. No reliable UK-executable price source, or < 50% of events priced two-sided at decision time.
2. No clean, untouched chronological holdout.
3. Insufficient history: fewer than about 2,000 labelled outcomes.
4. Poor liquidity: median spread above the bsv2 gate, or < £2 at the decision price.
5. HIGH-case unique-event contribution < about 3 qualified bets a month, unless the build is almost free (< 1 week)
   or it is the first market of a family whose HIGH case is ≥ 10.
6. Engineering weeks > about 3 × BASE bets a month.
7. Data or API cost above BASE first-year profit at £1–£5 stakes.
8. Correlation > 0.7 with an existing engine on the same events (the one-per-event cap makes it redundant).
9. Legal or licensing problem, e.g. non-commercial data for a live system.
10. Cannot beat or complement the strongest sensible comparator at the pre-registered N.
11. Any retuning after a holdout means the market is killed, never re-run on the same holdout.

## Research priority
- U_m = C_m (candidates/month) × q_m (qualification rate) × u_m (unique-event fraction) × e_m (executable share),
  each as a LOW–HIGH range.
- Research value = U_m(BASE) × P(validates) ÷ (research weeks + data cost in week-equivalents).
- A family is scored on the sum over its markets, weighted by P(validates | first market passes).
- When ranges overlap, prefer the option whose **next probe** is cheapest.
- Recompute monthly from measured qualification rates and CLV.

## NBA breadth (2026-10-08 findings)
**Data held (M):**
- wippa 2016–26: OddsPortal average closing moneyline only.
- SBR (flancast90, MIT) 2011-12 → 2021-22: closing moneyline, spread and total, one line per game, not multi-book.
- 2025-26 player logs only; no box-score source reachable.

**Bookmaker coverage:**
- The Odds API lists NBA spreads/totals; UK-region book coverage is **unknown**. Probe C3 measures it from 20 Oct.
- Team totals are mostly at US books (I).

**Volume:** about 215 regular-season games a month, so about 215 candidates per market (one P ≥ 0.5 side per game).

**Qualification:**
- At P ≈ 0.5 and −110-type prices, EV ≈ −4.5%.
- So qualification needs UK books that disagree on the *line*, priced by a margin-distribution model calibrated on
  SBR closing lines.

**Estimates (P):**
- spread 0 / 0.5 / 3 a month;
- totals 0 / 0.5 / 3;
- team totals 0 / 0 / 1;
- u ≈ 0.6–0.9 (shares events with NBA moneyline).

**Cost:** adapter about 1 week; margin model plus holdout (2020–22 seasons) about 1–2 weeks.

**Verdict:**
- **Pre-register only if probe C3 shows ≥ 3 UK books on ≥ 50% of games AND line disagreement on ≥ 20% of games.**
- Team totals: DEFER.
- Player props: DEFER until a valid data source and UK price route exist.

## Volume scenarios (qualified bets/month; MEASURED now, PROJECTED after)
| Point | Candidates/month | LOW / BASE / HIGH | Unique-event share | Consensus : proprietary | What it assumes | Confidence |
|---|---|---|---|---|---|---|
| Now (Oct 2026) | ~1,000 | 0 / 3 / 6 (M) | ~1.0 | 100 : 0 | bsv2-4, consensus engines | high |
| Dec 2026 | 800–1,100 | 1 / 4 / 10 | ~1.0 | 100 : 0 | tennis off-season; NBA + NFL live | medium |
| Mar 2027 | 1,300–1,800 | 3 / 10 / 25 | 0.9 | 85 : 15 | tennis back; corners or SOT in paper/provisional | low |
| Jun 2027 | 1,500–2,500 | 5 / 15 / 40 | 0.85 | 70 : 30 | SOT provisional if validated; 0–2% interim; MLB | low |
| Oct 2027 (12 months) | 2,000–3,500 | 8 / 25 / 60 | 0.8 | 55 : 45 | 0–2% final; 1–2 families live | low |
| Mature (2028) | 3,500+ | 10 / 40 / 100+ | 0.75 | 40 : 60 | 4–6 validated families | very low |

**Turnover and expected profit (at the BASE count; profit = bets × stake × edge):**

| Point | BASE bets | Turnover £1 / £5 / £10 | Profit at 2% / 3% / 5% (£10 stake) |
|---|---|---|---|
| Now | 3 | £3 / £15 / £30 | £0.6 / £0.9 / £1.5 |
| Mar 2027 | 10 | £10 / £50 / £100 | £2 / £3 / £5 |
| Oct 2027 | 25 | £25 / £125 / £250 | £5 / £7.5 / £12.5 |
| 2028 | 40 | £40 / £200 / £400 | £8 / £12 / £20 |

At £1, divide the profit by 10. Each £1 bet has an SD of about £0.78, so monthly P&L is noise for a long time and
CLV is the decision metric.

**What would have to validate:**
- **50 a month:** the 0–2% band (tennis about 15–35 in season under production gates; measured arrival
  ≈ 23/month), plus 2–3 proprietary families at about 8–15 each, plus about 6 from current engines and NBA.
  Difficult but possible by about 2028.
- **100 a month:** the 0–2% band, plus 4–6 families (player props ≈ 20–30 with props beyond the EPL, counts ≈ 10,
  tennis games ≈ 10–15, NBA lines ≈ 5, MLB ≈ 5–10), with about 3,500+ candidates at an average q of 3–4%.
  Depends on unverified price coverage.
- **150+ a month:** unrealistic with free UK-executable data. It needs paid feeds, multi-league props liquidity,
  a Betfair live key, and a raised daily cap.

## Stopped / deprioritised (2026-10-08)
- Big Card development;
- presentation polish;
- the team SOT line;
- extra prop-price probes beyond probe 2;
- NHL work beyond free paper tracking;
- threshold-tuning grids;
- extending the football shadow tiers.
