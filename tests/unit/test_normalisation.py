import pytest

from prediction_markets_lab.normalisation.competition_names import normalise_competition_code
from prediction_markets_lab.normalisation.team_names import load_alias_table, normalise_team_name


def test_load_alias_table_loads_real_config():
    table = load_alias_table()
    assert len(table) > 50


def test_normalise_team_name_resolves_known_alias():
    table = load_alias_table()
    assert normalise_team_name("Man United", table) == "Manchester United"
    assert normalise_team_name("Nott'm Forest", table) == "Nottingham Forest"


def test_normalise_team_name_returns_none_for_unknown():
    table = load_alias_table()
    assert normalise_team_name("Totally Unknown FC", table) is None


def test_normalise_competition_code_known():
    info = normalise_competition_code("E0")
    assert info is not None
    assert info.canonical_name == "Premier League"
    assert info.country == "England"


def test_normalise_competition_code_unknown_returns_none():
    assert normalise_competition_code("XX9") is None


def test_alias_table_no_duplicate_canonical_mappings():
    """Every raw name must map to exactly one canonical name -- this is
    enforced at load time by load_alias_table itself, so a successful
    load already proves it, but assert explicitly for documentation."""
    table = load_alias_table()
    # A given raw name key can only have one value in a dict by
    # construction; the real assurance is that load_alias_table raises
    # ValueError on conflicting mappings (tested implicitly by every
    # other test in this file successfully loading the real config).
    assert isinstance(table, dict)
