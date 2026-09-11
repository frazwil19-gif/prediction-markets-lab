"""Unit tests for prediction_markets_lab.ingestion.tennis_data_loader.

Entirely mocked HTTP -- no network access, per project instructions
section 19 ("do not repeatedly hit the live website while running the
test suite"), mirroring tests/unit/test_football_data_loader.py's
approach of substituting a fake client with a canned
(status, content_type, body) response queue.
"""

from __future__ import annotations

import pytest

import ssl
import urllib.error
from unittest.mock import patch

from prediction_markets_lab.ingestion.tennis_data_loader import (
    AcquisitionConfig,
    HttpClient,
    build_legacy_tolerant_ssl_context,
    compute_sha256_bytes,
    compute_sha256_text,
    fetch_one_bytes,
    fetch_one_text,
    looks_like_html_bytes,
    looks_like_html_text,
    tennis_data_co_uk_url,
    tml_database_match_file_url,
    write_raw_file_atomic_bytes,
    write_raw_file_atomic_text,
)


class FakeClient:
    """Returns one canned response per call, in order. Raises
    IndexError if called more times than responses were queued (a bug
    in the test, not the code under test)."""

    def __init__(self, text_responses=None, bytes_responses=None, raise_on_call=None):
        self._text_responses = list(text_responses or [])
        self._bytes_responses = list(bytes_responses or [])
        self._raise_on_call = raise_on_call
        self.calls = 0

    def get_text(self, url: str):
        self.calls += 1
        if self._raise_on_call and self.calls in self._raise_on_call:
            raise self._raise_on_call[self.calls]
        return self._text_responses.pop(0)

    def get_bytes(self, url: str):
        self.calls += 1
        if self._raise_on_call and self.calls in self._raise_on_call:
            raise self._raise_on_call[self.calls]
        return self._bytes_responses.pop(0)


def no_sleep(_seconds):
    pass


CONFIG = AcquisitionConfig(max_retries=2, initial_backoff_seconds=0.0, backoff_multiplier=1.0)

VALID_XLSX_BYTES = b"PK\x03\x04" + b"\x00" * 16


# --- TLS workaround for tennis-data.co.uk's OpenSSL-3-incompatible server --

def test_build_legacy_tolerant_ssl_context_returns_an_ssl_context():
    context = build_legacy_tolerant_ssl_context()
    assert isinstance(context, ssl.SSLContext)


def test_build_legacy_tolerant_ssl_context_still_verifies_certificates():
    # The legacy-compatibility relaxations (see the function's
    # docstring and https://bugs.python.org/issue43791) are scoped to
    # signature-algorithm/cipher security level and protocol-version
    # ceiling only -- none of them may disable certificate verification.
    context = build_legacy_tolerant_ssl_context()
    assert context.verify_mode == ssl.CERT_REQUIRED
    assert context.check_hostname is True


def test_build_legacy_tolerant_ssl_context_caps_the_protocol_ceiling_at_tls_1_2():
    # A second, stronger compatibility measure added after @SECLEVEL=0
    # alone proved insufficient against the real site: some old servers
    # send a generic TLSV1_ALERT_INTERNAL_ERROR when a modern client
    # offers TLS 1.3's newer ClientHello extensions at all.
    context = build_legacy_tolerant_ssl_context()
    assert context.maximum_version == ssl.TLSVersion.TLSv1_2


def test_http_client_defaults_to_the_legacy_tolerant_context():
    client = HttpClient(user_agent="test-agent", timeout_seconds=5.0)
    assert isinstance(client.ssl_context, ssl.SSLContext)
    assert client.ssl_context.verify_mode == ssl.CERT_REQUIRED


def test_http_client_accepts_an_explicit_ssl_context_override():
    custom = ssl.create_default_context()
    client = HttpClient(user_agent="test-agent", timeout_seconds=5.0, ssl_context=custom)
    assert client.ssl_context is custom


# --- URL builders ---------------------------------------------------

def test_tml_database_match_file_url():
    assert (
        tml_database_match_file_url(
            "https://raw.githubusercontent.com/Tennismylife/TML-Database/master", "{season}.csv", "2024"
        )
        == "https://raw.githubusercontent.com/Tennismylife/TML-Database/master/2024.csv"
    )


def test_tml_database_match_file_url_formats_season_into_template():
    assert (
        tml_database_match_file_url("https://example.com/tml", "{season}_matches.csv", "2025")
        == "https://example.com/tml/2025_matches.csv"
    )


def test_tennis_data_co_uk_url_selects_men_template_for_atp():
    url = tennis_data_co_uk_url("https://www.tennis-data.co.uk", "ATP", "2023", "{year}/{year}.xlsx", "{year}w/{year}.xlsx")
    assert url == "https://www.tennis-data.co.uk/2023/2023.xlsx"


def test_tennis_data_co_uk_url_selects_women_template_for_wta():
    url = tennis_data_co_uk_url("https://www.tennis-data.co.uk", "WTA", "2023", "{year}/{year}.xlsx", "{year}w/{year}.xlsx")
    assert url == "https://www.tennis-data.co.uk/2023w/2023.xlsx"


# --- HTML sniffing ----------------------------------------------------

def test_looks_like_html_text_detects_doctype():
    assert looks_like_html_text("<!DOCTYPE html><html><body>404</body></html>")


def test_looks_like_html_text_accepts_real_csv():
    assert not looks_like_html_text("tourney_id,tourney_name\n2024-001,Australian Open\n")


def test_looks_like_html_bytes_accepts_real_xlsx_magic():
    assert not looks_like_html_bytes(VALID_XLSX_BYTES)


def test_looks_like_html_bytes_detects_html_error_page():
    assert looks_like_html_bytes(b"<html><body>Not Found</body></html>")


# --- HttpClient._get_raw / real urllib.error.HTTPError handling -----------
#
# Regression tests for a real bug found against the live acquisition
# run (originally against Sackmann's repos, before the TML-Database
# pivot): urllib.request.urlopen() raises urllib.error.HTTPError
# for ANY non-2xx response (it does NOT return it as a normal response
# object the way `requests` does). HTTPError is a subclass of URLError,
# so without explicit handling in HttpClient._get_raw, a real 404 was
# being caught by _retry_loop's broad `except URLError`, misclassified
# as a transient network error, retried max_retries times, and finally
# reported as "network error: HTTP Error 404: Not Found" instead of
# failing fast via the intended status-code branching. These tests
# exercise the real HttpClient (not FakeClient) against a mocked
# urlopen, since that is the only way to reach this code path.

class _FakeHTTPErrorResponse:
    """Minimal stand-in for the file-like object urllib.error.HTTPError
    behaves as (it subclasses addinfourl), enough for our _get_raw to
    call .headers.get(...) and .read() on it."""

    def __init__(self, body: bytes, content_type: str):
        self._body = body
        self.headers = {"Content-Type": content_type}

    def read(self):
        return self._body


def _make_http_error(code: int, body: bytes = b"Not Found", content_type: str = "text/plain") -> urllib.error.HTTPError:
    exc = urllib.error.HTTPError(url="https://example.com/x", code=code, msg="error", hdrs=None, fp=None)
    fake = _FakeHTTPErrorResponse(body, content_type)
    exc.headers = fake.headers
    exc.read = fake.read
    return exc


def test_http_client_get_text_converts_404_httperror_into_a_normal_tuple():
    client = HttpClient(user_agent="test-agent", timeout_seconds=5.0)
    with patch("urllib.request.urlopen", side_effect=_make_http_error(404)):
        status, content_type, body = client.get_text("https://example.com/x.csv")
    assert status == 404
    assert body == "Not Found"


def test_fetch_one_text_fails_fast_on_a_real_404_httperror_without_retrying():
    client = HttpClient(user_agent="test-agent", timeout_seconds=5.0)
    with patch("urllib.request.urlopen", side_effect=_make_http_error(404)):
        result = fetch_one_text("k", "https://example.com/x.csv", CONFIG, client, sleep_fn=no_sleep)
    assert result.success is False
    assert result.http_status == 404
    assert "network error" not in (result.error_message or "")


def test_fetch_one_text_retries_a_real_503_httperror_then_gives_up():
    # A 5xx HTTPError should still go through the retry/backoff path
    # (just via the http_status branch now, not the network-error
    # branch) and be exhausted after max_retries + 1 attempts.
    client = HttpClient(user_agent="test-agent", timeout_seconds=5.0)
    with patch("urllib.request.urlopen", side_effect=_make_http_error(503)):
        result = fetch_one_text("k", "https://example.com/x.csv", CONFIG, client, sleep_fn=no_sleep)
    assert result.success is False
    assert "server error" in result.error_message


# --- fetch_one_text ----------------------------------------------------

def test_fetch_one_text_success_on_first_try():
    client = FakeClient(text_responses=[(200, "text/csv", "a,b\n1,2\n")])
    result = fetch_one_text("k", "https://example.com/x.csv", CONFIG, client, sleep_fn=no_sleep)
    assert result.success is True
    assert result.raw_text == "a,b\n1,2\n"
    assert result.sha256 == compute_sha256_text("a,b\n1,2\n")
    assert result.retries_used == 0


def test_fetch_one_text_retries_on_429_then_succeeds():
    client = FakeClient(text_responses=[(429, "text/html", "rate limited"), (200, "text/csv", "a,b\n1,2\n")])
    result = fetch_one_text("k", "https://example.com/x.csv", CONFIG, client, sleep_fn=no_sleep)
    assert result.success is True
    assert result.rate_limited_count == 1


def test_fetch_one_text_retries_on_500_then_succeeds():
    client = FakeClient(text_responses=[(503, "text/html", "oops"), (200, "text/csv", "a,b\n1,2\n")])
    result = fetch_one_text("k", "https://example.com/x.csv", CONFIG, client, sleep_fn=no_sleep)
    assert result.success is True


def test_fetch_one_text_fails_after_exhausting_retries():
    client = FakeClient(text_responses=[(503, "text/html", "oops")] * (CONFIG.max_retries + 1))
    result = fetch_one_text("k", "https://example.com/x.csv", CONFIG, client, sleep_fn=no_sleep)
    assert result.success is False
    assert "server error" in result.error_message


def test_fetch_one_text_rejects_html_error_page_body_immediately():
    client = FakeClient(text_responses=[(200, "text/html", "<!DOCTYPE html><html><body>oops</body></html>")])
    result = fetch_one_text("k", "https://example.com/x.csv", CONFIG, client, sleep_fn=no_sleep)
    assert result.success is False
    assert "HTML error page" in result.error_message
    assert client.calls == 1  # not retried -- a 200 with HTML body is not transient


def test_fetch_one_text_does_not_retry_on_plain_404():
    client = FakeClient(text_responses=[(404, "text/plain", "not found")])
    result = fetch_one_text("k", "https://example.com/x.csv", CONFIG, client, sleep_fn=no_sleep)
    assert result.success is False
    assert result.http_status == 404
    assert client.calls == 1


def test_fetch_one_text_retries_on_network_error():
    client = FakeClient(text_responses=[(200, "text/csv", "a,b\n1,2\n")], raise_on_call={1: OSError("connection reset")})
    result = fetch_one_text("k", "https://example.com/x.csv", CONFIG, client, sleep_fn=no_sleep)
    assert result.success is True


# --- fetch_one_bytes ----------------------------------------------------

def test_fetch_one_bytes_success():
    client = FakeClient(bytes_responses=[(200, "application/octet-stream", VALID_XLSX_BYTES)])
    result = fetch_one_bytes("k", "https://example.com/x.xlsx", CONFIG, client, sleep_fn=no_sleep)
    assert result.success is True
    assert result.raw_bytes == VALID_XLSX_BYTES
    assert result.sha256 == compute_sha256_bytes(VALID_XLSX_BYTES)


def test_fetch_one_bytes_rejects_html_body():
    client = FakeClient(bytes_responses=[(200, "text/html", b"<html>not xlsx</html>")])
    result = fetch_one_bytes("k", "https://example.com/x.xlsx", CONFIG, client, sleep_fn=no_sleep)
    assert result.success is False
    assert "HTML error page" in result.error_message


# --- write_raw_file_atomic_text / _bytes ----------------------------------

def test_write_raw_file_atomic_text_writes_new_file(tmp_path):
    dest = tmp_path / "sub" / "file.csv"
    assert write_raw_file_atomic_text(dest, "a,b\n1,2\n") is True
    assert dest.read_text() == "a,b\n1,2\n"


def test_write_raw_file_atomic_text_is_idempotent_on_identical_content(tmp_path):
    dest = tmp_path / "file.csv"
    write_raw_file_atomic_text(dest, "a,b\n1,2\n")
    assert write_raw_file_atomic_text(dest, "a,b\n1,2\n") is True


def test_write_raw_file_atomic_text_refuses_silent_overwrite_on_hash_mismatch(tmp_path):
    dest = tmp_path / "file.csv"
    write_raw_file_atomic_text(dest, "a,b\n1,2\n")
    with pytest.raises(FileExistsError):
        write_raw_file_atomic_text(dest, "a,b\n9,9\n")


def test_write_raw_file_atomic_bytes_writes_new_file(tmp_path):
    dest = tmp_path / "file.xlsx"
    assert write_raw_file_atomic_bytes(dest, VALID_XLSX_BYTES) is True
    assert dest.read_bytes() == VALID_XLSX_BYTES


def test_write_raw_file_atomic_bytes_refuses_silent_overwrite_on_hash_mismatch(tmp_path):
    dest = tmp_path / "file.xlsx"
    write_raw_file_atomic_bytes(dest, VALID_XLSX_BYTES)
    with pytest.raises(FileExistsError):
        write_raw_file_atomic_bytes(dest, VALID_XLSX_BYTES + b"\x00")
