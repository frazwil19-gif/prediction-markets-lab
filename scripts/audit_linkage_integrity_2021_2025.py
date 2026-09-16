"""Outcome-blind linkage-integrity audit of the frozen 2021-2025 Betfair<->TML
match linkage (Workstream B historical scale-up, Phase 2 gate, 2026-09-16).

Per the operator's explicit instruction, this MUST run and pass BEFORE any
2021-2025 outcome/market-edge data is opened or inspected:

    "Audit linkage accuracy by tournament-date-distance band, especially:
    0-2 days / 3-7 days / 8-10 days / 11-14 days ... Check player pair,
    tournament identity, market identity, round if available, and whether
    there are competing plausible markets ... If the 11-14 day group
    remains clean, freeze the linkage algorithm. Do not modify it once
    outcomes are opened."

This script is deliberately OUTCOME-BLIND: it never reads outcome_a_won,
never reads who won any match, and never uses any result to decide
anything. Every check here uses only pre-match, structural information
that is public before a ball is struck:
  - the TML round label (R32, R16, ... -- part of the published draw, not
    a result of the specific match being audited)
  - the TML tourney_date (published before the tournament starts)
  - the Betfair market's own scheduled date (from final_market_time)
  - which OTHER Betfair markets exist between the same two named players
    (a structural fact about the corpus, not an outcome)

Three checks, per date-distance band (0-2 / 3-7 / 8-10 / 11-14 days):

  1. Round-chronology consistency: within each tourney_id, do earlier
     rounds (by the published draw) have earlier-or-equal Betfair market
     dates than later rounds? A violation (a "final" market dated before
     an "R32" market in the same tournament) is structurally impossible
     if the two are correctly linked to the real matches they claim to
     be -- so a violation flags a probable false link on at least one of
     the two matches involved.

  2. Competing-candidate risk: for each MATCHED row, look at every OTHER
     usable MATCH_ODDS market between the same two named players anywhere
     in the whole 2021-2025 corpus (not just within the 14-day window),
     and find the closest one in date. If that nearest "other" candidate
     is itself close to the 14-day tolerance boundary, the match could
     easily have been AMBIGUOUS under a marginally different tolerance --
     this is a proxy for "how much of a coincidence was this specific
     link", reported by band.

  3. Sign check: a Betfair market dated BEFORE the tournament's own
     published start date is structurally suspicious (no match should be
     playable before the tournament begins) -- reported regardless of band.

Reads only already-produced, already-committed artifacts:
  - data/interim/workstream_b_2021_2025_linkage.csv (frozen linkage output)
  - data/processed/tennis/cycle_002_canonical_matches.csv (round/tourney_id)
  - ~/betfair_2021_2025_index/markets_*.parquet (market dates, for both the
    matched market and every other candidate sharing a name pair)

Writes no outcome statistic of any kind.
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

from prediction_markets_lab.normalisation.tennis_betfair_linkage import _fold  # noqa: E402

INDEX_DIR = Path.home() / "betfair_2021_2025_index"
CANONICAL_PATH = REPO_ROOT / "data" / "processed" / "tennis" / "cycle_002_canonical_matches.csv"
LINKAGE_PATH = REPO_ROOT / "data" / "interim" / "workstream_b_2021_2025_linkage.csv"
DATE_TOLERANCE_DAYS = 14

BANDS = [(0, 2), (3, 7), (8, 10), (11, 14)]

# Coarse round order for structural chronology checks only -- never used to
# infer or resolve who won anything. RR (round-robin group stage, ATP Finals)
# is placed before the knockout stages that follow it in those events; BR
# (Olympic bronze medal match, 2 real rows) is placed alongside F since both
# are played at the very end of the event.
ROUND_ORDER = {"R128": 0, "R64": 1, "R32": 2, "R16": 3, "RR": 3, "QF": 4, "SF": 5, "F": 6, "BR": 6}


def band_for(distance_days: int) -> str:
    d = abs(distance_days)
    for lo, hi in BANDS:
        if lo <= d <= hi:
            return f"{lo}-{hi}"
    return f"OUT_OF_RANGE({d})"


def load_market_dates() -> dict[str, date]:
    """market_id -> scheduled date, for every MATCH_ODDS market (usable or
    not) so we can look up both the matched market and any other candidate."""
    dataset = ds.dataset(sorted(INDEX_DIR.glob("markets_*.parquet")), format="parquet")
    table = dataset.to_table(columns=["market_id", "market_type", "final_market_time", "runner_names", "n_price_points"])
    df = table.to_pandas()
    df = df[(df["market_type"] == "MATCH_ODDS") & (df["n_price_points"] > 0)].copy()
    out = {}
    for row in df.itertuples(index=False):
        try:
            d = datetime.fromisoformat(row.final_market_time).date()
        except (ValueError, TypeError):
            continue
        out[row.market_id] = d
    return out, df


def build_pair_date_index(df: pd.DataFrame) -> dict[frozenset, list[date]]:
    """name-pair (folded) -> sorted list of every usable MATCH_ODDS market
    date for that pair, anywhere in 2021-2025 -- used only to measure how
    close the NEAREST OTHER candidate is, never to pick a winner."""
    idx: dict[frozenset, list[date]] = defaultdict(list)
    for row in df.itertuples(index=False):
        names = list(row.runner_names)
        if len(names) != 2 or any(n is None for n in names):
            continue
        try:
            d = datetime.fromisoformat(row.final_market_time).date()
        except (ValueError, TypeError):
            continue
        key = frozenset({_fold(names[0]), _fold(names[1])})
        idx[key].append(d)
    for key in idx:
        idx[key].sort()
    return idx


def main():
    linkage = pd.read_csv(LINKAGE_PATH, dtype={"tml_match_id": str, "matched_market_id": str})
    matched = linkage[linkage["linkage_status"] == "MATCHED"].copy()
    print(f"Loaded {len(linkage)} linkage rows; {len(matched)} MATCHED to audit")

    canonical = pd.read_csv(CANONICAL_PATH, dtype={"tourney_date": str})
    canonical = canonical.set_index("match_id")

    market_dates, mo_df = load_market_dates()
    pair_date_index = build_pair_date_index(mo_df)

    # --- Assemble one row per MATCHED link with everything needed ---
    records = []
    missing_canonical = 0
    missing_market_date = 0
    for row in matched.itertuples(index=False):
        if row.tml_match_id not in canonical.index:
            missing_canonical += 1
            continue
        crow = canonical.loc[row.tml_match_id]
        tourney_date = datetime.strptime(crow["tourney_date"], "%Y%m%d").date()
        betfair_date = market_dates.get(row.matched_market_id)
        if betfair_date is None:
            missing_market_date += 1
            continue
        distance = (betfair_date - tourney_date).days
        records.append({
            "tml_match_id": row.tml_match_id,
            "tourney_id": crow["tourney_id"],
            "round": crow["round"],
            "tourney_date": tourney_date,
            "betfair_date": betfair_date,
            "distance_days": distance,
            "band": band_for(distance),
            "player_a_name": row.player_a_name,
            "player_b_name": row.player_b_name,
            "matched_market_id": row.matched_market_id,
        })
    print(f"Assembled {len(records)} auditable rows "
          f"(skipped {missing_canonical} missing-canonical, {missing_market_date} missing-market-date)")

    df = pd.DataFrame(records)

    # === Check 0: sign / structural sanity ===
    negative = df[df["distance_days"] < 0]
    print(f"\n=== Check 0: sign sanity ===")
    print(f"Betfair market dated BEFORE tourney_date (structurally suspicious): "
          f"{len(negative)} / {len(df)} ({100*len(negative)/len(df):.2f}%)")
    if len(negative) > 0:
        print("Distribution of negative distances:")
        print(negative["distance_days"].value_counts().sort_index())

    # === Check 1: round-chronology consistency, by band ===
    print(f"\n=== Check 1: round-chronology consistency (outcome-blind) ===")
    band_violations = defaultdict(int)
    band_pairs_checked = defaultdict(int)
    violation_examples = []

    for tourney_id, group in df.groupby("tourney_id"):
        rows = group.to_dict("records")
        if len(rows) < 2:
            continue
        for i in range(len(rows)):
            for j in range(i + 1, len(rows)):
                r1, r2 = rows[i], rows[j]
                o1, o2 = ROUND_ORDER.get(r1["round"]), ROUND_ORDER.get(r2["round"])
                if o1 is None or o2 is None or o1 == o2:
                    continue
                early, late = (r1, r2) if o1 < o2 else (r2, r1)
                # Attribute the check to the LATER match's band (the one
                # more likely to be the fragile/ambiguous link, since the
                # earlier rounds in a tournament are denser and easier).
                band = late["band"]
                band_pairs_checked[band] += 1
                if early["betfair_date"] > late["betfair_date"]:
                    band_violations[band] += 1
                    if len(violation_examples) < 15:
                        violation_examples.append((tourney_id, early["round"], early["betfair_date"],
                                                    late["round"], late["betfair_date"]))

    for lo, hi in BANDS:
        band = f"{lo}-{hi}"
        checked = band_pairs_checked.get(band, 0)
        viol = band_violations.get(band, 0)
        rate = (100 * viol / checked) if checked else 0.0
        print(f"  band {band:>6} days: {viol}/{checked} round-order violations ({rate:.2f}%)")

    print("\nSample violations (tourney_id, early_round, early_date, late_round, late_date):")
    for ex in violation_examples:
        print(" ", ex)

    # === Check 2: competing-candidate risk, by band ===
    print(f"\n=== Check 2: competing-candidate proximity (outcome-blind) ===")
    print("For each MATCHED link, distance (days) to the NEAREST OTHER usable")
    print("MATCH_ODDS market for the same two named players anywhere in 2021-2025")
    print("(smaller = more fragile; a value <= 14 would mean the wider corpus")
    print("actually contains a second plausible candidate that the 14-day window")
    print("around the WRONG anchor date could have picked up).\n")

    nearest_other_by_band = defaultdict(list)
    near_miss_within_30 = defaultdict(int)
    total_by_band = defaultdict(int)

    for rec in records:
        key = frozenset({_fold(rec["player_a_name"]), _fold(rec["player_b_name"])})
        all_dates = pair_date_index.get(key, [])
        other_dates = [d for d in all_dates if d != rec["betfair_date"]]
        if not other_dates:
            nearest = None
        else:
            nearest = min(abs((d - rec["betfair_date"]).days) for d in other_dates)
        band = rec["band"]
        total_by_band[band] += 1
        if nearest is not None:
            nearest_other_by_band[band].append(nearest)
            if nearest <= 30:
                near_miss_within_30[band] += 1

    for lo, hi in BANDS:
        band = f"{lo}-{hi}"
        vals = nearest_other_by_band.get(band, [])
        n_total = total_by_band.get(band, 0)
        n_any_other = len(vals)
        n_near = near_miss_within_30.get(band, 0)
        median_nearest = sorted(vals)[len(vals)//2] if vals else None
        print(f"  band {band:>6} days: n={n_total}, {n_any_other} have >=1 other same-pair market anywhere in corpus; "
              f"{n_near} ({100*n_near/n_total:.2f}% of band) have one within 30 days; "
              f"median nearest-other-distance among those with any = {median_nearest}")

    # === Summary ===
    print(f"\n=== Band sizes ===")
    print(df["band"].value_counts().sort_index())

    df.to_csv(REPO_ROOT / "data" / "interim" / "workstream_b_linkage_integrity_audit_rows.csv", index=False)
    print(f"\nWrote per-row audit detail to data/interim/workstream_b_linkage_integrity_audit_rows.csv")


if __name__ == "__main__":
    main()
