# Historical Price Data and CLV Limitations

This document defines precise terminology for anything derived from
Football-Data.co.uk historical prices, so that a bookmaker-consensus
observation is never mistaken for — or reported as — a claim about
what a real exchange bet would actually have achieved.

## The core limitation

Football-Data.co.uk provides, per match, per bookmaker: one **opening**
price and one **closing** price. It does not provide:

- An intraday time series of price movement.
- Any Smarkets or Betfair exchange price, historical or otherwise.
- Confirmation that the opening price was still available at the
  moment a hypothetical bettor would have wanted to enter.
- Confirmation that the closing price was achievable in size (no
  liquidity/order-book data).

## Required terminology

| Term | Meaning | May be computed from Football-Data? |
|---|---|---|
| **bookmaker_consensus_movement** | The change in the cross-bookmaker median fair probability between the opening and closing snapshots. | Yes. |
| **opening_to_closing_probability_change** | The change in a single named bookmaker's own fair probability between its opening and closing price. | Yes. |
| **proxy_clv** | A CLV-like statistic computed by comparing a hypothetical opening-price "entry" against the closing consensus, used only as a research proxy. | Yes, but must always be labelled `proxy_clv`, never `clv`. |
| **true_execution_clv** | The actual difference between a real, executed entry price (on Smarkets/Betfair, at the actual time of entry) and the actual closing price on that same exchange. | **No** — this source cannot produce this. True execution CLV requires live, forward-collected exchange price data (see `docs/RESEARCH_ENGINE.md`, and hypothesis H-FB-003 in the registry, which is `DATA_REQUIRED` for exactly this reason). |

## Rules

1. **Never call a Football-Data-derived statistic "CLV" without the
   `proxy_` prefix.** Any report, chart, or `ResearchResult` field
   that mixes bookmaker-consensus movement with the word "CLV" alone
   is a labelling error and must be corrected before publication.
2. **`proxy_clv` is a legitimate and useful research signal** — it
   tells you whether the market as a whole moved toward or away from
   a given side between open and close, which is informative about
   market efficiency and information flow. It is not, however, evidence
   that a specific execution would have captured that movement.
3. **Opening bookmaker odds ≠ the price a user could have entered at.**
   By the time a person checks a market, sees an EV signal, and places
   a bet, the "opening" price recorded in this dataset may be hours or
   days stale. Historical backtests using opening odds as a simulated
   entry price are therefore optimistic relative to what a live,
   manually-operated workflow (this project's actual operating model —
   see `docs/MOBILE_WORKFLOW.md`) could realistically achieve.
4. **Closing bookmaker odds ≠ Smarkets/Betfair closing odds.** Even
   where a bookmaker's closing price is a very liquid, well-calibrated
   number (many practitioners treat bookmaker closing lines as a
   strong efficiency benchmark), it is still a different market from
   the exchange this project actually trades on. Use it as a
   **market-quality benchmark**, not as a stand-in for the exchange.
5. **Any hypothesis or hypothesis test that depends on
   `true_execution_clv`** (rather than `proxy_clv`) must be marked
   `DATA_REQUIRED` in the Hypothesis Registry until real exchange price
   history — either paid, or forward-collected by the user — is
   available. Do not backfill this requirement by quietly substituting
   `proxy_clv` and calling it CLV.

## What historical Football-Data prices ARE good for

- Calibration research (does the margin-free bookmaker consensus, as a
  probability estimate, actually match realised outcome frequency?).
- Cross-bookmaker dispersion analysis (H-FB-002).
- Opening-to-closing bookmaker-consensus movement analysis.
- Approximate, clearly-labelled historical value simulations, used to
  decide whether a hypothesis is worth the cost of further, more
  realistic testing (paper trading, forward data collection) — not as
  a final answer about live tradability.
