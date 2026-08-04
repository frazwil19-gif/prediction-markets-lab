"""Local CSV persistence for Markets, Bets, Results and related records.

This is the Stage 2 default storage backend — free, works offline, and
inspectable from a phone via any spreadsheet app. storage.schemas
defines the record shapes; this module handles reading and appending
rows to CSV files without losing type safety.
"""

from __future__ import annotations

import csv
from pathlib import Path
from typing import Type, TypeVar

from pydantic import BaseModel

RecordT = TypeVar("RecordT", bound=BaseModel)


def append_record(path: Path, record: BaseModel) -> None:
    """Append a single record to a CSV file, writing a header if new.

    Args:
        path: Path to the CSV file. Parent directories are created if
            missing.
        record: A pydantic model instance whose field names become the
            CSV columns.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    row = record.model_dump(by_alias=True)
    file_exists = path.exists() and path.stat().st_size > 0

    with open(path, "a", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(row.keys()))
        if not file_exists:
            writer.writeheader()
        writer.writerow(row)


def read_records(path: Path, model: Type[RecordT]) -> list[RecordT]:
    """Read all records from a CSV file into validated model instances.

    Empty CSV cells are converted to None before validation, so that
    optional numeric fields (e.g. a bet's closing_odds before the
    market has closed) round-trip correctly instead of failing to
    parse as an empty string.

    Args:
        path: Path to the CSV file.
        model: The pydantic model class to validate each row against.

    Returns:
        A list of validated model instances. Returns an empty list if
        the file does not exist.
    """
    if not path.exists():
        return []

    nullable_fields = {
        name
        for name, info in model.model_fields.items()
        if _accepts_none(info.annotation)
    }

    with open(path, newline="") as f:
        reader = csv.DictReader(f)
        records = []
        for row in reader:
            if not any(row.values()):
                continue
            cleaned_row = {
                k: (None if v == "" and k in nullable_fields else v)
                for k, v in row.items()
            }
            records.append(model.model_validate(cleaned_row))
        return records


def _accepts_none(annotation: object) -> bool:
    """Check whether a pydantic field annotation includes None (Optional)."""
    return type(None) in getattr(annotation, "__args__", ())


def overwrite_records(path: Path, records: list[BaseModel]) -> None:
    """Overwrite a CSV file with the given list of records.

    Used for settlement updates (e.g. marking a bet's result), where
    an existing row needs to change rather than a new row being
    appended.

    Args:
        path: Path to the CSV file. Parent directories are created if
            missing.
        records: The full list of records to write. If empty, an empty
            file (no header) is written.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    if not records:
        path.write_text("")
        return

    fieldnames = list(records[0].model_dump(by_alias=True).keys())
    with open(path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for record in records:
            writer.writerow(record.model_dump(by_alias=True))
