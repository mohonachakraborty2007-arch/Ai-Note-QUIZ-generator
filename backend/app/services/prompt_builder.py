"""Builds the single structured prompt sent to the LLM — implements PRD
FR-2.2 (language applies to all generated text, not just a UI label) and
FR-3.1 (truncation for oversized lecture text)."""

LANGUAGE_NAMES = {"en": "English", "hi": "Hindi", "bn": "Bengali"}

# NOTE: JSON braces are doubled ({{ }}) because this string is later
# formatted with .format() — the doubled braces are literal braces in the
# output, not format placeholders.
SYSTEM_INSTRUCTIONS_TEMPLATE = """You are an assistant that converts lecture text into revision material for students.

Respond with ONLY valid JSON matching this exact schema — no prose, no markdown code fences, nothing before or after the JSON object:
{{
  "summary": "string",
  "key_points": ["string", "string", ...],
  "mcqs": [
    {{
      "question": "string",
      "options": ["string", "string", "string", "string"],
      "correct_answer": "string — must exactly match one of the strings in options",
      "explanation": "string"
    }}
  ]
}}

Generate between {min_mcqs} and {max_mcqs} multiple-choice questions covering the most
important concepts in the lecture. Write ALL text — summary, key points, questions,
options, and explanations — in {language_name}. Do not mix languages within a field."""


def build_prompt(
    lecture_text: str,
    language_code: str,
    min_mcqs: int,
    max_mcqs: int,
    max_chars: int,
) -> tuple[str, str]:
    """Returns (system_prompt, user_prompt) ready to send to the LLM client."""
    language_name = LANGUAGE_NAMES.get(language_code, "English")
    truncated_text = lecture_text[:max_chars]

    system_prompt = SYSTEM_INSTRUCTIONS_TEMPLATE.format(
        min_mcqs=min_mcqs, max_mcqs=max_mcqs, language_name=language_name
    )
    user_prompt = f"Lecture content:\n\n{truncated_text}"

    return system_prompt, user_prompt
