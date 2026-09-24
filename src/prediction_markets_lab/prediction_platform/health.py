"""Lightweight system health for the Prediction Board. Critical staleness is made explicit, never hidden."""
from __future__ import annotations

import csv
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

STALE = timedelta(hours=30)       # daily jobs; GitHub cron delays of up to ~7h are tolerated
OUTAGE = timedelta(hours=48)


def _ts(s: str | None) -> datetime | None:
    if not s:
        return None
    try:
        d = datetime.fromisoformat(str(s).replace("Z", "+00:00"))
    except ValueError:
        return None
    return d if d.tzinfo else d.replace(tzinfo=timezone.utc)


def _last_csv(path: Path) -> dict | None:
    if not path.exists():
        return None
    with path.open(newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    return rows[-1] if rows else None


def credits_last_observed(logs: list[Path]) -> dict:
    best = None
    for p in logs:
        r = _last_csv(p)
        if r and r.get("x_requests_remaining"):
            t = _ts(r.get("timestamp_utc"))
            if t and (best is None or t > best[0]):
                best = (t, int(r["x_requests_remaining"]), p.name)
    if best is None:
        return {"remaining": None, "observed_at": None, "source": None}
    return {"remaining": best[1], "observed_at": best[0].isoformat(), "source": best[2],
            "note": "last value seen by a logging consumer; daily_scan does not log credits"}


def evaluate(repo: Path, now: datetime, state: dict) -> dict:
    status = json.loads((repo / "status/latest.json").read_text()) if (repo / "status/latest.json").exists() else {}
    scan = status.get("last_scan") or {}
    settle = status.get("last_settlement") or {}
    tennis = _last_csv(repo / "tennis_predictions/run_log.csv")
    comps = {
        "daily_scan": (_ts(scan.get("at")), scan.get("status")),
        "settlement": (_ts(settle.get("at")), settle.get("status")),
        "tennis_board": (_ts((tennis or {}).get("scan_timestamp_utc")) or _ts(state.get("last_tennis_ingest")), "success"),
        "ci_tests": (_ts(state.get("last_ci_pass")), "success"),
    }
    out, warnings, critical = {}, [], False
    for name, (t, st) in comps.items():
        age = (now - t) if t else None
        flag = "OK"
        if t is None:
            flag = "UNKNOWN"
        elif st not in (None, "success"):
            flag = "FAILED"
        elif age > OUTAGE:
            flag = "OUTAGE"
        elif age > STALE:
            flag = "STALE"
        if flag != "OK":
            warnings.append(f"{name}: {flag}" + (f" (last {t.isoformat()})" if t else ""))
        if name in ("daily_scan", "settlement") and flag in ("FAILED", "OUTAGE", "STALE"):
            critical = True
        out[name] = {"last": t.isoformat() if t else None, "status": st, "flag": flag,
                     "age_hours": round(age.total_seconds() / 3600, 1) if age else None}
    creds = credits_last_observed([repo / "tennis_predictions/credit_log.csv", repo / "predictions/nba_credit_log.csv"])
    if creds["remaining"] is not None and creds["remaining"] < 75:
        warnings.append(f"API credits below reserve: {creds['remaining']}")
        critical = True
    overall = "DEGRADED" if critical else ("HEALTHY_WITH_WARNINGS" if warnings else "HEALTHY")
    return {"generated_at": now.isoformat(), "overall": overall, "outage_flag": any(v["flag"] == "OUTAGE" for v in out.values()),
            "components": out, "api_credits": creds, "warnings": warnings,
            "stale_data_warning": any(v["flag"] in ("STALE", "OUTAGE") for v in out.values())}
