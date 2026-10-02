"""Derive settlement team aliases from FIXTURE IDENTITY (settlement hardening, 2026-10-02).

Two listings of the SAME fixtures are required: football-data.co.uk names (fixtures.csv / results) and The Odds API
names (free /events or archived /scores), in the same competition. A football-data name x is mapped to an Odds API
name y only when the fixture structure forces it:

  1. slot constraint: every fixture of x has an Odds event in the same competition at the same kickoff (+/- tolerance),
     and y occupies x's role (home/away) in that event, for EVERY fixture of x;
  2. pair constraint: the fixture's opponent must map to that same event's opponent;
  3. bijection: one Odds name per football-data name per competition (eliminations propagate).

Only where a kickoff slot holds several simultaneous fixtures that fixture identity cannot separate, source team names
are used as evidence: a candidate y is accepted for x only if it is the ONLY fixture-consistent candidate sharing a
distinctive name token with x, and x is the only unresolved name sharing a token with y. Every accepted alias records
its method and the fixtures supporting it; anything still ambiguous stays unresolved (never guessed). A final check
re-verifies that every fully-mapped fixture corresponds to exactly one Odds event; any conflict rejects the whole
competition (fail closed).
"""
from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field
from datetime import datetime, timedelta

GENERIC_TOKENS = frozenset({"fc", "sc", "sv", "ac", "as", "us", "cf", "afc", "vfb", "vfl", "tsg", "fsv", "rc", "ogc", "club", "de", "the",
                            "1", "04", "05", "1899", "1846", "1909", "united", "city", "real", "sporting", "stade", "ssc", "bv", "ss"})


@dataclass(frozen=True)
class Fixture:
    competition: str
    kickoff: datetime     # timezone-aware UTC
    home: str
    away: str


@dataclass
class Derivation:
    competition: str
    aliases: dict[str, str] = field(default_factory=dict)              # fd raw -> odds name
    method: dict[str, str] = field(default_factory=dict)
    evidence: dict[str, list[str]] = field(default_factory=dict)
    unresolved: dict[str, list[str]] = field(default_factory=dict)     # fd raw -> remaining candidates
    fixtures_without_slot: list[str] = field(default_factory=list)
    rejected: str = ""


def tokens(name: str) -> set[str]:
    s = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode().lower()
    return {t for t in re.split(r"[^a-z0-9]+", s) if t and t not in GENERIC_TOKENS}


def _slot(f: Fixture, odds: list[Fixture], tol: timedelta) -> list[Fixture]:
    return [e for e in odds if abs(e.kickoff - f.kickoff) <= tol]


def derive(fd: list[Fixture], odds: list[Fixture], known: dict[str, str] | None = None,
           tolerance: timedelta = timedelta(minutes=10)) -> Derivation:
    """fd / odds: fixtures of ONE competition. known: fd raw -> odds name already established (e.g. existing aliases)."""
    comp = fd[0].competition if fd else (odds[0].competition if odds else "")
    out = Derivation(comp)
    known = known or {}
    slots: dict[Fixture, list[Fixture]] = {}
    for f in fd:
        s = _slot(f, odds, tolerance)
        if s:
            slots[f] = s
        else:
            out.fixtures_without_slot.append(f"{f.kickoff:%Y-%m-%d %H:%M} {f.home} v {f.away}")
    names = sorted({n for f in slots for n in (f.home, f.away)})
    cand: dict[str, set[str]] = {}
    for x in names:
        if x in known:
            cand[x] = {known[x]}
            continue
        sets = [{e.home if f.home == x else e.away for e in s} for f, s in slots.items() if x in (f.home, f.away)]
        cand[x] = set.intersection(*sets)
    method = {x: "KNOWN_ALIAS" for x in names if x in known}

    def propagate() -> None:
        changed = True
        while changed:
            changed = False
            for f, s in slots.items():
                ok = [e for e in s if e.home in cand[f.home] and e.away in cand[f.away]]
                for x, allowed in ((f.home, {e.home for e in ok}), (f.away, {e.away for e in ok})):
                    if not cand[x] <= allowed:
                        cand[x] &= allowed
                        changed = True
            for x in names:
                if len(cand[x]) == 1:
                    (y,) = cand[x]
                    for z in names:
                        if z != x and y in cand[z]:
                            cand[z].discard(y)
                            changed = True

    def record(new_method: str) -> None:
        for x in names:
            if len(cand[x]) == 1 and x not in method:
                method[x] = new_method

    propagate()
    record("FIXTURE_IDENTITY")
    while True:   # name-token evidence only inside fixture-consistent candidate sets
        open_names = [x for x in names if len(cand[x]) > 1]
        picks = {}
        for x in open_names:
            hits = [y for y in cand[x] if tokens(x) & tokens(y)]
            if len(hits) == 1 and sum(1 for z in open_names if hits[0] in cand[z] and tokens(z) & tokens(hits[0])) == 1:
                picks[x] = hits[0]
        if not picks:
            break
        for x, y in picks.items():
            cand[x] = {y}
            method[x] = "FIXTURE_IDENTITY+NAME_TOKEN"
        propagate()
        record("FIXTURE_IDENTITY_BY_ELIMINATION")
    if any(not c for c in cand.values()):
        out.rejected = "contradiction: a name has no fixture-consistent candidate (" + ", ".join(x for x, c in cand.items() if not c) + ")"
        return out
    mapped = {x: next(iter(c)) for x, c in cand.items() if len(c) == 1}
    if len(set(mapped.values())) != len(mapped):
        out.rejected = "contradiction: two football-data names mapped to one Odds API name"
        return out
    for f, s in slots.items():
        if f.home in mapped and f.away in mapped:
            if sum(1 for e in s if e.home == mapped[f.home] and e.away == mapped[f.away]) != 1:
                out.rejected = f"verification failed for {f.home} v {f.away} {f.kickoff:%Y-%m-%d %H:%M}"
                return out
    for x, y in mapped.items():
        if method.get(x) == "KNOWN_ALIAS":
            continue
        out.aliases[x] = y
        out.method[x] = method.get(x, "FIXTURE_IDENTITY")
        out.evidence[x] = [f"{f.kickoff:%Y-%m-%d %H:%M}Z {f.home} v {f.away} = {mapped.get(f.home, '?')} v {mapped.get(f.away, '?')}"
                           for f in slots if x in (f.home, f.away)]
    out.unresolved = {x: sorted(c) for x, c in cand.items() if len(c) > 1}
    return out
