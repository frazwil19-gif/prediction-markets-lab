from datetime import date

import pytest

from prediction_markets_lab.models.football_naive_frequency import (
    NaiveFrequencyMatchInput,
    compute_naive_frequency_predictions,
)


def _match(match_id, comp, d, result):
    return NaiveFrequencyMatchInput(match_id, comp, d, result)


def test_first_match_of_a_competition_uses_laplace_prior():
    matches = [_match("m1", "E0", date(2020, 8, 1), "H")]
    preds = compute_naive_frequency_predictions(matches, laplace_alpha=1.0)
    assert preds[0].n_prior_matches == 0
    assert preds[0].p_home == pytest.approx(1 / 3)
    assert preds[0].p_draw == pytest.approx(1 / 3)
    assert preds[0].p_away == pytest.approx(1 / 3)


def test_probabilities_always_sum_to_one():
    matches = [
        _match("m1", "E0", date(2020, 8, 1), "H"),
        _match("m2", "E0", date(2020, 8, 8), "D"),
        _match("m3", "E0", date(2020, 8, 15), "A"),
        _match("m4", "E0", date(2020, 8, 22), "H"),
    ]
    for pred in compute_naive_frequency_predictions(matches):
        total = pred.p_home + pred.p_draw + pred.p_away
        assert total == pytest.approx(1.0)


def test_probabilities_never_negative_or_above_one():
    matches = [_match(f"m{i}", "E0", date(2020, 8, 1 + i), "H") for i in range(20)]
    for pred in compute_naive_frequency_predictions(matches):
        assert 0.0 <= pred.p_home <= 1.0
        assert 0.0 <= pred.p_draw <= 1.0
        assert 0.0 <= pred.p_away <= 1.0


def test_frequency_shifts_toward_observed_results():
    # Ten home wins in a row should push p_home for the 11th prediction
    # well above the smoothed prior of 1/3.
    matches = [_match(f"m{i}", "E0", date(2020, 8, 1 + i), "H") for i in range(10)]
    matches.append(_match("m10", "E0", date(2020, 8, 11), "D"))
    preds = compute_naive_frequency_predictions(matches)
    assert preds[10].n_prior_matches == 10
    assert preds[10].p_home > 0.8


def test_leakage_a_later_result_never_changes_an_earlier_prediction():
    base = [
        _match("m1", "E0", date(2020, 8, 1), "H"),
        _match("m2", "E0", date(2020, 8, 8), "H"),
        _match("m3", "E0", date(2020, 8, 15), "H"),
    ]
    altered = [
        _match("m1", "E0", date(2020, 8, 1), "H"),
        _match("m2", "E0", date(2020, 8, 8), "H"),
        _match("m3", "E0", date(2020, 8, 15), "A"),  # changed, but this is the LAST match
    ]
    preds_base = compute_naive_frequency_predictions(base)
    preds_altered = compute_naive_frequency_predictions(altered)
    # m1 and m2's predictions must be identical regardless of m3's result,
    # since m3 occurs strictly after both.
    assert preds_base[0] == preds_altered[0]
    assert preds_base[1] == preds_altered[1]


def test_competitions_tracked_independently():
    matches = [
        _match("e1", "E0", date(2020, 8, 1), "H"),
        _match("s1", "SC0", date(2020, 8, 1), "A"),  # SC0 history must not see E0's results
        _match("e2", "E0", date(2020, 8, 8), "H"),
    ]
    preds = compute_naive_frequency_predictions(matches)
    sc0_pred = next(p for p in preds if p.match_id == "s1")
    assert sc0_pred.n_prior_matches == 0
    assert sc0_pred.p_home == pytest.approx(1 / 3)


def test_rejects_out_of_order_matches():
    matches = [
        _match("m1", "E0", date(2020, 8, 15), "H"),
        _match("m2", "E0", date(2020, 8, 1), "D"),  # earlier date, listed second
    ]
    with pytest.raises(ValueError, match="chronologically"):
        compute_naive_frequency_predictions(matches)


def test_rejects_invalid_result_code():
    matches = [_match("m1", "E0", date(2020, 8, 1), "X")]
    with pytest.raises(ValueError, match="full_time_result"):
        compute_naive_frequency_predictions(matches)


def test_rejects_empty_input():
    with pytest.raises(ValueError):
        compute_naive_frequency_predictions([])


def test_deterministic_given_same_input():
    matches = [
        _match("m1", "E0", date(2020, 8, 1), "H"),
        _match("m2", "E0", date(2020, 8, 8), "D"),
    ]
    assert compute_naive_frequency_predictions(matches) == compute_naive_frequency_predictions(matches)
