"""Paced, safe acquisition of historical tennis data for Cycle 2.

Two independent source families, each with its own content shape:

- Tennismylife/TML-Database (raw.githubusercontent.com), an
  actively-maintained continuation of Jeff Sackmann's tennis_atp repo:
  plain CSV, one self-contained file per ATP season (match metadata,
  players, surface, score, and winner/loser rank/rank_points/age/
  height/hand/country all embedded per row -- no separate rankings or
  player-bio files needed). Reconciled against this project's
  football_data_loader.py convention as closely as possible: same
  AcquisitionConfig/FetchResult/HttpClient/fetch_one/
  write_raw_file_atomic shape, urllib-based (no new dependency), same
  retry/backoff/rate-limit handling, same "reject bodies that look like
  an HTML error page" safeguard.

  PIVOT NOTE (2026-09-11): the original plan used Jeff Sackmann's
  tennis_atp/tennis_wta GitHub repos directly. Confirmed via
  `git ls-remote` (direct to GitHub's git servers -- no CDN, no cache,
  no rate limit involved) and the GitHub API, from a real GitHub
  Actions runner, that both repos no longer exist at that path
  ("Repository not found", not a branch issue, not flakiness).
  Tennismylife/TML-Database was found and independently verified
  (fetched and inspected 2021.csv, 2024.csv, and 2025.csv directly)
  before switching -- never blindly swapped a URL without checking
  real content first. See config/cycle_002_tennis_data.yaml's
  top-of-file note and research/cycles/CYCLE_002_TENNIS/PLAN.md for the
  full diagnosis. WTA is descoped for this phase: no actively-maintained
  free WTA equivalent was found in a reasonably bounded search.
- Tennis-data.co.uk: per-season Excel (.xlsx) files, i.e. **binary**
  content, unlike football-data.co.uk's plain-text CSV. This module
  therefore provides a `_bytes` counterpart to every text-based
  primitive (FetchResult carries either `raw_text` or `raw_bytes`,
  never both) rather than forcing the xlsx payload through a text
  decode, which would corrupt it.

This module intentionally does NOT do player-name normalisation, odds
parsing into probabilities, or consensus construction. Cross-source
player-name matching (TML-Database's full names vs. Tennis-data.co.uk's
"Djokovic N."-style abbreviated name strings) is a real, nontrivial
entity-resolution problem -- the tennis analogue of football's
team-name normalisation -- and is deliberately deferred to its own
checkpoint (see config/cycle_002_tennis_data.yaml's top-of-file note
and research/cycles/CYCLE_002_TENNIS/PLAN.md).

Network-egress note (same as football_data_loader.py): this module
cannot be exercised against the live sources from this project's own
sandboxed CI/dev environments -- both the cloud research sandbox and,
as of 2026-09-11, this developer's own machine are proxy-blocked from
raw.githubusercontent.com and tennis-data.co.uk. It is designed to run
from an environment with normal internet access (a GitHub Actions
runner, per .github/workflows/cycle_002_tennis_data_acquisition.yml,
mirroring the Cycle 1 acquisition workflow) and is tested here entirely
with mocked HTTP responses.
"""

from __future__ import annotations

import hashlib
import ssl
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

DEFAULT_USER_AGENT = (
    "PredictionMarketsLab/0.1 (personal research project; "
    "contact via repository issues; see docs/DATA_LEAKAGE_RULES.md "
    "and docs/HISTORICAL_PRICE_AND_CLV_LIMITATIONS.md for how this "
    "data is used)"
)

# Real .xlsx files are ZIP archives; this magic number is the cheapest
# reliable positive signal that a byte response is a genuine xlsx
# payload rather than an HTML error page served with a misleading
# Content-Type.
XLSX_ZIP_MAGIC = b"PK\x03\x04"


@dataclass(frozen=True)
class AcquisitionConfig:
    """Configuration for a paced acquisition run.

    Unlike football_data_loader.AcquisitionConfig, this has no single
    default base_url -- Cycle 2 has two distinct source base URLs
    (tml_database_atp, tennis_data_co_uk), each supplied per-target by
    the orchestrator via config/cycle_002_tennis_data.yaml rather than
    defaulted here. All other fields are configurable per project
    coding standards (no magic numbers) and default to the same
    conservative values Cycle 1 discovered during its feasibility audit
    -- treated as a reasonable starting point for new hosts, not
    independently re-verified against TML-Database's or
    Tennis-data.co.uk's actual rate limits yet.
    """

    user_agent: str = DEFAULT_USER_AGENT
    delay_between_requests_seconds: float = 6.0
    max_retries: int = 4
    initial_backoff_seconds: float = 10.0
    backoff_multiplier: float = 2.0
    request_timeout_seconds: float = 30.0


@dataclass(frozen=True)
class FetchResult:
    """Outcome of attempting to fetch a single source file.

    Exactly one of raw_text / raw_bytes is populated on success,
    depending on which fetch_one_* variant produced it; both are None
    on failure.
    """

    source_key: str  # e.g. "tml_database_match:ATP:2024" or "tennis_data_co_uk:ATP:2024"
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
    raw_text: str | None = None
    raw_bytes: bytes | None = None


def looks_like_html_text(text: str) -> bool:
    """Detect whether a text response body is an HTML error page.

    Identical logic to football_data_loader.looks_like_html -- kept as
    a separate copy rather than a cross-module import so this module
    has no dependency on football_data_loader (the two sports' loaders
    should be independently deletable/replaceable).
    """
    stripped = text.strip().lower()
    return stripped.startswith("<!doctype") or stripped.startswith("<html") or "<body" in stripped[:2000]


def looks_like_html_bytes(content: bytes) -> bool:
    """Detect whether a byte response body is an HTML error page served
    where a binary xlsx payload was expected. A genuine xlsx file
    always starts with the ZIP magic number; anything else is treated
    as suspect and sniffed as text."""
    if content[:4] == XLSX_ZIP_MAGIC:
        return False
    return looks_like_html_text(content.decode("utf-8", errors="replace"))


def compute_sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def compute_sha256_bytes(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def build_legacy_tolerant_ssl_context() -> ssl.SSLContext:
    """Build an SSLContext that can complete a TLS handshake with an
    old server that OpenSSL 3.x's modern defaults refuse to talk to.

    Discovered against the real acquisition run (2026-09-11):
    Tennis-data.co.uk failed every single request with
    `[SSL: TLSV1_ALERT_INTERNAL_ERROR] tlsv1 alert internal error`,
    never reaching the HTTP layer at all -- this is a well-documented
    class of OpenSSL 3.0 incompatibility with old servers (see
    https://bugs.python.org/issue43791), not a bug in this code or a
    wrong URL.

    A first attempt at this fix used only `@SECLEVEL=0` (lowering the
    signature-algorithm/DH-key-size security floor) and it was NOT
    sufficient -- the identical error recurred against the real site.
    This version combines three independent, individually-documented
    compatibility relaxations, since an old commercial site like this
    one plausibly has more than one legacy quirk stacked together:

    1. `@SECLEVEL=0` in the cipher string -- removes the signature-
       algorithm/key-size floor (the bpo-43791 fix).
    2. Cap `maximum_version` at TLS 1.2 -- some old server stacks
       mishandle the extensions a modern client's TLS 1.3 ClientHello
       includes (key_share, supported_versions, etc.) and fail with a
       generic "internal_error" alert rather than a clean version
       mismatch; capping the ceiling avoids offering TLS 1.3 at all.
    3. `OP_LEGACY_SERVER_CONNECT`, when this Python/OpenSSL build
       exposes it (added in Python 3.12's ssl module; guarded with
       getattr since this project's pinned Python is 3.11) -- permits
       the old, insecure-renegotiation handshake extension some
       ancient servers still use, a distinct legacy TLS quirk from
       either of the above.

    None of these touch certificate verification: `check_hostname` and
    `verify_mode` are left at `create_default_context()`'s secure
    defaults throughout.

    Scoped to this one loader (not football_data_loader.py) because
    football-data.co.uk's server has never shown this failure; no
    reason to weaken TLS requirements for a host that doesn't need it.
    """
    context = ssl.create_default_context()
    context.set_ciphers("DEFAULT@SECLEVEL=0")
    context.maximum_version = ssl.TLSVersion.TLSv1_2
    context.options |= getattr(ssl, "OP_LEGACY_SERVER_CONNECT", 0)
    return context


class HttpClient:
    """Thin, mockable wrapper around the HTTP calls this loader needs.

    Kept as a small seam so unit tests can substitute a fake client
    that returns canned (status, content_type, body) tuples without
    touching the network, mirroring football_data_loader.HttpClient.
    """

    def __init__(self, user_agent: str, timeout_seconds: float, ssl_context: ssl.SSLContext | None = None):
        self.user_agent = user_agent
        self.timeout_seconds = timeout_seconds
        # Defaults to the legacy-tolerant context (see
        # build_legacy_tolerant_ssl_context) because this client talks
        # to both raw.githubusercontent.com (which does not need it)
        # and tennis-data.co.uk (which does) -- using it everywhere is
        # simpler than threading a per-host context through fetch_one_*
        # and does not weaken certificate verification for either host.
        self.ssl_context = ssl_context if ssl_context is not None else build_legacy_tolerant_ssl_context()

    def get_text(self, url: str) -> tuple[int, str, str]:
        """GET a URL expected to return text (CSV). Returns
        (http_status, content_type, body_text)."""
        status, content_type, body = self._get_raw(url)
        return status, content_type, body.decode("utf-8-sig", errors="replace")

    def get_bytes(self, url: str) -> tuple[int, str, bytes]:
        """GET a URL expected to return binary content (xlsx). Returns
        (http_status, content_type, body_bytes)."""
        return self._get_raw(url)

    def _get_raw(self, url: str) -> tuple[int, str, bytes]:
        request = urllib.request.Request(url, headers={"User-Agent": self.user_agent})
        try:
            with urllib.request.urlopen(request, timeout=self.timeout_seconds, context=self.ssl_context) as response:
                status = response.status
                content_type = response.headers.get("Content-Type", "")
                body = response.read()
                return status, content_type, body
        except urllib.error.HTTPError as exc:
            # urlopen raises HTTPError for ANY non-2xx response instead of
            # returning it as a normal response object. HTTPError is a
            # subclass of URLError, so without this except clause it would
            # propagate straight through to _retry_loop's
            # `except (urllib.error.URLError, ...)` -- meaning every real
            # HTTP error status, including a plain 404, would be
            # misclassified as a transient "network error", retried
            # max_retries times (wasting the full backoff schedule), and
            # then reported as "network error: HTTP Error 404: Not Found"
            # instead of the intended immediate, no-retry "http_error"
            # outcome. Converting it back into the normal
            # (status, content_type, body) tuple here restores the status-
            # code branching in _retry_loop (429/5xx retry; anything else,
            # 404 included, fails fast).
            content_type = exc.headers.get("Content-Type", "") if exc.headers else ""
            body = exc.read()
            return exc.code, content_type, body


def _retry_loop(source_key: str, url: str, config: AcquisitionConfig, sleep_fn, do_fetch):
    """Shared retry/backoff/rate-limit-handling skeleton for both the
    text and bytes fetch variants below, factored out so the two stay
    behaviourally identical (mirrors the control flow of
    football_data_loader.fetch_one exactly; the only difference between
    the text/bytes callers is what `do_fetch` returns and how the
    "looks like HTML" and hashing checks are performed on it)."""
    backoff = config.initial_backoff_seconds
    retries_used = 0
    rate_limited_count = 0
    last_error: str | None = None

    for attempt in range(config.max_retries + 1):
        try:
            status, content_type, body = do_fetch()
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
            return "http_error", status, content_type, body, attempt, rate_limited_count, f"unexpected HTTP status {status}"

        return "ok", status, content_type, body, attempt, rate_limited_count, None

    return "exhausted", None, None, None, retries_used, rate_limited_count, last_error or "unknown failure"


def fetch_one_text(source_key: str, url: str, config: AcquisitionConfig, client: HttpClient, sleep_fn=time.sleep) -> FetchResult:
    """Fetch a single CSV source (a TML-Database match file) with
    retry/backoff. Mirrors football_data_loader.fetch_one's control
    flow exactly."""
    outcome, status, content_type, body, attempt, rate_limited_count, error = _retry_loop(
        source_key, url, config, sleep_fn, lambda: client.get_text(url)
    )

    if outcome == "exhausted":
        return FetchResult(
            source_key=source_key, url=url, success=False, http_status=None, content_type=None,
            byte_size=None, sha256=None, downloaded_at=None, retries_used=attempt,
            rate_limited_count=rate_limited_count, error_message=error,
        )
    if outcome == "http_error":
        return FetchResult(
            source_key=source_key, url=url, success=False, http_status=status, content_type=content_type,
            byte_size=None, sha256=None, downloaded_at=None, retries_used=attempt,
            rate_limited_count=rate_limited_count, error_message=error,
        )
    if looks_like_html_text(body):
        return FetchResult(
            source_key=source_key, url=url, success=False, http_status=status, content_type=content_type,
            byte_size=None, sha256=None, downloaded_at=None, retries_used=attempt,
            rate_limited_count=rate_limited_count,
            error_message="response body looks like an HTML error page, not CSV -- rejected",
        )
    return FetchResult(
        source_key=source_key, url=url, success=True, http_status=status, content_type=content_type,
        byte_size=len(body.encode("utf-8")), sha256=compute_sha256_text(body),
        downloaded_at=datetime.now(timezone.utc).isoformat(timespec="seconds"),
        retries_used=attempt, rate_limited_count=rate_limited_count, error_message=None, raw_text=body,
    )


def fetch_one_bytes(source_key: str, url: str, config: AcquisitionConfig, client: HttpClient, sleep_fn=time.sleep) -> FetchResult:
    """Fetch a single binary source (a Tennis-data.co.uk xlsx file) with
    retry/backoff. Same control flow as fetch_one_text; the payload is
    kept as bytes throughout so the xlsx content is never corrupted by
    a text decode."""
    outcome, status, content_type, body, attempt, rate_limited_count, error = _retry_loop(
        source_key, url, config, sleep_fn, lambda: client.get_bytes(url)
    )

    if outcome == "exhausted":
        return FetchResult(
            source_key=source_key, url=url, success=False, http_status=None, content_type=None,
            byte_size=None, sha256=None, downloaded_at=None, retries_used=attempt,
            rate_limited_count=rate_limited_count, error_message=error,
        )
    if outcome == "http_error":
        return FetchResult(
            source_key=source_key, url=url, success=False, http_status=status, content_type=content_type,
            byte_size=None, sha256=None, downloaded_at=None, retries_used=attempt,
            rate_limited_count=rate_limited_count, error_message=error,
        )
    if looks_like_html_bytes(body):
        return FetchResult(
            source_key=source_key, url=url, success=False, http_status=status, content_type=content_type,
            byte_size=None, sha256=None, downloaded_at=None, retries_used=attempt,
            rate_limited_count=rate_limited_count,
            error_message="response body looks like an HTML error page, not an xlsx file -- rejected",
        )
    return FetchResult(
        source_key=source_key, url=url, success=True, http_status=status, content_type=content_type,
        byte_size=len(body), sha256=compute_sha256_bytes(body),
        downloaded_at=datetime.now(timezone.utc).isoformat(timespec="seconds"),
        retries_used=attempt, rate_limited_count=rate_limited_count, error_message=None, raw_bytes=body,
    )


def write_raw_file_atomic_text(path: Path, content: str) -> bool:
    """Write raw text content to disk atomically, refusing silent
    overwrites. Identical behaviour to
    football_data_loader.write_raw_file_atomic."""
    path.parent.mkdir(parents=True, exist_ok=True)
    new_hash = compute_sha256_text(content)
    if path.exists():
        existing_hash = compute_sha256_text(path.read_text(encoding="utf-8"))
        if existing_hash == new_hash:
            return True
        raise FileExistsError(
            f"{path} already exists with different content (existing sha256="
            f"{existing_hash}, new sha256={new_hash}) -- raw files must never be "
            "silently overwritten; resolve manually or use a new file name"
        )
    tmp_path = path.with_suffix(path.suffix + ".tmp")
    tmp_path.write_text(content, encoding="utf-8")
    tmp_path.replace(path)
    return True


def write_raw_file_atomic_bytes(path: Path, content: bytes) -> bool:
    """Byte-safe counterpart to write_raw_file_atomic_text, for xlsx
    payloads. Same idempotency/refusal semantics."""
    path.parent.mkdir(parents=True, exist_ok=True)
    new_hash = compute_sha256_bytes(content)
    if path.exists():
        existing_hash = compute_sha256_bytes(path.read_bytes())
        if existing_hash == new_hash:
            return True
        raise FileExistsError(
            f"{path} already exists with different content (existing sha256="
            f"{existing_hash}, new sha256={new_hash}) -- raw files must never be "
            "silently overwritten; resolve manually or use a new file name"
        )
    tmp_path = path.with_suffix(path.suffix + ".tmp")
    tmp_path.write_bytes(content)
    tmp_path.replace(path)
    return True


def tml_database_match_file_url(base_url: str, filename_template: str, season: str) -> str:
    """Build the URL for one season's ATP match file from
    Tennismylife/TML-Database (github.com/Tennismylife/TML-Database),
    the actively-maintained continuation of Jeff Sackmann's tennis_atp
    repo -- see config/cycle_002_tennis_data.yaml's top-of-file note for
    why this replaced sackmann_match_file_url/_ranking_file_url/
    _player_file_url (all three removed 2026-09-11: JeffSackmann/tennis_atp
    and /tennis_wta no longer exist at their historical path, confirmed
    via `git ls-remote` and the GitHub API from a real GitHub Actions
    runner, not a CDN/rate-limit artifact). TML-Database embeds
    winner/loser rank, rank_points, age, height, hand, and country
    directly in every match row, so the separate ranking/player-file
    fetches this function's predecessors supported are no longer needed
    for this project's stated data requirements."""
    return f"{base_url}/{filename_template.format(season=season)}"


def tennis_data_co_uk_url(
    base_url: str, tour_code: str, season: str, men_path_template: str, women_path_template: str
) -> str:
    template = men_path_template if tour_code == "ATP" else women_path_template
    return f"{base_url}/{template.format(year=season)}"
