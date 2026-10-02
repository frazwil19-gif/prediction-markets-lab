"""Fit corners-A-1.0 (pre-registered: research/platform_v2/corners_abc/PREREGISTRATION.md §1).

Frozen Model A specification (props_c1/corners/model_a/FROZEN_SPEC.json) refit ONCE on all Matches.csv data before
2026-07-01. Writes research/platform_v2/corners_abc/corners_A_v1_params.json. Reuses the frozen script's functions
unchanged (imported, not copied).
Usage: python scripts/corners_a_fit_v1.py <Matches.csv>
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

REPO = Path(__file__).resolve().parents[1]
OUT = REPO / "research/platform_v2/corners_abc/corners_A_v1_params.json"
TRAIN_END = pd.Timestamp("2026-07-01")
VERSION = "corners-A-1.0"


def frozen():
    spec = importlib.util.spec_from_file_location("cma_frozen", REPO / "scripts/corners_model_a.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def main(path: str) -> int:
    M = frozen()
    fs = json.loads((REPO / "research/platform_v2/props_c1/corners/model_a/FROZEN_SPEC.json").read_text())
    assert fs["family"] == "MA4", "corners-A-1.0 is defined for the frozen MA4 family"
    ev = M.build(path)
    tr = ev[ev.MatchDate < TRAIN_END]
    out = {"version": VERSION, "family": fs["family"], "groups": fs["selected_groups"],
           "columns": {g: M.GROUPS[g] for g in fs["selected_groups"]}, "train_end": str(TRAIN_END.date()), "n_train": int(len(tr)),
           "frozen_spec_sha256": hashlib.sha256((REPO / "research/platform_v2/props_c1/corners/model_a/FROZEN_SPEC.json").read_bytes()).hexdigest(),
           "constants": {"MINP": M.MINP, "LEAGUE_WIN": M.LEAGUE_WIN, "LEAGUE_MINP": M.LEAGUE_MINP, "MC_DRAWS": M.MC_DRAWS,
                         "MC_SEED": M.MC_SEED, "MC_MIX": M.MC_MIX, "GRID_MAX": int(M.GRID[-1]), "log_floor": 0.05},
           "sides": {}}
    rng = np.random.default_rng(M.MC_SEED)
    z = {}
    for side, col, base in (("H", "HomeCorners", "lm_H"), ("A", "AwayCorners", "lm_A")):
        X = M.design(tr, fs["selected_groups"], base)
        y = tr[col].to_numpy(float)
        b = M.poisson_fit(X, y)
        mu = np.exp(X @ b)
        al = M.nb_alpha(y, mu)
        z[side] = M.pit_normal(y, mu, al, rng)
        out["sides"][side] = {"base": base, "coef": [float(v) for v in b], "alpha": al,
                              "design": ["intercept", f"log({base})"] + [f"log({c})" for g in fs["selected_groups"] for c in M.GROUPS[g]]}
    out["rho"] = float(np.corrcoef(z["H"], z["A"])[0, 1])
    OUT.write_text(json.dumps(out, indent=1) + "\n")
    print(json.dumps(out, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1]))
