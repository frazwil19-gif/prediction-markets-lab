"""Liquidity assessment for exchange markets.

PLACEHOLDER — deferred beyond Stage 1.

In V1, liquidity is assessed manually by the user checking available
exchange depth at the price required, and recorded as a boolean
(liquidity_adequate) consumed by decisions.grading.GradingInput. An
automated liquidity score from exchange order-book data is planned for
a later stage, contingent on a free/low-cost exchange data source being
identified; see docs/ROADMAP.md.
"""

from __future__ import annotations
