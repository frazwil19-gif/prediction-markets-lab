"""SOT cycle 2 pipeline on synthetic API-Football-shaped files (no real data): gate + develop run end to end, read 2022 only."""
from __future__ import annotations

import gzip
import importlib.util
import json
from pathlib import Path

import numpy as np
import pandas as pd

REPO = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("c2", REPO / "scripts/player_sot_cycle2.py")
C2 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(C2)
TEAMS = [(1, "Arsenal"), (2, "Manchester City"), (3, "Chelsea"), (4, "Nottingham Forest")]


def write(p: Path, obj) -> None:
    with gzip.open(p, "wt", encoding="utf-8") as f:
        json.dump(obj, f)


def synth(tmp: Path) -> tuple[Path, Path]:
    rng = np.random.default_rng(0)
    raw = tmp / "raw"; raw.mkdir()
    fixtures, fd, mid = [], [], 1000
    dates = pd.date_range("2022-08-06", "2023-05-20", freq="7D")
    for i, d in enumerate(dates):
        for h, a in ((0, 1), (2, 3)) if i % 2 else ((1, 2), (3, 0)):
            mid += 1
            (hid, hn), (aid, an) = TEAMS[h], TEAMS[a]
            blocks, tot = [], {}
            for tid, tn in ((hid, hn), (aid, an)):
                players = []
                for k in range(13):
                    pos = "G" if k == 0 else "D" if k < 5 else "M" if k < 9 else "F"
                    sub = k >= 11
                    sot = int(rng.poisson({"G": 0, "D": .2, "M": .5, "F": 1.0}[pos] * (1.3 if tid in (1, 2) else 1)))
                    players.append({"player": {"id": tid * 100 + k, "name": f"p{tid}{k}"},
                                    "statistics": [{"games": {"minutes": 20 if sub else 90, "position": pos, "substitute": sub},
                                                    "shots": {"total": sot + int(rng.poisson(.5)), "on": sot}, "goals": {"total": 0}}]})
                    tot[tid] = tot.get(tid, 0) + sot
                blocks.append({"team": {"id": tid, "name": tn}, "players": players})
            fx = {"fixture": {"id": mid, "date": d.strftime("%Y-%m-%dT15:00:00+00:00")}, "teams": {"home": {"id": hid, "name": hn}, "away": {"id": aid, "name": an}}}
            write(raw / f"players_2022_{mid}.json.gz", {**fx, "players": blocks})
            fixtures.append(fx)
            fd.append({"Division": "E0", "MatchDate": d.date(), "HomeTeam": C2.FD_NAME.get(hn, hn), "AwayTeam": C2.FD_NAME.get(an, an),
                       "HomeTarget": tot[hid], "AwayTarget": tot[aid]})
    write(raw / "fixtures_39_2022.json.gz", {"response": fixtures})
    write(raw / "players_2023_9.json.gz", {"poison": True})          # holdout-season file must never be read
    m = tmp / "Matches.csv"
    pd.DataFrame(fd).to_csv(m, index=False)
    return raw, m


def test_gate_and_develop_on_synthetic(tmp_path, monkeypatch):
    raw, m = synth(tmp_path)
    g = C2.gate(raw, str(m))
    assert g["verdict"] == "PASS" and g["checks"]["team_sot_ratio_api_over_fd"] == 1.0 and g["checks"]["fd_matched_fixture_share"] == 1.0
    res, spec_ = C2.develop(raw)
    assert spec_["structure"] in ("S1", "S2", "S3") and spec_["comparator"] in ("B0", "B1", "B2")
    assert res["n_train"] > 0 and res["n_dev"] > 0 and set(res["targets"]) == {"sot_1plus", "sot_2plus"}
