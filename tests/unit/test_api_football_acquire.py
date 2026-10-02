"""API-Football acquisition: parser on a synthetic response, no key leakage, private output path."""
from __future__ import annotations

import importlib.util
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("afa", REPO / "scripts/api_football_acquire.py")
A = importlib.util.module_from_spec(spec)
spec.loader.exec_module(A)


def test_rows_from_fixture():
    fx = {"fixture": {"id": 9, "date": "2022-08-05T19:00:00+00:00"}, "teams": {"home": {"id": 1}, "away": {"id": 2}},
          "players": [{"team": {"id": 1}, "players": [
              {"player": {"id": 10, "name": "A"}, "statistics": [{"games": {"minutes": 90, "position": "F", "substitute": False},
                                                                   "shots": {"total": 3, "on": 2}, "goals": {"total": 1}}]},
              {"player": {"id": 11, "name": "B"}, "statistics": [{"games": {"minutes": 20, "position": "M", "substitute": True},
                                                                   "shots": {"total": None, "on": None}, "goals": {"total": None}}]},
              {"player": {"id": 12, "name": "C"}, "statistics": [{"games": {"minutes": None, "position": "D", "substitute": True}}]}]}]}
    rows = A.rows_from_fixture(fx, 2022)
    assert [(r["player_id"], r["starter"], r["minutes"], r["sot"], r["role"]) for r in rows] == [(10, True, 90, 2, "FW"), (11, False, 20, 0, "MD")]
    assert rows[0]["opponent_id"] == 2 and rows[0]["season"] == "2022-23" and rows[0]["home"] is True


def test_private_output_is_gitignored_and_key_never_in_source_paths():
    assert "data/private/" in (REPO / ".gitignore").read_text()
    assert A.OUT.relative_to(REPO).as_posix().startswith("data/private/")
    assert "print(key" not in (REPO / "scripts/api_football_acquire.py").read_text()
