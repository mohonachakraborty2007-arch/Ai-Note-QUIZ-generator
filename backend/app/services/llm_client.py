"""LLM API wrapper — implements PRD FR-3.2 (structured JSON generation) and
FR-3.3 (one retry on parse failure before surfacing an error).

Uses Google's Gemini API (free tier, no credit card required).
"""

import json

from google import genai
from google.genai import types

from app.config import get_settings


class LLMGenerationError(Exception):
    """Raised when the LLM fails to return valid JSON even after retrying."""


def generate_structured(system_prompt: str, user_prompt: str, retries: int = 1) -> dict:
    """Calls the LLM and parses its response as JSON.

    Retries once (by default) on a JSON parse failure, per FR-3.3. Raises
    LLMGenerationError if every attempt fails, so the caller can map that to
    a clean user-facing error (see routes/generate.py).
    """
    settings = get_settings()
    client = genai.Client(api_key=settings.gemini_api_key)

    last_error: Exception | None = None

    for attempt in range(retries + 1):
        response = client.models.generate_content(
            model="gemini-3.6-flash",
            contents=user_prompt,
            config=types.GenerateContentConfig(
                system_instruction=system_prompt,
                response_mime_type="application/json",
            ),
        )
        raw_text = response.text
        try:
            return json.loads(raw_text)
        except json.JSONDecodeError as exc:
            last_error = exc
            continue  # one more attempt, per FR-3.3

    raise LLMGenerationError(
        f"LLM did not return valid JSON after {retries + 1} attempt(s): {last_error}"
    )