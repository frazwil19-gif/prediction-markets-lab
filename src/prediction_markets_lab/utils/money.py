"""GBP money rounding and formatting helpers.

All monetary values in this project are GBP, and are rounded to whole
pence to avoid floating-point stake/profit values that don't match
what a phone screen or a bookmaker/exchange would actually show.
"""

from __future__ import annotations

from decimal import ROUND_HALF_UP, Decimal


def round_gbp(amount: float) -> float:
    """Round a GBP amount to the nearest whole penny.

    Args:
        amount: A monetary amount in GBP, e.g. 0.2549999.

    Returns:
        The amount rounded to 2 decimal places using round-half-up,
        e.g. 0.25.
    """
    quantised = Decimal(str(amount)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    return float(quantised)


def format_gbp(amount: float) -> str:
    """Format a GBP amount for display, e.g. "£0.25".

    Args:
        amount: A monetary amount in GBP.

    Returns:
        A string with a leading "£" sign and exactly 2 decimal places.
    """
    return f"£{round_gbp(amount):.2f}"
