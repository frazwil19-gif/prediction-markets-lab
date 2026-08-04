from datetime import datetime, timezone

import pytest

from prediction_markets_lab.utils.dates import (
    is_stale,
    now_utc_iso,
    parse_iso_timestamp,
)


def test_now_utc_iso_is_parseable():
    ts = now_utc_iso()
    parsed = parse_iso_timestamp(ts)
    assert parsed.tzinfo is not None


def test_parse_iso_timestamp_assumes_utc_if_naive():
    parsed = parse_iso_timestamp("2026-08-03T12:00:00")
    assert parsed.tzinfo == timezone.utc


def test_is_stale_true_when_older_than_max_age():
    reference = datetime(2026, 8, 3, 12, 5, 0, tzinfo=timezone.utc)
    old_ts = "2026-08-03T12:00:00+00:00"  # 5 minutes before reference
    assert is_stale(old_ts, max_age_seconds=60, reference=reference)


def test_is_stale_false_when_within_max_age():
    reference = datetime(2026, 8, 3, 12, 0, 30, tzinfo=timezone.utc)
    recent_ts = "2026-08-03T12:00:00+00:00"  # 30 seconds before reference
    assert not is_stale(recent_ts, max_age_seconds=60, reference=reference)
