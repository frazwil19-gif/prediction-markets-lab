import bz2
import json
from pathlib import Path

import pyarrow.parquet as pq
import pytest

from prediction_markets_lab.ingestion.betfair_market_index import (
    day_output_paths,
    process_day,
    run_over_days,
    summarise_market_bytes,
)

# Hand-built lines matching Betfair's DOCUMENTED market-change-message
# shape (not a real captured file -- same convention as
# test_betfair_historical_schema.py).
DEFINITION_LINE = json.dumps({
    "op": "mcm",
    "pt": 1741593600000,
    "mc": [
        {
            "id": "1.123456789",
            "marketDefinition": {
                "eventId": "31234567",
                "marketTime": "2025-03-10T14:00:00.000Z",
                "marketType": "MATCH_ODDS",
                "status": "OPEN",
                "runners": [
                    {"id": 11111, "name": "Novak Djokovic", "sortPriority": 1},
                    {"id": 22222, "name": "Rafael Nadal", "sortPriority": 2},
                ],
            },
        }
    ],
})

PRICE_LINE = json.dumps({
    "op": "mcm",
    "pt": 1741593660000,
    "mc": [
        {
            "id": "1.123456789",
            "rc": [
                {"id": 11111, "ltp": 1.65},
                {"id": 22222, "ltp": 2.30},
            ],
        }
    ],
})

ONE_MARKET_FILE_BYTES = bz2.compress((DEFINITION_LINE + "\n" + PRICE_LINE + "\n").encode("utf-8"))


def test_summarise_market_bytes_extracts_final_definition_and_prices():
    summary, manifest = summarise_market_bytes("31234567", ONE_MARKET_FILE_BYTES, "2026/Jan/1/31234567/1.123456789.bz2")

    assert summary["market_id"] == "1.123456789"
    assert summary["market_type"] == "MATCH_ODDS"
    assert summary["status"] == "OPEN"
    assert summary["runner_names"] == ["Novak Djokovic", "Rafael Nadal"]
    assert summary["n_messages"] == 2
    assert summary["n_price_points"] == 2
    assert summary["price_ltp"] == [1.65, 2.30]


def test_summarise_market_bytes_hashes_raw_bytes_not_parsed_content():
    import hashlib

    _summary, manifest = summarise_market_bytes("31234567", ONE_MARKET_FILE_BYTES, "some/relpath.bz2")

    assert manifest["raw_sha256"] == hashlib.sha256(ONE_MARKET_FILE_BYTES).hexdigest()
    assert manifest["raw_size_bytes"] == len(ONE_MARKET_FILE_BYTES)
    assert manifest["raw_relpath"] == "some/relpath.bz2"
    assert manifest["market_id"] == "1.123456789"


def test_summarise_market_bytes_never_fabricates_missing_definition():
    # A file with only a price update, no marketDefinition ever seen.
    price_only = bz2.compress((PRICE_LINE + "\n").encode("utf-8"))
    summary, _manifest = summarise_market_bytes("31234567", price_only, "x.bz2")

    assert summary["market_type"] is None
    assert summary["final_market_time"] is None
    assert summary["status"] is None
    assert summary["runner_names"] == []


def _write_market_file(basic_root: Path, day_dir: Path, event_id: str, market_id_suffix: str, data: bytes):
    event_dir = day_dir / event_id
    event_dir.mkdir(parents=True, exist_ok=True)
    (event_dir / f"1.{market_id_suffix}.bz2").write_bytes(data)
    # A combined per-event file alongside it, which must be skipped.
    (event_dir / f"{event_id}.bz2").write_bytes(data)


def test_process_day_only_reads_per_market_files_not_combined_event_file(tmp_path):
    basic_root = tmp_path / "BASIC"
    day_dir = basic_root / "2026" / "Jan" / "1"
    _write_market_file(basic_root, day_dir, "31234567", "123456789", ONE_MARKET_FILE_BYTES)
    out_dir = tmp_path / "out"

    result = process_day(day_dir, out_dir, basic_root)

    assert result["files_processed"] == 1  # not 2 -- the combined file was skipped
    assert result["skipped_already_done"] is False


def test_process_day_writes_parquet_readable_summary_and_manifest(tmp_path):
    basic_root = tmp_path / "BASIC"
    day_dir = basic_root / "2026" / "Jan" / "1"
    _write_market_file(basic_root, day_dir, "31234567", "123456789", ONE_MARKET_FILE_BYTES)
    out_dir = tmp_path / "out"

    process_day(day_dir, out_dir, basic_root)
    _label, summary_path, manifest_path = day_output_paths(day_dir, out_dir)

    summary_table = pq.read_table(summary_path)
    manifest_table = pq.read_table(manifest_path)
    assert summary_table.num_rows == 1
    assert manifest_table.num_rows == 1
    assert manifest_table.column("raw_relpath").to_pylist()[0].endswith("1.123456789.bz2")


def test_process_day_is_idempotent_and_skips_when_both_outputs_exist(tmp_path):
    basic_root = tmp_path / "BASIC"
    day_dir = basic_root / "2026" / "Jan" / "1"
    _write_market_file(basic_root, day_dir, "31234567", "123456789", ONE_MARKET_FILE_BYTES)
    out_dir = tmp_path / "out"

    first = process_day(day_dir, out_dir, basic_root)
    second = process_day(day_dir, out_dir, basic_root)

    assert first["skipped_already_done"] is False
    assert second["skipped_already_done"] is True
    assert second["files_processed"] == 0


def test_process_day_reprocesses_when_only_partially_written(tmp_path):
    # Simulates an interrupted run: only one of the two output files exists.
    basic_root = tmp_path / "BASIC"
    day_dir = basic_root / "2026" / "Jan" / "1"
    _write_market_file(basic_root, day_dir, "31234567", "123456789", ONE_MARKET_FILE_BYTES)
    out_dir = tmp_path / "out"

    process_day(day_dir, out_dir, basic_root)
    _label, summary_path, _manifest_path = day_output_paths(day_dir, out_dir)
    summary_path.unlink()  # simulate an interrupted write

    result = process_day(day_dir, out_dir, basic_root)

    assert result["skipped_already_done"] is False
    assert result["files_processed"] == 1
    assert summary_path.exists()


def test_run_over_days_processes_each_day_independently_and_resumes(tmp_path):
    basic_root = tmp_path / "BASIC"
    day1 = basic_root / "2026" / "Jan" / "1"
    day2 = basic_root / "2026" / "Jan" / "2"
    _write_market_file(basic_root, day1, "31234567", "111111111", ONE_MARKET_FILE_BYTES)
    _write_market_file(basic_root, day2, "31234568", "222222222", ONE_MARKET_FILE_BYTES)
    out_dir = tmp_path / "out"

    first_run = run_over_days([day1, day2], out_dir, basic_root)
    assert [r["files_processed"] for r in first_run] == [1, 1]
    assert all(r["skipped_already_done"] is False for r in first_run)

    second_run = run_over_days([day1, day2], out_dir, basic_root)
    assert all(r["skipped_already_done"] is True for r in second_run)


def test_process_day_returns_zero_files_processed_for_empty_day(tmp_path):
    basic_root = tmp_path / "BASIC"
    empty_day = basic_root / "2026" / "Jan" / "5"
    empty_day.mkdir(parents=True)
    out_dir = tmp_path / "out"

    result = process_day(empty_day, out_dir, basic_root)

    assert result["files_processed"] == 0
    assert result["skipped_already_done"] is False


def test_day_output_paths_uses_month_and_zero_padded_day():
    day_dir = Path("/some/root/2026/Jan/5")
    label, summary_path, manifest_path = day_output_paths(day_dir, Path("/out"))

    assert label == "Jan_05"
    assert summary_path.name == "markets_Jan_05.parquet"
    assert manifest_path.name == "manifest_Jan_05.parquet"
