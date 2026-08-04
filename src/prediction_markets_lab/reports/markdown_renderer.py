"""Shared Markdown rendering helpers for reports.

Small, dependency-free helpers used by reports.daily_report (and later
weekly/monthly reports) to render consistent Markdown sections.
"""

from __future__ import annotations

from typing import Mapping


def render_field_list(fields: Mapping[str, str | float | int | None]) -> str:
    """Render a mapping of field name to value as a Markdown bullet list.

    Args:
        fields: Ordered mapping of display label to value. None values
            render as an empty placeholder rather than the string
            "None", since these lists are meant to be filled in by hand
            when a value isn't available yet.

    Returns:
        A Markdown string with one "- Label: value" line per field.
    """
    lines = []
    for label, value in fields.items():
        display_value = "" if value is None else value
        lines.append(f"- {label}: {display_value}")
    return "\n".join(lines)


def render_heading(text: str, level: int = 2) -> str:
    """Render a Markdown heading.

    Args:
        text: The heading text.
        level: Heading level (1-6). Defaults to 2 ("## ").

    Returns:
        A Markdown heading string, e.g. "## Summary".
    """
    if not (1 <= level <= 6):
        raise ValueError("level must be between 1 and 6")
    return f"{'#' * level} {text}"
