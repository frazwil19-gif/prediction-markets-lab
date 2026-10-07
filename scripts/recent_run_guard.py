"""Skip a LATE scheduled run when the same workflow already succeeded recently (e.g. via the Mac dispatcher).

GitHub cron runs 3-9 h late on this repo. The Mac dispatcher (scripts/dispatch_workflows.sh) triggers the price scans at
fixed UK times; the cron stays as a fallback. This guard stops the fallback from paying for a second scan when a
successful DISPATCHED (workflow_dispatch) run of the same workflow started within --hours.
Fix 2026-10-07: run 1 also counted a late earlier cron run, which wrongly skipped the 15:30 tennis board. It never skips: manual/dispatch runs, an --exempt-schedule
slot (e.g. the tennis 22:30 settlement), or when the API cannot be read (fail open = run as before).
Writes skip=true|false to $GITHUB_OUTPUT. 0 Odds API credits.
"""
from __future__ import annotations

import argparse
import json
import os
import urllib.request
from datetime import datetime, timedelta, timezone


def should_skip(runs: list[dict], now: datetime, hours: float, event: str, schedule: str, exempt: list[str], current_id: int | None) -> bool:
    if event != "schedule" or schedule in exempt:
        return False
    cutoff = now - timedelta(hours=hours)
    for r in runs:
        # only a run the Mac dispatcher started counts; another (late) cron run must never suppress this slot
        if r.get("id") == current_id or r.get("conclusion") != "success" or r.get("event") != "workflow_dispatch":
            continue
        t = datetime.fromisoformat(r["run_started_at"].replace("Z", "+00:00"))
        if t >= cutoff:
            return True
    return False


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--workflow", required=True)
    ap.add_argument("--hours", type=float, required=True)
    ap.add_argument("--event", default="")
    ap.add_argument("--schedule", default="")
    ap.add_argument("--exempt-schedule", action="append", default=[])
    a = ap.parse_args()
    skip = False
    try:
        url = f"https://api.github.com/repos/{os.environ['GITHUB_REPOSITORY']}/actions/workflows/{a.workflow}/runs?per_page=20"
        req = urllib.request.Request(url, headers={"Authorization": f"Bearer {os.environ['GH_TOKEN']}", "Accept": "application/vnd.github+json"})
        runs = json.loads(urllib.request.urlopen(req, timeout=30).read())["workflow_runs"]
        cur = int(os.environ.get("GITHUB_RUN_ID", "0") or 0)
        skip = should_skip(runs, datetime.now(timezone.utc), a.hours, a.event, a.schedule, a.exempt_schedule, cur)
    except Exception as exc:  # noqa: BLE001 -- fail open: run as before
        print(f"guard could not read recent runs ({exc}); running")
    print(f"skip={str(skip).lower()}")
    with open(os.environ.get("GITHUB_OUTPUT", os.devnull), "a") as f:
        f.write(f"skip={str(skip).lower()}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
