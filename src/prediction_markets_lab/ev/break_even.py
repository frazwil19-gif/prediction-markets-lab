"""Break-even probability calculations.

Re-exports break_even_probability from expected_value.py, which holds
the canonical implementation.
"""

from __future__ import annotations

from prediction_markets_lab.ev.expected_value import break_even_probability

__all__ = ["break_even_probability"]
