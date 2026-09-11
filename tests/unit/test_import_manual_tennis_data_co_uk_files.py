"""Unit tests for scripts/import_manual_tennis_data_co_uk_files.py.

Entirely local-filesystem -- no network access, consistent with this
project's testing philosophy (see tests/unit/test_tennis_data_loader.py's
module docstring).
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
SCRIPT_PATH = REPO_ROOT / "scripts" / "import_manual_tennis_data_co_uk_files.py"

spec = importlib.util.spec_from_file_location("import_manual_tennis_data_co_uk_files", SCRIPT_PATH)
import_manual = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = import_manual
spec.loader.exec_module(import_manual)

VALID_XLSX_BYTES = b"PK\x03\x04" + b"\x00" * 16
HTML_ERROR_BYTES = b"<html><body>Not Found</body></html>"


def make_config(tmp_path: Path, seasons: list[str]) -> Path:
    config = {
        "tours": [{"code": "ATP", "name": "ATP Tour (men's)"}],
        "seasons": seasons,
        "sources": {
            "tennis_data_co_uk": {
                "base_url": "https://www.tennis-data.co.uk",
                "men_path_template": "{year}/{year}.xlsx",
                "women_path_template": "{year}w/{year}.xlsx",
            }
        },
    }
    config_path = tmp_path / "config.yaml"
    config_path.write_text(yaml.dump(config))
    return config_path


def test_validate_xlsx_bytes_accepts_real_xlsx_magic():
    assert import_manual.validate_xlsx_bytes(VALID_XLSX_BYTES, "2024.xlsx") is None


def test_validate_xlsx_bytes_rejects_empty_file():
    assert "empty" in import_manual.validate_xlsx_bytes(b"", "2024.xlsx")


def test_validate_xlsx_bytes_rejects_html_error_page():
    error = import_manual.validate_xlsx_bytes(HTML_ERROR_BYTES, "2024.xlsx")
    assert error is not None
    assert "HTML error page" in error


def test_validate_xlsx_bytes_rejects_other_garbage():
    error = import_manual.validate_xlsx_bytes(b"not an xlsx file at all", "2024.xlsx")
    assert error is not None
    assert "ZIP magic number" in error


def test_run_imports_a_valid_file_into_the_expected_raw_path(tmp_path):
    source_dir = tmp_path / "downloads"
    source_dir.mkdir()
    (source_dir / "2024.xlsx").write_bytes(VALID_XLSX_BYTES)

    config_path = make_config(tmp_path, seasons=["2024"])
    output_root = tmp_path / "data"

    exit_code = import_manual.run([
        "--source-dir", str(source_dir),
        "--config", str(config_path),
        "--output-root", str(output_root),
    ])

    assert exit_code == 0
    dest = output_root / "raw" / "tennis" / "tennis_data_co_uk" / "ATP" / "2024.xlsx"
    assert dest.read_bytes() == VALID_XLSX_BYTES


def test_run_fails_loudly_when_a_season_file_is_missing(tmp_path):
    source_dir = tmp_path / "downloads"
    source_dir.mkdir()
    # Deliberately do not create 2024.xlsx.

    config_path = make_config(tmp_path, seasons=["2024"])
    output_root = tmp_path / "data"

    exit_code = import_manual.run([
        "--source-dir", str(source_dir),
        "--config", str(config_path),
        "--output-root", str(output_root),
    ])

    assert exit_code == 1
    dest = output_root / "raw" / "tennis" / "tennis_data_co_uk" / "ATP" / "2024.xlsx"
    assert not dest.exists()


def test_run_rejects_an_html_error_page_saved_as_xlsx(tmp_path):
    source_dir = tmp_path / "downloads"
    source_dir.mkdir()
    (source_dir / "2024.xlsx").write_bytes(HTML_ERROR_BYTES)

    config_path = make_config(tmp_path, seasons=["2024"])
    output_root = tmp_path / "data"

    exit_code = import_manual.run([
        "--source-dir", str(source_dir),
        "--config", str(config_path),
        "--output-root", str(output_root),
    ])

    assert exit_code == 1
    dest = output_root / "raw" / "tennis" / "tennis_data_co_uk" / "ATP" / "2024.xlsx"
    assert not dest.exists()


def test_run_refuses_to_silently_overwrite_a_differing_existing_file(tmp_path):
    source_dir = tmp_path / "downloads"
    source_dir.mkdir()
    (source_dir / "2024.xlsx").write_bytes(VALID_XLSX_BYTES)

    config_path = make_config(tmp_path, seasons=["2024"])
    output_root = tmp_path / "data"
    dest = output_root / "raw" / "tennis" / "tennis_data_co_uk" / "ATP" / "2024.xlsx"
    dest.parent.mkdir(parents=True)
    dest.write_bytes(VALID_XLSX_BYTES + b"\xff")  # different content

    exit_code = import_manual.run([
        "--source-dir", str(source_dir),
        "--config", str(config_path),
        "--output-root", str(output_root),
    ])

    assert exit_code == 1
    # Existing (different) content must be untouched.
    assert dest.read_bytes() == VALID_XLSX_BYTES + b"\xff"


def test_run_is_idempotent_when_rerun_against_identical_existing_content(tmp_path):
    source_dir = tmp_path / "downloads"
    source_dir.mkdir()
    (source_dir / "2024.xlsx").write_bytes(VALID_XLSX_BYTES)

    config_path = make_config(tmp_path, seasons=["2024"])
    output_root = tmp_path / "data"

    first = import_manual.run([
        "--source-dir", str(source_dir), "--config", str(config_path), "--output-root", str(output_root),
    ])
    second = import_manual.run([
        "--source-dir", str(source_dir), "--config", str(config_path), "--output-root", str(output_root),
    ])

    assert first == 0
    assert second == 0


def test_run_respects_season_filter(tmp_path):
    source_dir = tmp_path / "downloads"
    source_dir.mkdir()
    (source_dir / "2023.xlsx").write_bytes(VALID_XLSX_BYTES)
    (source_dir / "2024.xlsx").write_bytes(VALID_XLSX_BYTES)

    config_path = make_config(tmp_path, seasons=["2023", "2024"])
    output_root = tmp_path / "data"

    exit_code = import_manual.run([
        "--source-dir", str(source_dir),
        "--config", str(config_path),
        "--output-root", str(output_root),
        "--season", "2023",
    ])

    assert exit_code == 0
    assert (output_root / "raw" / "tennis" / "tennis_data_co_uk" / "ATP" / "2023.xlsx").exists()
    assert not (output_root / "raw" / "tennis" / "tennis_data_co_uk" / "ATP" / "2024.xlsx").exists()
