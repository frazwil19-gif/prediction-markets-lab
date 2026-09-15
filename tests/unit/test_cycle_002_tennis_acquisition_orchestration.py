"""Tests for scripts/run_cycle_002_tennis_data_acquisition.py.

Per project instructions, no real network calls are made -- fetch_one_text
and fetch_one_bytes are monkeypatched to return canned FetchResult objects,
mirroring test_cycle_001_acquisition_orchestration.py's convention.

Focus of this file: the optional_source_families behaviour added
2026-09-15 after real acquisition runs (2026-09-13, 2026-09-15) confirmed
tennis_data_co_uk's HTTPS endpoint fails the TLS handshake for every real
client tried (a GitHub Actions runner even after bumping to Python 3.12,
Anthropic's own web-fetch infrastructure, and an unmodified Chrome browser)
-- see config/cycle_002_tennis_data.yaml's comment above
optional_source_families. A source confirmed broken like this should not
block progress on tml_database_match, which has fetched cleanly on every
real run and is the only source this project has for actual match results.
"""

import importlib.util
import sys
from datetime import datetime, timezone
from pathlib import Path

import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
SCRIPT_PATH = REPO_ROOT / "scripts" / "run_cycle_002_tennis_data_acquisition.py"


def load_script_module():
    spec = importlib.util.spec_from_file_location("run_cycle_002_tennis_data_acquisition", SCRIPT_PATH)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def script_module():
    return load_script_module()


def _fake_fetch_result(source_key: str, url: str, success: bool, raw_text=None, raw_bytes=None, error_message=None):
    return dict(
        source_key=source_key, url=url, success=success, http_status=200 if success else None,
        content_type="text/csv", byte_size=len(raw_text or raw_bytes or b""), sha256=None,
        downloaded_at=datetime.now(timezone.utc).isoformat(timespec="seconds"), retries_used=0,
        rate_limited_count=0, error_message=error_message, raw_text=raw_text, raw_bytes=raw_bytes,
    )


def test_config_declares_tennis_data_co_uk_as_the_only_optional_source():
    with open(REPO_ROOT / "config" / "cycle_002_tennis_data.yaml") as f:
        config = yaml.safe_load(f)
    assert config["optional_source_families"] == ["tennis_data_co_uk"]
    assert "tml_database_match" not in config["optional_source_families"]


def test_optional_source_failure_does_not_fail_the_run(script_module, tmp_path, monkeypatch):
    """tennis_data_co_uk (optional) failing must not make the run exit
    non-zero as long as tml_database_match (required) succeeds -- this is
    the exact real-world case from the 2026-09-13/09-15 acquisition runs."""
    from prediction_markets_lab.ingestion.tennis_data_loader import FetchResult

    def fake_fetch_text(source_key, url, config, client, sleep_fn=None):
        return FetchResult(**_fake_fetch_result(source_key, url, success=True, raw_text="tourney_id\nX\n"))

    def fake_fetch_bytes(source_key, url, config, client, sleep_fn=None):
        return FetchResult(**_fake_fetch_result(
            source_key, url, success=False,
            error_message="network error: [SSL: TLSV1_ALERT_INTERNAL_ERROR] tlsv1 alert internal error",
        ))

    monkeypatch.setattr(script_module, "fetch_one_text", fake_fetch_text)
    monkeypatch.setattr(script_module, "fetch_one_bytes", fake_fetch_bytes)

    exit_code = script_module.run([
        "--tour", "ATP", "--season", "2024",
        "--output-root", str(tmp_path), "--reports-root", str(tmp_path / "reports"),
    ])

    assert exit_code == 0


def test_optional_source_failure_is_recorded_honestly_not_hidden(script_module, tmp_path, monkeypatch):
    """A failed optional source must still show up in the run summary and
    the data-version record -- never silently dropped, never faked as
    present. This is what keeps 'optional' from becoming 'fabricated'."""
    from prediction_markets_lab.ingestion.tennis_data_loader import FetchResult
    import json

    monkeypatch.setattr(
        script_module, "fetch_one_text",
        lambda source_key, url, config, client, sleep_fn=None: FetchResult(
            **_fake_fetch_result(source_key, url, success=True, raw_text="tourney_id\nX\n")
        ),
    )
    monkeypatch.setattr(
        script_module, "fetch_one_bytes",
        lambda source_key, url, config, client, sleep_fn=None: FetchResult(
            **_fake_fetch_result(source_key, url, success=False, error_message="network error: TLS handshake failed"),
        ),
    )

    exit_code = script_module.run([
        "--tour", "ATP", "--season", "2024",
        "--output-root", str(tmp_path), "--reports-root", str(tmp_path / "reports"),
    ])
    assert exit_code == 0

    # NOTE: manifest_path/data_version_path are computed from config as
    # REPO_ROOT-relative paths, ignoring --output-root/--reports-root (a
    # known, pre-existing quirk -- see
    # research/cycles/CYCLE_002_TENNIS/PLAN.md). That's why this test reads
    # from the real repo paths below rather than under tmp_path, and cleans
    # up afterwards so it never leaves fake data behind in the real repo.
    data_version_path = REPO_ROOT / "data" / "processed" / "tennis" / "cycle_002_data_version.json"
    with open(data_version_path) as f:
        data_version = json.load(f)
    try:
        assert data_version["summary"]["files_failed_optional"] == 1
        assert data_version["summary"]["files_failed"] == 0
        assert "tennis_data_co_uk:ATP:2024" in data_version["summary"]["failed_optional_source_keys"]
        assert data_version["optional_source_families"] == ["tennis_data_co_uk"]
    finally:
        # This script writes manifest/data-version to REPO_ROOT-relative
        # paths regardless of --output-root/--reports-root (a known,
        # documented quirk -- see research/cycles/CYCLE_002_TENNIS/PLAN.md);
        # clean up so this test never leaves fake data behind in the real
        # repo paths.
        data_version_path.unlink(missing_ok=True)
        manifest_path = REPO_ROOT / "reports" / "audits" / "tennis_data_manifest.csv"
        manifest_path.unlink(missing_ok=True)


def test_required_source_failure_still_fails_the_run(script_module, tmp_path, monkeypatch):
    """tml_database_match (required) failing must still exit non-zero,
    exactly like before this change -- only tennis_data_co_uk is optional."""
    from prediction_markets_lab.ingestion.tennis_data_loader import FetchResult

    monkeypatch.setattr(
        script_module, "fetch_one_text",
        lambda source_key, url, config, client, sleep_fn=None: FetchResult(
            **_fake_fetch_result(source_key, url, success=False, error_message="network error: 404"),
        ),
    )
    monkeypatch.setattr(
        script_module, "fetch_one_bytes",
        lambda source_key, url, config, client, sleep_fn=None: FetchResult(
            **_fake_fetch_result(source_key, url, success=True, raw_bytes=b"PK\x03\x04fake"),
        ),
    )

    exit_code = script_module.run([
        "--tour", "ATP", "--season", "2024",
        "--output-root", str(tmp_path), "--reports-root", str(tmp_path / "reports"),
    ])

    assert exit_code == 1

    data_version_path = REPO_ROOT / "data" / "processed" / "tennis" / "cycle_002_data_version.json"
    data_version_path.unlink(missing_ok=True)
    manifest_path = REPO_ROOT / "reports" / "audits" / "tennis_data_manifest.csv"
    manifest_path.unlink(missing_ok=True)


def test_optional_source_gets_the_reduced_retry_budget(script_module, tmp_path, monkeypatch):
    """The config in front of tennis_data_co_uk (optional) must use
    pacing.optional_source_max_retries, not the full pacing.max_retries
    used for tml_database_match (required) -- this is the fix for a real
    run sitting for ~10+ minutes retrying a source already known to be
    broken (see PLAN.md's 2026-09-15 diagnostic notes)."""
    from prediction_markets_lab.ingestion.tennis_data_loader import FetchResult

    seen_max_retries = {}

    def fake_fetch_text(source_key, url, config, client, sleep_fn=None):
        seen_max_retries["tml_database_match"] = config.max_retries
        return FetchResult(**_fake_fetch_result(source_key, url, success=True, raw_text="tourney_id\nX\n"))

    def fake_fetch_bytes(source_key, url, config, client, sleep_fn=None):
        seen_max_retries["tennis_data_co_uk"] = config.max_retries
        return FetchResult(**_fake_fetch_result(source_key, url, success=False, error_message="network error"))

    monkeypatch.setattr(script_module, "fetch_one_text", fake_fetch_text)
    monkeypatch.setattr(script_module, "fetch_one_bytes", fake_fetch_bytes)

    script_module.run([
        "--tour", "ATP", "--season", "2024",
        "--output-root", str(tmp_path), "--reports-root", str(tmp_path / "reports"),
    ])

    with open(REPO_ROOT / "config" / "cycle_002_tennis_data.yaml") as f:
        config = yaml.safe_load(f)
    assert seen_max_retries["tml_database_match"] == config["pacing"]["max_retries"]
    assert seen_max_retries["tennis_data_co_uk"] == config["pacing"]["optional_source_max_retries"]
    assert seen_max_retries["tennis_data_co_uk"] < seen_max_retries["tml_database_match"]

    data_version_path = REPO_ROOT / "data" / "processed" / "tennis" / "cycle_002_data_version.json"
    data_version_path.unlink(missing_ok=True)
    manifest_path = REPO_ROOT / "reports" / "audits" / "tennis_data_manifest.csv"
    manifest_path.unlink(missing_ok=True)


def test_max_retries_cli_override_only_applies_to_required_family(script_module, tmp_path, monkeypatch):
    """--max-retries is a real, always-passed workflow_dispatch input with a
    default value (see the workflow's "Build acquisition command" step) --
    it is NEVER actually omitted on a real run. If it were still allowed to
    also raise the optional family's retry budget, it would silently
    re-introduce the exact ~10+ minute stall this fix exists to prevent
    (see PLAN.md's 2026-09-15 diagnostic notes). So --max-retries must only
    affect the required family; the optional family's budget is controlled
    solely by config's pacing.optional_source_max_retries, independently,
    unless --optional-max-retries is explicitly passed too."""
    from prediction_markets_lab.ingestion.tennis_data_loader import FetchResult

    seen_max_retries = {}

    def fake_fetch_text(source_key, url, config, client, sleep_fn=None):
        seen_max_retries["tml_database_match"] = config.max_retries
        return FetchResult(**_fake_fetch_result(source_key, url, success=True, raw_text="tourney_id\nX\n"))

    def fake_fetch_bytes(source_key, url, config, client, sleep_fn=None):
        seen_max_retries["tennis_data_co_uk"] = config.max_retries
        return FetchResult(**_fake_fetch_result(source_key, url, success=False, error_message="network error"))

    monkeypatch.setattr(script_module, "fetch_one_text", fake_fetch_text)
    monkeypatch.setattr(script_module, "fetch_one_bytes", fake_fetch_bytes)

    script_module.run([
        "--tour", "ATP", "--season", "2024", "--max-retries", "2",
        "--output-root", str(tmp_path), "--reports-root", str(tmp_path / "reports"),
    ])

    with open(REPO_ROOT / "config" / "cycle_002_tennis_data.yaml") as f:
        config = yaml.safe_load(f)

    assert seen_max_retries["tml_database_match"] == 2
    assert seen_max_retries["tennis_data_co_uk"] == config["pacing"]["optional_source_max_retries"]
    assert seen_max_retries["tennis_data_co_uk"] != 2

    data_version_path = REPO_ROOT / "data" / "processed" / "tennis" / "cycle_002_data_version.json"
    data_version_path.unlink(missing_ok=True)
    manifest_path = REPO_ROOT / "reports" / "audits" / "tennis_data_manifest.csv"
    manifest_path.unlink(missing_ok=True)


def test_explicit_optional_max_retries_cli_override_applies_only_to_optional_family(script_module, tmp_path, monkeypatch):
    """--optional-max-retries is the deliberate escape hatch for a
    diagnostic pass that wants to give the known-broken optional source a
    longer, uniform retry budget -- it must apply only to the optional
    family and leave the required family's budget (from --max-retries, or
    config's pacing.max_retries when that's absent too) untouched."""
    from prediction_markets_lab.ingestion.tennis_data_loader import FetchResult

    seen_max_retries = {}

    def fake_fetch_text(source_key, url, config, client, sleep_fn=None):
        seen_max_retries["tml_database_match"] = config.max_retries
        return FetchResult(**_fake_fetch_result(source_key, url, success=True, raw_text="tourney_id\nX\n"))

    def fake_fetch_bytes(source_key, url, config, client, sleep_fn=None):
        seen_max_retries["tennis_data_co_uk"] = config.max_retries
        return FetchResult(**_fake_fetch_result(source_key, url, success=False, error_message="network error"))

    monkeypatch.setattr(script_module, "fetch_one_text", fake_fetch_text)
    monkeypatch.setattr(script_module, "fetch_one_bytes", fake_fetch_bytes)

    script_module.run([
        "--tour", "ATP", "--season", "2024", "--max-retries", "4", "--optional-max-retries", "7",
        "--output-root", str(tmp_path), "--reports-root", str(tmp_path / "reports"),
    ])

    assert seen_max_retries["tml_database_match"] == 4
    assert seen_max_retries["tennis_data_co_uk"] == 7

    data_version_path = REPO_ROOT / "data" / "processed" / "tennis" / "cycle_002_data_version.json"
    data_version_path.unlink(missing_ok=True)
    manifest_path = REPO_ROOT / "reports" / "audits" / "tennis_data_manifest.csv"
    manifest_path.unlink(missing_ok=True)
