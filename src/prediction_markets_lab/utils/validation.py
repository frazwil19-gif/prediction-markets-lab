"""Shared validation helpers used across ingestion and storage modules."""

from __future__ import annotations


def require_non_empty_string(value: str, field_name: str) -> str:
    """Validate that a string field is present and non-blank.

    Args:
        value: The string to check.
        field_name: Name of the field, used in the error message.

    Returns:
        The value unchanged, if valid.

    Raises:
        ValueError: If value is empty or whitespace-only.
    """
    if not value or not value.strip():
        raise ValueError(f"{field_name} must not be empty")
    return value


def require_positive(value: float, field_name: str) -> float:
    """Validate that a numeric field is strictly positive.

    Args:
        value: The number to check.
        field_name: Name of the field, used in the error message.

    Returns:
        The value unchanged, if valid.

    Raises:
        ValueError: If value is not strictly positive.
    """
    if value <= 0:
        raise ValueError(f"{field_name} must be positive, got {value!r}")
    return value
