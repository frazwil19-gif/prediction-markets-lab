"""Research-only settlement of prospective shadow cards (cer-2). NOT SCHEDULED unless `settlement_enabled` is approved.

Outcomes come only from the verified production tennis settlement ledger (read-only). A card settles only when EVERY
leg has a final valid result; nothing is guessed. Corrections are appended as superseding rows; nothing is erased.
"""
from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timedelta

from prediction_markets_lab.card_engine.shadow import ts
from prediction_markets_lab.normalisation.tennis_betfair_linkage import names_are_equivalent

SETTLE_FIELDS = ["settlement_id", "card_id", "cohort", "k", "status", "legs_won", "legs_lost", "legs_void", "legs_total",
                 "leg_outcomes_json", "flags", "odds_indicative", "reduced_odds_indicative", "return_per_unit_indicative",
                 "supersedes", "settled_at", "source", "source_evidence_sha"]
FINAL = ("SETTLED_CORRECT", "SETTLED_INCORRECT", "VOID")
RETIREMENT = re.compile(r"\bRET\b|retired|\bret\.", re.IGNORECASE)


def _same(a: str, b: str) -> bool:
    return names_are_equivalent(a, b) or names_are_equivalent(b, a)


def event_outcomes(ledger_preds: list[dict], ledger_settle: list[dict]) -> dict[str, dict]:
    """event_id -> {"state": FINAL|CONFLICT, "status", "winner", "score"} from ALL predictions of that event.
    Identical duplicate rows are fine; any disagreement (status or winner) is a CONFLICT and never settles."""
    by_pred: dict[str, list[dict]] = {}
    for s in ledger_settle:
        by_pred.setdefault(s["prediction_id"], []).append(s)
    out: dict[str, dict] = {}
    for p in ledger_preds:
        for s in by_pred.get(p["prediction_id"], []):
            if s.get("status") not in FINAL:
                continue
            cur = {"status": s["status"] if s["status"] == "VOID" else "RESULT", "winner": s.get("winner", ""),
                   "score": s.get("score", "")}
            prev = out.get(p["event_id"])
            if prev is None:
                out[p["event_id"]] = {"state": "FINAL", **cur}
            elif prev["state"] == "FINAL" and (prev["status"] != cur["status"] or
                                               (cur["status"] == "RESULT" and not _same(prev["winner"], cur["winner"]))):
                out[p["event_id"]] = {"state": "CONFLICT", **cur}
    return out


def leg_outcome(leg: list, ev: dict | None) -> tuple[str, list[str]]:
    """leg = [event_id, selection, opponent, start, p]. Returns WON/LOST/VOID/PENDING/UNMATCHED/CONFLICT + flags."""
    if ev is None:
        return "PENDING", []
    if ev["state"] == "CONFLICT":
        return "CONFLICT", ["SOURCE_CONFLICT"]
    if ev["status"] == "VOID":
        return "VOID", ["WALKOVER_OR_VOID"]
    flags = ["RETIREMENT_BOOK_RULE_UNVERIFIED"] if RETIREMENT.search(ev.get("score", "") or "") else []
    sel, opp = _same(leg[1], ev["winner"]), _same(leg[2], ev["winner"])
    if sel == opp:              # neither or both names match: never guess
        return "UNMATCHED", flags + ["WINNER_NAME_UNMATCHED"]
    return ("WON" if sel else "LOST"), flags


def attach_legs(cards: list[dict], leg_rows: list[dict]) -> tuple[list[dict], int]:
    """Resolve each card's legs (event, selection, opponent, start, p) from the research legs table of the SAME scan record.
    Cards whose legs cannot all be resolved are skipped (fail closed) and counted."""
    idx: dict[tuple[str, str, str], dict] = {}
    for r in leg_rows:
        idx.setdefault((r["record_id"], r["event_id"], r["selection"]), r)
    out, unresolved = [], 0
    for c in cards:
        legs = []
        for part in c["legset"].split(";"):
            ev, sel = part.split(":", 1)
            r = idx.get((c["record_id"], ev, sel))
            if r is None:
                break
            legs.append([ev, sel, r["opponent"], r["start"], float(r["p"])])
        if len(legs) != int(c["k"]):
            unresolved += 1
            continue
        out.append({**c, "legs_compact": json.dumps(legs)})
    return out, unresolved


def settle_cards(cards: list[dict], legs_by_id: dict[str, dict], ledger_preds: list[dict], ledger_settle: list[dict],
                 prior: list[dict], now: datetime, overdue_days: float) -> tuple[list[dict], dict]:
    """Returns (new settlement rows, diagnostics). Idempotent: identical evidence -> identical settlement_id -> no row.
    A changed source result for an already-settled card appends a superseding row (the original stays)."""
    outcomes = event_outcomes(ledger_preds, ledger_settle)
    current: dict[str, dict] = {}
    for r in prior:                                   # last row per card is current (append-only)
        current[r["card_id"]] = r
    known_ids = {r["settlement_id"] for r in prior}
    new, diag = [], {"pending": 0, "overdue_unsettled": 0, "unmatched": 0, "conflict": 0, "settled_new": 0, "superseded": 0}
    for c in cards:
        legs = json.loads(c["legs_compact"])
        res = [leg_outcome(l, outcomes.get(l[0])) for l in legs]
        states = [r[0] for r in res]
        flags = sorted({f for _, fl in res for f in fl})
        if any(s in ("PENDING", "UNMATCHED", "CONFLICT") for s in states):
            diag["pending"] += 1
            diag["unmatched"] += int("UNMATCHED" in states)
            diag["conflict"] += int("CONFLICT" in states)
            last_start = max(ts(l[3]) for l in legs)
            if now - last_start > timedelta(days=overdue_days):
                diag["overdue_unsettled"] += 1
            continue
        won, lost, void = states.count("WON"), states.count("LOST"), states.count("VOID")
        if lost:
            status = "LOST"
        elif void == len(legs):
            status = "VOID"
        elif void:
            status = "WON_REDUCED_VOID_LEG"            # standard acca rule assumed (void leg at 1.00): BOOK RULE UNVERIFIED
            flags.append("VOID_LEG_REDUCTION_BOOK_RULE_UNVERIFIED")
        else:
            status = "WON"
        odds = c.get("odds_indicative", "")
        reduced, ret = "", ""
        if odds != "" and c.get("leg_ids"):
            leg_odds = [float(legs_by_id[i]["odds"]) for i in c["leg_ids"].split("|") if i in legs_by_id]
            if len(leg_odds) == len(legs):
                by_event = {legs_by_id[i]["event_id"]: float(legs_by_id[i]["odds"]) for i in c["leg_ids"].split("|")}
                red = 1.0
                for l, s in zip(legs, states):
                    red *= by_event[l[0]] if s == "WON" else 1.0
                reduced = round(red, 4) if void else ""
                ret = round((red - 1.0) if status.startswith("WON") else (-1.0 if status == "LOST" else 0.0), 6)
        evidence = json.dumps([[l[0], s, (outcomes.get(l[0]) or {}).get("winner", "")] for l, s in zip(legs, states)])
        ev_sha = hashlib.sha256(evidence.encode()).hexdigest()[:16]
        sid = hashlib.sha256(f"settle|{c['card_id']}|{ev_sha}".encode()).hexdigest()[:16]
        if sid in known_ids:
            continue                                  # duplicate settlement prevented
        prev = current.get(c["card_id"])
        new.append({"settlement_id": sid, "card_id": c["card_id"], "cohort": c["cohort"], "k": c["k"], "status": status,
                    "legs_won": won, "legs_lost": lost, "legs_void": void, "legs_total": len(legs),
                    "leg_outcomes_json": evidence, "flags": "|".join(flags), "odds_indicative": odds,
                    "reduced_odds_indicative": reduced, "return_per_unit_indicative": ret,
                    "supersedes": prev["settlement_id"] if prev else "", "settled_at": now.isoformat(),
                    "source": "tennis_predictions/ledger_settlements.csv (read-only)", "source_evidence_sha": ev_sha})
        known_ids.add(sid)
        diag["settled_new"] += 1
        diag["superseded"] += int(prev is not None)
    return new, diag
