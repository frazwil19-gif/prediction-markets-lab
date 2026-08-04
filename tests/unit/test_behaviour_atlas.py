from pathlib import Path

import pytest

from prediction_markets_lab.research.behaviour_atlas import (
    add_behaviour,
    load_atlas,
    update_behaviour_status,
)
from prediction_markets_lab.research.schemas import Behaviour


def make_behaviour(behaviour_id="B-0001", **overrides) -> Behaviour:
    base = dict(
        behaviour_id=behaviour_id,
        behaviour_name="test behaviour",
        sport="football",
        market_type="pre_match_1x2",
        definition="Some precisely defined pattern.",
    )
    base.update(overrides)
    return Behaviour(**base)


def test_add_and_load_behaviour(tmp_path: Path):
    path = tmp_path / "atlas.csv"
    add_behaviour(path, make_behaviour())
    loaded = load_atlas(path)
    assert len(loaded) == 1
    assert loaded[0].behaviour_id == "B-0001"


def test_add_rejects_duplicate_id(tmp_path: Path):
    path = tmp_path / "atlas.csv"
    add_behaviour(path, make_behaviour("B-0001"))
    with pytest.raises(ValueError, match="already exists"):
        add_behaviour(path, make_behaviour("B-0001"))


def test_update_status_allowed_transition(tmp_path: Path):
    path = tmp_path / "atlas.csv"
    add_behaviour(path, make_behaviour("B-0001"))
    updated = update_behaviour_status(path, "B-0001", "TESTING")
    assert updated.status == "TESTING"


def test_update_status_rejects_disallowed_transition(tmp_path: Path):
    path = tmp_path / "atlas.csv"
    add_behaviour(path, make_behaviour("B-0001"))
    with pytest.raises(ValueError, match="cannot move"):
        update_behaviour_status(path, "B-0001", "MONITORING")


def test_load_atlas_returns_empty_for_missing_file(tmp_path: Path):
    assert load_atlas(tmp_path / "missing.csv") == []
