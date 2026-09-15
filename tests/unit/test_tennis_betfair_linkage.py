from datetime import date

import pytest

from prediction_markets_lab.normalisation.tennis_betfair_linkage import (
    BetfairEventCandidate,
    TMLMatchRecord,
    classify_all,
    classify_tennis_betfair_match,
    names_are_equivalent,
)


# --- names_are_equivalent: the three supported conventions ---

def test_exact_full_name_match():
    assert names_are_equivalent("Novak Djokovic", "Novak Djokovic")


def test_exact_full_name_match_is_diacritic_and_case_insensitive():
    assert names_are_equivalent("Novak Djokovic", "novak djokovic")
    assert names_are_equivalent("Novak Djokovic", "Novak Djoković")


def test_abbreviated_surname_initial_convention():
    assert names_are_equivalent("Novak Djokovic", "Djokovic N.")
    assert names_are_equivalent("Novak Djokovic", "Djokovic N")


def test_comma_inverted_convention():
    assert names_are_equivalent("Novak Djokovic", "Djokovic, Novak")


def test_unrelated_names_are_not_equivalent():
    assert not names_are_equivalent("Novak Djokovic", "Rafael Nadal")


def test_no_convention_applies_returns_false_not_a_guess():
    # Not exact, not "Surname I.", not "Surname, First" -- must not guess.
    assert not names_are_equivalent("Novak Djokovic", "N Djokovic garbled")


# --- classify_tennis_betfair_match ---

def _tml(match_id="m1", d=date(2025, 3, 10), a="Novak Djokovic", b="Rafael Nadal"):
    return TMLMatchRecord(match_id=match_id, match_date=d, player_a_name=a, player_b_name=b)


def _bf(market_id, d, runners):
    return BetfairEventCandidate(market_id=market_id, event_id=f"e_{market_id}", event_open_date=d, runner_names=runners)


def test_matched_when_exactly_one_candidate_fits():
    tml = _tml()
    candidates = [_bf("1.1", date(2025, 3, 10), ("Novak Djokovic", "Rafael Nadal"))]
    result = classify_tennis_betfair_match(tml, candidates)
    assert result.status == "MATCHED"
    assert result.matched_market_id == "1.1"


def test_matched_regardless_of_runner_order():
    tml = _tml()
    candidates = [_bf("1.1", date(2025, 3, 10), ("Rafael Nadal", "Novak Djokovic"))]
    result = classify_tennis_betfair_match(tml, candidates)
    assert result.status == "MATCHED"


def test_matched_with_abbreviated_runner_names():
    tml = _tml()
    candidates = [_bf("1.1", date(2025, 3, 10), ("Djokovic N.", "Nadal R."))]
    result = classify_tennis_betfair_match(tml, candidates)
    assert result.status == "MATCHED"


def test_matched_within_date_tolerance_but_not_exact_date():
    tml = _tml(d=date(2025, 3, 10))
    candidates = [_bf("1.1", date(2025, 3, 11), ("Novak Djokovic", "Rafael Nadal"))]
    result = classify_tennis_betfair_match(tml, candidates, date_tolerance_days=1)
    assert result.status == "MATCHED"


def test_unmatched_outside_date_tolerance():
    tml = _tml(d=date(2025, 3, 10))
    candidates = [_bf("1.1", date(2025, 3, 15), ("Novak Djokovic", "Rafael Nadal"))]
    result = classify_tennis_betfair_match(tml, candidates, date_tolerance_days=1)
    assert result.status == "UNMATCHED"
    assert result.candidates_in_date_window == 0


def test_unmatched_when_players_dont_correspond():
    tml = _tml()
    candidates = [_bf("1.1", date(2025, 3, 10), ("Carlos Alcaraz", "Daniil Medvedev"))]
    result = classify_tennis_betfair_match(tml, candidates)
    assert result.status == "UNMATCHED"
    assert result.candidates_in_date_window == 1  # in window, just not a name match


def test_ambiguous_when_two_candidates_both_fit():
    tml = _tml()
    candidates = [
        _bf("1.1", date(2025, 3, 10), ("Novak Djokovic", "Rafael Nadal")),
        _bf("1.2", date(2025, 3, 10), ("Djokovic N.", "Nadal R.")),  # a genuine duplicate-looking listing
    ]
    result = classify_tennis_betfair_match(tml, candidates)
    assert result.status == "AMBIGUOUS"
    assert result.ambiguous_market_ids == ("1.1", "1.2")
    assert result.matched_market_id is None


def test_never_silently_picks_a_candidate_on_ambiguity():
    # Two structurally distinct real markets on the same day naming the
    # same two players differently must be surfaced, not resolved by
    # picking the first one found.
    tml = _tml()
    candidates = [
        _bf("1.1", date(2025, 3, 10), ("Novak Djokovic", "Rafael Nadal")),
        _bf("2.1", date(2025, 3, 10), ("Novak Djokovic", "Rafael Nadal")),
    ]
    result = classify_tennis_betfair_match(tml, candidates)
    assert result.status == "AMBIGUOUS"


def test_classify_all_groups_by_status():
    matches = [
        _tml(match_id="m1"),
        _tml(match_id="m2", a="Carlos Alcaraz", b="Daniil Medvedev"),
    ]
    candidates = [_bf("1.1", date(2025, 3, 10), ("Novak Djokovic", "Rafael Nadal"))]
    grouped = classify_all(matches, candidates)
    assert [r.tml_match_id for r in grouped["MATCHED"]] == ["m1"]
    assert [r.tml_match_id for r in grouped["UNMATCHED"]] == ["m2"]
    assert grouped["AMBIGUOUS"] == []
