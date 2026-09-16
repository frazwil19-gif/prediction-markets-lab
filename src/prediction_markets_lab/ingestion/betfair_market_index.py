"""Consolidated, hash-provenanced, resumable Betfair market index
(Workstream B historical scale-up architecture, 2026-09-16).

Built in direct response to the operator's explicit instruction: "Before
asking Fraser to download ~2.7 GB / ~1.07 million files, first verify
that our ingestion architecture can handle this file count efficiently
... Prefer a deterministic indexed/consolidated intermediate
representation (e.g. Parquet if appropriate), with hashes/provenance
back to the raw archive."

This module is deliberately small and pure-function-first so it can be
unit tested without a real multi-gigabyte download: `summarise_market_file`
and `day_output_paths` take plain paths/bytes and are exercised in
`tests/unit/test_betfair_market_index.py` against small synthetic
fixtures (a real per-market file is never used as a test fixture, per the
project's "never silently guess" / real-discoveries-only-as-fixtures
discipline -- see `betfair_historical_schema.py`'s existing tests for the
established pattern this follows). `process_day` and `run_over_days` are
the orchestration layer, benchmarked against Fraser's real Jan-Sep 2026
BASIC sample as a stand-in for the not-yet-acquired 2021-2025 download --
see `research/cycles/CYCLE_002_TENNIS/
WORKSTREAM_B_HISTORICAL_SCALEUP_AND_DISCOVERY_PROTOCOL.md` section 2 for
the real benchmark numbers this produced.

Design, restated from that benchmark run:
  - Only per-marketId `1.<marketId>.bz2` files are read; the redundant
    combined `<eventId>.bz2` capture (confirmed in the sample audit) is
    skipped.
  - Each per-market file's raw (compressed) bytes are SHA-256 hashed
    BEFORE decompression -- this is the provenance hash, over the exact
    bytes Fraser downloaded, never over anything derived.
  - Each market's full message history reduces to ONE summary row (final
    marketDefinition + a compact per-runner price series) plus one
    manifest row (which raw file, its size, its hash) -- so any
    consolidated row is always traceable back to its untouched raw
    source.
  - Output is written one Parquet part per calendar day (the real
    directory's natural chunk boundary), never as one in-memory table
    spanning the whole corpus -- this bounds peak memory to a single
    day's markets regardless of how many years are being indexed.
  - `process_day` is resumable: if a day's summary+manifest Parquet parts
    already exist, it is skipped entirely and does no I/O beyond two
    `Path.exists()` checks. An interrupted run resumes at the next
    unfinished day; a completed run re-invoked does no additional work.
"""

from __future__ import annotations

import bz2
import hashlib
import tarfile
import time
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq

from prediction_markets_lab.ingestion.betfair_historical_schema import (
    parse_market_change_line,
)


def iter_per_market_files(day_dir: Path):
    """Yield (event_id, path) for only the per-marketId `1.<marketId>.bz2`
    files under one real Betfair day directory -- skips each event's
    redundant combined `<eventId>.bz2` capture."""
    for event_dir in sorted(p for p in day_dir.iterdir() if p.is_dir()):
        for f in sorted(event_dir.glob("1.*.bz2")):
            yield event_dir.name, f


def summarise_market_bytes(event_id: str, raw_bytes: bytes, raw_relpath: str) -> tuple[dict, dict]:
    """Parse one market's raw (bz2-compressed) bytes into
    (summary_row, manifest_row). Pure function -- no filesystem access --
    so it is directly unit-testable against a small synthetic fixture.

    Never fabricates: a field genuinely absent from every message (e.g.
    no marketDefinition ever seen) is left `None`, not guessed.
    """
    raw_sha256 = hashlib.sha256(raw_bytes).hexdigest()
    text = bz2.decompress(raw_bytes).decode("utf-8")

    market_id = None
    market_type = None
    final_market_time = None
    status = None
    runner_names: dict[int, str | None] = {}
    price_points: list[tuple[int, float, int | None]] = []
    n_messages = 0

    for line in text.splitlines():
        if not line.strip():
            continue
        n_messages += 1
        for msg in parse_market_change_line(line):
            market_id = msg.market_id
            pt_ms = int(msg.published_at.timestamp() * 1000) if msg.published_at is not None else None
            if msg.market_definition is not None:
                md = msg.market_definition
                market_type = md.market_type
                if md.market_time is not None:
                    final_market_time = md.market_time.isoformat()
                status = md.status
                for r in md.runners:
                    runner_names[r.selection_id] = r.name
            for rc in msg.runner_changes:
                if rc.last_traded_price is not None:
                    price_points.append((rc.selection_id, rc.last_traded_price, pt_ms))

    summary_row = {
        "market_id": market_id,
        "event_id": event_id,
        "market_type": market_type,
        "final_market_time": final_market_time,
        "status": status,
        "runner_ids": list(runner_names.keys()),
        "runner_names": list(runner_names.values()),
        "n_messages": n_messages,
        "n_price_points": len(price_points),
        "price_runner_ids": [p[0] for p in price_points],
        "price_ltp": [p[1] for p in price_points],
        "price_epoch_ms": [p[2] for p in price_points],
    }
    manifest_row = {
        "market_id": market_id,
        "raw_relpath": raw_relpath,
        "raw_sha256": raw_sha256,
        "raw_size_bytes": len(raw_bytes),
    }
    return summary_row, manifest_row


def summarise_market_file(event_id: str, path: Path, basic_root: Path) -> tuple[dict, dict]:
    """Filesystem-touching wrapper around `summarise_market_bytes`."""
    raw_bytes = path.read_bytes()
    return summarise_market_bytes(event_id, raw_bytes, str(path.relative_to(basic_root)))


def day_output_paths(day_dir: Path, out_dir: Path) -> tuple[str, Path, Path]:
    """Deterministic (day_label, summary_path, manifest_path) for one real
    day directory, e.g. `.../2026/Jan/15` -> "2026_Jan_15".

    The label includes the YEAR (not just month/day): a single-year benchmark
    run (Jan-Sep 2026) never exposed this, but processing multiple years
    (2021-2025) without it would silently collide -- "Jan_15" would be the
    same output file for 2021, 2022, 2023, 2024, and 2025, each one
    overwriting the last. Fixed here, before any multi-year run, rather
    than discovered after data went missing.
    """
    year = day_dir.parent.parent.name
    month = day_dir.parent.name
    day = day_dir.name.zfill(2)
    day_label = f"{year}_{month}_{day}"
    return day_label, out_dir / f"markets_{day_label}.parquet", out_dir / f"manifest_{day_label}.parquet"


def iter_per_market_members_from_tar(tar_path: Path):
    """Yield (day_label, event_id, member_name, member) for every
    per-marketId `1.<marketId>.bz2` entry in a Betfair download packaged
    as a single tar archive -- a real, second real packaging format
    (the Jan-Sep 2026 sample arrived as a plain directory tree; the
    2021-2025 bulk download arrived as one `data.tar`). Skips the
    redundant combined `<eventId>.bz2` entries and any non-market file
    (e.g. a stray `.DS_Store`), by construction, same as the
    directory-walking path.

    Reads the tar's member headers only (no data) to build this list --
    the data for a given member is read lazily by the caller via
    `tar.extractfile(member)`, keyed by day, so peak memory stays bounded
    to one day's markets exactly as the directory-based path guarantees.
    """
    import re

    pattern = re.compile(r"^BASIC/(\d{4})/([A-Za-z]+)/(\d+)/([^/]+)/1\.\d+\.bz2$")
    with tarfile.open(tar_path, "r") as tf:
        for member in tf.getmembers():
            if not member.isfile():
                continue
            m = pattern.match(member.name)
            if m is None:
                continue
            year, month, day, event_id = m.groups()
            day_label = f"{year}_{month}_{day.zfill(2)}"
            yield day_label, event_id, member.name, member


def run_over_tar(tar_path: Path, out_dir: Path) -> list[dict]:
    """Process an entire tar-packaged Betfair download into per-day
    Parquet parts, resumable exactly like `run_over_days`. Unlike the
    directory-walking path, this opens the tar archive ONCE (headers
    only) to build a day->members index, then makes one pass per
    not-yet-done day, extracting only that day's members from the
    already-open archive -- so a `.tar`-packaged download never needs to
    be fully extracted to disk first.
    """
    out_dir.mkdir(parents=True, exist_ok=True)

    by_day: dict[str, list[tuple[str, str, "tarfile.TarInfo"]]] = {}
    for day_label, event_id, member_name, member in iter_per_market_members_from_tar(tar_path):
        by_day.setdefault(day_label, []).append((event_id, member_name, member))

    results = []
    with tarfile.open(tar_path, "r") as tf:
        for day_label in sorted(by_day):
            summary_path = out_dir / f"markets_{day_label}.parquet"
            manifest_path = out_dir / f"manifest_{day_label}.parquet"
            if summary_path.exists() and manifest_path.exists():
                results.append({"day": day_label, "skipped_already_done": True, "files_processed": 0})
                continue

            t0 = time.time()
            summaries, manifests = [], []
            raw_bytes_total = 0
            for event_id, member_name, member in by_day[day_label]:
                raw_bytes = tf.extractfile(member).read()
                s, m = summarise_market_bytes(event_id, raw_bytes, member_name)
                summaries.append(s)
                manifests.append(m)
                raw_bytes_total += m["raw_size_bytes"]

            pq.write_table(pa.Table.from_pylist(summaries), summary_path, compression="zstd")
            pq.write_table(pa.Table.from_pylist(manifests), manifest_path, compression="zstd")
            elapsed = time.time() - t0
            out_bytes = summary_path.stat().st_size + manifest_path.stat().st_size
            result = {
                "day": day_label,
                "skipped_already_done": False,
                "files_processed": len(by_day[day_label]),
                "raw_bytes_in": raw_bytes_total,
                "parquet_bytes_out": out_bytes,
                "elapsed_seconds": round(elapsed, 3),
                "files_per_second": round(len(by_day[day_label]) / elapsed, 1) if elapsed > 0 else None,
            }
            print(result, flush=True)
            results.append(result)
    return results


def process_day(day_dir: Path, out_dir: Path, basic_root: Path) -> dict:
    """Process one real day directory into its Parquet parts, or skip it
    if both parts already exist (resume/idempotency). Never partially
    writes -- if a prior run was interrupted mid-day, at most one of the
    two output files exists, which fails the `both exist` check and the
    whole day is reprocessed and overwritten from scratch (never merged
    with a partial prior write, which could double-count)."""
    out_dir.mkdir(parents=True, exist_ok=True)
    day_label, summary_path, manifest_path = day_output_paths(day_dir, out_dir)

    if summary_path.exists() and manifest_path.exists():
        return {"day": day_label, "skipped_already_done": True, "files_processed": 0}

    t0 = time.time()
    summaries, manifests = [], []
    raw_bytes_total = 0
    n_files = 0
    for event_id, f in iter_per_market_files(day_dir):
        s, m = summarise_market_file(event_id, f, basic_root)
        summaries.append(s)
        manifests.append(m)
        raw_bytes_total += m["raw_size_bytes"]
        n_files += 1

    if n_files == 0:
        return {"day": day_label, "skipped_already_done": False, "files_processed": 0}

    pq.write_table(pa.Table.from_pylist(summaries), summary_path, compression="zstd")
    pq.write_table(pa.Table.from_pylist(manifests), manifest_path, compression="zstd")

    elapsed = time.time() - t0
    out_bytes = summary_path.stat().st_size + manifest_path.stat().st_size
    return {
        "day": day_label,
        "skipped_already_done": False,
        "files_processed": n_files,
        "raw_bytes_in": raw_bytes_total,
        "parquet_bytes_out": out_bytes,
        "elapsed_seconds": round(elapsed, 3),
        "files_per_second": round(n_files / elapsed, 1) if elapsed > 0 else None,
    }


def run_over_days(day_dirs: list[Path], out_dir: Path, basic_root: Path) -> list[dict]:
    """Process a list of real day directories in order, writing/skipping
    one Parquet part-pair per day. Memory is bounded by the largest
    single day, never by the total number of days passed in."""
    out_dir.mkdir(parents=True, exist_ok=True)
    return [process_day(day_dir, out_dir, basic_root) for day_dir in day_dirs]
