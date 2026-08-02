"""Probability edge calculations.

Re-exports edge functions from expected_value.py, which holds the
canonical implementation. Kept as a separate module so grading and
reporting code can depend on `prediction_markets_lab.ev.edge` without
coupling to the full EV evaluation pipeline.
"""

from __future__ import annotations

from prediction_markets_lab.ev.expected_value import (
    edge_relative_to_market,
    probability_edge,
)

__all__ = ["probability_edge", "edge_relative_to_market"]
