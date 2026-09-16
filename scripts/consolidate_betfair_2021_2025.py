"""One-off orchestration: consolidate the real 2021-2025 Betfair BASIC
download (Workstream B historical scale-up, 2026-09-16) into the
resumable, hash-provenanced Parquet index built and benchmarked in
`betfair_market_index.py`.

Not unit-tested itself (it is a research orchestration script over
Fraser's real local download, in the same category as
`run_workstream_b_january_2026_observation_pipeline.py`); its correctness
rests entirely on the tested building blocks it calls
(`run_over_tar`, `summarise_market_bytes`, `parse_market_change_line`).

Reads directly from the single `data.tar` archive Fraser downloaded --
per the real discovery that this bulk download arrived as one tar file,
unlike the Jan-Sep 2026 sample which was a plain directory tree. Never
extracts the tar to disk; reads each per-market member's bytes directly
via `tarfile.extractfile()`.
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

REPO_ROOT = Path.home() / "mnt" / "prediction-markets-lab"
sys.path.insert(0, str(REPO_ROOT / "src"))

from prediction_markets_lab.ingestion.betfair_market_index import run_over_tar  # noqa: E402

TAR_PATH = Path.home() / "mnt" / "tennis data" / "data.tar"
OUT_DIR = Path.home() / "betfair_2021_2025_index"

if __name__ == "__main__":
    t0 = time.time()
    results = run_over_tar(TAR_PATH, OUT_DIR)
    elapsed = time.time() - t0
    processed = [r for r in results if r["files_processed"] > 0]
    skipped = [r for r in results if r["skipped_already_done"]]
    print("===DONE===")
    print(f"days_total={len(results)} days_processed={len(processed)} days_skipped={len(skipped)}")
    print(f"total_files={sum(r['files_processed'] for r in processed)}")
    print(f"wall_clock_seconds={round(elapsed, 1)}")
