"""Compare Betfair --capture summaries across observation windows (10 October liquidity curve). Aggregates only.

Usage: python scripts/betfair_liquidity_report.py CAPTURE_SUMMARY_a.json CAPTURE_SUMMARY_b.json ... > LIQUIDITY_CURVE.md
Execution/microstructure description only: no thresholds are set here and the corners A/B/C rules are untouched.
Duplicate summaries (same capture_ts) are counted once.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

FAMILIES = ("corners", "player_sot")


def load(paths: list[str]) -> list[dict]:
    seen, out = set(), []
    for p in paths:
        s = json.loads(Path(p).read_text())
        if s["capture_ts"] in seen:
            continue
        seen.add(s["capture_ts"])
        out.append(s)
    return sorted(out, key=lambda s: s["capture_ts"])


def table(summaries: list[dict]) -> str:
    lines = ["| capture (UTC) | competition | market type | events | markets | runners | both | back-only | lay-only | none | two-sided share | "
             "spread p25/p50/p75 | back size p50 | lay size p50 | matched p50 | mins to KO | 10% gate (corners) |",
             "|" + "---|" * 17]
    for s in summaries:
        for key, g in sorted(s["groups"].items()):
            if g["family"] not in FAMILIES:
                continue
            comp, mt = key.split("|", 1)
            sp = g.get("spread_p25_p50_p75") or [None] * 3
            mid = lambda k: (g.get(k) or [None, None, None])[1]
            lines.append(f"| {s['capture_ts'][:16]} | {comp} | {mt} | {g['events']} | {g['markets']} | {g['runners']} | {g['both']} | {g['back_only']} | "
                         f"{g['lay_only']} | {g['none']} | {g.get('two_sided_share')} | {sp[0]}/{sp[1]}/{sp[2]} | {mid('back_size_p25_p50_p75')} | "
                         f"{mid('lay_size_p25_p50_p75')} | {mid('market_matched_p25_p50_p75')} | {g['mins_to_kickoff_range']} | "
                         f"{g.get('markets_passing_preregistered_10pct_gate', '')} |")
    return "\n".join(lines)


def main(argv: list[str]) -> int:
    s = load(argv)
    print(f"# Betfair liquidity curve ({len(s)} capture windows)\n\nDescriptive only; no thresholds set; corners 10% gate unchanged.\n")
    print(table(s))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
