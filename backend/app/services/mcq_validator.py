"""MCQ self-validation — implements PRD FR-3.5, a hard gate (not a warning).

Any MCQ whose correct_answer doesn't exactly match one of its own options is
dropped before the user ever sees it. This is also enforced at the database
level for v2 (see /db/schema.sql: correct_index_in_range CHECK constraint) —
defense in depth, per data-model.md Section 5.
"""


def validate_and_filter_mcqs(mcqs: list[dict]) -> list[dict]:
    valid_mcqs = []
    for mcq in mcqs:
        options = mcq.get("options", [])
        if mcq.get("correct_answer") in options:
            valid_mcqs.append(mcq)
    return valid_mcqs
