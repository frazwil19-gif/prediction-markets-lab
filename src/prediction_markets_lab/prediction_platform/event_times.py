"""Current event start-time resolution (V2-10 fix A, rule ``est-1``).

Problem (V2-9 audit s.12): the unified ledger is append-only and keyed on ``prediction_id``, so a prediction row keeps the
``event_start`` observed when it was FIRST recorded. The Odds API often lists tennis matches with a placeholder start
(e.g. 02:00) and moves them later. Consumers that filtered ``event_start > now`` then treated legitimately future matches
as started and dropped them silently.

Semantics (nothing historical is rewritten):
  * every source that records a provider start time at a known observation time is a START OBSERVATION;
    the ledger row itself is one observation (observed at its ``prediction_timestamp``);
  * the CURRENT start is the start carried by the most recently observed valid observation(s);
  * unparseable observations are ignored and counted (never guessed);
  * if the most recent observation time carries two different starts the event is START_TIME_CONFLICT and is
    excluded with that reason (fail closed) -- never resolved by picking one;
  * eligibility for current decisions uses the current start; the original ledger start is kept alongside.

Reads only files production already writes; 0 API calls.
"""
from __future__ import annotations

import csv
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

RULE_VERSION = "est-1"

# start_time_status
UNCHANGED, RESCHEDULED, LEDGER_ONLY, CONFLICT = "UNCHANGED", "RESCHEDULED", "LEDGER_ONLY", "START_TIME_CONFLICT"
# exclusion reasons (machine readable)
EXCL_STARTED, EXCL_CONFLICT, EXCL_INVALID = "EVENT_STARTED", "START_TIME_CONFLICT", "START_TIME_INVALID"
ELIGIBLE, EXCLUDED = "ELIGIBLE", "EXCLUDED"

LEDGER_SOURCE = "unified_ledger.event_start"
# tennis files that record the provider commence_time per scan (both append-only, written by the tennis board)
TENNIS_START_SOURCES = ("tennis_predictions/probability_snapshots.csv", "tennis_predictions/exchange_probability_snapshots.csv")

RESOLUTION_FIELDS = ["prediction_id", "event_key", "event_name", "event_start_original", "event_start_current",
                     "start_time_status", "start_time_source", "start_observed_at", "n_start_observations",
                     "invalid_start_observations", "eligibility", "exclusion_reason", "start_time_rule"]


def parse_ts(s: object) -> datetime | None:
    """ISO timestamp -> aware UTC datetime; None when missing or unparseable (never guessed)."""
    if s in (None, ""):
        return None
    try:
        d = datetime.fromisoformat(str(s).strip().replace("Z", "+00:00"))
    except ValueError:
        return None
    return (d if d.tzinfo else d.replace(tzinfo=timezone.utc)).astimezone(timezone.utc)


@dataclass(frozen=True)
class StartObservation:
    event_key: str
    observed_at: datetime
    start: datetime
    source: str


@dataclass(frozen=True)
class ResolvedStart:
    event_key: str
    original_start: str             # ledger value, verbatim
    current_start: str | None       # None only for START_TIME_CONFLICT / START_TIME_INVALID
    status: str
    source: str
    observed_at: str
    n_observations: int
    n_invalid: int


class StartIndex:
    """event_key -> valid observations (+ count of invalid ones)."""

    def __init__(self) -> None:
        self.obs: dict[str, list[StartObservation]] = defaultdict(list)
        self.invalid: dict[str, int] = defaultdict(int)

    def add(self, event_key: str, observed_at: object, start: object, source: str) -> bool:
        o, s = parse_ts(observed_at), parse_ts(start)
        if o is None or s is None:
            self.invalid[event_key] += 1
            return False
        self.obs[event_key].append(StartObservation(event_key, o, s, source))
        return True

    def add_tennis_rows(self, rows: list[dict], source: str) -> None:
        for r in rows:
            if not r.get("sport_key") or not r.get("event_id"):
                continue
            self.add(f"tennis|{r['sport_key']}|{r['event_id']}", r.get("scan_timestamp_utc"), r.get("commence_time"), source)


def load_index(repo: Path, sources: tuple[str, ...] = TENNIS_START_SOURCES) -> StartIndex:
    idx = StartIndex()
    for rel in sources:
        p = repo / rel
        if p.exists():
            with p.open(newline="", encoding="utf-8") as f:
                idx.add_tennis_rows(list(csv.DictReader(f)), rel)
    return idx


def resolve(pred: dict, idx: StartIndex) -> ResolvedStart:
    key, original = pred["event_key"], pred["event_start"]
    obs = list(idx.obs.get(key, []))
    n_invalid = idx.invalid.get(key, 0)
    own_start, own_at = parse_ts(original), parse_ts(pred.get("prediction_timestamp"))
    if own_start is not None and own_at is not None:
        obs.append(StartObservation(key, own_at, own_start, LEDGER_SOURCE))
    elif own_start is None:
        n_invalid += 1
    if not obs:
        return ResolvedStart(key, original, None, EXCL_INVALID, "", "", 0, n_invalid)
    latest_at = max(o.observed_at for o in obs)
    latest = [o for o in obs if o.observed_at == latest_at]
    starts = {o.start for o in latest}
    n = len(obs)
    if len(starts) > 1:
        return ResolvedStart(key, original, None, CONFLICT, "|".join(sorted({o.source for o in latest})), latest_at.isoformat(),
                             n, n_invalid)
    cur = starts.pop()
    only_ledger = all(o.source == LEDGER_SOURCE for o in obs)
    src = "|".join(sorted({o.source for o in latest}))
    status = LEDGER_ONLY if only_ledger else (UNCHANGED if own_start is not None and cur == own_start else RESCHEDULED)
    return ResolvedStart(key, original, cur.isoformat(), status, src, latest_at.isoformat(), n, n_invalid)


def exclusion_reason(r: ResolvedStart, now: datetime) -> str | None:
    if r.status == CONFLICT:
        return EXCL_CONFLICT
    if r.current_start is None:
        return EXCL_INVALID
    return EXCL_STARTED if parse_ts(r.current_start) <= now else None


def overlay(pred: dict, r: ResolvedStart) -> dict:
    """Copy of the prediction whose ``event_start`` is the current start (original kept in ``event_start_original``).
    The ledger row itself is never modified."""
    out = dict(pred)
    out["event_start_original"] = r.original_start
    out["event_start"] = r.current_start or r.original_start
    out["start_time_status"] = r.status
    out["start_time_source"] = r.source
    return out


def apply(preds: list[dict], idx: StartIndex, now: datetime) -> tuple[list[dict], list[dict]]:
    """-> (eligible predictions with current start overlaid, resolution rows for EVERY prediction)."""
    eligible, rows = [], []
    for p in preds:
        r = resolve(p, idx)
        why = exclusion_reason(r, now)
        rows.append({"prediction_id": p["prediction_id"], "event_key": r.event_key, "event_name": p.get("event_name", ""),
                     "event_start_original": r.original_start, "event_start_current": r.current_start or "",
                     "start_time_status": r.status, "start_time_source": r.source, "start_observed_at": r.observed_at,
                     "n_start_observations": r.n_observations, "invalid_start_observations": r.n_invalid,
                     "eligibility": EXCLUDED if why else ELIGIBLE, "exclusion_reason": why or "",
                     "start_time_rule": RULE_VERSION})
        if not why:
            eligible.append(overlay(p, r))
    return eligible, rows


def summary(rows: list[dict]) -> dict:
    out: dict[str, dict[str, int]] = {"eligibility": defaultdict(int), "exclusion_reason": defaultdict(int),
                                       "start_time_status": defaultdict(int)}
    for r in rows:
        for k in out:
            if r[k]:
                out[k][r[k]] += 1
    res = {k: dict(sorted(v.items())) for k, v in out.items()}
    res["eligible_rescheduled"] = sum(r["eligibility"] == ELIGIBLE and r["start_time_status"] == RESCHEDULED for r in rows)
    res["rule"] = RULE_VERSION
    return res


def write_resolution(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=RESOLUTION_FIELDS)
        w.writeheader()
        w.writerows(rows)
