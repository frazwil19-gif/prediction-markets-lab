"""Settlement completeness monitor (diagnostic only; never changes decisions, grades, stakes or settlements).

Every record is classified as:
  NOT_STARTED                    event has not started yet
  SETTLED                        a final settlement exists
  NORMAL_SOURCE_LAG              started, unsettled, still inside the source's expected refresh lag
  UNRESOLVED_AFTER_EXPECTED_LAG  started, unsettled, older than the expected lag  -> surfaced as a warning
  SOURCE_UNAVAILABLE             no settlement source is configured for this sport/competition
"""
from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path

import yaml

CONFIG = Path(__file__).resolve().parents[3] / "config" / "settlement_monitor.yaml"
STATUSES = ("NOT_STARTED", "NORMAL_SOURCE_LAG", "SETTLED", "UNRESOLVED_AFTER_EXPECTED_LAG", "SOURCE_UNAVAILABLE")


@dataclass(frozen=True)
class Record:
    ledger: str
    record_id: str
    sport: str
    competition: str
    event: str
    start: datetime
    settled: bool
    source: str | None          # None -> no configured source


def parse_ts(s: str) -> datetime:
    s = s.strip().replace("Z", "+00:00")
    d = datetime.fromisoformat(s if "T" in s or " " in s else s + "T00:00:00")
    return d if d.tzinfo else d.replace(tzinfo=timezone.utc)


def load_config(path: Path = CONFIG) -> dict:
    return yaml.safe_load(path.read_text())


def classify(r: Record, now: datetime, lag_hours: dict[str, float]) -> str:
    if r.settled:
        return "SETTLED"
    if r.start > now:
        return "NOT_STARTED"
    if r.source is None or r.source not in lag_hours:
        return "SOURCE_UNAVAILABLE"
    return "NORMAL_SOURCE_LAG" if now - r.start <= timedelta(hours=lag_hours[r.source]) else "UNRESOLVED_AFTER_EXPECTED_LAG"


def summarise(records: list[Record], now: datetime, lag_hours: dict[str, float]) -> dict:
    by: dict[tuple, Counter] = defaultdict(Counter)
    flagged = []
    for r in records:
        s = classify(r, now, lag_hours)
        by[(r.ledger, r.sport, r.competition, r.source or "NONE")][s] += 1
        if s in ("UNRESOLVED_AFTER_EXPECTED_LAG", "SOURCE_UNAVAILABLE"):
            flagged.append({"ledger": r.ledger, "id": r.record_id, "sport": r.sport, "competition": r.competition, "event": r.event,
                            "start": r.start.isoformat(), "status": s, "hours_since_start": round((now - r.start).total_seconds() / 3600, 1)})
    groups = []
    for (ledger, sport, comp, src), c in sorted(by.items()):
        started = sum(c[s] for s in STATUSES if s != "NOT_STARTED")
        groups.append({"ledger": ledger, "sport": sport, "competition": comp, "source": src, **{s: c[s] for s in STATUSES},
                       "completed_events_past_lag": c["SETTLED"] + c["UNRESOLVED_AFTER_EXPECTED_LAG"],
                       "settled_share_of_started": round(c["SETTLED"] / started, 4) if started else None})
    total = Counter()
    for g in groups:
        for s in STATUSES:
            total[s] += g[s]
    return {"generated_at": now.isoformat(), "lag_hours": lag_hours, "totals": {s: total[s] for s in STATUSES},
            "groups": groups, "flagged": flagged, "healthy": total["UNRESOLVED_AFTER_EXPECTED_LAG"] == 0 and total["SOURCE_UNAVAILABLE"] == 0}
