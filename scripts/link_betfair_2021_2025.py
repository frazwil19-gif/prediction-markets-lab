"""One-off orchestration: link the consolidated 2021-2025 Betfair MATCH_ODDS
index against the frozen TML-Database 2021-2025 canonical dataset
(Workstream B historical scale-up, Phase 1 steps 6-10, 2026-09-16).

Not unit-tested itself -- correctness rests on tested building blocks
(`tennis_betfair_linkage.classify_tennis_betfair_match`,
`names_are_equivalent`, `_fold`) exactly like the January 2026 pipeline
script. Two real, evidence-based design decisions this script makes, both
recorded in full in `WORKSTREAM_B_2021_2025_PHASE1_AUDIT_REPORT.md`:

1. **date_tolerance_days=14, not 1.** TML-Database's `tourney_date` field
   is the tournament's START date, not each match's individual date --
   confirmed directly (every one of a tournament's R32-through-Final
   matches share the identical `tourney_date`, even though they are
   really played on different days up to ~2 weeks apart). A real
   empirical sweep (3/7/10/14/18/21/30/45 days) showed MATCHED rate
   peaking sharply around 10-14 days before AMBIGUOUS overtakes further
   gains -- 14 was chosen as it sits at that peak AND matches the real,
   independently-known fact that Grand Slams run exactly two weeks.

2. **MATCH_ODDS candidates with zero real price points are excluded**
   before linkage. A real, second discrepancy was found by direct
   inspection: ~968 real events carry TWO MATCH_ODDS market_ids for the
   same two players (same event_id) -- in 928 of those 968 cases, one of
   the two is a near-empty "ghost" market (as few as 1 message, 0 real
   price updates), almost certainly an administrative market
   recreation, with the other carrying the real trading history.
   Dropping zero-price-point candidates removes the ghost half of nearly
   every one of these pairs, which is also the right call independent of
   linkage: a market with no price history is unusable for the
   eventual observation pipeline regardless of whether it can be linked.

Deliberately does NOT compute or inspect any market-edge/outcome
statistic -- that is Phase 2 (discovery), not authorised by this script.
"""

from __future__ import annotations

import sys
from collections import defaultdict
from datetime import date, datetime
from pathlib import Path

import pandas as pd
import pyarrow.dataset as ds

REPO_ROOT = Path.home() / "mnt" / "prediction-markets-lab"
sys.path.insert(0, str(REPO_ROOT / "src"))

from prediction_markets_lab.normalisation.tennis_betfair_linkage import (  # noqa: E402
    BetfairEventCandidate,
    TMLMatchRecord,
    classify_tennis_betfair_match,
    _fold,
)

INDEX_DIR = Path.home() / "betfair_2021_2025_index"
CANONICAL_PATH = REPO_ROOT / "data" / "processed" / "tennis" / "cycle_002_canonical_matches.csv"
OUTPUT_PATH = REPO_ROOT / "data" / "interim" / "workstream_b_2021_2025_linkage.csv"
DATE_TOLERANCE_DAYS = 14


def load_betfair_match_odds_candidates() -> list[BetfairEventCandidate]:
    dataset = ds.dataset(sorted(INDEX_DIR.glob("markets_*.parquet")), format="parquet")
    table = dataset.to_table(columns=["market_id", "event_id", "market_type", "final_market_time", "runner_names", "n_price_points"])
    df = table.to_pandas()
    df = df[(df["market_type"] == "MATCH_ODDS") & (df["n_price_points"] > 0)].copy()

    candidates = []
    n_skipped_bad_runners = 0
    n_skipped_bad_date = 0
    for row in df.itertuples(index=False):
        names = list(row.runner_names)
        if len(names) != 2 or any(n is None for n in names):
            n_skipped_bad_runners += 1
            continue
        try:
            event_open_date = datetime.fromisoformat(row.final_market_time).date()
        except (ValueError, TypeError):
            n_skipped_bad_date += 1
            continue
        candidates.append(BetfairEventCandidate(
            market_id=row.market_id,
            event_id=row.event_id,
            event_open_date=event_open_date,
            runner_names=(names[0], names[1]),
        ))
    print(f"Loaded {len(candidates)} usable (non-stub) MATCH_ODDS candidates "
          f"(skipped {n_skipped_bad_runners} with != 2 named runners, "
          f"{n_skipped_bad_date} with unparseable market time)")
    return candidates


def load_tml_matches() -> list[TMLMatchRecord]:
    df = pd.read_csv(CANONICAL_PATH, dtype={"tourney_date": str})
    matches = []
    for row in df.itertuples(index=False):
        match_date = datetime.strptime(row.tourney_date, "%Y%m%d").date()
        matches.append(TMLMatchRecord(
            match_id=row.match_id,
            match_date=match_date,
            player_a_name=row.player_a_name,
            player_b_name=row.player_b_name,
        ))
    return matches


def main():
    candidates = load_betfair_match_odds_candidates()
    tml_matches = load_tml_matches()
    print(f"Loaded {len(tml_matches)} TML canonical matches (2021-2025)")

    # Fast prefilter: exact-folded-name-pair -> candidates (ignores date).
    # This bypasses the O(candidates-in-date-window) scan
    # classify_tennis_betfair_match's own docstring warns callers to avoid,
    # since a naive full cross-product is ~14,564 x 200,000 comparisons.
    # Final classification is still done by the tested, unmodified
    # classify_tennis_betfair_match on this narrowed candidate set -- this
    # index only speeds up finding candidates, it never changes the
    # matching decision itself.
    pair_index: dict[frozenset, list[BetfairEventCandidate]] = defaultdict(list)
    for c in candidates:
        key = frozenset({_fold(c.runner_names[0]), _fold(c.runner_names[1])})
        pair_index[key].append(c)

    rows = []
    results_by_year: dict[str, dict[str, int]] = defaultdict(lambda: {"MATCHED": 0, "AMBIGUOUS": 0, "UNMATCHED": 0})
    davis_cup_unmatched = 0

    for tml in tml_matches:
        key = frozenset({_fold(tml.player_a_name), _fold(tml.player_b_name)})
        subset = pair_index.get(key, [])
        result = classify_tennis_betfair_match(tml, subset, date_tolerance_days=DATE_TOLERANCE_DAYS)
        year = str(tml.match_date.year)
        results_by_year[year][result.status] += 1
        if result.status == "UNMATCHED" and "-M-DC-" in tml.match_id:
            davis_cup_unmatched += 1
        rows.append({
            "tml_match_id": tml.match_id,
            "tml_match_date": tml.match_date.isoformat(),
            "player_a_name": tml.player_a_name,
            "player_b_name": tml.player_b_name,
            "linkage_status": result.status,
            "matched_market_id": result.matched_market_id,
            "ambiguous_market_ids": "|".join(result.ambiguous_market_ids) if result.ambiguous_market_ids else "",
        })

    out_df = pd.DataFrame(rows)
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    out_df.to_csv(OUTPUT_PATH, index=False)
    print(f"Wrote {len(out_df)} linkage rows to {OUTPUT_PATH}")

    print("\n=== Coverage by year ===")
    total = {"MATCHED": 0, "AMBIGUOUS": 0, "UNMATCHED": 0}
    for year in sorted(results_by_year):
        r = results_by_year[year]
        n = sum(r.values())
        print(f"{year}: MATCHED={r['MATCHED']} ({100*r['MATCHED']/n:.1f}%) "
              f"AMBIGUOUS={r['AMBIGUOUS']} ({100*r['AMBIGUOUS']/n:.1f}%) "
              f"UNMATCHED={r['UNMATCHED']} ({100*r['UNMATCHED']/n:.1f}%) -- n={n}")
        for k in total:
            total[k] += r[k]

    grand_n = sum(total.values())
    print(f"\nTOTAL: MATCHED={total['MATCHED']} ({100*total['MATCHED']/grand_n:.2f}%) "
          f"AMBIGUOUS={total['AMBIGUOUS']} ({100*total['AMBIGUOUS']/grand_n:.2f}%) "
          f"UNMATCHED={total['UNMATCHED']} ({100*total['UNMATCHED']/grand_n:.2f}%) -- n={grand_n}")
    print(f"Of UNMATCHED, Davis Cup ties: {davis_cup_unmatched} / {total['UNMATCHED']}")


if __name__ == "__main__":
    main()
