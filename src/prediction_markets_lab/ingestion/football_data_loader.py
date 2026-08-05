"""Paced, safe acquisition of historical football data from Football-Data.co.uk.

This module contains the production loader. It cannot be exercised
against the live site from this project's own sandboxed CI/dev
environment (no network egress to football-data.co.uk is permitted
there) -- it is designed to be run from an environment with normal
internet access (e.g. a developer's machine, or Claude Code with
network access), and is tested here entirely with mocked HTTP
responses (see tests/unit/test_football_data_loader.py), per project
instructions section 19 ("do not repeatedly hit the live website
while running the test suite").

Design constraints confirmed directly against the live site during the
Stage 3A feasibility work (see reports/audits/FOOTBALL_DATA_FEASIBILITY.md):

- No authentication required; plain HTTPS GET returning CSV.
- The site rate-limits rapid sequential requests (a 429 was observed
  after ~2 fetches in quick succession) -- this loader paces requests
  and backs off on 429/5xx.
- Column schema varies by season (more bookmakers/markets in recent
  seasons) -- this loader does not assume a fixed header; schema
  inventory is a separate downstream step (schema_inventory.py-style
  analysis, not enforced at download time).
- Occasional per-bookmaker blank cells exist even in complete files --
  this loader does not attempt to repair or reject rows for that
  reason; that is a downstream concern (probability.market_pipeline
  already treats blanks as "did not quote").
"""

from __future__ import annotations

import hashlib
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

DEFAULT_BASE_URL = "https://www.football-data.co.uk/mmz4281"
DEFAULT_USER_AGENT = (
    "PredictionMarketsLab/0.1 (personal research project; "
    "contact via repository issues; see docs/DATA_LEAKAGE_RULES.md "
    "and docs/HISTORICAL_PRICE_AND_CLV_LIMITATIONS.md for how this "
    "data is used)"
)


@dataclass(frozen=True)
class AcquisitionConfig:
    """Configuration for a paced acquisition run.

    All fields are configurable per project coding standards (no magic
    numbers) and default to conservative values discovered during the
    Stage 3A feasibility audit.
    """

    base_url: str = DEFAULT_BASE_URL
    user_agent: str = DEFAULT_USER_AGENT
    delay_between_requests_seconds: float = 6.0
    max_retries: int = 4
    initial_backoff_seconds: float = 10.0
    backoff_multiplier: float = 2.0
    request_timeout_seconds: float = 30.0


@dataclass(frozen=True)
class FetchResult:
    """Outcome of attempting to fetch a single season/competition file."""

    competition_code: str
    season: str
    url: str
    success: bool
    http_status: int | None
    content_type: str | None
    byte_size: int | None
    sha256: str | None
    downloaded_at: str | None
    retries_used: int
    rate_limited_count: int
    error_message: str | None
    raw_text: str | None = None  # only populated on success; caller writes to disk


def build_url(base_url: str, season: str, competition_code: str) -> str:
    """Build the Football-Data.co.uk CSV URL for a season/competition.

    Args:
        base_url: e.g. "https://www.football-data.co.uk/mmz4281".
        season: Football-Data's compact season code, e.g. "2425" for
            2024/25. Callers typically derive this from a human-readable
            season like "2024_25" via `season_to_footballdata_code`.
        competition_code: e.g. "E0", "E1", "SC0".

    Returns:
        The full CSV URL.
    """
    return f"{base_url}/{season}/{competition_code}.csv"


def season_to_footballdata_code(human_season: str) -> str:
    """Convert a human-readable season like "2024_25" to Football-Data's "2425".

    Args:
        human_season: A season string like "2024_25" or "2024/25".

    Returns:
        The 4-digit compact code, e.g. "2425".

    Raises:
        ValueError: If human_season is not in a recognised format.
    """
    normalised = human_season.replace("/", "_")
    parts = normalised.split("_")
    if len(parts) != 2 or len(parts[0]) != 4 or len(parts[1]) != 2:
        raise ValueError(f"unrecognised season format: {human_season!r}")
    return parts[0][2:] + parts[1]


def looks_like_html(text: str) -> bool:
    """Detect whether a response body is an HTML error page rather than CSV.

    Args:
        text: The response body.

    Returns:
        True if the content looks like HTML (e.g. a 404/rate-limit
        error page served instead of the expected CSV), so callers can
        reject it rather than saving it as a raw data file.
    """
    stripped = text.strip().lower()
    return stripped.startswith("<!doctype") or stripped.startswith("<html") or "<body" in stripped[:2000]


def compute_sha256(text: str) -> str:
    """Compute the SHA-256 hex digest of a string, encoded as UTF-8.

    Args:
        text: The content to hash.

    Returns:
        The hex-encoded SHA-256 digest.
    """
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


class HttpClient:
    """Thin, mockable wrapper around the HTTP call this loader needs.

    Kept as a small seam so unit tests can substitute a fake client
    that returns canned (status, content_type, body) tuples without
    touching the network, per project instructions section 19.
    """

    def __init__(self, user_agent: str, timeout_seconds: float):
        self.user_agent = user_agent
        self.timeout_seconds = timeout_seconds

    def get(self, url: str) -> tuple[int, str, str]:
        """Perform a GET request.

        Returns:
            (http_status, content_type, body_text)

        Raises:
            urllib.error.URLError / socket.timeout on network failure.
        """
        request = urllib.request.Request(url, headers={"User-Agent": self.user_agent})
        with urllib.request.urlopen(request, timeout=self.timeout_seconds) as response:
            status = response.status
            content_type = response.headers.get("Content-Type", "")
            body = response.read().decode("utf-8-sig", errors="replace")
            return status, content_type, body


def fetch_one(
    competition_code: str,
    season: str,
    config: AcquisitionConfig,
    client: HttpClient,
    sleep_fn=time.sleep,
) -> FetchResult:
    """Fetch a single competition/season CSV with retry/backoff.

    Args:
        competition_code: e.g. "E0".
        season: Football-Data compact season code, e.g. "2425".
        config: Acquisition configuration (pacing, retries, backoff).
        client: An HttpClient (or test double) to perform the GET.
        sleep_fn: Injectable sleep function for deterministic tests.

    Returns:
        A FetchResult describing the outcome. On success, raw_text
        holds the CSV content for the caller to write atomically to
        disk; on failure, raw_text is None and error_message explains
        why.
    """
    url = build_url(config.base_url, season, competition_code)
    backoff = config.initial_backoff_seconds
    retries_used = 0
    rate_limited_count = 0
    last_error: str | None = None

    for attempt in range(config.max_retries + 1):
        try:
            status, content_type, body = client.get(url)
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            last_error = f"network error: {exc}"
            retries_used = attempt
            if attempt < config.max_retries:
                sleep_fn(backoff)
                backoff *= config.backoff_multiplier
                continue
            break

        if status == 429:
            rate_limited_count += 1
            last_error = "rate limited (HTTP 429)"
            retries_used = attempt
            if attempt < config.max_retries:
                sleep_fn(backoff)
                backoff *= config.backoff_multiplier
                continue
            break

        if status >= 500:
            last_error = f"server error (HTTP {status})"
            retries_used = attempt
            if attempt < config.max_retries:
                sleep_fn(backoff)
                backoff *= config.backoff_multiplier
                continue
            break

        if status != 200:
            return FetchResult(
                competition_code=competition_code,
                season=season,
                url=url,
                success=False,
                http_status=status,
                content_type=content_type,
                byte_size=None,
                sha256=None,
                downloaded_at=None,
                retries_used=attempt,
                rate_limited_count=rate_limited_count,
                error_message=f"unexpected HTTP status {status}",
            )

        if looks_like_html(body):
            return FetchResult(
                competition_code=competition_code,
                season=season,
                url=url,
                success=False,
                http_status=status,
                content_type=content_type,
                byte_size=None,
                sha256=None,
                downloaded_at=None,
                retries_used=attempt,
                rate_limited_count=rate_limited_count,
                error_message="response body looks like an HTML error page, not CSV -- rejected",
            )

        return FetchResult(
            competition_code=competition_code,
            season=season,
            url=url,
            success=True,
            http_status=status,
            content_type=content_type,
            byte_size=len(body.encode("utf-8")),
            sha256=compute_sha256(body),
            downloaded_at=datetime.now(timezone.utc).isoformat(timespec="seconds"),
            retries_used=attempt,
            rate_limited_count=rate_limited_count,
            error_message=None,
            raw_text=body,
        )

    return FetchResult(
        competition_code=competition_code,
        season=season,
        url=url,
        success=False,
        http_status=None,
        content_type=None,
        byte_size=None,
        sha256=None,
        downloaded_at=None,
        retries_used=retries_used,
        rate_limited_count=rate_limited_count,
        error_message=last_error or "unknown failure",
    )


def write_raw_file_atomic(path: Path, content: str, allow_overwrite_if_hash_matches: bool = True) -> bool:
    """Write raw content to disk atomically, refusing silent overwrites.

    Args:
        path: Destination path.
        content: The raw file content to write.
        allow_overwrite_if_hash_matches: If the destination already
            exists, only overwrite if its content hash matches the new
            content's hash (i.e. it's a genuine no-op re-download);
            otherwise refuse.

    Returns:
        True if the file was written (or already matched), False if
        writing was refused because an existing file would be
        overwritten with different content.

    Raises:
        FileExistsError: If the destination exists with different
            content and allow_overwrite_if_hash_matches is False, or
            if it exists with different content regardless (raw files
            must never be silently modified in place).
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    new_hash = compute_sha256(content)

    if path.exists():
        existing_hash = compute_sha256(path.read_text(encoding="utf-8"))
        if existing_hash == new_hash:
            return True  # identical content already present; no-op
        raise FileExistsError(
            f"{path} already exists with different content (existing sha256="
            f"{existing_hash}, new sha256={new_hash}) -- raw files must never be "
            "silently overwritten; resolve manually or use a new file name"
        )

    tmp_path = path.with_suffix(path.suffix + ".tmp")
    tmp_path.write_text(content, encoding="utf-8")
    tmp_path.replace(path)  # atomic on POSIX
    return True
