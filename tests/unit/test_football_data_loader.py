"""Tests for ingestion.football_data_loader.

Per project instructions section 19, all HTTP interaction is mocked --
these tests never touch the live football-data.co.uk site.
"""

from pathlib import Path

import pytest

from prediction_markets_lab.ingestion.football_data_loader import (
    AcquisitionConfig,
    build_url,
    compute_sha256,
    fetch_one,
    looks_like_html,
    season_to_footballdata_code,
    write_raw_file_atomic,
)


class FakeHttpClient:
    """A scripted HTTP client for deterministic tests.

    `responses` is a list of (status, content_type, body) tuples
    returned in order, one per call to `.get()`.
    """

    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []

    def get(self, url):
        self.calls.append(url)
        if not self.responses:
            raise AssertionError("FakeHttpClient ran out of scripted responses")
        return self.responses.pop(0)


CSV_BODY = "Div,Date,HomeTeam,AwayTeam,FTHG,FTAG,FTR\nE0,16/08/2024,Man United,Fulham,1,0,H\n"
HTML_ERROR_BODY = "<!DOCTYPE html><html><body><h1>429 Too Many Requests</h1></body></html>"


def test_build_url():
    url = build_url("https://www.football-data.co.uk/mmz4281", "2425", "E0")
    assert url == "https://www.football-data.co.uk/mmz4281/2425/E0.csv"


def test_season_to_footballdata_code():
    assert season_to_footballdata_code("2024_25") == "2425"
    assert season_to_footballdata_code("2020/21") == "2021"


def test_season_to_footballdata_code_rejects_bad_format():
    with pytest.raises(ValueError):
        season_to_footballdata_code("2024")


def test_looks_like_html_detects_error_page():
    assert looks_like_html(HTML_ERROR_BODY)


def test_looks_like_html_false_for_csv():
    assert not looks_like_html(CSV_BODY)


def test_compute_sha256_deterministic():
    h1 = compute_sha256("hello")
    h2 = compute_sha256("hello")
    assert h1 == h2
    assert len(h1) == 64


def test_fetch_one_success_first_try():
    client = FakeHttpClient([(200, "text/csv", CSV_BODY)])
    config = AcquisitionConfig(max_retries=3)
    result = fetch_one("E0", "2425", config, client, sleep_fn=lambda s: None)

    assert result.success
    assert result.http_status == 200
    assert result.raw_text == CSV_BODY
    assert result.sha256 == compute_sha256(CSV_BODY)
    assert result.retries_used == 0
    assert result.rate_limited_count == 0
    assert len(client.calls) == 1


def test_fetch_one_retries_on_429_then_succeeds():
    client = FakeHttpClient(
        [
            (429, "text/html", HTML_ERROR_BODY),
            (429, "text/html", HTML_ERROR_BODY),
            (200, "text/csv", CSV_BODY),
        ]
    )
    config = AcquisitionConfig(max_retries=3, initial_backoff_seconds=0.01, backoff_multiplier=1.0)
    sleeps = []
    result = fetch_one("E0", "2425", config, client, sleep_fn=sleeps.append)

    assert result.success
    assert result.rate_limited_count == 2
    assert len(client.calls) == 3
    assert len(sleeps) == 2  # slept before each retry


def test_fetch_one_gives_up_after_max_retries():
    client = FakeHttpClient([(429, "text/html", HTML_ERROR_BODY)] * 5)
    config = AcquisitionConfig(max_retries=2, initial_backoff_seconds=0.01, backoff_multiplier=1.0)
    result = fetch_one("E0", "2425", config, client, sleep_fn=lambda s: None)

    assert not result.success
    assert result.rate_limited_count >= 1
    assert "rate limited" in result.error_message
    # max_retries=2 means 3 total attempts (initial + 2 retries)
    assert len(client.calls) == 3


def test_fetch_one_rejects_html_error_page_even_with_200_status():
    """A misconfigured server could return 200 with an HTML error body --
    this must still be rejected rather than saved as CSV."""
    client = FakeHttpClient([(200, "text/html", HTML_ERROR_BODY)])
    config = AcquisitionConfig(max_retries=1)
    result = fetch_one("E0", "2425", config, client, sleep_fn=lambda s: None)

    assert not result.success
    assert "HTML error page" in result.error_message
    assert result.raw_text is None


def test_fetch_one_rejects_unexpected_status_without_retry():
    client = FakeHttpClient([(404, "text/html", HTML_ERROR_BODY)])
    config = AcquisitionConfig(max_retries=3)
    result = fetch_one("E0", "9999", config, client, sleep_fn=lambda s: None)

    assert not result.success
    assert result.http_status == 404
    assert len(client.calls) == 1  # no retry on a plain 404


def test_fetch_one_retries_on_server_error():
    client = FakeHttpClient([(503, "text/html", ""), (200, "text/csv", CSV_BODY)])
    config = AcquisitionConfig(max_retries=2, initial_backoff_seconds=0.01, backoff_multiplier=1.0)
    result = fetch_one("E0", "2425", config, client, sleep_fn=lambda s: None)

    assert result.success
    assert len(client.calls) == 2


def test_write_raw_file_atomic_creates_new_file(tmp_path: Path):
    path = tmp_path / "E0" / "2024_25" / "E0.csv"
    written = write_raw_file_atomic(path, CSV_BODY)
    assert written
    assert path.exists()
    assert path.read_text(encoding="utf-8") == CSV_BODY


def test_write_raw_file_atomic_noop_when_hash_matches(tmp_path: Path):
    path = tmp_path / "E0.csv"
    write_raw_file_atomic(path, CSV_BODY)
    # Re-writing identical content should succeed as a no-op.
    written_again = write_raw_file_atomic(path, CSV_BODY)
    assert written_again


def test_write_raw_file_atomic_refuses_silent_overwrite(tmp_path: Path):
    path = tmp_path / "E0.csv"
    write_raw_file_atomic(path, CSV_BODY)
    with pytest.raises(FileExistsError):
        write_raw_file_atomic(path, CSV_BODY + "\nEXTRA_ROW")
    # Original content must be untouched.
    assert path.read_text(encoding="utf-8") == CSV_BODY
