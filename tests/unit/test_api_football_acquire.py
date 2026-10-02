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


def test_per_fixture_loop_stops_on_allowance_and_resumes(tmp_path, monkeypatch):
    monkeypatch.setattr(A, "OUT", tmp_path)
    monkeypatch.setattr(A, "SEASONS", (2022,))
    monkeypatch.setattr(A, "PAUSE_SECONDS", 0)
    monkeypatch.setenv("API_FOOTBALL_KEY", "SECRET")
    fixtures = [{"fixture": {"id": i, "date": "2022-08-05T19:00:00+00:00"}, "teams": {"home": {"id": 1}, "away": {"id": 2}}} for i in range(4)]
    A.save(tmp_path / "raw" / "fixtures_39_2022.json.gz", {"results": 4, "response": fixtures})
    remaining = iter([6, 4, 50, 50])
    calls = []

    def fake_get(path, key):
        calls.append(path)
        return {"response": []}, {"x-ratelimit-requests-remaining": str(next(remaining))}
    monkeypatch.setattr(A, "get", fake_get)
    assert A.main() == 0 and len(calls) == 2                     # stopped when remaining < 5
    assert A.main() == 0 and len(calls) == 4                     # resumed: only the 2 missing fixtures fetched
    assert (tmp_path / "player_match.csv.gz").exists()
    assert all("SECRET" not in c for c in calls)
