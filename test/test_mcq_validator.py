"""Unit tests for services/mcq_validator.py — implementing PRD FR-3.5's
hard validation gate. See testing.md Section 2, 'MCQ Self-Validation' table."""

from app.services.mcq_validator import validate_and_filter_mcqs


def test_valid_mcqs_pass_through_unchanged():
    mcqs = [
        {
            "question": "What is the first law of thermodynamics?",
            "options": ["Energy is conserved", "Entropy decreases", "Mass is infinite", "Time reverses"],
            "correct_answer": "Energy is conserved",
            "explanation": "Energy cannot be created or destroyed.",
        }
    ]
    result = validate_and_filter_mcqs(mcqs)
    assert result == mcqs


def test_mcq_with_correct_answer_not_in_options_is_dropped():
    """The exact scenario FR-3.5 exists to catch: a hallucinated
    correct_answer that doesn't match any of its own options."""
    mcqs = [
        {
            "question": "Valid question",
            "options": ["A", "B", "C", "D"],
            "correct_answer": "A",
            "explanation": "ok",
        },
        {
            "question": "Hallucinated question",
            "options": ["W", "X", "Y", "Z"],
            "correct_answer": "Not one of the options",
            "explanation": "should be dropped",
        },
    ]
    result = validate_and_filter_mcqs(mcqs)
    assert len(result) == 1
    assert result[0]["question"] == "Valid question"


def test_mcq_with_empty_options_is_dropped():
    mcqs = [
        {"question": "Broken", "options": [], "correct_answer": "anything", "explanation": "x"}
    ]
    result = validate_and_filter_mcqs(mcqs)
    assert result == []


def test_all_mcqs_failing_returns_empty_list_not_an_error():
    """Per architecture.md Section 4: 'a hard gate, not a warning' — the
    function must never raise, even if every MCQ is invalid."""
    mcqs = [
        {"question": "Bad 1", "options": ["A"], "correct_answer": "B", "explanation": "x"},
        {"question": "Bad 2", "options": ["C"], "correct_answer": "D", "explanation": "x"},
    ]
    result = validate_and_filter_mcqs(mcqs)
    assert result == []


def test_empty_input_returns_empty_list():
    assert validate_and_filter_mcqs([]) == []


def test_mcq_missing_correct_answer_key_is_dropped_not_crashed():
    """Defensive case: a malformed LLM response missing an expected key
    should be filtered out, not raise a KeyError."""
    mcqs = [{"question": "Malformed", "options": ["A", "B"], "explanation": "x"}]
    result = validate_and_filter_mcqs(mcqs)
    assert result == []
