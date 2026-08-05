from prediction_markets_lab.ingestion.match_identity import (
    DuplicateClassification,
    MatchRow,
    build_match_id,
    classify_duplicate,
)


def test_build_match_id_deterministic():
    id1 = build_match_id("E0", "2024_25", "2024-08-16", "Manchester United", "Fulham")
    id2 = build_match_id("E0", "2024_25", "2024-08-16", "Manchester United", "Fulham")
    assert id1 == id2
    assert len(id1) == 16


def test_build_match_id_differs_for_different_fixtures():
    id1 = build_match_id("E0", "2024_25", "2024-08-16", "Manchester United", "Fulham")
    id2 = build_match_id("E0", "2024_25", "2024-08-16", "Arsenal", "Wolves")
    assert id1 != id2


def test_classify_exact_duplicate():
    a = MatchRow("id1", "2024-08-16", "A", "B", 1, 0, "hash1")
    b = MatchRow("id1", "2024-08-16", "A", "B", 1, 0, "hash1")
    assert classify_duplicate(a, b) == DuplicateClassification.EXACT_DUPLICATE


def test_classify_conflicting_duplicate_different_scores():
    a = MatchRow("id1", "2024-08-16", "A", "B", 1, 0, "hash1")
    b = MatchRow("id1", "2024-08-16", "A", "B", 2, 1, "hash2")
    assert classify_duplicate(a, b) == DuplicateClassification.CONFLICTING_DUPLICATE


def test_classify_possible_reschedule_different_date():
    a = MatchRow("id1", "2024-08-16", "A", "B", 1, 0, "hash1")
    b = MatchRow("id1", "2024-09-01", "A", "B", 1, 0, "hash2")
    assert classify_duplicate(a, b) == DuplicateClassification.POSSIBLE_RESCHEDULE


def test_classify_manual_review_when_ambiguous():
    a = MatchRow("id1", "2024-08-16", "A", "B", 1, 0, "hash1")
    b = MatchRow("id1", "2024-08-16", "A", "B", 1, 0, "hash2")  # same score, diff hash
    assert classify_duplicate(a, b) == DuplicateClassification.MANUAL_REVIEW
