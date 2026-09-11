from datetime import date

import pytest

from prediction_markets_lab.validation.leakage_checks import (
    DatedRecord,
    check_chronological_order,
    check_no_test_period_in_development,
    check_rolling_window_uses_only_past_data,
)
from prediction_markets_lab.validation.time_splits import (
    DateRange,
    SplitPlan,
    assign_split,
    validate_test_period_untouched,
)


def make_plan() -> SplitPlan:
    return SplitPlan(
        training=DateRange(date(2020, 8, 1), date(2023, 5, 31)),
        validation=DateRange(date(2023, 8, 1), date(2024, 5, 31)),
        test=DateRange(date(2024, 8, 1), date(2025, 5, 31)),
    )


def test_split_plan_rejects_overlapping_ranges():
    with pytest.raises(ValueError):
        SplitPlan(
            training=DateRange(date(2020, 1, 1), date(2023, 1, 1)),
            validation=DateRange(date(2022, 1, 1), date(2024, 1, 1)),  # overlaps training
            test=DateRange(date(2025, 1, 1), date(2026, 1, 1)),
        )


def test_assign_split_training():
    plan = make_plan()
    assert assign_split(date(2021, 3, 1), plan) == "training"


def test_assign_split_validation():
    plan = make_plan()
    assert assign_split(date(2023, 12, 1), plan) == "validation"


def test_assign_split_test():
    plan = make_plan()
    assert assign_split(date(2024, 12, 1), plan) == "test"


def test_assign_split_gap_returns_none():
    plan = make_plan()
    assert assign_split(date(2023, 6, 15), plan) is None  # summer gap


def test_validate_test_period_untouched_true_before_test_start():
    plan = make_plan()
    assert validate_test_period_untouched(plan, date(2024, 5, 31))


def test_validate_test_period_untouched_false_once_test_touched():
    plan = make_plan()
    assert not validate_test_period_untouched(plan, date(2024, 8, 1))


def test_check_chronological_order_clean():
    records = [
        DatedRecord("a", date(2024, 1, 1)),
        DatedRecord("b", date(2024, 1, 2)),
        DatedRecord("c", date(2024, 1, 2)),  # same date is fine
    ]
    assert check_chronological_order(records) == []


def test_check_chronological_order_detects_violation():
    records = [
        DatedRecord("a", date(2024, 1, 5)),
        DatedRecord("b", date(2024, 1, 2)),
    ]
    violations = check_chronological_order(records)
    assert len(violations) == 1
    assert "out of chronological order" in violations[0]


def test_check_rolling_window_uses_only_past_data_clean():
    violations = check_rolling_window_uses_only_past_data(
        date(2024, 8, 16), [date(2024, 8, 1), date(2024, 8, 10)]
    )
    assert violations == []


def test_check_rolling_window_detects_future_leak():
    violations = check_rolling_window_uses_only_past_data(
        date(2024, 8, 16), [date(2024, 8, 1), date(2024, 8, 20)]
    )
    assert len(violations) == 1
    assert "leak future information" in violations[0]


def test_check_no_test_period_in_development_clean():
    violations = check_no_test_period_in_development(
        [date(2024, 5, 1), date(2024, 5, 15)], test_period_start=date(2024, 8, 1)
    )
    assert violations == []


def test_check_no_test_period_in_development_detects_violation():
    violations = check_no_test_period_in_development(
        [date(2024, 5, 1), date(2024, 9, 1)], test_period_start=date(2024, 8, 1)
    )
    assert len(violations) == 1
    assert "test period has been touched" in violations[0]


from prediction_markets_lab.validation.time_splits import (  # noqa: E402
    WalkForwardFold,
    generate_expanding_walk_forward_folds,
)


def test_generate_expanding_walk_forward_folds_produces_n_minus_1_folds():
    seasons = ["2020_21", "2021_22", "2022_23", "2023_24"]
    folds = generate_expanding_walk_forward_folds(seasons)
    assert len(folds) == 3


def test_generate_expanding_walk_forward_folds_expands_correctly():
    seasons = ["2020_21", "2021_22", "2022_23", "2023_24"]
    folds = generate_expanding_walk_forward_folds(seasons)
    assert folds[0] == WalkForwardFold(
        fold_id="train_through_2020_21_eval_2021_22",
        train_seasons=("2020_21",),
        evaluate_season="2021_22",
    )
    assert folds[1].train_seasons == ("2020_21", "2021_22")
    assert folds[1].evaluate_season == "2022_23"
    assert folds[2].train_seasons == ("2020_21", "2021_22", "2022_23")
    assert folds[2].evaluate_season == "2023_24"


def test_generate_expanding_walk_forward_folds_never_lets_a_season_evaluate_itself():
    seasons = ["2020_21", "2021_22", "2022_23", "2023_24"]
    for fold in generate_expanding_walk_forward_folds(seasons):
        assert fold.evaluate_season not in fold.train_seasons


def test_generate_expanding_walk_forward_folds_rejects_too_few_seasons():
    with pytest.raises(ValueError):
        generate_expanding_walk_forward_folds(["2020_21"])


def test_generate_expanding_walk_forward_folds_rejects_duplicate_seasons():
    with pytest.raises(ValueError):
        generate_expanding_walk_forward_folds(["2020_21", "2021_22", "2020_21"])
