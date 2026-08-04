from pathlib import Path

import pytest

from prediction_markets_lab.research.registry import (
    add_hypothesis,
    load_registry,
    update_hypothesis_status,
)
from prediction_markets_lab.research.schemas import Hypothesis


def make_hypothesis(hypothesis_id="H-0001", **overrides) -> Hypothesis:
    base = dict(
        hypothesis_id=hypothesis_id,
        created_at="2026-08-03T00:00:00+00:00",
        updated_at="2026-08-03T00:00:00+00:00",
        sport="football",
        market_type="pre_match_1x2",
        behaviour_name="test behaviour",
        hypothesis_statement="Some falsifiable claim.",
        economic_or_market_rationale="Some rationale.",
        target_metric="net_ev",
        minimum_observations=50,
    )
    base.update(overrides)
    return Hypothesis(**base)


def test_add_and_load_hypothesis(tmp_path: Path):
    path = tmp_path / "registry.csv"
    add_hypothesis(path, make_hypothesis())
    loaded = load_registry(path)
    assert len(loaded) == 1
    assert loaded[0].hypothesis_id == "H-0001"


def test_add_rejects_duplicate_id(tmp_path: Path):
    path = tmp_path / "registry.csv"
    add_hypothesis(path, make_hypothesis("H-0001"))
    with pytest.raises(ValueError, match="already exists"):
        add_hypothesis(path, make_hypothesis("H-0001"))


def test_update_status_allowed_transition(tmp_path: Path):
    path = tmp_path / "registry.csv"
    add_hypothesis(path, make_hypothesis("H-0001"))
    updated = update_hypothesis_status(path, "H-0001", "DEFINED")
    assert updated.status == "DEFINED"

    loaded = load_registry(path)
    assert loaded[0].status == "DEFINED"


def test_update_status_rejects_disallowed_transition(tmp_path: Path):
    path = tmp_path / "registry.csv"
    add_hypothesis(path, make_hypothesis("H-0001"))
    with pytest.raises(ValueError, match="cannot move"):
        update_hypothesis_status(path, "H-0001", "VALIDATED")


def test_update_status_rejects_missing_id(tmp_path: Path):
    path = tmp_path / "registry.csv"
    add_hypothesis(path, make_hypothesis("H-0001"))
    with pytest.raises(ValueError, match="not found"):
        update_hypothesis_status(path, "H-9999", "DEFINED")


def test_load_registry_returns_empty_for_missing_file(tmp_path: Path):
    assert load_registry(tmp_path / "missing.csv") == []
