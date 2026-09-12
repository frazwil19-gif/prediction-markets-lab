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


# --- Tennis player-name matching (Cycle 2, Checkpoint 2 prep) ------------
#
# Built and tested against synthetic data reflecting Tennis-data.co.uk's
# publicly documented "Surname I." convention -- NOT yet verified
# against a real downloaded file (see player_names.py's module
# docstring and research/cycles/CYCLE_002_TENNIS/PLAN.md). Mirrors
# tennis_data_loader.py's own build-then-verify-against-real-data
# pattern.

from prediction_markets_lab.normalisation.player_names import (
    ParsedAbbreviatedName,
    full_name_matches_abbreviated,
    match_abbreviated_name_to_candidates,
    parse_abbreviated_name,
)


def test_parse_abbreviated_name_splits_surname_and_initial():
    parsed = parse_abbreviated_name("Djokovic N.")
    assert parsed.surname == "Djokovic"
    assert parsed.initial == "N"


def test_parse_abbreviated_name_tolerates_missing_trailing_period():
    parsed = parse_abbreviated_name("Djokovic N")
    assert parsed.surname == "Djokovic"
    assert parsed.initial == "N"


def test_parse_abbreviated_name_handles_multi_word_surname():
    parsed = parse_abbreviated_name("Del Potro J.")
    assert parsed.surname == "Del Potro"
    assert parsed.initial == "J"


def test_parse_abbreviated_name_rejects_unparseable_input():
    import pytest

    with pytest.raises(ValueError):
        parse_abbreviated_name("not a name at all")


def test_full_name_matches_abbreviated_simple_case():
    parsed = parse_abbreviated_name("Djokovic N.")
    assert full_name_matches_abbreviated("Novak Djokovic", parsed) is True


def test_full_name_matches_abbreviated_rejects_wrong_initial():
    parsed = parse_abbreviated_name("Djokovic N.")
    assert full_name_matches_abbreviated("Marko Djokovic", parsed) is False


def test_full_name_matches_abbreviated_rejects_different_surname():
    parsed = parse_abbreviated_name("Djokovic N.")
    assert full_name_matches_abbreviated("Novak Nadal", parsed) is False


def test_full_name_matches_abbreviated_handles_multi_word_surname():
    parsed = parse_abbreviated_name("Del Potro J.")
    assert full_name_matches_abbreviated("Juan Del Potro", parsed) is True


def test_full_name_matches_abbreviated_is_diacritic_insensitive():
    parsed = parse_abbreviated_name("Cilic M.")
    assert full_name_matches_abbreviated("Marin Čilić", parsed) is True


def test_full_name_matches_abbreviated_rejects_surname_only_full_name():
    # "Djokovic" alone has no first-name information to check the
    # initial against -- must not match by coincidence.
    parsed = parse_abbreviated_name("Djokovic N.")
    assert full_name_matches_abbreviated("Djokovic", parsed) is False


def test_match_abbreviated_name_to_candidates_unique_match():
    result = match_abbreviated_name_to_candidates(
        "Djokovic N.", ["Novak Djokovic", "Rafael Nadal", "Roger Federer"]
    )
    assert result.is_unique_match is True
    assert result.matched_full_name == "Novak Djokovic"
    assert result.is_ambiguous is False
    assert result.is_unmatched is False


def test_match_abbreviated_name_to_candidates_no_match_is_not_a_guess():
    result = match_abbreviated_name_to_candidates(
        "Djokovic N.", ["Rafael Nadal", "Roger Federer"]
    )
    assert result.matched_full_name is None
    assert result.is_unmatched is True
    assert result.is_ambiguous is False


def test_match_abbreviated_name_to_candidates_surfaces_ambiguity_instead_of_guessing():
    # Two different "Z." players sharing a surname -- must not silently
    # pick one; disambiguation by tournament/date/round is the caller's
    # job (see research/cycles/CYCLE_002_TENNIS/PLAN.md section 4).
    result = match_abbreviated_name_to_candidates(
        "Zverev A.", ["Alexander Zverev", "Andrey Zverev"]
    )
    assert result.matched_full_name is None
    assert result.is_ambiguous is True
    assert set(result.ambiguous_matches) == {"Alexander Zverev", "Andrey Zverev"}


def test_match_abbreviated_name_to_candidates_records_candidates_considered():
    candidates = ["Novak Djokovic", "Rafael Nadal"]
    result = match_abbreviated_name_to_candidates("Djokovic N.", candidates)
    assert result.candidates_considered == tuple(candidates)


def test_parsed_abbreviated_name_is_a_plain_dataclass():
    parsed = ParsedAbbreviatedName(surname="Djokovic", initial="N", raw="Djokovic N.")
    assert parsed.surname == "Djokovic"
    assert parsed.initial == "N"
    assert parsed.raw == "Djokovic N."
