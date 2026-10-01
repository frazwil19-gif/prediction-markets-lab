"""Guarded ONE-SHOT opener for the sealed V2-4 Football Double Chance holdout (2026/27 Aug-Dec, E0/E1/SC0).

Mirrors the tennis/NBA opener discipline (scripts/run_v2_1_tennis_holdout.py). It REFUSES unless ALL hold:
  1. today (UTC) >= the spec's open_not_before (2027-01-03);
  2. HOLDOUT_SPEC.json matches its committed SHA-256 (HOLDOUT_SPEC.sha256);
  3. HOLDOUT_RESULTS.json does not exist (opened once only; the file is also the no-peek guard's "opened" marker);
  4. the three raw Football-Data 2026/27 CSVs are supplied locally (their SHA-256 is recorded in the results).
It then applies exactly the frozen estimator of the spec (per-book multiplicative de-vig of B365/BW/PS CLOSING odds,
mean consensus, renormalised; DC = pairwise sums; no fitting) to matches dated date_from..date_to, and evaluates the
spec's pass criteria with the V2-4 functions (calibration slope 1000-bootstrap CI clustered by match; bands n>=200
inside 99.5% Wilson; >=80% best-selection share >=15%).

Usage (NOT before 2027-01-03):  python scripts/open_dc_holdout.py --data-dir <dir containing E0.csv E1.csv SC0.csv>
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import sys
from datetime import date, datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

REPO = Path(__file__).resolve().parents[1]
DC_DIR = REPO / "research/platform_v2/double_chance"
SPEC, SPEC_HASH, RESULTS = DC_DIR / "HOLDOUT_SPEC.json", DC_DIR / "HOLDOUT_SPEC.sha256", DC_DIR / "HOLDOUT_RESULTS.json"
PRIMARY_BOOKS = ("B365", "BW", "PS")
RESULT_IDX = {"H": 0, "D": 1, "A": 2}
SEED = 20270103


class Refused(SystemExit):
    pass


def check_guards(spec_path: Path, hash_path: Path, results_path: Path, today: date) -> dict:
    if results_path.exists():
        raise Refused("REFUSED: DC holdout already opened once (HOLDOUT_RESULTS.json exists).")
    if not spec_path.exists() or not hash_path.exists() or \
            hashlib.sha256(spec_path.read_bytes()).hexdigest() != hash_path.read_text().split()[0]:
        raise Refused("REFUSED: HOLDOUT_SPEC.json missing or does not match its frozen hash.")
    spec = json.loads(spec_path.read_text())
    if today < date.fromisoformat(spec["open_not_before"]):
        raise Refused(f"REFUSED: not before {spec['open_not_before']} (today {today.isoformat()}).")
    return spec


def parse_fd_date(s: str) -> date | None:
    for fmt in ("%d/%m/%Y", "%d/%m/%y"):
        try:
            return datetime.strptime(s.strip(), fmt).date()
        except ValueError:
            continue
    return None


def load_matches(data_dir: Path, spec: dict) -> tuple[pd.DataFrame, dict[str, str]]:
    lo, hi = date.fromisoformat(spec["date_from"]), date.fromisoformat(spec["date_to"])
    rows, shas = [], {}
    for code in spec["competitions"]:
        path = data_dir / f"{code}.csv"
        if not path.exists():
            raise Refused(f"REFUSED: raw file {path} not supplied.")
        shas[code] = hashlib.sha256(path.read_bytes()).hexdigest()
        with path.open(encoding="utf-8-sig") as f:
            for row in csv.DictReader(f):
                d = parse_fd_date(row.get("Date", ""))
                if d is None or not lo <= d <= hi or row.get("FTR") not in RESULT_IDX:
                    continue
                try:
                    books = [[float(row[f"{bk}C{o}"]) for o in "HDA"] for bk in PRIMARY_BOOKS]
                except (KeyError, ValueError):
                    continue
                if any(x <= 1.0 for bk in books for x in bk):
                    continue
                rows.append((f"{code}_2026_27_{row['Date']}_{row['HomeTeam']}_{row['AwayTeam']}", "2026_27",
                             RESULT_IDX[row["FTR"]], books))
    return pd.DataFrame(rows, columns=["match_id", "season", "outcome", "books"]), shas


def evaluate(df: pd.DataFrame) -> dict:
    sys.path.insert(0, str(REPO / "scripts"))
    import run_v2_4_double_chance_study as S  # frozen V2-4 functions (frame/events/calib/band_check)
    from prediction_markets_lab.research import probability_reliability as rel

    S.competition_of = lambda ids: ids.map(lambda x: str(x).split("_")[0])   # 2026/27 ids carry the competition code
    f = S.frame(df, "multiplicative")
    p, w, g = S.events(f)
    calib = S.calib(p, w, g, np.random.default_rng(SEED))
    bands_all = S.band_check(rel.band_table(p, w))
    bands_best = S.band_check(rel.band_table(f.best_p.to_numpy(), f.best_won.to_numpy()))
    share80 = float((f.best_p >= 0.8).mean()) if len(f) else 0.0
    passed = bool(calib["slope_ci_includes_1"] and all(b["inside"] for b in bands_all + bands_best) and share80 >= 0.15)
    return {"matches": int(len(f)), "events": int(len(p)), "calibration_all_events": calib,
            "bands_n200_check_all_events": bands_all, "bands_n200_check_best_selection": bands_best,
            "ge80_best_selection_share": share80, "passed": passed}


def main(argv: list[str] | None = None, today: date | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--data-dir", type=Path, required=True)
    a = ap.parse_args(argv)
    spec = check_guards(SPEC, SPEC_HASH, RESULTS, today or datetime.now(timezone.utc).date())
    df, shas = load_matches(a.data_dir, spec)
    res = {"opened_at": datetime.now(timezone.utc).isoformat(), "spec_sha256": SPEC_HASH.read_text().split()[0],
           "raw_file_sha256": shas, **evaluate(df)}
    RESULTS.write_text(json.dumps(res, indent=1, default=float))   # also flips the no-peek guard to OPENED
    print(json.dumps({k: res[k] for k in ("matches", "ge80_best_selection_share", "passed")}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
