# Expected Value Methodology

## Formula

For a £1 back bet at decimal odds `O`, estimated probability `p`, and
exchange commission `c` (charged on net winnings only, as on Smarkets
and Betfair):

```
EV = p * (O - 1) * (1 - c) - (1 - p)
```

Implemented in `ev/expected_value.py::net_expected_value`.

## Related quantities

All implemented in `ev/expected_value.py` and re-exported by
`ev/commission.py`, `ev/edge.py`, and `ev/break_even.py`:

| Quantity | Meaning |
|---|---|
| **Gross EV** | EV with no commission applied (`gross_expected_value`) |
| **Net EV** | Commission-adjusted EV (`net_expected_value`) — the primary grading input |
| **Expected ROI** | Net EV expressed as a percentage of stake |
| **Exchange implied probability** | `1 / O` — the market's own implied probability |
| **Break-even probability** | The probability at which net EV = 0 for given odds/commission (`break_even_probability`) |
| **Probability edge** | `(estimated_probability - market_probability) * 100`, in percentage points (`probability_edge`) |
| **Edge relative to market** | Edge as a proportion of the market probability (`edge_relative_to_market`) |

## Critical distinctions (project instructions, section 9)

The system must never conflate:

- **Probability edge** — a difference in probability estimates.
- **Expected value** — a probability-weighted average outcome, before
  any bet is placed.
- **Expected profit** — EV scaled by actual stake size.
- **Realised profit** — the actual outcome of a settled bet. This is
  not calculated in Stage 1; it belongs to `performance/roi.py`
  (Stage 5), which operates on settled results, not estimates.

Every function in `ev/expected_value.py` returns a value from exactly
one of these categories, and docstrings state which.
