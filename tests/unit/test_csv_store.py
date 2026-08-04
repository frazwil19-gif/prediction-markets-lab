from pathlib import Path

import pytest

from prediction_markets_lab.storage.csv_store import (
    append_record,
    overwrite_records,
    read_records,
)
from prediction_markets_lab.storage.schemas import ResultRecord


def make_result(market_id: str) -> ResultRecord:
    return ResultRecord(
        market_id=market_id,
        event="Arsenal vs Chelsea",
        settlement_date="2026-08-03",
        winning_outcome="home",
        result_source="manual",
        settlement_status="settled",
        notes="",
    )


def test_append_record_creates_file_with_header(tmp_path: Path):
    path = tmp_path / "results.csv"
    append_record(path, make_result("M-FB-001"))
    contents = path.read_text()
    assert "market_id" in contents.splitlines()[0]
    assert "M-FB-001" in contents


def test_append_record_appends_without_duplicating_header(tmp_path: Path):
    path = tmp_path / "results.csv"
    append_record(path, make_result("M-FB-001"))
    append_record(path, make_result("M-FB-002"))
    lines = path.read_text().splitlines()
    assert len(lines) == 3  # header + 2 rows
    assert lines[0].startswith("market_id")


def test_read_records_round_trip(tmp_path: Path):
    path = tmp_path / "results.csv"
    r1 = make_result("M-FB-001")
    r2 = make_result("M-FB-002")
    append_record(path, r1)
    append_record(path, r2)

    loaded = read_records(path, ResultRecord)
    assert len(loaded) == 2
    assert loaded[0].market_id == "M-FB-001"
    assert loaded[1].market_id == "M-FB-002"


def test_read_records_returns_empty_list_for_missing_file(tmp_path: Path):
    path = tmp_path / "does_not_exist.csv"
    assert read_records(path, ResultRecord) == []


def test_overwrite_records_replaces_file_contents(tmp_path: Path):
    path = tmp_path / "results.csv"
    append_record(path, make_result("M-FB-001"))
    append_record(path, make_result("M-FB-002"))

    updated = [make_result("M-FB-003")]
    overwrite_records(path, updated)

    loaded = read_records(path, ResultRecord)
    assert len(loaded) == 1
    assert loaded[0].market_id == "M-FB-003"


def test_overwrite_records_with_empty_list_clears_file(tmp_path: Path):
    path = tmp_path / "results.csv"
    append_record(path, make_result("M-FB-001"))
    overwrite_records(path, [])
    assert path.read_text() == ""
